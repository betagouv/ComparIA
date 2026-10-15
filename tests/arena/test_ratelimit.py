"""
The model allowances and the cooldowns (no network, no real Redis).

Four allowances run at once: the whole pool, in characters, and the expensive
one, in millionths of a dollar, each counted per anonymous session and per
network. The session one is the one that matters, since people behind a
shared NAT each get their own; the network one is only there to catch a
client that drops the session cookie to get a fresh allowance.

Pytest-free: collects under pytest AND runs directly with
    uv run python tests/arena/test_ratelimit.py
"""

import contextlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from redis.exceptions import ConnectionError as RedisConnectionError

import backend.arena.limits as limits
import backend.arena.session as session
from backend.arena.limits import AllowanceSpent, Identity
from backend.config import RATELIMIT_SENT_WARNINGS_PER_HOUR, settings
from backend.utils.user import ip_bucket
from tests.arena import fakes
from tests.arena.fakes import FakeRedis

# The expensive allowances, in the counters' millionths of a dollar.
EXPENSIVE_PER_SESSION = limits.limit("expensive", "session")
EXPENSIVE_PER_NETWORK = limits.limit("expensive", "network")


@contextlib.contextmanager
def fake_redis(fake=None):
    with fakes.fake_redis(limits, session, fake=fake) as fake:
        yield fake


def charge(session_hash, ip, chars=0, micro_usd=None):
    """Charge one message, True when it may go to the models. `micro_usd` is
    what its expensive model costs, None for a cheap pair."""
    cost = {"all": chars}
    if micro_usd is not None:
        cost["expensive"] = micro_usd
    try:
        limits.reserve(Identity.of(session_hash, ip), cost)
    except AllowanceSpent:
        return False
    return True


def spent(session_hash, ip):
    return bool(limits.read_status(Identity.of(session_hash, ip)).spent)


def test_exactly_the_limit_is_not_spent():
    with fake_redis():
        charge("sess-a", "1.1.1.1", micro_usd=EXPENSIVE_PER_SESSION)
        assert spent("sess-a", "1.1.1.1") is False


def test_past_the_limit_is_spent():
    with fake_redis():
        charge("sess-a", "1.1.1.1", micro_usd=EXPENSIVE_PER_SESSION + 1)
        assert spent("sess-a", "1.1.1.1") is True


def test_an_allowance_is_per_session_not_shared():
    with fake_redis():
        # One session spends its allowance; a second (same IP, other cookie)
        # is clean, as long as the network one is nowhere near spent.
        charge("sess-a", "1.1.1.1", micro_usd=EXPENSIVE_PER_SESSION + 1)
        assert spent("sess-a", "1.1.1.1") is True
        assert spent("sess-b", "1.1.1.1") is False


def test_dropping_the_cookie_does_not_reset_the_allowance():
    """The point of the network allowance: a fresh session every request used
    to buy a fresh allowance every request."""
    with fake_redis():
        total = 0
        n = 0
        while total <= EXPENSIVE_PER_NETWORK:
            charge(f"sess-{n}", "1.1.1.1", micro_usd=EXPENSIVE_PER_SESSION // 2)
            total += EXPENSIVE_PER_SESSION // 2
            n += 1

        # Every one of those sessions was under its own allowance.
        assert spent("brand-new-session", "1.1.1.1") is True
        # A different network is untouched.
        assert spent("brand-new-session", "2.2.2.2") is False


def test_cheap_models_are_counted_too():
    """Only expensive models used to be counted, so everything else was free."""
    with fake_redis():
        charge("sess-a", "1.1.1.1", settings.RATELIMIT_ALL_PER_SESSION + 1)
        assert spent("sess-a", "1.1.1.1") is True


def test_a_cheap_pair_does_not_spend_the_expensive_allowance():
    with fake_redis():
        charge("sess-a", "1.1.1.1", EXPENSIVE_PER_SESSION + 1)
        assert spent("sess-a", "1.1.1.1") is False


def test_one_ipv6_subscriber_shares_one_allowance():
    """An IPv6 connection usually owns a whole /64, so changing the last bits
    of the address must not buy a fresh allowance."""
    with fake_redis():
        charge("sess-a", "2001:db8:1:2::1", micro_usd=EXPENSIVE_PER_NETWORK + 1)
        assert spent("sess-b", "2001:db8:1:2:ffff::9") is True
        assert spent("sess-b", "2001:db8:1:3::1") is False


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


def test_an_unknown_session_has_nothing_spent():
    with fake_redis():
        assert spent("never-seen", "9.9.9.9") is False


def test_a_message_goes_through_while_the_allowance_was_not_spent_before_it():
    """The rule the counters always had: the last message may overshoot by its
    own size, and the next one is refused."""
    with fake_redis():
        limit = settings.RATELIMIT_ALL_PER_SESSION
        assert charge("sess-a", "1.1.1.1", limit)
        assert charge("sess-a", "1.1.1.1", 10)
        assert not charge("sess-a", "1.1.1.1", 1)


def test_requests_at_the_edge_cannot_all_pass():
    """Each charge reads the total it made, so a burst at the last character of
    the allowance lets exactly one message through."""
    with fake_redis() as fake:
        fake.store[limits.budget_key("all", "s:sess-a")] = (
            settings.RATELIMIT_ALL_PER_SESSION
        )
        allowed = [charge("sess-a", "1.1.1.1", 100) for _ in range(8)]
        assert allowed == [True] + [False] * 7


def test_a_refused_message_is_charged_nothing():
    with fake_redis() as fake:
        spent_key = limits.budget_key("expensive", "ip:1.1.1.1")
        fake.set(spent_key, EXPENSIVE_PER_NETWORK + 1, ex=600)

        assert not charge("sess-a", "1.1.1.1", 500, micro_usd=500)

        assert {k: v for k, v in fake.store.items() if v} == {
            spent_key: EXPENSIVE_PER_NETWORK + 1
        }
        # The window of the spent allowance does not move on a refusal, but
        # the empty counters the refusal created still expire.
        assert fake.ttl(spent_key) == 600
        assert all(fake.ttl(k) > 0 for k in fake.store if k != spent_key)


def test_a_first_message_opens_a_two_hour_window():
    with fake_redis() as fake:
        charge("sess-a", "1.1.1.1", 10, micro_usd=10)
        assert {fake.ttl(k) for k in fake.store} == {limits.WINDOW_SECONDS}


def test_a_counter_expires_even_when_redis_drops_mid_charge():
    """A counter used to get its expiry in a second call. Had Redis failed
    between the two, the network counters would never expire and that network
    would stay locked out."""
    with fake_redis(FakeRedis(pipelines_that_work=1)) as fake:
        try:
            charge("sess-a", "1.1.1.1", 10, micro_usd=10)
        except RedisConnectionError:
            pass
        assert len(fake.store) == 4
        assert all(fake.ttl(k) > 0 for k in fake.store)


def run():
    test_exactly_the_limit_is_not_spent()
    test_past_the_limit_is_spent()
    test_an_allowance_is_per_session_not_shared()
    test_dropping_the_cookie_does_not_reset_the_allowance()
    test_cheap_models_are_counted_too()
    test_a_cheap_pair_does_not_spend_the_expensive_allowance()
    test_one_ipv6_subscriber_shares_one_allowance()
    test_warnings_sent_anyway_cool_down_the_session_only()
    test_ip_bucket()
    test_an_unknown_session_has_nothing_spent()
    test_a_message_goes_through_while_the_allowance_was_not_spent_before_it()
    test_requests_at_the_edge_cannot_all_pass()
    test_a_refused_message_is_charged_nothing()
    test_a_first_message_opens_a_two_hour_window()
    test_a_counter_expires_even_when_redis_drops_mid_charge()
    print("All rate limit cases passed.")


if __name__ == "__main__":
    run()
