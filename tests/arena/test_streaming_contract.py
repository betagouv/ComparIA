"""
What a comparison streams, checked through the arena HTTP API against a fake
model provider on a local socket.

The tests only look at what leaves the API and what lands in the database, never
at which LiteLLM function made the call, so they hold when the call moves from
the synchronous to the asynchronous one.
"""

from sqlalchemy import create_engine, text


def rows(postgres_uri: str, query: str):
    engine = create_engine(
        postgres_uri.replace("postgresql://", "postgresql+psycopg://")
    )
    try:
        with engine.connect() as connection:
            return connection.execute(text(query)).mappings().all()
    finally:
        engine.dispose()


def last_chunk(events: list[dict], pos: str) -> dict:
    return [e for e in events if e["type"] == "chunk" and e["pos"] == pos][-1][
        "llm_msg"
    ]


def test_a_comparison_streams_both_answers_to_the_end(arena):
    arena.provider.tokens = ["Bonjour", " le", " monde"]

    events = arena.ask()

    assert events[0]["type"] == "init"
    assert events[-1] == {"type": "complete"}
    for pos in ("a", "b"):
        assert last_chunk(events, pos)["content"] == "Bonjour le monde"
        assert {"type": "complete", "pos": pos} in events
    assert len(arena.provider.requests) == 2


def test_the_reasoning_is_kept_apart_from_the_answer(arena):
    arena.provider.reasoning_tokens = ["Je", " réfléchis"]
    arena.provider.tokens = ["Voilà"]

    message = last_chunk(arena.ask(), "a")

    assert message["reasoning_content"] == "Je réfléchis"
    assert message["content"] == "Voilà"


def saved_messages(postgres_uri: str):
    return rows(
        postgres_uri,
        "select content, reasoning_content, tokens, generation_id from llm_message",
    )


def test_without_a_reported_token_count_the_answer_is_counted_locally(
    arena, postgres_uri
):
    arena.provider.reported_tokens = None

    arena.ask()

    assert all(m["tokens"] > 0 for m in saved_messages(postgres_uri))


def test_the_provider_generation_id_is_saved_but_not_sent(arena, postgres_uri):
    events = arena.ask()

    assert "generation_id" not in last_chunk(events, "a")
    assert {m["generation_id"] for m in saved_messages(postgres_uri)} == {
        "chatcmpl-fake"
    }


def test_the_timestamps_frame_the_stream(arena):
    arena.provider.first_byte_delay = 0.2
    arena.provider.token_delay = 0.05

    message = last_chunk(arena.ask(), "a")

    from datetime import datetime

    created, responded, updated = (
        datetime.fromisoformat(message[key])
        for key in ("created_at", "responded_at", "updated_at")
    )
    assert created <= responded <= updated
    assert (responded - created).total_seconds() >= 0.2
    assert (updated - responded).total_seconds() >= 0.05


def test_an_answer_cut_at_the_token_limit_is_still_kept(arena):
    arena.provider.tokens = ["Une", " réponse", " coupée"]
    arena.provider.finish_reason = "length"

    events = arena.ask()

    assert last_chunk(events, "a")["content"] == "Une réponse coupée"
    assert events[-1] == {"type": "complete"}


def test_an_empty_answer_is_an_error_of_the_conversation(arena):
    arena.provider.tokens = []

    events = arena.ask()

    error = next(e for e in events if e["type"] == "error")
    assert error["error"] == "empty_response"
    assert events[-1]["type"] == "error"


def test_the_finished_turn_is_saved(arena, postgres_uri):
    arena.provider.reasoning_tokens = ["Je", " réfléchis"]
    arena.provider.tokens = ["Bonjour", " le", " monde"]

    arena.ask()

    messages = saved_messages(postgres_uri)
    assert len(messages) == 2
    for message in messages:
        assert message["content"] == "Bonjour le monde"
        assert message["reasoning_content"] == "Je réfléchis"


def test_a_provider_that_answers_429_first_is_retried(arena):
    arena.provider.rate_limited_first = 1

    events = arena.ask()

    assert last_chunk(events, "a")["content"] == "Bonjour le monde"
    assert events[-1] == {"type": "complete"}
    # Two answers were asked for, one of them refused once.
    assert len(arena.provider.requests) == 3
