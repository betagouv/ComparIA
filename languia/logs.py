"""
Logging and data persistence for ComparIA.

This module handles:
- JSON formatted logging to files and PostgreSQL
- Vote and reaction persistence to database
- Conversation history recording
- User preferences tracking
"""

import datetime
import json
import logging
import os
from typing import List

import gradio as gr

from backend.arena.models import Conversation
from backend.utils.user import get_ip
from languia.utils import (
    count_turns,
    get_chosen_model_name,
    get_matomo_tracker_from_cookies,
    is_unedited_prompt,
    messages_to_dict_list,
    sum_tokens,
)

# Directory for local log files (fallback if DB unavailable)
LOGDIR = os.getenv("LOGDIR", "./data")


import psycopg2
from psycopg2 import sql


def save_vote_to_db(data):
    """
    Save vote data to PostgreSQL database.

    Inserts or updates a vote record with comprehensive preference data.
    This function handles the final vote when a user selects a preferred model
    or marks them as equal, along with detailed preference ratings.

    Args:
        data: Dictionary containing vote fields:
            - timestamp: When the vote was cast
            - model_a_name, model_b_name: Model identifiers
            - chosen_model_name: Winner (None if both_equal)
            - both_equal: Boolean indicating tie
            - opening_msg: Initial user prompt
            - conversation_a, conversation_b: Full chat histories (JSON)
            - conv_turns: Number of conversation turns
            - selected_category: Category/use case for the prompt
            - is_unedited_prompt: Whether user modified prompt
            - system_prompt_a/b: System prompts used
            - ip, session_hash, visitor_id: User identification
            - Preference fields: useful, complete, creative, clear_formatting,
              incorrect, superficial, instructions_not_followed (for both models)
            - conv_comments_a/b: User feedback text

    Returns:
        None. Vote data is persisted to database.
    """
    from backend.config import settings

    dsn = settings.COMPARIA_DB_URI

    logger = logging.getLogger("languia")
    if not dsn:
        logger.warning("Cannot log to db: no db configured")
        return
    conn = psycopg2.connect(dsn)
    cursor = conn.cursor()
    try:
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

        # TODO: also increment redis counter
        # if data.get("country_portal") == "da":
        #     from languia.session import r

        #     if r:
        #         try:
        #             r.incr("danish_count")
        #         except Exception as e:
        #             logger.error(f"Error incrementing danish count in Redis: {e}")

    except Exception as e:
        logger.error(f"Error saving vote to db: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def vote_last_response(
    conversations,
    which_model_radio,
    category,
    details: list,
    request: gr.Request,
):
    """
    Record user's model preference vote and detailed feedback.

    Main event handler called when user submits voting form.
    Aggregates conversation state, user preferences, and feedback.
    Writes to both JSON log files (for backup) and PostgreSQL (for analysis).

    Args:
        conversations: List of 2 Conversation objects (model_a, model_b)
        which_model_radio: User's selection ("Model A", "Model B", or "Both equal")
        category: Problem category (e.g., "writing", "math", "coding")
        details: Dict containing:
            - prefs_a/b: List of selected preference tags for each model
            - comments_a/b: Text comments for each model
        request: Gradio request object with session_hash, IP, cookies

    Returns:
        dict: Vote data saved to database, including:
            - timestamp, model names, chosen model
            - full conversation histories
            - preference ratings
            - IP, session_hash, visitor_id
            - comment text

    Process:
        1. Extract chosen model from radio selection
        2. Get conversation messages and convert to dict format
        3. Determine opening prompt and turn count
        4. Assemble metadata (system prompts, model pair, etc.)
        5. Write to JSON log file
        6. Call save_vote_to_db() for database persistence
    """
    logger = logging.getLogger("languia")
    from languia.config import get_model_system_prompt

    chosen_model_name = get_chosen_model_name(which_model_radio, conversations)
    both_equal = chosen_model_name is None
    conversation_a_messages = messages_to_dict_list(conversations[0].messages)
    conversation_b_messages = messages_to_dict_list(conversations[1].messages)

    t = datetime.datetime.now()

    model_pair_name = sorted(
        filter(None, [conversations[0].model_name, conversations[1].model_name])
    )

    if conversations[0].messages[0].role == "system":
        opening_msg = conversations[0].messages[1].content
    else:
        opening_msg = conversations[0].messages[0].content

    data = {
        "timestamp": str(t),
        "model_a_name": conversations[0].model_name,
        "model_b_name": conversations[1].model_name,
        # sorted
        "model_pair_name": json.dumps(model_pair_name),
        "chosen_model_name": chosen_model_name,
        "both_equal": both_equal,
        "opening_msg": opening_msg,
        "conversation_a": json.dumps(conversation_a_messages),
        "conversation_b": json.dumps(conversation_b_messages),
        "conv_turns": count_turns((conversations[0].messages)),
        "selected_category": category,
        "is_unedited_prompt": (is_unedited_prompt(opening_msg, category)),
        "system_prompt_a": get_model_system_prompt(conversations[0].model_name),
        "system_prompt_b": get_model_system_prompt(conversations[1].model_name),
        "conversation_pair_id": conversations[0].conv_id
        + "-"
        + conversations[1].conv_id,
        # Warning: IP is a PII
        "ip": str(get_ip(request)),
        "session_hash": str(request.session_hash),
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
    vote_log_filename = f"vote-{t.year}-{t.month:02d}-{t.day:02d}-{t.hour:02d}-{t.minute:02d}-{request.session_hash}.json"
    vote_log_path = os.path.join(LOGDIR, vote_log_filename)
    with open(vote_log_path, "a") as fout:
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


def upsert_reaction_to_db(data, request):
    """
    Insert or update a reaction record in PostgreSQL using UPSERT.

    Allows users to change their reactions (like → dislike or vice versa)
    without creating duplicate records. Updates on conflict of
    (refers_to_conv_id, msg_index).

    Args:
        data: Reaction data dict (see record_reaction for fields)
        request: Gradio request object (for logging)

    Returns:
        dict: The inserted/updated data

    Database Operation:
        - Uses PostgreSQL UPSERT (INSERT ... ON CONFLICT ... DO UPDATE)
        - Key conflict: (refers_to_conv_id, msg_index)
        - Updates all fields except timestamps on conflict
    """
    logger = logging.getLogger("languia")
    from backend.config import settings

    dsn = settings.COMPARIA_DB_URI

    # Ensure database configuration exists
    if not dsn:
        logger.warning("Cannot log to db: no db configured")
        return

    conn = None
    cursor = None

    try:
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

        conn = psycopg2.connect(dsn)
        cursor = conn.cursor()
        cursor.execute(query, data)
        conn.commit()
        logger.info("Reaction data successfully saved to DB.")

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

    except Exception as e:
        logger.error(f"Error saving reaction to DB: {e}")
        logger.error(f"SQL: {query}")

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return data


def delete_reaction_in_db(msg_index, refers_to_conv_id):
    """
    Delete a reaction record from PostgreSQL.

    Called when user removes a reaction (changes from liked/disliked to none).
    Deletes exactly one reaction identified by message index and conversation ID.

    Args:
        msg_index: Message index in conversation
        refers_to_conv_id: Conversation ID

    Returns:
        dict: The deletion parameters for logging

    Database Operation:
        - Deletes single row matching (msg_index, refers_to_conv_id)
        - Safely handles missing records (no error if not found)
    """
    logger = logging.getLogger("languia")
    from backend.config import settings

    dsn = settings.COMPARIA_DB_URI

    # Ensure database configuration exists
    if not dsn:
        logger.warning("Cannot log to db: no db configured")
        return

    conn = None
    cursor = None
    data = {"msg_index": msg_index, "refers_to_conv_id": refers_to_conv_id}
    try:
        conn = psycopg2.connect(dsn)
        cursor = conn.cursor()
        query = sql.SQL(
            """DELETE FROM reactions
WHERE refers_to_conv_id = %(refers_to_conv_id)s
  AND msg_index = %(msg_index)s
"""
        )
        # Execute the delete query
        cursor.execute(query, data)
        conn.commit()
        logger.info("Reaction data deleted from DB.")

    except Exception as e:
        logger.error(f"Error deleting reaction from DB: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return data


def sync_reactions(conv_a, conv_b, chatbot, state_reactions, request):
    """
    Synchronize reaction updates from UI to database.

    Processes all pending reactions (likes/dislikes) from the merged 3-way chatbot
    view and records them individually to database. Handles message index mapping
    from 3-way view back to individual conversation indices.

    Args:
        conv_a: Conversation object for model A
        conv_b: Conversation object for model B
        chatbot: Merged 3-way chatbot list (alternating A/B/user messages)
        state_reactions: List of reaction objects from UI state, each containing:
            - index: Position in 3-way chatbot
            - liked: Boolean or None (True=like, False=dislike, None=undone)
            - prefs: List of preference tags
            - value: Response text content
            - comment: User comment text
        request: Gradio request object

    Returns:
        None. Reactions are persisted via record_reaction() calls.

    Logic:
        - Iterates through state_reactions
        - Maps 3-way chatbot index to individual conversation message index
        - Handles system prompt offsets (if present in conversation)
        - Calls record_reaction() for each reaction
    """

    for data in state_reactions:
        if data == None:
            continue
        chatbot_index = data["index"]
        role = chatbot[chatbot_index]["metadata"]["bot"]

        if data["liked"]:
            reaction = "liked"
        elif data["liked"] == False:
            reaction = "disliked"
        else:
            reaction = "none"

        # Alternative:
        # Index is from the 3-way chatbot, can associate it to conv a or conv b w/
        # role_index = chatbot_index % 3
        # system prompt doesn't influence msg_rank, only msg_index, should'nt if filtered in threeway conv?
        # TODO: save it as msg metadata instead?
        bot_msg_rank = chatbot_index // 3
        # FIXME: make msg_index be sent correctly from view... needs refacto to pass both convs to view instead of a merged one
        # skip rank * 2 past messages + 1 to get the bot message and not the user one + 1 if system prompt
        if role == "a" and conv_a.messages[0].role == "system":
            system_prompt_offset = 1
        elif role == "b" and conv_b.messages[0].role == "system":
            system_prompt_offset = 1
        else:
            system_prompt_offset = 0

        msg_index = bot_msg_rank * 2 + 1 + system_prompt_offset
        # FIXME: make msg_index be sent correctly from view... needs refacto to pass both convs to view instead of a merged one
        if role == "a":
            question_content = chatbot[chatbot_index - 1]["content"]
        elif role == "b":
            question_content = chatbot[chatbot_index - 2]["content"]
        else:
            # if no role available: alternatively, if message before is a bot's, then it's the message even before
            if chatbot[chatbot_index - 1]["role"] == "bot":
                question_content = chatbot[chatbot_index - 2]["content"]
            else:
                question_content = chatbot[chatbot_index - 1]["content"]

        record_reaction(
            conversations=[conv_a, conv_b],
            model_pos=role,
            msg_index=msg_index,
            chatbot_index=chatbot_index,
            question_content=question_content,
            response_content=data["value"],
            reaction=reaction,
            prefs=data.get("prefs", []),
            comment=data.get("comment", ""),
            request=request,
        )


def record_reaction(
    conversations,
    model_pos,
    # FIXME: msg_index is wrong because of formula in sync_reactions
    msg_index,
    chatbot_index,
    question_content,
    response_content,
    reaction,
    prefs,
    comment,
    request: gr.Request,
):
    """
    Record a single message reaction (like/dislike + preferences).

    Handles individual reactions to specific bot responses. Uses UPSERT logic
    to allow users to change reactions without creating duplicates.
    Also handles deleting reactions when user removes feedback.

    Args:
        conversations: List of 2 Conversation objects
        model_pos: Which model ("a" or "b")
        msg_index: Message index in the conversation
        chatbot_index: Index in the 3-way merged chatbot view
        question_content: User's question text
        response_content: Bot's response text
        reaction: "liked", "disliked", or "none" (undone)
        prefs: List of preference tags (useful, complete, creative, etc.)
        comment: User's comment text
        request: Gradio request object

    Returns:
        dict: Reaction data saved/deleted, including:
            - msg_rank: Which turn in conversation (msg_index // 2)
            - question_id: Unique ID combining pair_id and turn
            - All model/conversation context
            - IP, session_hash, visitor_id

    Special Handling:
        - reaction="none": Deletes reaction from database (undo)
        - Uses UPSERT to allow reaction changes
        - Handles system prompt offsets in message indexing
    """
    from languia.config import get_model_system_prompt

    logger = logging.getLogger("languia")
    if model_pos not in ["a", "b"]:
        raise gr.Error(f"Weird model_pos: {model_pos}")
    current_conversation = conversations[0] if model_pos == "a" else conversations[1]

    # a reaction has been undone and none replaced it
    if reaction == "none":
        delete_reaction_in_db(
            msg_index=msg_index, refers_to_conv_id=current_conversation.conv_id
        )
        return {
            "msg_index": msg_index,
            "refers_to_conv_id": current_conversation.conv_id,
        }

    conversation_a_messages = messages_to_dict_list(conversations[0].messages)
    conversation_b_messages = messages_to_dict_list(conversations[1].messages)

    model_pair_name = sorted([conversations[0].model_name, conversations[1].model_name])

    if conversations[0].messages[0].role == "system":
        opening_msg = conversations[0].messages[1].content
    else:
        opening_msg = conversations[0].messages[0].content

    conv_turns = count_turns((conversations[0].messages))
    t = datetime.datetime.now()
    refers_to_model = current_conversation.model_name
    # rank begins at zero
    msg_rank = msg_index // 2

    conversation_pair_id = conversations[0].conv_id + "-" + conversations[1].conv_id
    question_id = conversation_pair_id + "-" + str(msg_rank)
    data = {
        # id
        # "timestamp": t,
        "model_a_name": conversations[0].model_name,
        "model_b_name": conversations[1].model_name,
        "refers_to_model": refers_to_model,  # (model name)
        "msg_index": msg_index,
        "opening_msg": opening_msg,
        "conversation_a": json.dumps(conversation_a_messages),
        "conversation_b": json.dumps(conversation_b_messages),
        "model_pos": model_pos,
        # conversation can be longer if like is on older messages
        "conv_turns": conv_turns,
        "system_prompt": get_model_system_prompt(current_conversation.model_name),
        "conversation_pair_id": conversation_pair_id,
        "conv_a_id": conversations[0].conv_id,
        "conv_b_id": conversations[1].conv_id,
        "session_hash": str(request.session_hash),
        "visitor_id": (get_matomo_tracker_from_cookies(request.cookies)),
        "refers_to_conv_id": current_conversation.conv_id,
        # Warning: IP is a PII
        "ip": str(get_ip(request)),
        "comment": comment,
        "response_content": response_content,
        "question_content": question_content,
        "liked": reaction == "liked",
        "disliked": reaction == "disliked",
        "useful": "useful" in prefs,
        "complete": "complete" in prefs,
        "creative": "creative" in prefs,
        "clear_formatting": "clear-formatting" in prefs,
        "incorrect": "incorrect" in prefs,
        "superficial": "superficial" in prefs,
        "instructions_not_followed": "instructions-not-followed" in prefs,
        # Not asked:
        "chatbot_index": chatbot_index,
        "msg_rank": msg_rank,
        "model_pair_name": json.dumps(model_pair_name),
        "question_id": question_id,
    }

    reaction_log_filename = f"reaction-{t.year}-{t.month:02d}-{t.day:02d}-{t.hour:02d}-{t.minute:02d}-{request.session_hash}.json"
    reaction_log_path = os.path.join(LOGDIR, reaction_log_filename)
    with open(reaction_log_path, "a") as fout:
        fout.write(json.dumps(data) + "\n")
    logger.info(f"saved_reaction: {json.dumps(data)}", extra={"request": request})

    upsert_reaction_to_db(data=data, request=request)

    return data


def upsert_conv_to_db(data):
    """
    Insert or update a conversation record in PostgreSQL using UPSERT.

    Allows conversation data to be updated as users continue chatting.
    Uses conversation_pair_id as the unique key. Updates token counts and
    message histories while preserving other metadata.

    Args:
        data: Conversation data dict from record_conversations containing:
            - conversation_pair_id: Unique key for this pair
            - All fields from record_conversations (see docstring there)
            - total_conv_a/b_output_tokens: Token usage for each model

    Returns:
        dict: The inserted/updated data

    Database Operation:
        - Key: conversation_pair_id (text, unique)
        - On conflict: Updates message histories and token counts
        - On conflict: Updates country_portal only if EXCLUDED value exists
        - Preserves initial timestamps on updates
    """

    from backend.config import settings

    dsn = settings.COMPARIA_DB_URI

    logger = logging.getLogger("languia")
    if not dsn:
        logger.warning("Cannot log to db: no db configured")
        return

    conn = None
    cursor = None

    try:
        query = sql.SQL(
            # TODO: tstamp should be earlier
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

        conn = psycopg2.connect(dsn)
        cursor = conn.cursor()
        cursor.execute(query, data)
        conn.commit()
        logger.debug("Conversation data successfully saved to DB.")

    except Exception as e:
        logger.error(f"Error saving conversation to DB: {e}")

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return data


def record_conversations(
    app_state_scoped,
    conversations: List[Conversation],
    request: gr.Request,
    locale: str | None = None,
    cohorts_comma_separated: str | None = None,
):
    """
    Record complete conversation pair to database and JSON log files.

    Called when conversation ends or when collecting data.
    Captures full chat history, metadata, and token usage for both models.
    Uses UPSERT to allow updates as conversation continues.

    Args:
        app_state_scoped: Application state containing:
            - category: Problem category/use case
            - mode: Model selection mode (random, big-vs-small, etc.)
            - custom_models_selection: List of custom selected models (if mode=custom)
        conversations: List of 2 Conversation objects
        request: Gradio request object with session_hash, IP, cookies
        locale: Country portal code (e.g., "fr", "en") - optional
        cohorts_comma_separated: Liste de nom de cohorts sous for de str comma separated ou None

    Returns:
        dict: Conversation record saved, including:
            - conversation_pair_id: Unique pair identifier
            - Full message histories (JSON)
            - Total token counts for each model
            - System prompts used
            - Model pair name (sorted)
            - Category and mode
            - User tracking info (IP, session_hash, visitor_id)
            - Opening prompt text
            - Is the prompt unmodified

    Process:
        1. Extract messages from both conversations
        2. Get opening prompt (skip system prompt if present)
        3. Count conversation turns
        4. Determine category and mode from app state
        5. Calculate total output tokens for each model
        6. Write JSON log file (full overwrite)
        7. Call upsert_conv_to_db() for database
    """
    from languia.config import get_model_system_prompt

    conversation_a_messages = messages_to_dict_list(conversations[0].messages)
    conversation_b_messages = messages_to_dict_list(conversations[1].messages)

    model_pair_name = sorted([conversations[0].model_name, conversations[1].model_name])

    if conversations[0].messages[0].role == "system":
        opening_msg = conversations[0].messages[1].content
    else:
        opening_msg = conversations[0].messages[0].content

    conv_turns = count_turns((conversations[0].messages))
    t = datetime.datetime.now()

    conv_pair_id = conversations[0].conv_id + "-" + conversations[1].conv_id

    if hasattr(app_state_scoped, "category"):
        category = app_state_scoped.category
    else:
        category = None

    if hasattr(app_state_scoped, "mode"):
        mode = app_state_scoped.mode
    else:
        mode = None

    if hasattr(app_state_scoped, "custom_models_selection"):
        custom_models_selection = app_state_scoped.custom_models_selection
    else:
        custom_models_selection = []

    data = {
        "selected_category": category,
        "is_unedited_prompt": (is_unedited_prompt(opening_msg, category)),
        "model_a_name": conversations[0].model_name,
        "model_b_name": conversations[1].model_name,
        "opening_msg": opening_msg,
        "conversation_a": json.dumps(conversation_a_messages),
        "conversation_b": json.dumps(conversation_b_messages),
        "conv_turns": conv_turns,
        "system_prompt_a": get_model_system_prompt(conversations[0].model_name),
        "system_prompt_b": get_model_system_prompt(conversations[1].model_name),
        "conversation_pair_id": conv_pair_id,
        "conv_a_id": conversations[0].conv_id,
        "conv_b_id": conversations[1].conv_id,
        "session_hash": str(request.session_hash),
        "visitor_id": (get_matomo_tracker_from_cookies(request.cookies)),
        # Warning: IP is a PII
        "ip": str(get_ip(request)),
        "model_pair_name": model_pair_name,
        "mode": str(mode),
        "custom_models_selection": json.dumps(custom_models_selection),
        "total_conv_a_output_tokens": sum_tokens(conversations[0].messages),
        "total_conv_b_output_tokens": sum_tokens(conversations[1].messages),
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
    # print(json.dumps(data))
    upsert_conv_to_db(data=data)

    return data
