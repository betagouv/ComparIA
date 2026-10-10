"""
Unit tests for the input-character budgets (no network, no real Redis).

Four budgets run at once: pricey models and the whole pool, each counted per
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

import backend.arena.session as session
from backend.arena.session import (
    RATELIMIT_ALL_MODELS_INPUT,
    RATELIMIT_PRICEY_MODELS_INPUT_PER_IP,
)
from backend.config import RATELIMIT_PRICEY_MODELS_INPUT
from backend.utils.user import ip_bucket


class FakeRedis:
    """Minimal string-counter stub matching decode_responses=True behaviour.
    Shared with the other arena budget tests.

    `pipelines_that_work` makes every pipeline after that many fail, as when
    Redis drops between two calls."""

    def __init__(self, pipelines_that_work=None):
        self.store: dict[str, int] = {}
        self.ttl: dict[str, int] = {}
        self.pipelines_left = pipelines_that_work

    def set(self, key, value, ex=None, nx=False):
        if nx and key in self.store:
            return None
        self.store[key] = int(value)
        if ex is not None:
            self.ttl[key] = ex
        return True

    def incrby(self, key, amount):
        self.store[key] = self.store.get(key, 0) + amount
        return self.store[key]

    def decrby(self, key, amount):
        return self.incrby(key, -amount)

    def expire(self, key, ttl):
        self.ttl[key] = ttl

    def get(self, key):
        v = self.store.get(key)
        return None if v is None else str(v)

    def pipeline(self):
        return FakePipeline(self)


class FakePipeline:
    """Queues calls and runs them in order on `execute`, as MULTI/EXEC does."""

    def __init__(self, redis):
        self.redis = redis
        self.calls = []

    def __getattr__(self, name):
        def queue(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            return self

        return queue

    def execute(self):
        if self.redis.pipelines_left is not None:
            if self.redis.pipelines_left == 0:
                raise ConnectionError("Redis went away")
            self.redis.pipelines_left -= 1
        results = [
            getattr(self.redis, name)(*args, **kwargs)
            for name, args, kwargs in self.calls
        ]
        self.calls = []
        return results


@contextlib.contextmanager
def fake_redis(fake=None):
    orig = session.get_redis_client
    fake = fake or FakeRedis()
    session.get_redis_client = lambda: fake
    try:
        yield fake
    finally:
        session.get_redis_client = orig


def test_under_threshold_not_limited():
    with fake_redis():
        session.reserve_input_chars(
            "sess-a", "1.1.1.1", RATELIMIT_PRICEY_MODELS_INPUT * 2, pricey=True
        )
        # exactly 2x is not over (check is strictly greater-than)
        assert session.is_ratelimited("sess-a", "1.1.1.1") is False


def test_over_threshold_is_limited():
    with fake_redis():
        session.reserve_input_chars(
            "sess-a", "1.1.1.1", RATELIMIT_PRICEY_MODELS_INPUT * 2 + 1, pricey=True
        )
        assert session.is_ratelimited("sess-a", "1.1.1.1") is True


def test_budget_is_per_session_not_shared():
    with fake_redis():
        # One session blows its budget; a second (same IP, different cookie) is
        # clean, as long as the IP backstop is nowhere near spent.
        session.reserve_input_chars(
            "sess-a", "1.1.1.1", RATELIMIT_PRICEY_MODELS_INPUT * 3, pricey=True
        )
        assert session.is_ratelimited("sess-a", "1.1.1.1") is True
        assert session.is_ratelimited("sess-b", "1.1.1.1") is False


def test_dropping_the_cookie_does_not_reset_the_budget():
    """The point of the IP backstop: a fresh session every request used to buy a
    fresh budget every request."""
    with fake_redis():
        spent = 0
        n = 0
        while spent <= RATELIMIT_PRICEY_MODELS_INPUT_PER_IP:
            session.reserve_input_chars(
                f"sess-{n}", "1.1.1.1", RATELIMIT_PRICEY_MODELS_INPUT, pricey=True
            )
            spent += RATELIMIT_PRICEY_MODELS_INPUT
            n += 1

        # Every one of those sessions was under its own budget.
        assert session.is_ratelimited("brand-new-session", "1.1.1.1") is True
        # A different IP is untouched.
        assert session.is_ratelimited("brand-new-session", "2.2.2.2") is False


def test_cheap_models_are_counted_too():
    """Only pricey models used to be counted, so everything else was free."""
    with fake_redis():
        session.reserve_input_chars(
            "sess-a", "1.1.1.1", RATELIMIT_ALL_MODELS_INPUT + 1, pricey=False
        )
        assert session.is_ratelimited("sess-a", "1.1.1.1") is True


def test_a_cheap_message_does_not_spend_the_pricey_budget():
    with fake_redis():
        session.reserve_input_chars(
            "sess-a", "1.1.1.1", RATELIMIT_PRICEY_MODELS_INPUT * 3, pricey=False
        )
        assert session.is_ratelimited("sess-a", "1.1.1.1") is False


def test_one_ipv6_subscriber_shares_one_budget():
    """An IPv6 connection usually owns a whole /64, so changing the last bits
    of the address must not buy a fresh budget."""
    with fake_redis():
        session.increment_input_chars(
            "sess-a",
            "2001:db8:1:2::1",
            RATELIMIT_PRICEY_MODELS_INPUT_PER_IP + 1,
            pricey=True,
        )
        assert session.is_ratelimited("sess-b", "2001:db8:1:2:ffff::9") is True
        assert session.is_ratelimited("sess-b", "2001:db8:1:3::1") is False


def test_ip_bucket():
    assert ip_bucket("1.2.3.4") == "1.2.3.4"
    assert ip_bucket("2001:db8:1:2:3:4:5:6") == "2001:db8:1:2::/64"
    assert ip_bucket("::ffff:1.2.3.4") == "1.2.3.4"
    assert ip_bucket("") == ""


def test_unknown_key_not_limited():
    with fake_redis():
        assert session.is_ratelimited("never-seen", "9.9.9.9") is False


def test_a_message_goes_through_while_the_budget_was_not_spent_before_it():
    """The rule the counters always had: the last message may overshoot by its
    own length, and the next one is refused."""
    with fake_redis():
        limit = RATELIMIT_ALL_MODELS_INPUT
        assert session.reserve_input_chars("sess-a", "1.1.1.1", limit, pricey=False)
        assert session.reserve_input_chars("sess-a", "1.1.1.1", 10, pricey=False)
        assert not session.reserve_input_chars("sess-a", "1.1.1.1", 1, pricey=False)


def test_requests_at_the_edge_cannot_all_pass():
    """Each charge reads the total it made, so a burst at the last character of
    the budget lets exactly one message through."""
    with fake_redis() as fake:
        fake.store[session._budget_key("all", "sess-a")] = RATELIMIT_ALL_MODELS_INPUT
        allowed = [
            session.reserve_input_chars("sess-a", "1.1.1.1", 100, pricey=False)
            for _ in range(8)
        ]
        assert allowed == [True] + [False] * 7


def test_a_refused_message_is_charged_nothing():
    with fake_redis() as fake:
        spent = session._budget_key("pricey_ip", "1.1.1.1")
        fake.store[spent] = RATELIMIT_PRICEY_MODELS_INPUT_PER_IP + 1

        assert not session.reserve_input_chars("sess-a", "1.1.1.1", 500, pricey=True)

        assert {k: v for k, v in fake.store.items() if v} == {
            spent: RATELIMIT_PRICEY_MODELS_INPUT_PER_IP + 1
        }
        # The window of the spent budget does not move on a refusal, but the
        # empty counters the refusal created still expire.
        assert spent not in fake.ttl
        assert all(k in fake.ttl for k in fake.store if k != spent)


def test_a_charged_message_restarts_the_window():
    with fake_redis() as fake:
        session.reserve_input_chars("sess-a", "1.1.1.1", 10, pricey=True)
        assert set(fake.ttl) == set(fake.store)
        assert set(fake.ttl.values()) == {session.BUDGET_TTL_SECONDS}


def test_a_counter_expires_even_when_redis_drops_mid_charge():
    """A counter used to get its expiry in a second call. Had Redis failed
    between the two, the IP counters would never expire and that IP would stay
    locked out."""
    with fake_redis(FakeRedis(pipelines_that_work=1)) as fake:
        try:
            session.reserve_input_chars("sess-a", "1.1.1.1", 10, pricey=True)
        except ConnectionError:
            pass
        assert len(fake.store) == 4
        assert set(fake.ttl) == set(fake.store)


def run():
    test_under_threshold_not_limited()
    test_over_threshold_is_limited()
    test_budget_is_per_session_not_shared()
    test_dropping_the_cookie_does_not_reset_the_budget()
    test_cheap_models_are_counted_too()
    test_a_cheap_message_does_not_spend_the_pricey_budget()
    test_one_ipv6_subscriber_shares_one_budget()
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
