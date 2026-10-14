"""
A turn costs what the models are sent and what they write (no network, no DB,
no real Redis).

A message used to cost its own length, while each model is sent the system
prompt, the whole transcript and the web search results, and writes answers
far longer than the question. The expensive allowance now counts each
expensive model's characters as many times as its cost weight.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")

from linkup import LinkupSearchTextResult  # noqa: E402

from backend.arena.conversation import SystemMessageRead  # noqa: E402
from backend.arena.litellm import litellm_messages, sent_chars  # noqa: E402
from backend.arena.web_search import merge_web_search_with_content  # noqa: E402
from utils.database.models import LLMMessageRead, UserMessageRead  # noqa: E402

SYSTEM = "Tu es un assistant."
FIRST, SECOND = "Bonjour ?", "Et la suite ?"


def answer(content, reasoning=None):
    return LLMMessageRead.model_construct(
        role="assistant", content=content, reasoning_content=reasoning
    )


def test_a_model_is_sent_the_system_prompt_the_transcript_and_its_answers():
    messages = [
        SystemMessageRead(content=SYSTEM),
        UserMessageRead(content=FIRST),
        # Its reasoning is not sent back to it.
        answer("Bonjour à vous.", reasoning="Je réfléchis."),
        UserMessageRead(content=SECOND),
    ]

    assert sent_chars(messages) == len(SYSTEM + FIRST + "Bonjour à vous." + SECOND)


def test_web_search_results_count_as_sent():
    results = [
        LinkupSearchTextResult(
            type="text",
            name="Le Monde",
            url="https://a.example/article",
            content="Paris est la capitale de la France.",
            favicon="",
        )
    ]
    prompt = UserMessageRead(content=FIRST, web_search_results=results)

    [sent] = litellm_messages([prompt])
    assert sent["content"] == merge_web_search_with_content(FIRST, results)
    assert sent_chars([prompt]) == len(sent["content"]) > len(FIRST) + 30
