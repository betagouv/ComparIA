"""
Tags are admin metadata: a blind selection mode may draw from a tag, so
publishing them would give its pool away. They stay off the public model list
and the dataset, while `arena_tools` (how a model is called) stays published.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("LOG_FORMAT", "JSON")

from pydantic import TypeAdapter  # noqa: E402

from backend.llms.data import LLMList  # noqa: E402
from backend.llms.models import APILLMData  # noqa: E402
from tests.llms.test_selection_engine import llm  # noqa: E402
from utils.dataset.compute import _model_metadata  # noqa: E402
from utils.dataset.models import DatasetLLM  # noqa: E402

TAGGED = llm("tagged", tags=["legal"], arena_tools=False)


def test_the_engine_still_reads_tags():
    assert TAGGED.tags == ["legal"]


def test_the_public_model_list_has_no_tags():
    # The field get_llms_list fills from the enabled models.
    models = TypeAdapter(LLMList.model_fields["models"].annotation)
    listed = models.validate_python([TAGGED], context={"ranking": None})
    published = models.dump_python(listed, mode="json")[0]
    assert "tags" not in published
    assert published["arena_tools"] is False
    assert "tags" not in APILLMData.model_json_schema()["properties"]


def test_the_dataset_models_file_has_no_tags():
    published = _model_metadata(DatasetLLM.model_validate(TAGGED.model_dump()))
    assert "tags" not in published
    assert published["arena_tools"] is False
