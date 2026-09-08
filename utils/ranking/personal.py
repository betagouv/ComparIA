"""
Personal ranking: scores one user's own votes, with no Bradley-Terry fit.

A single user's votes form a scatter of mostly disconnected pairs, which the
global solver cannot fit, so each model is scored on its own record shrunk
towards the user's average.

Note that a personal battle is *any* scored turn, ties included, which is wider
than the ``battle`` of ``utils.ranking.compute``, where ties are dropped before
the fit. The two must not share a helper.
"""

import math
from dataclasses import dataclass
from typing import Iterable, Literal
from uuid import UUID

from pydantic import BaseModel

# Two phantom battles at the user's own average, so a 1-0 record cannot top the
# table and twenty battles outweigh one at comparable rates.
SHRINKAGE_BATTLES = 2
# Points per battle assumed for a user who has not voted at all.
DEFAULT_MEAN_POINTS = 0.5

Outcome = Literal["win", "loss", "tie"]

# What a vote does to each side. "both_bad" counts against both models rather
# than being neutral: it reports dissatisfaction, not a draw. "idk" is absent on
# purpose, it is not a battle for either side.
OUTCOMES: dict[str, tuple[Outcome, Outcome]] = {
    "a_better": ("win", "loss"),
    "b_better": ("loss", "win"),
    "both_good": ("tie", "tie"),
    "both_bad": ("loss", "loss"),
}


@dataclass
class PersonalTally:
    llm_id: UUID
    name: str
    wins: int = 0
    losses: int = 0
    ties: int = 0
    # Position in the general ranking, used only to break ties. None when the
    # model is missing from the last computed ranking.
    general_rank: int | None = None

    @property
    def battles(self) -> int:
        return self.wins + self.losses + self.ties

    @property
    def points(self) -> float:
        return self.wins + self.ties / 2


class PersonalRankingRow(BaseModel):
    """
    One model in a user's own ranking, scored, ordered and numbered.

    Carries the model name as well as its id: a model the user voted on can have
    left the arena since, and is then missing from the model list the client
    holds.
    """

    llm_id: UUID
    name: str
    rank: int
    score: float
    battles: int
    wins: int
    losses: int
    ties: int


def tally_votes(
    votes: Iterable[tuple[UUID, UUID, str | None, int]],
) -> dict[UUID, PersonalTally]:
    """Fold grouped ``(model a, model b, choice, count)`` rows into per-model tallies."""
    tallies: dict[UUID, PersonalTally] = {}
    for llm_id_a, llm_id_b, choice, count in votes:
        outcomes = OUTCOMES.get(choice or "")
        if not outcomes:
            continue
        for llm_id, outcome in zip((llm_id_a, llm_id_b), outcomes):
            tally = tallies.setdefault(llm_id, PersonalTally(llm_id=llm_id, name=""))
            if outcome == "win":
                tally.wins += count
            elif outcome == "loss":
                tally.losses += count
            else:
                tally.ties += count
    return tallies


def rank_personal_models(
    tallies: Iterable[PersonalTally],
) -> list[PersonalRankingRow]:
    """
    Score, order and number a user's models from their per-model tallies.

    The score is the model's points shrunk towards the user's own mean points
    per battle, ``(points + 2m) / (battles + 2)``. Anchoring on the observed
    mean rather than on 0.5 keeps the score independent of the tie rule: because
    "both bad" awards nothing to either side, points do not sum to 1 per battle
    and the mean drifts below 0.5 on its own.

    Two properties are load-bearing: models with equal battle counts never
    reorder under shrinkage, and models with more battles beat models with fewer
    at comparable rates.
    """
    tallies = list(tallies)
    battles = sum(tally.battles for tally in tallies)
    mean = (
        sum(tally.points for tally in tallies) / battles
        if battles
        else DEFAULT_MEAN_POINTS
    )

    # Rounded before ordering and numbering, so two models the table shows as
    # 0.866 share a rank instead of being split by a digit the user cannot see.
    scored = [
        (
            tally,
            round(
                (tally.points + SHRINKAGE_BATTLES * mean)
                / (tally.battles + SHRINKAGE_BATTLES),
                3,
            ),
        )
        for tally in tallies
    ]
    scored.sort(
        key=lambda scored_tally: (
            -scored_tally[1],
            -scored_tally[0].battles,
            (
                scored_tally[0].general_rank
                if scored_tally[0].general_rank is not None
                else math.inf
            ),
            scored_tally[0].name,
        )
    )

    rows = []
    rank = 0
    previous_score = None
    for position, (tally, score) in enumerate(scored, 1):
        # Competition ranking: equal scores share a number, the next distinct
        # score skips ahead (1, 1, 1, 4).
        if score != previous_score:
            rank = position
            previous_score = score
        rows.append(
            PersonalRankingRow(
                llm_id=tally.llm_id,
                name=tally.name,
                rank=rank,
                score=score,
                battles=tally.battles,
                wins=tally.wins,
                losses=tally.losses,
                ties=tally.ties,
            )
        )
    return rows
