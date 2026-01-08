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
import os
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import psycopg2
from fastapi import Request
from psycopg2 import sql
from pydantic import BaseModel, Field, PlainSerializer, WrapSerializer, model_serializer

from backend.arena.models import (
    Conversations,
    MessageRole,
    ReactionData,
    VoteRequest,
)
from backend.arena.utils import (
    count_turns,
    get_matomo_tracker_from_cookies,
    is_unedited_prompt,
    messages_to_dict_list,
    sum_tokens,
)
from backend.config import CountryCode, SelectionMode, settings
from backend.utils.user import get_ip

if TYPE_CHECKING:
    from pydantic import SerializerFunctionWrapHandler

logger = logging.getLogger("languia")

JSONSerializer = PlainSerializer(lambda v: json.dumps(v))
JSONModelSerializer = WrapSerializer(lambda v, handler: json.dumps(handler(v)))


def get_db_connection():
    """Get PostgreSQL database connection."""
    return psycopg2.connect(settings.DATABASE_URI)


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
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # SQL INSERT for votes table
        insert_statement = sql.SQL(
            """
        INSERT INTO votes (
            timestamp, 
            model_a_name, 
            model_b_name, 
            model_pair_name, 
            chosen_model_name, 
            both_equal, 
            opening_msg, 
            conversation_a, 
            conversation_b, 
            conv_turns, 
            selected_category, 
            is_unedited_prompt, 
            system_prompt_a, 
            system_prompt_b, 
            conversation_pair_id, 
            ip, 
            session_hash, 
            visitor_id, 
            conv_useful_a, 
            conv_complete_a, 
            conv_creative_a, 
            conv_clear_formatting_a, 
            conv_incorrect_a, 
            conv_superficial_a, 
            conv_instructions_not_followed_a, 
            conv_useful_b, 
            conv_complete_b, 
            conv_creative_b, 
            conv_clear_formatting_b, 
            conv_incorrect_b, 
            conv_superficial_b, 
            conv_instructions_not_followed_b, 
            conv_comments_a, 
            conv_comments_b
        )
        VALUES (
            %(timestamp)s, 
            %(model_a_name)s, 
            %(model_b_name)s, 
            %(model_pair_name)s, 
            %(chosen_model_name)s, 
            %(both_equal)s, 
            %(opening_msg)s, 
            %(conversation_a)s, 
            %(conversation_b)s, 
            %(conv_turns)s, 
            %(selected_category)s, 
            %(is_unedited_prompt)s, 
            %(system_prompt_a)s, 
            %(system_prompt_b)s, 
            %(conversation_pair_id)s, 
            %(ip)s, 
            %(session_hash)s, 
            %(visitor_id)s, 
            %(conv_useful_a)s, 
            %(conv_complete_a)s, 
            %(conv_creative_a)s, 
            %(conv_clear_formatting_a)s, 
            %(conv_incorrect_a)s, 
            %(conv_superficial_a)s, 
            %(conv_instructions_not_followed_a)s, 
            %(conv_useful_b)s, 
            %(conv_complete_b)s, 
            %(conv_creative_b)s, 
            %(conv_clear_formatting_b)s, 
            %(conv_incorrect_b)s, 
            %(conv_superficial_b)s, 
            %(conv_instructions_not_followed_b)s, 
            %(conv_comments_a)s, 
            %(conv_comments_b)s
        )
    """
        )

        cursor.execute(insert_statement, data)
        conn.commit()

        logger.info(f"[DB] Saved vote for {data['conversation_pair_id']}")

        # TODO: also increment redis counter
        # if data.get("country_portal") == "da":
        #     from languia.session import r

        #     if r:
        #         try:
        #             r.incr("danish_count")
        #         except Exception as e:
        #             logger.error(f"Error incrementing danish count in Redis: {e}")

    except psycopg2.Error as e:
        logger.error(f"[DB] Error saving vote: {e}", exc_info=True)
        if conn:
            conn.rollback()
        raise

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return data


def upsert_reaction_to_db(data: dict, request: Request) -> dict:
    """
    UPSERT a reaction to the database.

    Uses ON CONFLICT to update existing reactions or insert new ones.

    Args:
        data: Reaction data dict (see record_reaction for fields)
        request: FastApi Request

    Returns:
        dict: The saved reaction data

    Database Operation:
        - Uses PostgreSQL UPSERT (INSERT ... ON CONFLICT ... DO UPDATE)
        - Key conflict: (refers_to_conv_id, msg_index)
        - Updates all fields except timestamps on conflict
    """
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # SQL UPSERT for reactions table
        query = sql.SQL(
            """
        INSERT INTO reactions (
            model_a_name, 
            model_b_name, 
            refers_to_model, 
            msg_index, 
            opening_msg, 
            conversation_a, 
            conversation_b, 
            model_pos, 
            conv_turns, 
            system_prompt, 
            conversation_pair_id, 
            conv_a_id, 
            conv_b_id, 
            refers_to_conv_id, 
            session_hash, 
            visitor_id, 
            ip, 
            response_content, 
            question_content, 
            liked, 
            disliked, 
            comment, 
            useful, 
            complete,
            creative, 
            clear_formatting, 
            incorrect, 
            superficial, 
            instructions_not_followed, 
            model_pair_name, 
            msg_rank,
            chatbot_index,
            question_id
        )
        VALUES (
            %(model_a_name)s, 
            %(model_b_name)s, 
            %(refers_to_model)s, 
            %(msg_index)s, 
            %(opening_msg)s, 
            %(conversation_a)s, 
            %(conversation_b)s, 
            %(model_pos)s, 
            %(conv_turns)s, 
            %(system_prompt)s, 
            %(conversation_pair_id)s, 
            %(conv_a_id)s, 
            %(conv_b_id)s, 
            %(refers_to_conv_id)s, 
            %(session_hash)s, 
            %(visitor_id)s, 
            %(ip)s, 
            %(response_content)s, 
            %(question_content)s, 
            %(liked)s, 
            %(disliked)s, 
            %(comment)s, 
            %(useful)s, 
            %(complete)s, 
            %(creative)s, 
            %(clear_formatting)s, 
            %(incorrect)s, 
            %(superficial)s, 
            %(instructions_not_followed)s, 
            %(model_pair_name)s, 
            %(msg_rank)s,
            %(chatbot_index)s,
            %(question_id)s
        )
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
        conn.commit()
        logger.info(
            f"[DB] Upserted reaction for {data['refers_to_conv_id']} msg_index={data['msg_index']}"
        )

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

    except psycopg2.Error as e:
        logger.error(f"[DB] Error upserting reaction: {e}", exc_info=True)
        if conn:
            conn.rollback()
        raise

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

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
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        delete_query = sql.SQL(
            """
            DELETE FROM reactions
            WHERE refers_to_conv_id = %s AND msg_index = %s
        """
        )

        cursor.execute(delete_query, (refers_to_conv_id, msg_index))
        deleted_count = cursor.rowcount

        conn.commit()
        logger.info(
            f"[DB] Deleted reaction for {refers_to_conv_id} msg_index={msg_index} (count={deleted_count})"
        )

        return {
            "deleted": deleted_count,
            "refers_to_conv_id": refers_to_conv_id,
            "msg_index": msg_index,
        }

    except psycopg2.Error as e:
        logger.error(f"[DB] Error deleting reaction: {e}", exc_info=True)
        if conn:
            conn.rollback()
        raise

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


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
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # SQL UPSERT for conversations table
        # FIXME add tstamp?

        upsert_query = sql.SQL(
            """
            INSERT INTO conversations (
                model_a_name,
                model_b_name,
                conversation_a,
                conversation_b,
                conv_turns,
                system_prompt_a,
                system_prompt_b,
                conversation_pair_id,
                conv_a_id,
                conv_b_id,
                session_hash,
                visitor_id,
                ip,
                model_pair_name,
                opening_msg,
                selected_category,
                is_unedited_prompt,
                mode,
                custom_models_selection,
                total_conv_a_output_tokens,
                total_conv_b_output_tokens,
                country_portal,
                cohorts
            )
            VALUES (
                %(model_a_name)s,
                %(model_b_name)s,
                %(conversation_a)s,
                %(conversation_b)s,
                %(conv_turns)s,
                %(system_prompt_a)s,
                %(system_prompt_b)s,
                %(conversation_pair_id)s,
                %(conv_a_id)s,
                %(conv_b_id)s,
                %(session_hash)s,
                %(visitor_id)s,
                %(ip)s,
                %(model_pair_name)s,
                %(opening_msg)s,
                %(selected_category)s,
                %(is_unedited_prompt)s,
                %(mode)s,
                %(custom_models_selection)s,
                %(total_conv_a_output_tokens)s,
                %(total_conv_b_output_tokens)s,
                %(country_portal)s,
                %(cohorts)s
            )
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
        conn.commit()
        logger.info(f"[DB] Upserted conversation {data['conversation_pair_id']}")

    except psycopg2.Error as e:
        logger.error(f"[DB] Error upserting conversation: {e}", exc_info=True)
        if conn:
            conn.rollback()
        raise

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return data


# ============================================================================
# High-Level Orchestration Functions
# ============================================================================


def record_vote(
    conversations: Conversations,
    vote: VoteRequest,
    session_hash: str,
    request: Request,
):
    """
    Record a vote to the database with all metadata.

    This is the high-level function that constructs the complete vote record
    and saves it to both PostgreSQL and JSON backup.

    Args:
        conversations: Conversations object with both conversation_a and conversation_b
        vote_data: VoteRequest with user's vote choices
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
    from backend.arena.utils import get_chosen_model, get_chosen_model_name

    conv_a = conversations.conversation_a
    conv_b = conversations.conversation_b

    chosen_model_name = get_chosen_model_name(
        vote.which_model_radio_output, [conv_a, conv_b]
    )
    both_equal = chosen_model_name is None

    conversation_a_messages = messages_to_dict_list(conv_a.messages)
    conversation_b_messages = messages_to_dict_list(conv_b.messages)

    t = datetime.now()

    model_pair_name = sorted(filter(None, [conv_a.model_name, conv_b.model_name]))
    opening_msg = conv_a.messages[1 if conv_a.has_system_msg else 0]

    details = {
        "prefs_a": [*vote.positive_a_output, *vote.negative_a_output],
        "prefs_b": [*vote.positive_b_output, *vote.negative_b_output],
        "comments_a": str(vote.comments_a_output),
        "comments_b": str(vote.comments_b_output),
    }

    data = {
        "timestamp": str(t),
        "model_a_name": conv_a.model_name,
        "model_b_name": conv_b.model_name,
        # sorted
        "model_pair_name": json.dumps(model_pair_name),
        "chosen_model_name": chosen_model_name,
        "both_equal": both_equal,
        "opening_msg": opening_msg,
        "conversation_a": json.dumps(conversation_a_messages),
        "conversation_b": json.dumps(conversation_b_messages),
        "conv_turns": count_turns((conv_a.messages)),
        "selected_category": conversations.category,
        "is_unedited_prompt": (is_unedited_prompt(opening_msg, conversations.category)),
        "system_prompt_a": conv_a.system_msg,
        "system_prompt_b": conv_b.system_msg,
        "conversation_pair_id": conv_a.conv_id + "-" + conv_b.conv_id,
        # Warning: IP is a PII
        "ip": str(get_ip(request)),
        "session_hash": session_hash,
        "visitor_id": (get_matomo_tracker_from_cookies(request.cookies)),
        "conv_useful_a": "useful" in details["prefs_a"],
        "conv_complete_a": "complete" in details["prefs_a"],
        "conv_creative_a": "creative" in details["prefs_a"],
        "conv_clear_formatting_a": "clear-formatting" in details["prefs_a"],
        "conv_incorrect_a": "incorrect" in details["prefs_a"],
        "conv_superficial_a": "superficial" in details["prefs_a"],
        "conv_instructions_not_followed_a": "instructions-not-followed"
        in details["prefs_a"],
        "conv_useful_b": "useful" in details["prefs_b"],
        "conv_complete_b": "complete" in details["prefs_b"],
        "conv_creative_b": "creative" in details["prefs_b"],
        "conv_clear_formatting_b": "clear-formatting" in details["prefs_b"],
        "conv_incorrect_b": "incorrect" in details["prefs_b"],
        "conv_superficial_b": "superficial" in details["prefs_b"],
        "conv_instructions_not_followed_b": "instructions-not-followed"
        in details["prefs_b"],
        "conv_comments_a": details["comments_a"],
        "conv_comments_b": details["comments_b"],
    }
    vote_string = chosen_model_name or "both_equal"

    vote_log_filename = f"vote-{t.year}-{t.month:02d}-{t.day:02d}-{t.hour:02d}-{t.minute:02d}-{session_hash}.json"
    vote_log_path = settings.LOGDIR / vote_log_filename
    with vote_log_path.open(mode="a") as fout:
        logger.info(f"vote: {vote_string}", extra={"request": request, "data": data})
        logger.info(
            f"preferences_a: {details['prefs_a']}",
            extra={"request": request},
        )
        logger.info(
            f"preferences_b: {details['prefs_b']}",
            extra={"request": request},
        )
        if details["comments_a"] != "":
            logger.info(
                f"commentaires_a: {details.get('comments_a', '')}",
                extra={"request": request},
            )
        if details["comments_b"] != "":
            logger.info(
                f"commentaires_b: {details.get('comments_b', '')}",
                extra={"request": request},
            )
        fout.write(json.dumps(data) + "\n")

    save_vote_to_db(data=data)

    return data


def record_reaction(
    conversations: Conversations,
    reaction: ReactionData,
    msg_index: int,
    session_hash: str,
    request: Request,
):
    """
    Record a single message reaction (like/dislike + preferences).

    Handles individual reactions to specific bot responses. Uses UPSERT logic
    to allow users to change reactions without creating duplicates.
    Also handles deleting reactions when user removes feedback.

    Args:
        conversations: Conversations
        reaction: ReactionData
        request:  FastAPI Request for IP and cookies

    Returns:
        dict: The saved reaction record, or delete result if reaction was cleared

    Special Handling:
        - reaction="none": Deletes reaction from database (undo)
        - Uses UPSERT to allow reaction changes
        - Handles system prompt offsets in message indexing
    """

    if reaction.bot not in ["a", "b"]:  # FIXME remove, is handled before
        raise Exception(f"Weird reaction.bot: {reaction.bot}")

    conv_a = conversations.conversation_a
    conv_b = conversations.conversation_b
    current_conversation = conv_a if reaction.bot == "a" else conv_b
    response_content = current_conversation.messages[msg_index].content
    question_content = current_conversation.messages[msg_index - 1].content

    # a reaction has been undone and none replaced it
    if reaction.liked is None:
        delete_reaction_in_db(
            msg_index=msg_index, refers_to_conv_id=current_conversation.conv_id
        )
        return {
            "msg_index": msg_index,
            "refers_to_conv_id": current_conversation.conv_id,
        }

    conversation_a_messages = messages_to_dict_list(conv_a.messages)
    conversation_b_messages = messages_to_dict_list(conv_b.messages)

    model_pair_name = sorted([conv_a.model_name, conv_b.model_name])

    opening_msg = conv_a.messages[1 if conv_a.has_system_msg else 0]
    conv_turns = count_turns(conv_a.messages)
    t = datetime.now()  # FIXME

    conv_pair_id = conv_a.conv_id + "-" + conv_b.conv_id
    refers_to_model = current_conversation.model_name

    # rank begins at zero # FIXME change in msg_index computing, need to reflect (used in peren code)
    msg_rank = msg_index // 2
    question_id = conv_pair_id + "-" + str(msg_rank)

    data = {
        # id
        # "timestamp": t,
        "model_a_name": conv_a.model_name,
        "model_b_name": conv_b.model_name,
        "refers_to_model": refers_to_model,  # (model name)
        "msg_index": msg_index,
        "opening_msg": opening_msg,
        "conversation_a": json.dumps(conversation_a_messages),
        "conversation_b": json.dumps(conversation_b_messages),
        "model_pos": reaction.bot,
        # conversation can be longer if like is on older messages
        "conv_turns": conv_turns,
        "system_prompt": current_conversation.system_msg,
        "conversation_pair_id": conv_pair_id,
        "conv_a_id": conv_a.conv_id,
        "conv_b_id": conv_b.conv_id,
        "session_hash": session_hash,
        "visitor_id": (get_matomo_tracker_from_cookies(request.cookies)),
        "refers_to_conv_id": current_conversation.conv_id,
        # Warning: IP is a PII
        "ip": str(get_ip(request)),
        "comment": reaction.comment,
        "response_content": response_content,
        "question_content": question_content,
        "liked": reaction.liked is True,
        "disliked": reaction.liked is False,
        "useful": "useful" in reaction.prefs,
        "complete": "complete" in reaction.prefs,
        "creative": "creative" in reaction.prefs,
        "clear_formatting": "clear-formatting" in reaction.prefs,
        "incorrect": "incorrect" in reaction.prefs,
        "superficial": "superficial" in reaction.prefs,
        "instructions_not_followed": "instructions-not-followed" in reaction.prefs,
        # Not asked:
        "chatbot_index": msg_index,  # chatbot_index, FIXME legacy? changes in msg_index to reflect?
        "msg_rank": msg_rank,  # FIXME used in peren pipeline, what should it be?
        "model_pair_name": json.dumps(model_pair_name),
        "question_id": question_id,
    }

    reaction_log_filename = f"reaction-{t.year}-{t.month:02d}-{t.day:02d}-{t.hour:02d}-{t.minute:02d}-{session_hash}.json"
    reaction_log_path = settings.LOGDIR / reaction_log_filename
    with reaction_log_path.open(mode="a") as fout:
        fout.write(json.dumps(data) + "\n")
    logger.info(f"saved_reaction: {json.dumps(data)}", extra={"request": request})

    upsert_reaction_to_db(data=data, request=request)

    return data


class ConversationMessageRecord(BaseModel):
    class MessageMetadata(BaseModel):
        generation_id: str | None
        output_tokens: int | None
        duration: float | None

        # FIXME remove in favor of Field(exclude_if=lambda v: v is None)
        @model_serializer(mode="wrap")
        def serialize_model(self, handler: "SerializerFunctionWrapHandler") -> str:
            serialized = handler(self)

            if self.generation_id is None:
                serialized.pop("generation_id")
            if self.duration in (None, 0):
                serialized.pop("duration")

            return json.dumps(serialized)

    role: MessageRole
    content: str
    reasoning_content: Annotated[str | None, Field(validation_alias="reasoning")] = None
    metadata: MessageMetadata | None = None

    # FIXME remove in favor of Field(exclude_if=lambda v: v is None)
    @model_serializer(mode="wrap")
    def serialize_model(self, handler: "SerializerFunctionWrapHandler") -> str:
        serialized = handler(self)

        if not self.reasoning_content:
            serialized.pop("reasoning_content")
        if not self.metadata:
            serialized.pop("metadata")

        return serialized


class ConversationsRecord(BaseModel):
    """
    Database/logs record for a paired conversation comparison.

    Stores complete conversation data from both models for PostgreSQL persistence.
    This is the model used for database operations and post-processing.

    We do not use serialization on Conversations model but define here another model
    to make sure data is of database expected type.
    """

    # Set with database defaults, not present in logs?
    # id: int | None = None
    # timestamp: datetime | None = None
    # Conversations args
    selected_category: Annotated[str | None, Field(validation_alias="category")]
    mode: SelectionMode

    custom_models_selection: Annotated[
        list[str] | None, JSONSerializer
    ]  # FIXME, not sure what serialization is needed
    is_unedited_prompt: bool
    # General
    conv_turns: int
    conversation_pair_id: str
    model_pair_name: Annotated[
        list[str], JSONSerializer
    ]  # FIXME, not sure what serialization is needed
    opening_msg: str
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
    # Identity
    session_hash: str
    visitor_id: str | None
    ip: str  # FIXME | None? cf get_ip()
    country_portal: CountryCode
    cohorts: str  # FIXME | None?
    # Additional? (not found in record_conversations but present in conversations.sql)
    # archived: bool | None = None
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


def record_conversations(
    conversations: Conversations,
    session_hash: str,
    request: Request,
    locale: str,
    cohorts_comma_separated: str,
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
    convs_data = conversations.model_dump() | {
        "session_hash": session_hash,
        "visitor_id": get_matomo_tracker_from_cookies(request.cookies),
        "ip": str(get_ip(request)),
        "country_portal": locale,
        "cohorts": cohorts_comma_separated,
    }

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
        f"[COHORT] record_conversations - conv_pair_id={convs_record.conversation_pair_id}, cohorts_comma_separated={convs_record.cohorts}, type={type(convs_record.cohorts)}"
    )

    data = convs_record.model_dump()  # FIXME exclude_none=True
    conv_log_path = settings.LOGDIR / f"conv-{convs_record.conversation_pair_id}.json"
    # Always rewrite the file
    conv_log_path.write_text(json.dumps(data) + "\n")

    return upsert_conv_to_db(data=data)
