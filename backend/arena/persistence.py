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
from typing import Any

import psycopg2
from fastapi import Request
from psycopg2 import sql

from backend.arena.models import Conversations
from backend.arena.utils import (
    count_turns,
    get_matomo_tracker_from_cookies,
    is_unedited_prompt,
    sum_tokens,
)
from backend.config import settings
from backend.utils.user import get_ip

logger = logging.getLogger("languia")

# Directory for JSON backup files
LOGDIR = os.getenv("LOGDIR", "./data")
os.makedirs(LOGDIR, exist_ok=True)


def get_db_connection():
    """Get PostgreSQL database connection."""
    return psycopg2.connect(settings.DATABASE_URI)


def save_vote_to_db(data: dict) -> dict:
    """
    Save a vote to the database.

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
        insert_query = sql.SQL(
            """
            INSERT INTO votes (
                conversation_pair_id,
                chosen_model,
                session_hash,
                ip_address,
                matomo_visitor_id,
                tstamp,
                conv_turns,
                category,
                mode,
                opening_msg,
                is_unedited_prompt,
                positive_a,
                positive_b,
                negative_a,
                negative_b,
                model_a,
                model_b,
                model_a_tokens,
                model_b_tokens
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """
        )

        cursor.execute(
            insert_query,
            (
                data["conversation_pair_id"],
                data.get("chosen_model"),
                data["session_hash"],
                data.get("ip_address"),
                data.get("matomo_visitor_id"),
                data["tstamp"],
                data.get("conv_turns"),
                data.get("category"),
                data.get("mode"),
                data.get("opening_msg"),
                data.get("is_unedited_prompt"),
                data.get("positive_a"),
                data.get("positive_b"),
                data.get("negative_a"),
                data.get("negative_b"),
                data.get("model_a"),
                data.get("model_b"),
                data.get("model_a_tokens"),
                data.get("model_b_tokens"),
            ),
        )

        conn.commit()
        logger.info(f"[DB] Saved vote for {data['conversation_pair_id']}")

        # Write JSON backup file
        t = datetime.fromisoformat(data["tstamp"])
        filename = f"vote-{t.year}-{t.month:02d}-{t.day:02d}-{t.hour:02d}-{t.minute:02d}-{data['session_hash']}.json"
        filepath = os.path.join(LOGDIR, filename)
        with open(filepath, "w") as f:
            f.write(json.dumps(data, indent=2) + "\n")

        return data

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


def upsert_reaction_to_db(data: dict) -> dict:
    """
    UPSERT a reaction to the database.

    Uses ON CONFLICT to update existing reactions or insert new ones.

    Args:
        data: Reaction data dict with all fields

    Returns:
        dict: The saved reaction data

    Raises:
        psycopg2.Error: If database operation fails
    """
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # SQL UPSERT for reactions table
        upsert_query = sql.SQL(
            """
            INSERT INTO reactions (
                refers_to_conv_id,
                msg_index,
                msg_rank,
                question_id,
                session_hash,
                ip_address,
                matomo_visitor_id,
                tstamp,
                reaction_type,
                bot_position,
                model_name,
                category,
                mode,
                opening_msg,
                is_unedited_prompt,
                conv_turns,
                user_message,
                bot_message
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (refers_to_conv_id, msg_index)
            DO UPDATE SET
                reaction_type = EXCLUDED.reaction_type,
                tstamp = EXCLUDED.tstamp,
                matomo_visitor_id = EXCLUDED.matomo_visitor_id
        """
        )

        cursor.execute(
            upsert_query,
            (
                data["refers_to_conv_id"],
                data["msg_index"],
                data.get("msg_rank"),
                data.get("question_id"),
                data["session_hash"],
                data.get("ip_address"),
                data.get("matomo_visitor_id"),
                data["tstamp"],
                data.get("reaction_type"),
                data.get("bot_position"),
                data.get("model_name"),
                data.get("category"),
                data.get("mode"),
                data.get("opening_msg"),
                data.get("is_unedited_prompt"),
                data.get("conv_turns"),
                data.get("user_message"),
                data.get("bot_message"),
            ),
        )

        conn.commit()
        logger.info(
            f"[DB] Upserted reaction for {data['refers_to_conv_id']} msg_index={data['msg_index']}"
        )

        # Write JSON backup file
        t = datetime.fromisoformat(data["tstamp"])
        filename = f"reaction-{t.year}-{t.month:02d}-{t.day:02d}-{t.hour:02d}-{t.minute:02d}-{data['session_hash']}.json"
        filepath = os.path.join(LOGDIR, filename)
        with open(filepath, "a") as f:
            f.write(json.dumps(data) + "\n")

        return data

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
    vote_data: Any,
    request: Request,
    mode: str | None = None,
    category: str | None = None,
) -> dict:
    """
    Record a vote to the database with all metadata.

    This is the high-level function that constructs the complete vote record
    and saves it to both PostgreSQL and JSON backup.

    Args:
        conversations: Conversations object with both conversation_a and conversation_b
        vote_data: VoteRequest with user's vote choices
        request: FastAPI Request for IP and cookies
        mode: Model selection mode (from session metadata)
        category: Prompt category (from session metadata)

    Returns:
        dict: The saved vote record
    """
    from backend.arena.utils import get_chosen_model, get_chosen_model_name

    conv_a = conversations.conversation_a
    conv_b = conversations.conversation_b

    # Extract conversation IDs
    conv_a_id = conv_a.conv_id
    conv_b_id = conv_b.conv_id
    conversation_pair_id = f"{conv_a_id}-{conv_b_id}"

    # Extract chosen model
    chosen_model = get_chosen_model(vote_data.which_model_radio_output)
    chosen_model_name = get_chosen_model_name(
        vote_data.which_model_radio_output, (conv_a, conv_b)
    )

    # Get user context
    ip_address = get_ip(request)
    matomo_visitor_id = get_matomo_tracker_from_cookies(request.cookies)

    # Get opening message
    opening_msg = None
    if conv_a.messages and len(conv_a.messages) > 0:
        # First user message (skip system if present)
        for msg in conv_a.messages:
            if msg.role == "user":
                opening_msg = msg.content
                break

    # Count turns
    conv_turns = count_turns(conv_a.messages)

    # Calculate tokens
    model_a_tokens = sum_tokens(conv_a.messages)
    model_b_tokens = sum_tokens(conv_b.messages)

    # Build vote data dict
    data = {
        "conversation_pair_id": conversation_pair_id,
        "chosen_model": chosen_model,
        "session_hash": request.headers.get("X-Session-Hash", ""),
        "ip_address": ip_address,
        "matomo_visitor_id": matomo_visitor_id,
        "tstamp": datetime.now().isoformat(),
        "conv_turns": conv_turns,
        "category": category,
        "mode": mode,
        "opening_msg": opening_msg,
        "is_unedited_prompt": (
            is_unedited_prompt(opening_msg, category)
            if opening_msg and category
            else False
        ),
        "positive_a": vote_data.positive_a_output,
        "positive_b": vote_data.positive_b_output,
        "negative_a": vote_data.negative_a_output,
        "negative_b": vote_data.negative_b_output,
        "model_a": conv_a.model_name,
        "model_b": conv_b.model_name,
        "model_a_tokens": model_a_tokens,
        "model_b_tokens": model_b_tokens,
    }

    # Save to database
    return save_vote_to_db(data)


def record_reaction(
    conversations: Conversations,
    reaction_data: dict,
    session_hash: str,
    request: Request,
    mode: str | None = None,
    category: str | None = None,
) -> dict:
    """
    Record a reaction (like/dislike) to the database.

    Args:
        conversations: Conversations object with both conversation_a and conversation_b
        reaction_data: Reaction dict from frontend (Gradio format with index, value, liked)
        session_hash: Session identifier
        request: FastAPI Request for IP and cookies
        mode: Model selection mode (from session metadata)
        category: Prompt category (from session metadata)

    Returns:
        dict: The saved reaction record, or delete result if reaction was cleared
    """
    conv_a = conversations.conversation_a
    conv_b = conversations.conversation_b

    # Extract reaction details
    msg_index = reaction_data.get("index")
    reaction_value = reaction_data.get("value")
    liked = reaction_data.get("liked")

    if msg_index is None:
        raise ValueError("Missing reaction index")

    # Calculate msg_rank (which exchange in the conversation)
    msg_rank = msg_index // 2

    # Determine bot position (which conversation the reaction is for)
    bot_position = None
    model_name = None
    bot_message = None

    # Get the message at this index from conversation A
    # The reaction index corresponds to pairs of messages (user + assistant)
    message_position = msg_index * 2 + 1  # Assistant message position

    if message_position < len(conv_a.messages):
        msg = conv_a.messages[message_position]
        if msg.role == "assistant":
            bot_message = msg.content
            # Check if this message has metadata indicating bot position
            if hasattr(msg, "metadata") and msg.metadata:
                metadata_dict = (
                    msg.metadata.model_dump()
                    if hasattr(msg.metadata, "model_dump")
                    else msg.metadata
                )
                bot_position = metadata_dict.get("bot", "a")
                model_name = (
                    conv_a.model_name if bot_position == "a" else conv_b.model_name
                )

    # Get user message (previous message)
    user_message = None
    if message_position > 0 and message_position - 1 < len(conv_a.messages):
        user_msg = conv_a.messages[message_position - 1]
        if user_msg.role == "user":
            user_message = user_msg.content

    # Get opening message
    opening_msg = None
    for msg in conv_a.messages:
        if msg.role == "user":
            opening_msg = msg.content
            break

    # Handle reaction deletion (when user un-likes/un-dislikes)
    if liked is False or reaction_value is None:
        # Delete reaction
        conv_a_id = conv_a.conv_id
        return delete_reaction_in_db(msg_index, conv_a_id)

    # Determine reaction type
    reaction_type = None
    if liked is True:
        reaction_type = "like"
    elif liked is False:
        reaction_type = "dislike"

    # Get user context
    ip_address = get_ip(request)
    matomo_visitor_id = get_matomo_tracker_from_cookies(request.cookies)

    # Count turns
    conv_turns = count_turns(conv_a.messages)

    # Build conversation IDs
    conv_a_id = conv_a.conv_id
    conv_b_id = conv_b.conv_id
    conversation_pair_id = f"{conv_a_id}-{conv_b_id}"
    question_id = f"{conversation_pair_id}-{msg_rank}"

    # Build reaction data dict
    data = {
        "refers_to_conv_id": conv_a_id,
        "msg_index": msg_index,
        "msg_rank": msg_rank,
        "question_id": question_id,
        "session_hash": session_hash,
        "ip_address": ip_address,
        "matomo_visitor_id": matomo_visitor_id,
        "tstamp": datetime.now().isoformat(),
        "reaction_type": reaction_type,
        "bot_position": bot_position,
        "model_name": model_name,
        "category": category,
        "mode": mode,
        "opening_msg": opening_msg,
        "is_unedited_prompt": (
            is_unedited_prompt(opening_msg, category)
            if opening_msg and category
            else False
        ),
        "conv_turns": conv_turns,
        "user_message": user_message,
        "bot_message": bot_message,
    }

    # Save to database
    return upsert_reaction_to_db(data)


def record_conversations(
    conversations: Conversations,
    session_hash: str,
    request: Request,
    locale: str,
    cohorts_comma_separated: str,
    custom_models_selection: tuple[str] | tuple[str, str] | None,
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
        dict: The saved conversation record

    Process:
        1. Extract messages from both conversations
        2. Get opening prompt (skip system prompt if present)
        3. Count conversation turns
        4. Determine category and mode from app state
        5. Calculate total output tokens for each model
        6. Write JSON log file (full overwrite)
        7. Call upsert_conv_to_db() for database
    """
    from datetime import datetime

    from backend.arena.utils import messages_to_dict_list

    conv_a = conversations.conversation_a
    conv_b = conversations.conversation_b

    conversation_a_messages = messages_to_dict_list(conv_a.messages)
    conversation_b_messages = messages_to_dict_list(conv_b.messages)

    model_pair_name = sorted([conv_a.model_name, conv_b.model_name])

    opening_msg = conv_a.messages[1 if conv_a.has_system_msg else 0]
    conv_turns = count_turns(conv_a.messages)
    t = datetime.now()  # FIXME

    conv_pair_id = conv_a.conv_id + "-" + conv_b.conv_id

    data = {
        "selected_category": conversations.category,
        "is_unedited_prompt": (is_unedited_prompt(opening_msg, conversations.category)),
        "model_a_name": conv_a.model_name,
        "model_b_name": conv_b.model_name,
        "opening_msg": conv_a.opening_msg,
        "conversation_a": json.dumps(conversation_a_messages),
        "conversation_b": json.dumps(conversation_b_messages),
        "conv_turns": conv_turns,
        "system_prompt_a": conv_a.system_msg,
        "system_prompt_b": conv_b.system_msg,
        "conversation_pair_id": conv_pair_id,
        "conv_a_id": conv_a.conv_id,
        "conv_b_id": conv_b.conv_id,
        "session_hash": session_hash,
        "visitor_id": (get_matomo_tracker_from_cookies(request.cookies)),
        # Warning: IP is a PII
        "ip": str(get_ip(request)),
        "model_pair_name": model_pair_name,
        "mode": conversations.mode,
        "custom_models_selection": json.dumps(custom_models_selection),
        "total_conv_a_output_tokens": sum_tokens(conv_a.messages),
        "total_conv_b_output_tokens": sum_tokens(conv_b.messages),
        "country_portal": locale,
        "cohorts": cohorts_comma_separated,
    }

    logger = logging.getLogger("languia")
    logger.debug(
        f"[COHORT] record_conversations - conv_pair_id={conv_pair_id}, cohorts_comma_separated={cohorts_comma_separated}, type={type(cohorts_comma_separated)}"
    )

    conv_log_filename = f"conv-{conv_pair_id}.json"
    conv_log_path = os.path.join(LOGDIR, conv_log_filename)

    # Always rewrite the file
    with open(conv_log_path, "w") as fout:
        fout.write(json.dumps(data) + "\n")

    return upsert_conv_to_db(data=data)
