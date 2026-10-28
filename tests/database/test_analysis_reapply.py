import os
import sys
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")

from utils.database.actions.analysis_reapply import _apply
from utils.database.actions.llm_analyze import update_from_scores
from utils.database.models import Comparison
from utils.database.models.dataset_check import DEFAULT_CRITERIA, DatasetCheck

CRITERIA = DatasetCheck(criteria=[dict(c) for c in DEFAULT_CRITERIA]).typed_criteria


def row(**fields) -> Comparison:
    c = Comparison(
        ip="127.0.0.1", mode="random", llm_id_a=uuid.uuid4(), llm_id_b=uuid.uuid4()
    )
    for key, value in fields.items():
        setattr(c, key, value)
    return c


def new(scores: dict[str, float]):
    return update_from_scores(scores, "m", CRITERIA, 0.5, 0.5)


def test_a_looser_rule_releases_a_held_row():
    held = row(
        archived=True,
        archived_reason="pii",
        archived_at=datetime(2026, 1, 1),
        contains_pii=True,
        contains_spam=False,
        categories=["Other"],
        languages=[],
    )
    changes: Counter[str] = Counter()
    assert _apply(held, new({"pii": 0.2}), changes)
    assert not held.archived and held.archived_reason is None
    assert held.archived_at is None
    assert changes["released"] == 1


def test_a_row_archived_for_another_reason_stays_archived():
    corrupted = row(
        archived=True,
        archived_reason="corrupted_no_response",
        contains_pii=False,
        contains_spam=False,
        categories=["Other"],
        languages=[],
    )
    changes: Counter[str] = Counter()
    _apply(corrupted, new({"pii": 0.9}), changes)
    assert corrupted.archived and corrupted.archived_reason == "corrupted_no_response"
    assert corrupted.contains_pii
    assert changes["excluded"] == 0


def test_nothing_moves_when_nothing_changed():
    kept = row(
        archived=False,
        contains_pii=False,
        contains_spam=False,
        categories=["Sports"],
        languages=["fr"],
    )
    changes: Counter[str] = Counter()
    assert not _apply(kept, new({"category_sports": 0.9, "language_fr": 0.9}), changes)
    assert sum(changes.values()) == 0
