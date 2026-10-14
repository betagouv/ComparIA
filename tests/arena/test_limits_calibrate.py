"""
The calibration replay charges a stored conversation as the arena does (no
database: the rows are built here).
"""

from datetime import datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

from linkup import LinkupSearchTextResult

from backend.arena.web_search import merge_web_search_with_content
from utils.arena.calibrate import replay

CHEAP, EXPENSIVE = uuid4(), uuid4()
WEIGHTS = {CHEAP: 1.0, EXPENSIVE: 4.0}
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

    result = replay(rows, WEIGHTS)

    # Turn 1: a is sent its system prompt and the prompt with the search
    # results, b the prompt only. Turn 2 resends all that, the side's answer
    # (not its reasoning) and the new prompt; b failed and wrote nothing.
    sent_a = [10 + searched, 10 + searched + 100 + len("Encore")]
    sent_b = [searched, searched + 200 + len("Encore")]
    all_chars = sum(sent_a) + sum(sent_b) + (100 + 40) + 200 + 100
    expensive = 4 * (sent_b[0] + 200) + 4 * sent_b[1]
    assert result.conversations == [{"all": all_chars, "expensive": expensive}]
    assert result.turns == 2
    assert (result.answers, result.cached) == (3, 0)


def test_a_cached_answer_is_free_on_the_expensive_pool_only():
    rows = [turn(uuid4(), START, "Bonjour", (100, 0, False), (300, 0, True))]
    [spent] = replay(rows, WEIGHTS).conversations
    assert spent["expensive"] == 0
    assert spent["all"] == 10 + 7 + 100 + 7 + 300


def test_a_window_closes_after_two_quiet_hours():
    rows = [
        turn(uuid4(), START, "a", (10, 0, False), (10, 0, False)),
        turn(uuid4(), START + timedelta(hours=1), "b", (10, 0, False), (10, 0, False)),
        turn(uuid4(), START + timedelta(hours=4), "c", (10, 0, False), (10, 0, False)),
    ]
    result = replay(rows, WEIGHTS)

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
    result = replay(rows, WEIGHTS)

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
    result = replay(rows, WEIGHTS)

    assert (result.cached, result.answers) == (5, 6)
    assert (result.suggested_cached, result.suggested_answers) == (1, 2)
