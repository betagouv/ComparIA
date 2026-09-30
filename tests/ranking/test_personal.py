"""
Tests for the personal ranking scoring rule (utils/ranking/personal).

Deterministic and DB-free. Runnable either way:
    uv run python tests/ranking/test_personal.py
    pytest tests/ranking/test_personal.py
"""

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from utils.ranking.personal import (  # noqa: E402
    PersonalTally,
    rank_personal_models,
    tally_votes,
)


def model_id(name: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_DNS, name)


def tally(name, wins=0, losses=0, ties=0, general_rank=None) -> PersonalTally:
    return PersonalTally(
        llm_id=model_id(name),
        name=name,
        wins=wins,
        losses=losses,
        ties=ties,
        general_rank=general_rank,
    )


def ranked(*tallies) -> dict[str, tuple[int, float]]:
    return {row.name: (row.rank, row.score) for row in rank_personal_models(tallies)}


def order(*tallies) -> list[str]:
    return [row.name for row in rank_personal_models(tallies)]


def test_no_votes_is_an_empty_ranking():
    assert rank_personal_models([]) == []


def test_a_single_win_is_not_a_perfect_score():
    ranking = ranked(tally("winner", wins=1), tally("loser", losses=1))

    assert ranking["winner"] == (1, 0.667)
    assert ranking["loser"] == (2, 0.333)


def test_a_long_record_outranks_a_lone_win():
    ranking = ranked(
        tally("veteran", wins=18, losses=2),
        tally("veteran_rivals", wins=2, losses=18),
        tally("newcomer", wins=1),
        tally("newcomer_rival", losses=1),
    )

    assert ranking["veteran"] == (1, 0.864)
    assert ranking["newcomer"][1] == 0.667
    assert ranking["veteran"][0] < ranking["newcomer"][0]


def test_one_battle_each_keeps_the_preferred_models_on_top():
    assert order(
        tally("liked", wins=1),
        tally("disliked", losses=1),
        tally("also_liked", wins=1),
        tally("also_disliked", losses=1),
    ) == ["also_liked", "liked", "also_disliked", "disliked"]


def test_both_good_is_half_a_point_each_and_both_bad_is_none():
    ranking = ranked(
        tally("shared_good", ties=1),
        tally("shared_good_rival", ties=1),
        tally("shared_bad", losses=1),
        tally("shared_bad_rival", losses=1),
    )

    # mean points per battle is 0.25 here, so the anchor sits below 0.5
    assert ranking["shared_good"] == (1, 0.333)
    assert ranking["shared_good_rival"] == (1, 0.333)
    assert ranking["shared_bad"] == (3, 0.167)


def test_i_dont_know_produces_no_battle():
    a, b = model_id("a"), model_id("b")

    assert tally_votes([(a, b, "idk", 4)]) == {}
    assert set(tally_votes([(a, b, "idk", 4), (a, b, "a_better", 1)])) == {a, b}


def test_choices_become_wins_losses_and_ties():
    a, b = model_id("a"), model_id("b")
    tallies = tally_votes(
        [
            (a, b, "a_better", 3),
            (a, b, "b_better", 1),
            (a, b, "both_good", 2),
            (a, b, "both_bad", 4),
        ]
    )

    assert (tallies[a].wins, tallies[a].losses, tallies[a].ties) == (3, 5, 2)
    assert (tallies[b].wins, tallies[b].losses, tallies[b].ties) == (1, 7, 2)
    assert tallies[a].battles == 10
    assert tallies[a].points == 4.0


def test_equal_scores_share_a_rank_and_the_next_one_skips():
    ranking = ranked(
        tally("won_1", wins=1),
        tally("won_2", wins=1),
        tally("won_3", wins=1),
        tally("lost_1", losses=1),
        tally("lost_2", losses=1),
        tally("lost_3", losses=1),
    )

    assert sorted(rank for rank, _score in ranking.values()) == [1, 1, 1, 4, 4, 4]


def test_tied_rows_are_ordered_by_battles_then_by_general_rank():
    rows = rank_personal_models(
        [
            tally("few_battles_unranked", wins=1, losses=1),
            tally("many_battles", wins=2, losses=2),
            tally("few_battles_20th", wins=1, losses=1, general_rank=20),
            tally("few_battles_3rd", wins=1, losses=1, general_rank=3),
        ]
    )

    assert {row.rank for row in rows} == {1}
    assert [row.name for row in rows] == [
        "many_battles",
        "few_battles_3rd",
        "few_battles_20th",
        "few_battles_unranked",
    ]


def test_both_bad_votes_pull_every_score_down_without_breaking_the_order():
    ranking = ranked(
        tally("preferred", wins=1),
        tally("passed_over", losses=1),
        tally("bad_1", losses=1),
        tally("bad_2", losses=1),
    )

    # the mean anchor is 0.25 rather than 0.5, so a 1-0 record scores below 0.667
    assert ranking["preferred"] == (1, 0.5)
    assert ranking["passed_over"][0] == 2
    assert ranking["passed_over"] == ranking["bad_1"] == ranking["bad_2"]


def test_a_row_carries_the_record_behind_its_score():
    (row,) = rank_personal_models([tally("solo", wins=3, losses=2, ties=1)])

    assert (row.wins, row.losses, row.ties) == (3, 2, 1)
    assert row.battles == 6
    assert row.llm_id == model_id("solo")
    assert row.name == "solo"


if __name__ == "__main__":
    for name, test in sorted(dict(globals()).items()):
        if name.startswith("test_"):
            test()
