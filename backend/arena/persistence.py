"""
Database persistence for votes, reactions, and conversations.
Migrated from ComparIAGradio/languia/logs.py to FastAPI.

This module handles:
- Saving votes to PostgreSQL + JSON backup files
- UPSERT reactions to PostgreSQL + JSON backup files
- UPSERT conversations to PostgreSQL + JSON backup files (overwrite)
- Deletion of reactions
"""

import json
import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Annotated, Any, Iterator

import psycopg2
from fastapi import Request
from pydantic import BaseModel, Field, PlainSerializer, WrapSerializer

from backend.arena.models import (
    REACTIONS,
    BotPos,
    Conversation,
    Conversations,
    MessageRole,
    ReactionData,
    VoteBody,
)
from backend.config import CountryPortal, SelectionMode, settings

logger = logging.getLogger("languia")

JSONSerializer = PlainSerializer(lambda v: json.dumps(v))
JSONModelSerializer = WrapSerializer(lambda v, handler: json.dumps(handler(v)))


def is_not(v: Any) -> bool:
    return not v


@contextmanager
def db(
    data: dict,
    action: str,
) -> Iterator[tuple[Any, str, str]]:
    """
    Simple db context manager yielding cursor and data field/values strings.
    Also log error for convinience.
    Important: Every keys/values from `data` will be passed to the query string,
    make sure `data` datastructure reflects the related db model.

    Args:
        data: Pydantic model dump that will be passed to query
        action: string like "save 'vote'" to represent the current operation for logging

    Yields:
        Tuple with:
            - cursor: db connection cursor
            - str: comma separated list of field keys
            - str: comma separated list of fields Values keys (%(key)s)

    Raises:
        psycopg2.Error: If database operation fails
    """
    try:
        logger.debug(f"[DB] Try to {action} data")

        with psycopg2.connect(settings.DATABASE_URI) as conn:
            with conn.cursor() as cursor:
                data_keys = list(data.keys())
                field_keys = ", ".join(data_keys)
                value_keys = ", ".join(f"%({k})s" for k in data_keys)
                yield (cursor, field_keys, value_keys)

    except psycopg2.Error as e:
        logger.error(f"[DB] Error couldn't {action} data: {e}", exc_info=True)
        # FIXME Previous code never raise db error, raise it?


def save_vote_to_db(data: dict) -> dict:
    """
    Save a vote to the database.

    Inserts or updates a vote record with comprehensive preference data.
    This function handles the final vote when a user selects a preferred model
    or marks them as equal, along with detailed preference ratings.

    Args:
        data: Vote data dict with all fields

    Returns:
        dict: The saved vote data with conversation_pair_id

    Raises:
        psycopg2.Error: If database operation fails
    """

    with db(data, "save 'vote'") as (cursor, fields, values):
        # SQL INSERT for votes table
        insert_statement = psycopg2.sql.SQL(
            f"""
            INSERT INTO votes ({fields})
            VALUES ({values})
            """
        )

        cursor.execute(insert_statement, data)

        # TODO: also increment redis counter
        # if data.get("country_portal") == "da":
        #     from languia.session import r

        #     if r:
        #         try:
        #             r.incr("danish_count")
        #         except Exception as e:
        #             logger.error(f"Error incrementing danish count in Redis: {e}")

    logger.info(f"[DB] Saved vote for {data['conversation_pair_id']}")

    return data


def upsert_reaction_to_db(data: dict) -> dict:
    """
    UPSERT a reaction to the database.

    Uses ON CONFLICT to update existing reactions or insert new ones.

    Args:
        data: Reaction data dict (see record_reaction for fields)

    Returns:
        dict: The saved reaction data

    Database Operation:
        - Uses PostgreSQL UPSERT (INSERT ... ON CONFLICT ... DO UPDATE)
        - Key conflict: (refers_to_conv_id, msg_index)
        - Updates all fields except timestamps on conflict
    """
    with db(data, "upsert 'reaction'") as (cursor, fields, values):
        data_keys = list(data.keys())
        # SQL UPSERT for reactions table
        query = psycopg2.sql.SQL(
            f"""
            INSERT INTO reactions ({fields})
            VALUES ({values})
            ON CONFLICT (refers_to_conv_id, msg_index) 
            DO UPDATE SET
                model_a_name = EXCLUDED.model_a_name,
                model_b_name = EXCLUDED.model_b_name,
                refers_to_model = EXCLUDED.refers_to_model,
                opening_msg = EXCLUDED.opening_msg,
                conversation_a = EXCLUDED.conversation_a,
                conversation_b = EXCLUDED.conversation_b,
                model_pos = EXCLUDED.model_pos,
                conv_turns = EXCLUDED.conv_turns,
                system_prompt = EXCLUDED.system_prompt,
                conv_a_id = EXCLUDED.conv_a_id,
                conv_b_id = EXCLUDED.conv_b_id,
                conversation_pair_id = EXCLUDED.conversation_pair_id,
                session_hash = EXCLUDED.session_hash,
                visitor_id = EXCLUDED.visitor_id,
                ip = EXCLUDED.ip,
                response_content = EXCLUDED.response_content,
                question_content = EXCLUDED.question_content,
                liked = EXCLUDED.liked,
                disliked = EXCLUDED.disliked,
                comment = EXCLUDED.comment,
                useful = EXCLUDED.useful,
                complete = EXCLUDED.complete,
                creative = EXCLUDED.creative,
                clear_formatting = EXCLUDED.clear_formatting,
                incorrect = EXCLUDED.incorrect,
                superficial = EXCLUDED.superficial,
                instructions_not_followed = EXCLUDED.instructions_not_followed,
                model_pair_name = EXCLUDED.model_pair_name,
                msg_rank = EXCLUDED.msg_rank,
                chatbot_index = EXCLUDED.chatbot_index,
                question_id = EXCLUDED.question_id;
            """
        )
        # TODO: fixes some edge case
        #     RETURNING
        # (CASE
        #     WHEN (pg_trigger_depth() = 0) THEN 'inserted'
        #     ELSE 'updated'
        # END) AS operation;

        cursor.execute(query, data)

        # TODO: also increment redis counter
        # country_portal = request.query_params.get(
        #     "country_portal"
        # ) or request.query_params.get("locale")
        # if country_portal == "da":
        #     from languia.session import r

        #     if r:
        #         try:
        #             r.incr("danish_count")
        #         except Exception as e:
        #             logger.error(f"Error incrementing danish count in Redis: {e}")

    logger.info(
        f"[DB] Upserted reaction for {data['refers_to_conv_id']} msg_index={data['msg_index']}"
    )

    return data


def delete_reaction_in_db(msg_index: int, refers_to_conv_id: str) -> dict:
    """
    Delete a reaction from the database.

    Args:
        msg_index: Message index (position in conversation)
        refers_to_conv_id: Conversation ID this reaction refers to

    Returns:
        dict: Result with deleted count

    Raises:
        psycopg2.Error: If database operation fails
    """
    with db({}, "delete 'reaction'") as (cursor, _, __):
        delete_query = psycopg2.sql.SQL(
            """
            DELETE FROM reactions
            WHERE refers_to_conv_id = %s AND msg_index = %s
        """
        )

        cursor.execute(delete_query, (refers_to_conv_id, msg_index))
        deleted_count = cursor.rowcount

    logger.info(
        f"[DB] Deleted reaction for {refers_to_conv_id} msg_index={msg_index} (count={deleted_count})"
    )

    return {
        "deleted": deleted_count,
        "refers_to_conv_id": refers_to_conv_id,
        "msg_index": msg_index,
    }


def upsert_conv_to_db(data: dict) -> dict:
    """
    Insert or update a conversation record in PostgreSQL using UPSERT.

    Allows conversation data to be updated as users continue chatting.
    Uses conversation_pair_id as the unique key. Updates token counts and
    message histories while preserving other metadata.

    Args:
        data: Conversation data dict with all fields

    Returns:
        dict: The saved conversation data

    Raises:
        psycopg2.Error: If database operation fails

    Database Operation:
        - Key: conversation_pair_id (text, unique)
        - On conflict: Updates message histories and token counts
        - On conflict: Updates country_portal only if EXCLUDED value exists
        - Preserves initial timestamps on updates
    """
    with db(data, "upsert 'conversations'") as (cursor, fields, values):
        # FIXME add tstamp?
        data_keys = list(data.keys())
        # SQL UPSERT for conversations table
        upsert_query = psycopg2.sql.SQL(
            f"""
            INSERT INTO conversations ({fields})
            VALUES ({values})
            ON CONFLICT (conversation_pair_id)
            DO UPDATE SET
                country_portal =  coalesce(EXCLUDED.country_portal, conversations.country_portal),
                conversation_a = EXCLUDED.conversation_a,
                conversation_b = EXCLUDED.conversation_b,
                conv_turns = EXCLUDED.conv_turns,
                total_conv_a_output_tokens = EXCLUDED.total_conv_a_output_tokens,
                total_conv_b_output_tokens = EXCLUDED.total_conv_b_output_tokens,
                cohorts = EXCLUDED.cohorts
                """
        )

        cursor.execute(upsert_query, data)

    logger.info(f"[DB] Upserted conversation {data['conversation_pair_id']}")

    return data


# ============================================================================
# High-Level Orchestration Functions
# ============================================================================


# TODO since we can postprocess data from Conversations we could remove:
# - timestamp (let the db put a default)
# - visitor_id
# - ip
# - country_portal
# - cohorts
# - model_pair_name
# - opening_msg
# - model_a_name
# - model_b_name
# - system_prompt_a
# - system_prompt_b
# - conversation_a
# - conversation_b
# - also probably conv_turns since vote can only happen at the end of the Conversations
# and legacy:
# - selected_category
# - is_unedited_prompt
class VoteRecord(BaseModel):
    # Set with database defaults, not present in logs?
    # id: int | None = None
    timestamp: str

    # Session
    session_hash: str
    visitor_id: str | None
    ip: str
    country_portal: CountryPortal
    cohorts: str

    # Conversations
    selected_category: Annotated[str | None, Field(validation_alias="category")]
    conv_turns: int
    conversation_pair_id: str
    model_pair_name: Annotated[
        list[str], JSONSerializer
    ]  # FIXME, not sure what serialization is needed. Replace to string:string ?
    opening_msg: str
    is_unedited_prompt: bool

    # Language model pairs specific
    model_a_name: str
    model_b_name: str
    system_prompt_a: str | None
    system_prompt_b: str | None
    conversation_a: Annotated[list["ConversationMessageRecord"], JSONModelSerializer]
    conversation_b: Annotated[list["ConversationMessageRecord"], JSONModelSerializer]

    # Vote
    chosen_model_name: str | None
    both_equal: bool
    conv_comments_a: str
    conv_comments_b: str
    conv_useful_a: bool
    conv_useful_b: bool
    conv_complete_a: bool
    conv_complete_b: bool
    conv_creative_a: bool
    conv_creative_b: bool
    conv_clear_formatting_a: bool
    conv_clear_formatting_b: bool
    conv_incorrect_a: bool
    conv_incorrect_b: bool
    conv_superficial_a: bool
    conv_superficial_b: bool
    conv_instructions_not_followed_a: bool
    conv_instructions_not_followed_b: bool

    # Additional? (not found in record_vote but present in votes.sql)
    # archived: bool = False


def record_vote(
    conversations: Conversations,
    vote: VoteBody,
    request: Request,
) -> dict:
    """
    Record a vote to the database with all metadata.

    This is the high-level function that constructs the complete vote record
    and saves it to both PostgreSQL and JSON backup.

    Args:
        conversations: Conversations object with both conversation_a and conversation_b
        vote: VoteBody with user's vote choices
        request: FastAPI Request for IP and cookies

    Returns:
        dict: The saved vote record

    Process:
        1. Extract chosen model from radio selection
        2. Get conversation messages and convert to dict format
        3. Determine opening prompt and turn count
        4. Assemble metadata (system prompts, model pair, etc.)
        5. Write to JSON log file
        6. Call save_vote_to_db() for database persistence
    """

    t = datetime.now()

    conv_a = conversations.conversation_a
    conv_b = conversations.conversation_b
    chosen_model_name = (
        None
        if vote.chosen_llm == "both_equal"
        else getattr(conversations, f"conversation_{vote.chosen_llm}").model_name
    )

    vote_data = conversations.model_dump() | {
        "timestamp": str(t),
        # Vote
        "chosen_model_name": chosen_model_name,
        "both_equal": vote.chosen_llm == "both_equal",
    }

    for pos in {"a", "b"}:
        # Vote
        vote_data[f"conv_comments_{pos}"] = getattr(vote, f"comment_{pos}")
        for key in REACTIONS:
            vote_data[f"conv_{key}_{pos}"] = key in getattr(vote, f"prefs_{pos}")

        # Language model pairs specific
        conv = vote_data.pop(f"conversation_{pos}")
        for data_key, db_key in [
            ("model_name", "model_{}_name"),
            ("system_msg", "system_prompt_{}"),
            ("messages", "conversation_{}"),
        ]:
            vote_data[db_key.format(pos)] = conv[data_key]

    vote_record = VoteRecord(**vote_data)
    db_data = vote_record.model_dump(mode="json")

    vote_log_filename = f"vote-{t.year}-{t.month:02d}-{t.day:02d}-{t.hour:02d}-{t.minute:02d}-{conversations.session_hash}.json"
    vote_log_path = settings.LOGDIR / vote_log_filename
    with vote_log_path.open(mode="a") as fout:
        vote_string = chosen_model_name or "both_equal"
        logger.info(f"vote: {vote_string}", extra={"request": request, "data": db_data})
        for pos in {"a", "b"}:
            prefs = getattr(vote, f"prefs_{pos}")
            logger.info(f"preferences_{pos}: {prefs}", extra={"request": request})
            if comment := getattr(vote, f"comment_{pos}"):
                logger.info(
                    f"commentaires_{pos}: {comment}", extra={"request": request}
                )
        fout.write(json.dumps(db_data) + "\n")

    return save_vote_to_db(db_data)


# TODO since we can postprocess data from Conversations we could remove:
# - visitor_id
# - ip
# - model_pair_name
# - opening_msg
# - model_a_name
# - model_b_name
# - conv_a_id
# - conv_b_id
# - conversation_a
# - conversation_b
# Also based on refers_to_conv_id and msg_index we can postprocess:
# - model_pos
# - refers_to_model
# - system_prompt
# - response_content
# - question_content
# Also not sure that `question_id` is usefull
# And legacy:
# - chatbot_index
# - selected_category
# - is_unedited_prompt
class ReactionRecord(BaseModel):
    # Set with database defaults, not present in logs?
    # id: int | None = None
    # timestamp: datetime | None = None

    # Session
    session_hash: str
    visitor_id: str | None
    ip: str

    # Conversations
    conv_turns: int  # TODO rename to current_conv_turn_when_reacting?
    conversation_pair_id: str
    model_pair_name: Annotated[
        list[str], JSONSerializer
    ]  # FIXME, not sure what serialization is needed. Replace to string:string ?
    opening_msg: str

    # Language model pairs specific
    model_a_name: str
    model_b_name: str
    conv_a_id: str
    conv_b_id: str
    conversation_a: Annotated[list["ConversationMessageRecord"], JSONModelSerializer]
    conversation_b: Annotated[list["ConversationMessageRecord"], JSONModelSerializer]

    # Conversation
    model_pos: BotPos
    refers_to_model: str
    refers_to_conv_id: str
    system_prompt: str | None
    response_content: str
    question_content: str

    # Liked/disliked message data
    msg_index: int
    msg_rank: int
    chatbot_index: int
    question_id: str

    # Reaction
    liked: bool
    disliked: bool
    comment: str
    useful: bool
    complete: bool
    creative: bool
    clear_formatting: bool
    incorrect: bool
    superficial: bool
    instructions_not_followed: bool

    # Additional? (not found in record_reaction but present in reactions.sql)
    # archived: bool = False

    # FIXME add?
    # country_portal: CountryPortal
    # cohorts: str


def delete_reaction(
    conv: Conversation,
    msg_index: int,  # FIXME normalize msg_index with `record_reaction`
) -> dict:
    """
    Delete a single message's reaction when the user removes feedback (like == None).

    Args:
        msg_index: explicit assistant index of message (counting system message) FIXME

     Returns:
        dict: delete result
    """
    delete_reaction_in_db(msg_index=msg_index, refers_to_conv_id=conv.conv_id)

    return {
        "msg_index": msg_index,
        "refers_to_conv_id": conv.conv_id,
    }


def record_reaction(
    conversations: Conversations,
    reaction: ReactionData,
    msg_index: int,
    request: Request,
) -> dict:
    """
    Record a single message reaction (like/dislike + preferences).

    Handles individual reactions to specific bot responses. Uses UPSERT logic
    to allow users to change reactions without creating duplicates.

    Args:
        conversations: Conversations
        reaction: ReactionData with index not counting system message
        msg_index: explicit assistant index of message (counting system message) FIXME
        request:  FastAPI Request for IP and cookies

    Returns:
        dict: The saved reaction record

    Special Handling:
        - Uses UPSERT to allow reaction changes
        - Handles system prompt offsets in message indexing
    """

    conv_a = conversations.conversation_a
    conv_b = conversations.conversation_b
    conv = conv_a if reaction.bot == "a" else conv_b

    t = datetime.now()  # FIXME
    reaction_data = (
        # Conversations
        conversations.model_dump()
        | {
            # Conversation
            "model_pos": reaction.bot,
            "refers_to_model": conv.model_name,
            "refers_to_conv_id": conv.conv_id,
            "system_prompt": conv.system_msg,
            "response_content": conv.messages[msg_index].content,
            "question_content": conv.messages[msg_index - 1].content,
            # Liked/disliked message data
            "msg_index": msg_index,  # Counting system message
            "msg_rank": (
                reaction.index // 2  # Rank begins at zero (not counting system message)
            ),
            "chatbot_index": reaction.index,  # FIXME legacy to remove index from old front chatbot index
            "question_id": f"{conversations.conversation_pair_id}-{reaction.index // 2}",
            # Reaction
            "liked": reaction.liked is True,
            "disliked": reaction.liked is False,
            "comment": reaction.comment,
        }
        | {
            # Reaction
            key: key in reaction.prefs
            for key in REACTIONS
        }
    )

    # Language model pairs specific
    for pos in {"a", "b"}:
        _conv = reaction_data.pop(f"conversation_{pos}")
        for data_key, db_key in [
            ("model_name", "model_{}_name"),
            ("conv_id", "conv_{}_id"),
            ("messages", "conversation_{}"),
        ]:
            reaction_data[db_key.format(pos)] = _conv[data_key]

    reaction_record = ReactionRecord(**reaction_data)
    db_data = reaction_record.model_dump(mode="json")

    reaction_log_filename = f"reaction-{t.year}-{t.month:02d}-{t.day:02d}-{t.hour:02d}-{t.minute:02d}-{conversations.session_hash}.json"
    reaction_log_path = settings.LOGDIR / reaction_log_filename
    with reaction_log_path.open(mode="a") as fout:
        fout.write(json.dumps(db_data) + "\n")
    logger.info(f"saved_reaction: {json.dumps(db_data)}", extra={"request": request})

    return upsert_reaction_to_db(db_data)


class ConversationMessageRecord(BaseModel):
    """
    Model to parse AnyMessage, clean and filter out message's empty metadata
    for db/logs.
    """

    class MessageMetadata(BaseModel):
        generation_id: str
        output_tokens: int
        duration: float

    role: MessageRole
    content: str
    reasoning_content: Annotated[
        str | None, Field(validation_alias="reasoning", exclude_if=is_not)
    ] = None
    metadata: Annotated[MessageMetadata | None, Field(exclude_if=is_not)] = None


# TODO some field could be postprocessed or removed:
# - conv_turns
# - total_conv_a_output_tokens
# - total_conv_b_output_tokens
# - opening_msg
# And legacy:
# - selected_category
# - is_unedited_prompt
class ConversationsRecord(BaseModel):
    """
    Database/logs record for a paired conversation comparison.

    Stores complete conversation data from both models for PostgreSQL persistence.
    This is the model used for database operations and post-processing.

    We do not use serialization on Conversations model but define here another model
    to make sure data is of database expected type.
    """

    # Set from database defaults, not present in logs?
    # id: int | None = None
    # timestamp: datetime | None = None

    # Session
    session_hash: str
    visitor_id: str | None
    ip: str
    country_portal: CountryPortal
    cohorts: str

    # Conversations
    selected_category: Annotated[str | None, Field(validation_alias="category")]
    mode: SelectionMode
    custom_models_selection: Annotated[
        list[str] | None, JSONSerializer
    ]  # FIXME, not sure what serialization is needed. Replace to string:string ?
    conv_turns: int
    conversation_pair_id: str
    model_pair_name: Annotated[
        list[str], JSONSerializer
    ]  # FIXME, not sure what serialization is needed. Replace to string:string ?
    opening_msg: str
    is_unedited_prompt: bool

    # Language model pairs specific
    model_a_name: str
    model_b_name: str
    conv_a_id: str
    conv_b_id: str
    system_prompt_a: str | None
    system_prompt_b: str | None
    conversation_a: Annotated[list[ConversationMessageRecord], JSONModelSerializer]
    conversation_b: Annotated[list[ConversationMessageRecord], JSONModelSerializer]
    total_conv_a_output_tokens: int
    total_conv_b_output_tokens: int

    # Additional? (not found in record_conversations but present in conversations.sql)
    # archived: bool = False
    # short_summary: str | None = None
    # ip_map: str | None = None
    # keywords: dict[str, Any] | None = None
    # categories: dict[str, Any] | None = None
    # languages: dict[str, Any] | None = None
    # pii_analyzed: bool = False
    # contains_pii: bool | None = None
    # conversation_a_pii_removed: Any = None  # JSONB
    # conversation_b_pii_removed: Any = None  # JSONB

    # TODO: add 'interrupted' bool field?
    # TODO: add `error: boolean` or `error_message: str`, `conv_a|b_error: str`?


def record_conversations(
    conversations: Conversations,
) -> dict:
    """
    Record or update the conversation pair to database and JSON log files after each turn.

    Args:
        conversations: Conversations object with both conversation_a and conversation_b
        session_hash: Session identifier
        request: FastAPI Request for IP and cookies
        locale: Country portal code (e.g., "fr", "en") - optional
        cohorts_comma_separated: Liste de nom de cohorts sous for de str comma separated ou None

    Returns:
        dict: The saved serialized ConversationsRecord
    """

    t = datetime.now()  # FIXME
    convs_data = conversations.model_dump()

    # Language model pairs specific
    for pos in {"a", "b"}:
        conv = convs_data.pop(f"conversation_{pos}")
        for data_key, db_key in [
            ("model_name", "model_{}_name"),
            ("conv_id", "conv_{}_id"),
            ("system_msg", "system_prompt_{}"),
            ("messages", "conversation_{}"),
            ("tokens", "total_conv_{}_output_tokens"),
        ]:
            convs_data[db_key.format(pos)] = conv[data_key]

    convs_record = ConversationsRecord(**convs_data)

    logger.debug(
        f"record_conversations - conv_pair_id={convs_record.conversation_pair_id}, cohorts={convs_record.cohorts}, type={type(convs_record.cohorts)}"
    )

    db_data = convs_record.model_dump(mode="json")

    conv_log_path = settings.LOGDIR / f"conv-{convs_record.conversation_pair_id}.json"
    # Always rewrite the file
    conv_log_path.write_text(json.dumps(db_data) + "\n")

    return upsert_conv_to_db(db_data)
