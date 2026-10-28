"""
Unit tests for the publish run's analysis on the decision model (mocked HTTP,
no DB, no Redis).

    uv run pytest tests/database/test_llm_analyze.py
"""

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

import httpx  # noqa: E402
import pytest  # noqa: E402
from linkup import LinkupSearchTextResult  # noqa: E402

import backend.arena.checks as checks  # noqa: E402
from utils.database.models import Comparison, Turn  # noqa: E402
from utils.database.models.comparison import (  # noqa: E402
    ComparisonLLMAnalysisFailedUpdate,
    ComparisonLLMAnalysisUpdate,
)
from utils.database.models.dataset_check import (  # noqa: E402
    DEFAULT_CRITERIA,
    DatasetCheck,
)
from utils.database.models.messages import LLMMessage, UserMessage  # noqa: E402

# The package exports a function of the same name, which shadows the module.
import utils.database.actions.llm_analyze  # noqa: E402, F401  isort:skip

llm_analyze = sys.modules["utils.database.actions.llm_analyze"]

T0 = datetime(2026, 1, 1)
REAL_CLIENT = httpx.AsyncClient


def comparison(*exchanges: tuple[str, str, str]) -> Comparison:
    c = Comparison(
        ip="127.0.0.1", mode="random", llm_id_a=uuid.uuid4(), llm_id_b=uuid.uuid4()
    )
    turns = []
    for user, a, b in exchanges:
        t = Turn(created_at=T0)
        t.user_msg = UserMessage(content=user, created_at=T0)
        t.llm_msg_a = LLMMessage(content=a, created_at=T0, is_cached=False)
        t.llm_msg_b = LLMMessage(content=b, created_at=T0, is_cached=False)
        turns.append(t)
    c.turns = turns
    return c


def analysis(**overrides) -> "llm_analyze.Analysis":
    check = DatasetCheck(
        id=1, model="test/decider", criteria=[dict(c) for c in DEFAULT_CRITERIA]
    )
    for key, value in overrides.items():
        setattr(check, key, value)
    return llm_analyze.analysis_for(check, "test-key", "fr", ["da", "en", "fr"])


class Decider:
    """Answers each question with what `scorer` makes of (key, message), or
    with the next of `statuses` while any are left."""

    def __init__(self, scorer=lambda key, text: 0.0, statuses=()):
        self.scorer = scorer
        self.statuses = list(statuses)
        self.requests: list[dict] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        self.requests.append(body)
        if self.statuses:
            return httpx.Response(self.statuses.pop(0))
        text = body["state"]["message"]
        answers = {
            key: {"type": "noul", "noul": self.scorer(key, text)}
            for key in body["questions"]
        }
        return httpx.Response(200, json={"answers": answers})


def run(coro, decider: Decider, monkeypatch, updates=None):
    monkeypatch.setattr(
        checks.httpx,
        "AsyncClient",
        lambda **kwargs: REAL_CLIENT(
            transport=httpx.MockTransport(decider.handler), **kwargs
        ),
    )

    def no_redis():
        raise ConnectionError("no redis in tests")

    monkeypatch.setattr(checks, "get_redis_client", no_redis)
    monkeypatch.setattr(llm_analyze, "RETRY_DELAY", 0)
    if updates is not None:

        async def fake_update(comparison_id, data):
            updates.append((comparison_id, data))

        monkeypatch.setattr(llm_analyze, "update_comparison", fake_update)
    return asyncio.run(coro)


def scorer(scores: dict[str, float]):
    return lambda key, text: scores.get(key, 0.0)


def test_a_clean_comparison_gets_topics_and_languages(monkeypatch):
    decider = Decider(
        scorer(
            {
                "category_food_drink_cooking": 0.9,
                "category_health_wellness_medicine": 0.4,
                "language_fr": 0.95,
                "pii": 0.1,
            }
        )
    )
    updates: list = []
    analyzer = llm_analyze.Analyzer(analysis())
    comp = comparison(("Une recette de crêpes ?", "Voici...", "Il faut..."))
    run(analyzer.analyze_comparison(comp), decider, monkeypatch, updates)

    assert len(decider.requests) == 1
    asked = decider.requests[0]["questions"]
    # 2 criteria, 17 topics, 9 languages and "other".
    assert len(asked) == 2 + 17 + 10
    assert "[user]: Une recette de crêpes ?" in decider.requests[0]["state"]["message"]
    [(comparison_id, data)] = updates
    assert comparison_id == comp.id
    assert isinstance(data, ComparisonLLMAnalysisUpdate)
    assert data.categories == ["Food & Drink & Cooking"]
    assert data.languages == ["fr"]
    assert not data.archived
    assert data.analysis_scores["model"] == "test/decider"
    assert data.analysis_scores["scores"]["pii"] == 0.1
    assert "short_summary" not in data.model_dump()


def test_personal_data_in_an_answer_archives_it(monkeypatch):
    decider = Decider(lambda key, text: 0.8 if key == "pii" and "06 12" in text else 0)
    updates: list = []
    analyzer = llm_analyze.Analyzer(analysis())
    comp = comparison(("Mon voisin ?", "Jean Dupont, 06 12 34 56 78", "Je ne sais pas"))
    run(analyzer.analyze_comparison(comp), decider, monkeypatch, updates)

    data = updates[0][1]
    assert data.contains_pii and not data.contains_spam
    assert data.archived and data.archived_reason == "pii"
    # No topic reached the threshold.
    assert data.categories == ["Other"]


def test_the_threshold_is_the_admins(monkeypatch):
    decider = Decider(scorer({"spam": 0.35}))
    criteria = [dict(c) for c in DEFAULT_CRITERIA]
    for c in criteria:
        c["threshold"] = 0.4
    updates: list = []
    analyzer = llm_analyze.Analyzer(analysis(criteria=criteria))
    run(
        analyzer.analyze_comparison(comparison(("a", "b", "c"))),
        decider,
        monkeypatch,
        updates,
    )
    assert not updates[0][1].contains_spam


def test_a_long_comparison_is_read_in_windows_and_keeps_its_highest(monkeypatch):
    filler = "Parlons de cuisine. " * 1000
    decider = Decider(
        lambda key, text: 0.9 if key == "spam" and "ACHETEZ" in text else 0
    )
    updates: list = []
    analyzer = llm_analyze.Analyzer(analysis())
    comp = comparison((filler + "ACHETEZ ICI", "ok", "ok"))
    run(analyzer.analyze_comparison(comp), decider, monkeypatch, updates)

    assert len(decider.requests) > 2
    assert updates[0][1].contains_spam


def test_a_folded_spelling_is_scored_on_the_exclusion_criteria_only(monkeypatch):
    decider = Decider(
        lambda key, text: 0.9 if key == "spam" and "viagra" in text else 0
    )
    updates: list = []
    analyzer = llm_analyze.Analyzer(analysis())
    run(
        analyzer.analyze_comparison(comparison(("v1agra pas cher", "non", "non"))),
        decider,
        monkeypatch,
        updates,
    )

    assert len(decider.requests) == 2
    assert set(decider.requests[1]["questions"]) == {"pii", "spam"}
    assert updates[0][1].contains_spam


def test_the_web_search_results_are_read_as_published():
    comp = comparison(("Qui contacter ?", "Voici", "Voilà"))
    comp.turns[0].user_msg.web_search_results = [
        LinkupSearchTextResult(
            type="text",
            name="Annuaire",
            url="https://example.org",
            favicon="",
            content="Jean Dupont, jean.dupont@example.org",
        )
    ]
    assert "jean.dupont@example.org" in llm_analyze.conversation_text(comp)


def test_the_folded_spelling_shares_the_comparisons_deadline(monkeypatch):
    async def slow(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(0.035)
        return Decider().handler(request)

    monkeypatch.setattr(
        checks.httpx,
        "AsyncClient",
        lambda **kwargs: REAL_CLIENT(transport=httpx.MockTransport(slow), **kwargs),
    )
    monkeypatch.setattr(
        checks, "get_redis_client", lambda: (_ for _ in ()).throw(ConnectionError())
    )
    limits = llm_analyze.LIMITS._replace(deadline=0.05)
    text = llm_analyze.conversation_text(comparison(("v1agra pas cher", "non", "non")))
    with pytest.raises(checks.CheckOverloaded):
        asyncio.run(llm_analyze.score_comparison(text, analysis(), limits))


def test_a_question_with_no_score_never_reaches_a_zero_threshold():
    criteria = analysis().criteria
    for c in criteria:
        c.threshold = 0.0
    data = llm_analyze.update_from_scores(
        {"category_sports": 0.0}, "m", criteria, 0.0, 0.0
    )
    assert not data.contains_pii and not data.contains_spam
    # "Other" is what a comparison gets when no topic is found, never one more.
    assert data.categories == ["Sports"]


def test_a_comparison_too_long_to_send_is_failed_without_a_call(monkeypatch):
    decider = Decider()
    updates: list = []
    analyzer = llm_analyze.Analyzer(analysis())
    huge = "x" * (checks.CHUNK_CHARS * (llm_analyze.MAX_WINDOWS + 2))
    comp = comparison((huge, "", ""))
    run(analyzer.analyze_comparison(comp), decider, monkeypatch, updates)

    assert decider.requests == []
    assert isinstance(updates[0][1], ComparisonLLMAnalysisFailedUpdate)
    assert analyzer.failed == [str(comp.id)]


def test_a_failing_model_marks_the_comparison_failed_after_three_tries(monkeypatch):
    # Each try is a request and its own retry.
    decider = Decider(statuses=[500] * (2 * llm_analyze.MAX_RETRIES))
    updates: list = []
    analyzer = llm_analyze.Analyzer(analysis())
    comp = comparison(("a", "b", "c"))
    run(analyzer.analyze_comparison(comp), decider, monkeypatch, updates)

    assert len(decider.requests) == 2 * llm_analyze.MAX_RETRIES
    assert isinstance(updates[0][1], ComparisonLLMAnalysisFailedUpdate)


def test_a_failure_then_an_answer_is_analyzed(monkeypatch):
    decider = Decider(scorer({"language_en": 0.9}), statuses=[500, 500])
    updates: list = []
    analyzer = llm_analyze.Analyzer(analysis())
    run(
        analyzer.analyze_comparison(comparison(("hi", "hello", "hey"))),
        decider,
        monkeypatch,
        updates,
    )

    assert isinstance(updates[0][1], ComparisonLLMAnalysisUpdate)
    assert updates[0][1].languages == ["en"]
    assert analyzer.failed == []


def test_a_rescored_comparison_that_fails_keeps_what_it_had(monkeypatch):
    decider = Decider(statuses=[500] * (2 * llm_analyze.MAX_RETRIES))
    updates: list = []
    analyzer = llm_analyze.Analyzer(analysis(), keep_on_failure=True)
    comp = comparison(("a", "b", "c"))
    run(analyzer.analyze_comparison(comp), decider, monkeypatch, updates)

    assert updates == []
    assert analyzer.failed == [str(comp.id)]


def test_a_rescore_counts_the_comparisons_it_holds_back(monkeypatch):
    decider = Decider(scorer({"pii": 0.9}))
    analyzer = llm_analyze.Analyzer(analysis(), keep_on_failure=True)
    for _ in range(2):
        run(
            analyzer.analyze_comparison(comparison(("a", "b", "c"))),
            decider,
            monkeypatch,
            [],
        )

    assert (analyzer.analyzed, analyzer.held) == (2, 2)


def test_a_refused_key_stops_the_run(monkeypatch):
    for status in (401, 402):
        decider = Decider(statuses=[status])
        updates: list = []
        analyzer = llm_analyze.Analyzer(analysis())
        try:
            run(
                analyzer.analyze_comparison(comparison(("a", "b", "c"))),
                decider,
                monkeypatch,
                updates,
            )
        except llm_analyze.AnalysisStopped as e:
            assert str(status) in str(e)
        else:
            raise AssertionError("expected AnalysisStopped")
        assert updates == []


def test_languages_follow_the_instance():
    codes = llm_analyze.language_codes("da", ["da", "en", "nb-NO", "sv"])
    assert codes[:4] == ["da", "en", "nb", "sv"]
    assert len(codes) == len(set(codes))
    assert "fr" in codes and "zh" in codes


def test_reapplying_scores_moves_with_the_thresholds():
    scores = {"pii": 0.35, "category_sports": 0.55, "language_en": 0.6}
    criteria = analysis().criteria
    strict = llm_analyze.update_from_scores(scores, "m", criteria, 0.5, 0.5)
    assert strict.contains_pii and strict.categories == ["Sports"]
    for c in criteria:
        c.threshold = 0.5
    loose = llm_analyze.update_from_scores(scores, "m", criteria, 0.6, 0.7)
    assert not loose.contains_pii
    assert loose.categories == ["Other"] and loose.languages == []


def run_pipeline(monkeypatch, total: int, analyze):
    produced = []

    async def fake_stream(_filters):
        for _ in range(total):
            produced.append(1)
            yield comparison(("a", "b", "c"))

    async def fake_analysis():
        return analysis()

    monkeypatch.setattr(llm_analyze, "get_db_comparisons_stream", fake_stream)
    monkeypatch.setattr(llm_analyze, "get_analysis", fake_analysis)
    monkeypatch.setattr(llm_analyze.Analyzer, "analyze_comparison", analyze)
    return produced


def test_backlog_is_not_loaded_in_memory_faster_than_workers_consume_it(monkeypatch):
    total = 200
    seen_while_blocked = []

    async def scenario():
        gate = asyncio.Event()

        async def analyze(self, comp):
            await gate.wait()

        produced = run_pipeline(monkeypatch, total, analyze)
        task = asyncio.create_task(llm_analyze.analyze_comparisons())
        await asyncio.sleep(0.2)
        seen_while_blocked.append(len(produced))
        gate.set()
        await asyncio.wait_for(task, timeout=5)
        return len(produced)

    assert asyncio.run(scenario()) == total
    assert seen_while_blocked[0] <= llm_analyze.WORKERS + llm_analyze.QUEUE_SIZE + 1


def test_a_stopped_run_raises_and_does_not_hang(monkeypatch):
    async def scenario():
        async def analyze(self, comp):
            raise llm_analyze.AnalysisStopped("key refused")

        run_pipeline(monkeypatch, 200, analyze)
        await asyncio.wait_for(llm_analyze.analyze_comparisons(), timeout=5)

    try:
        asyncio.run(scenario())
    except llm_analyze.AnalysisStopped:
        pass
    else:
        raise AssertionError("expected AnalysisStopped")
