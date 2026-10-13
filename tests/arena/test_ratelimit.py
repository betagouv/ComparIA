"""
Unit tests for the model allowances (no network, no real Redis).

Four budgets run at once: expensive models and the whole pool, each counted per
anonymous session and per IP. The session budget is the one that matters, since
users behind a shared NAT each get their own; the IP one is only there to catch
a client that drops the session cookie to get a fresh budget.

Pytest-free: collects under pytest AND runs directly with
    uv run python tests/arena/test_ratelimit.py
"""

import contextlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import backend.arena.limits as limits
import backend.arena.session as session
from backend.arena.limits import AllowanceSpent, Identity
from backend.config import RATELIMIT_SENT_WARNINGS_PER_HOUR, settings
from backend.utils.user import ip_bucket
from tests.arena import fakes
from tests.arena.fakes import FakeRedis


@contextlib.contextmanager
def fake_redis(fake=None):
    with fakes.fake_redis(limits, session, fake=fake) as fake:
        yield fake


def reserve_input_chars(key, ip, input_chars, pricey):
    """Charge one message, True when it may go to the models."""
    cost = {"all": input_chars}
    if pricey:
        cost["expensive"] = input_chars
    try:
        limits.reserve(Identity.of(key, ip), cost)
    except AllowanceSpent:
        return False
    return True


def is_ratelimited(key, ip):
    return bool(limits.read_status(Identity.of(key, ip)).spent)


def test_under_threshold_not_limited():
    with fake_redis():
        reserve_input_chars(
            "sess-a", "1.1.1.1", settings.RATELIMIT_EXPENSIVE_PER_SESSION, pricey=True
        )
        # exactly the limit is not over (check is strictly greater-than)
        assert is_ratelimited("sess-a", "1.1.1.1") is False


def test_over_threshold_is_limited():
    with fake_redis():
        reserve_input_chars(
            "sess-a",
            "1.1.1.1",
            settings.RATELIMIT_EXPENSIVE_PER_SESSION + 1,
            pricey=True,
        )
        assert is_ratelimited("sess-a", "1.1.1.1") is True


def test_budget_is_per_session_not_shared():
    with fake_redis():
        # One session blows its budget; a second (same IP, different cookie) is
        # clean, as long as the IP backstop is nowhere near spent.
        reserve_input_chars(
            "sess-a",
            "1.1.1.1",
            settings.RATELIMIT_EXPENSIVE_PER_SESSION + 1,
            pricey=True,
        )
        assert is_ratelimited("sess-a", "1.1.1.1") is True
        assert is_ratelimited("sess-b", "1.1.1.1") is False


def test_dropping_the_cookie_does_not_reset_the_budget():
    """The point of the IP backstop: a fresh session every request used to buy a
    fresh budget every request."""
    with fake_redis():
        spent = 0
        n = 0
        while spent <= settings.RATELIMIT_EXPENSIVE_PER_IP:
            reserve_input_chars(
                f"sess-{n}",
                "1.1.1.1",
                settings.RATELIMIT_EXPENSIVE_PER_SESSION // 2,
                pricey=True,
            )
            spent += settings.RATELIMIT_EXPENSIVE_PER_SESSION // 2
            n += 1

        # Every one of those sessions was under its own budget.
        assert is_ratelimited("brand-new-session", "1.1.1.1") is True
        # A different IP is untouched.
        assert is_ratelimited("brand-new-session", "2.2.2.2") is False


def test_cheap_models_are_counted_too():
    """Only expensive models used to be counted, so everything else was free."""
    with fake_redis():
        reserve_input_chars(
            "sess-a", "1.1.1.1", settings.RATELIMIT_ALL_PER_SESSION + 1, pricey=False
        )
        assert is_ratelimited("sess-a", "1.1.1.1") is True


def test_a_cheap_message_does_not_spend_the_expensive_budget():
    with fake_redis():
        reserve_input_chars(
            "sess-a",
            "1.1.1.1",
            settings.RATELIMIT_EXPENSIVE_PER_SESSION + 1,
            pricey=False,
        )
        assert is_ratelimited("sess-a", "1.1.1.1") is False


def test_one_ipv6_subscriber_shares_one_budget():
    """An IPv6 connection usually owns a whole /64, so changing the last bits
    of the address must not buy a fresh budget."""
    with fake_redis():
        reserve_input_chars(
            "sess-a",
            "2001:db8:1:2::1",
            settings.RATELIMIT_EXPENSIVE_PER_IP + 1,
            pricey=True,
        )
        assert is_ratelimited("sess-b", "2001:db8:1:2:ffff::9") is True
        assert is_ratelimited("sess-b", "2001:db8:1:3::1") is False


def test_warnings_sent_anyway_cool_down_the_session_only():
    with fake_redis():
        for _ in range(RATELIMIT_SENT_WARNINGS_PER_HOUR):
            session.increment_sent_warnings("sess-a")
        assert session.is_warning_cooldown("sess-a") is True
        assert session.is_warning_cooldown("sess-b") is False


def test_ip_bucket():
    assert ip_bucket("1.2.3.4") == "1.2.3.4"
    assert ip_bucket("2001:db8:1:2:3:4:5:6") == "2001:db8:1:2::/64"
    assert ip_bucket("::ffff:1.2.3.4") == "1.2.3.4"
    assert ip_bucket("") == ""


def test_unknown_key_not_limited():
    with fake_redis():
        assert is_ratelimited("never-seen", "9.9.9.9") is False


def test_a_message_goes_through_while_the_budget_was_not_spent_before_it():
    """The rule the counters always had: the last message may overshoot by its
    own length, and the next one is refused."""
    with fake_redis():
        limit = settings.RATELIMIT_ALL_PER_SESSION
        assert reserve_input_chars("sess-a", "1.1.1.1", limit, pricey=False)
        assert reserve_input_chars("sess-a", "1.1.1.1", 10, pricey=False)
        assert not reserve_input_chars("sess-a", "1.1.1.1", 1, pricey=False)


def test_requests_at_the_edge_cannot_all_pass():
    """Each charge reads the total it made, so a burst at the last character of
    the budget lets exactly one message through."""
    with fake_redis() as fake:
        fake.store[limits.budget_key("all", "s:sess-a")] = (
            settings.RATELIMIT_ALL_PER_SESSION
        )
        allowed = [
            reserve_input_chars("sess-a", "1.1.1.1", 100, pricey=False)
            for _ in range(8)
        ]
        assert allowed == [True] + [False] * 7


def test_a_refused_message_is_charged_nothing():
    with fake_redis() as fake:
        spent = limits.budget_key("expensive", "ip:1.1.1.1")
        fake.store[spent] = settings.RATELIMIT_EXPENSIVE_PER_IP + 1

        assert not reserve_input_chars("sess-a", "1.1.1.1", 500, pricey=True)

        assert {k: v for k, v in fake.store.items() if v} == {
            spent: settings.RATELIMIT_EXPENSIVE_PER_IP + 1
        }
        # The window of the spent budget does not move on a refusal, but the
        # empty counters the refusal created still expire.
        assert fake.ttl(spent) == -1
        assert all(fake.ttl(k) > 0 for k in fake.store if k != spent)


def test_a_charged_message_restarts_the_window():
    with fake_redis() as fake:
        reserve_input_chars("sess-a", "1.1.1.1", 10, pricey=True)
        assert {fake.ttl(k) for k in fake.store} == {limits.WINDOW_SECONDS}


def test_a_counter_expires_even_when_redis_drops_mid_charge():
    """A counter used to get its expiry in a second call. Had Redis failed
    between the two, the IP counters would never expire and that IP would stay
    locked out."""
    with fake_redis(FakeRedis(pipelines_that_work=1)) as fake:
        try:
            reserve_input_chars("sess-a", "1.1.1.1", 10, pricey=True)
        except ConnectionError:
            pass
        assert len(fake.store) == 4
        assert all(fake.ttl(k) > 0 for k in fake.store)


def run():
    test_under_threshold_not_limited()
    test_over_threshold_is_limited()
    test_budget_is_per_session_not_shared()
    test_dropping_the_cookie_does_not_reset_the_budget()
    test_cheap_models_are_counted_too()
    test_a_cheap_message_does_not_spend_the_expensive_budget()
    test_one_ipv6_subscriber_shares_one_budget()
    test_warnings_sent_anyway_cool_down_the_session_only()
    test_ip_bucket()
    test_unknown_key_not_limited()
    test_a_message_goes_through_while_the_budget_was_not_spent_before_it()
    test_requests_at_the_edge_cannot_all_pass()
    test_a_refused_message_is_charged_nothing()
    test_a_charged_message_restarts_the_window()
    test_a_counter_expires_even_when_redis_drops_mid_charge()
    print("All rate limit cases passed.")


if __name__ == "__main__":
    run()
