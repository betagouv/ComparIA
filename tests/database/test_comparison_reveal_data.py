import os
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("COMPARIA_DB_URI", "postgresql://example/test")
os.environ.setdefault("LOG_FORMAT", "RAW")

from utils.database.models import comparison as comparison_model  # noqa: E402
from utils.database.models.comparison import ComparisonPublic  # noqa: E402

PRESENT = uuid.uuid4()
GONE = uuid.uuid4()


def _comparison(llm_id_a, llm_id_b):
    return {
        "id": uuid.uuid4(),
        "mode": "random",
        "custom_models_selection": None,
        "enabled_tools": [],
        "error": None,
        "revealed": True,
        "llm_id_a": llm_id_a,
        "llm_id_b": llm_id_b,
        "turns": [
            {
                "id": uuid.uuid4(),
                "user_msg": {"content": "question", "role": "user"},
                "choice": "a_better",
                "llm_msg_a": None,
                "keyword_annotations_a": [],
                "llm_msg_b": None,
                "keyword_annotations_b": [],
            }
        ],
    }


def _validate(monkeypatch, llm_id_a, llm_id_b):
    calls = []

    def fake_get_reveal_data(comparison, llms):
        calls.append(comparison.id)
        return {"b64": "", "chosen_llm": "a", "a": {}, "b": {}}

    monkeypatch.setattr(comparison_model, "get_reveal_data", fake_get_reveal_data)
    llms = SimpleNamespace(all={PRESENT: object()})
    result = ComparisonPublic.model_validate(
        _comparison(llm_id_a, llm_id_b), context={"llms_data": llms}
    )
    return result, calls


def test_reveal_data_is_built_when_both_models_are_in_the_catalogue(monkeypatch):
    result, calls = _validate(monkeypatch, PRESENT, PRESENT)

    assert result.reveal_data is not None
    assert len(calls) == 1


def test_a_model_gone_from_the_catalogue_leaves_the_comparison_readable(monkeypatch):
    # A model disabled after the comparison used to raise KeyError here, which
    # took down every conversation in the caller's history, not just this one.
    result, calls = _validate(monkeypatch, PRESENT, GONE)

    assert result.reveal_data is None
    assert calls == []
    assert result.turns[0].user_msg.content == "question"
