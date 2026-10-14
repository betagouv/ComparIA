"""
The calibration replay charges a stored conversation as the arena does (no
database: the rows are built here).
"""

from datetime import datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from linkup import LinkupSearchTextResult

from backend.arena.web_search import merge_web_search_with_content
from utils.arena.calibrate import Prices, in_setting_unit, propose, replay, round_up

CHEAP, EXPENSIVE = uuid4(), uuid4()
# In dollars per million tokens. At four characters a token, each character
# the expensive model is sent costs a millionth of a dollar, and each one it
# writes three.
PRICES = {CHEAP: Prices(0.4, 1.2), EXPENSIVE: Prices(4.0, 12.0)}
START = datetime(2026, 10, 1, 9, 0)
RESULTS = [
    LinkupSearchTextResult(
        type="text", name="", url="https://a.example", content="x" * 50, favicon=""
    )
]


def turn(comparison_id, at, prompt, a, b, session="s1", ip="10.0.0.1", **extra):
    """A stored turn: `a` and `b` are (content, reasoning, cached) or None."""
    row = dict(
        comparison_id=comparison_id,
        ip=ip,
        anonymous_user_hash=session,
        user_id=None,
        llm_id_a=CHEAP,
        llm_id_b=EXPENSIVE,
        system_a=10,
        system_b=0,
        created_at=at,
        prompt_chars=len(prompt),
        searched=None,
        web_search=None,
        suggested=False,
    )
    for pos, answer in (("a", a), ("b", b)):
        content, reasoning, cached = answer or (0, 0, None)
        row |= {
            f"content_{pos}": content,
            f"reasoning_{pos}": reasoning,
            f"cached_{pos}": cached,
        }
    return SimpleNamespace(**(row | extra))


def test_a_conversation_costs_its_transcript_and_answers_each_turn():
    first = uuid4()
    searched = len(merge_web_search_with_content("Bonjour", RESULTS))
    rows = [
        turn(
            first,
            START,
            "Bonjour",
            (100, 40, False),
            (200, 0, False),
            searched="Bonjour",
            web_search=[result.model_dump() for result in RESULTS],
        ),
        turn(first, START + timedelta(minutes=3), "Encore", (100, 0, False), None),
    ]

    result = replay(rows, PRICES)

    # Turn 1: a is sent its system prompt and the prompt with the search
    # results, b the prompt only. Turn 2 resends all that, the side's answer
    # (not its reasoning) and the new prompt; b failed and wrote nothing.
    sent_a = [10 + searched, 10 + searched + 100 + len("Encore")]
    sent_b = [searched, searched + 200 + len("Encore")]
    all_chars = sum(sent_a) + sum(sent_b) + (100 + 40) + 200 + 100
    expensive = (sent_b[0] + 3 * 200) + sent_b[1]
    assert result.conversations == [{"all": all_chars, "expensive": expensive}]
    assert result.turns == 2
    assert (result.answers, result.cached) == (3, 0)
    assert result.written == [140, 200, 100]


def test_a_cached_answer_is_free_on_the_expensive_pool_only():
    rows = [turn(uuid4(), START, "Bonjour", (100, 0, False), (300, 0, True))]
    [spent] = replay(rows, PRICES).conversations
    assert spent["expensive"] == 0
    assert spent["all"] == 10 + 7 + 100 + 7 + 300


def test_a_window_closes_after_two_quiet_hours():
    rows = [
        turn(uuid4(), START, "a", (10, 0, False), (10, 0, False)),
        turn(uuid4(), START + timedelta(hours=1), "b", (10, 0, False), (10, 0, False)),
        turn(uuid4(), START + timedelta(hours=4), "c", (10, 0, False), (10, 0, False)),
    ]
    result = replay(rows, PRICES)

    # a: system prompt, prompt, answer; b: prompt, answer.
    one_turn = (10 + 1 + 10) + (1 + 10)
    assert result.people["s:s1"].windows("all") == [2 * one_turn, one_turn]
    assert sorted(result.networks["10.0.0.1"].hours("all")) == [one_turn] * 3


def test_a_signed_in_person_counts_on_their_account():
    user_id = uuid4()
    rows = [
        turn(uuid4(), START, "a", None, None, session=None, user_id=user_id),
        turn(uuid4(), START, "b", None, None, session=None),
    ]
    result = replay(rows, PRICES)

    assert list(result.people) == [f"u:{user_id}"]
    assert result.unknown_people == 1


def test_cached_answers_on_suggested_prompts_are_counted_apart():
    suggested = uuid4()
    rows = [
        turn(suggested, START, "a", (10, 0, True), (10, 0, False), suggested=True),
        # Only a first turn counts as a suggested prompt.
        turn(
            suggested,
            START + timedelta(minutes=1),
            "a",
            (10, 0, True),
            (10, 0, True),
            suggested=True,
        ),
        turn(uuid4(), START, "b", (10, 0, True), (10, 0, True)),
    ]
    result = replay(rows, PRICES)

    assert (result.cached, result.answers) == (5, 6)
    assert (result.suggested_cached, result.suggested_answers) == (1, 2)


def test_a_json_null_in_the_search_results_counts_the_prompt_alone():
    rows = [
        turn(uuid4(), START, "Bonjour", None, None, searched="Bonjour", web_search=None)
    ]
    [spent] = replay(rows, PRICES).conversations
    assert spent["all"] == 10 + 2 * len("Bonjour")


@pytest.mark.parametrize(
    "value, rounded",
    [(1_234_567, 1_300_000), (508, 510), (99.1, 100), (7, 7), (0, 0)],
)
def test_a_proposal_rounds_up_to_two_digits(value, rounded):
    assert round_up(value) == rounded


@pytest.mark.parametrize(
    "micro_usd, dollars",
    [(359_644, 0.36), (17_982_000, 18.0), (1_234, 0.01), (0, 0.0)],
)
def test_a_dollar_proposal_rounds_up_to_two_digits_and_the_cent(micro_usd, dollars):
    assert in_setting_unit("expensive", micro_usd) == dollars


def test_a_model_the_database_no_longer_knows_costs_nothing():
    rows = [turn(uuid4(), START, "a", (10, 0, False), (10, 0, False))]
    [spent] = replay(rows, {}).conversations
    assert "expensive" not in spent


def hundred_people(**extra):
    """One turn each, person i's answers 10 x i long, on their own network."""
    return [
        turn(
            uuid4(),
            START,
            "x",
            (10 * i, 0, False),
            (10 * i, 0, False),
            session=f"s{i}",
            ip=f"10.0.{i}.1",
            **extra,
        )
        for i in range(1, 101)
    ]


def test_the_proposals_come_from_what_people_spent():
    proposals = {p.name: p for p in propose(replay(hundred_people(), PRICES))}

    # Person i spends (10 + 1 + 10i) + (1 + 10i): 32 to 2,012 on the whole
    # allowance, and 1 + 3 x 10i millionths of a dollar on the expensive one,
    # side b only: less than a cent, so the least the page takes.
    whole = proposals["all_per_session"]
    assert (whole.value, whole.sample, whole.percentile) == (2_000, 100, 99)
    # A typical turn costs 1,022: about one message fits.
    assert whole.messages == 1
    assert proposals["expensive_per_session"].value == 0.01

    # Room for 35 people spending what 95 in 100 do (1,913).
    network = proposals["all_per_ip"]
    assert (network.value, network.class_size, network.over_share) == (
        67_000,
        35,
        0.0,
    )
    # The median answer, of 200.
    answer = proposals["expected_answer_chars"]
    assert (answer.value, answer.sample) == (505, 200)


def test_a_busy_network_shows_in_the_share_over_the_proposal():
    rows = hundred_people() + [
        turn(uuid4(), START, "x", (1_000, 0, False), (1_000, 0, False), ip="10.9.9.9")
        for _ in range(100)
    ]
    proposals = {p.name: p for p in propose(replay(rows, PRICES))}
    # 101 networks, the busy one far past room for a class.
    assert proposals["all_per_ip"].over_share == pytest.approx(1 / 101)


def test_a_pool_nobody_spent_proposes_nothing():
    rows = hundred_people(llm_id_b=CHEAP)
    names = [p.name for p in propose(replay(rows, PRICES))]
    assert names == ["all_per_session", "all_per_ip", "expected_answer_chars"]
    assert propose(replay([], PRICES)) == []
