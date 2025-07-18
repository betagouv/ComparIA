import gradio as gr

import os


import json
import logging

import datetime


from languia.utils import (
    get_chosen_model_name,
    messages_to_dict_list,
    is_unedited_prompt,
    count_turns,
    get_ip,
    get_matomo_tracker_from_cookies,
)

LOGDIR = os.getenv("LOGDIR", "./data")


import psycopg2
from psycopg2 import sql


class JSONFormatter(logging.Formatter):
    def format(self, record):

        msg = super().format(record)

        log_data = {"message": msg}

        if hasattr(record, "request"):
            try:
                log_data["query_params"] = dict(record.request.query_params)
                log_data["path_params"] = dict(record.request.path_params)
                # TODO: remove IP?
                log_data["ip"] = get_ip(record.request)
                log_data["session_hash"] = record.request.session_hash
            
            except:
                pass
        if hasattr(record, "extra"):
            log_data["extra"] = record.extra
            
        return json.dumps(log_data)


class PostgresHandler(logging.Handler):
    def __init__(self, dsn):
        super().__init__()
        self.dsn = dsn
        self.connection = None

    def connect(self):
        if not self.connection or self.connection.closed:
            try:
                self.connection = psycopg2.connect(self.dsn)
            except psycopg2.Error as e:
                print(f"Error connecting to database: {e}")

    def emit(self, record):

        assert isinstance(record, logging.LogRecord)
        # print((record.__dict__))
        # print("LoggingHandler received LogRecord: {}".format(record))

        # record = super().format(record)
        self.format(record)

        try:
            self.connect()
            if self.connection:
                with self.connection.cursor() as cursor:

                    # del(record.__dict__["request"])

                    insert_statement = sql.SQL(
                        """
                        INSERT INTO logs (time, level, message, query_params, path_params, session_hash, extra)
                        VALUES (%(time)s, %(level)s, %(message)s, %(query_params)s, %(path_params)s, %(session_hash)s, %(extra)s)
                    """
                    )
                    values = {
                        "time": record.asctime,
                        "level": record.levelname,
                        "message": record.message,
                    }
                    if hasattr(record, "extra"):
                        values["extra"] = json.dumps(record.__dict__.get("extra"))
                    else:
                        values["extra"] = "{}"
                    if hasattr(record, "request"):
                        query_params = dict(record.request.query_params)
                        path_params = dict(record.request.path_params)
                        # ip = get_ip(record.request)
                        session_hash = record.request.session_hash
                        values["query_params"] = json.dumps(query_params)
                        values["path_params"] = json.dumps(path_params)
                        values["session_hash"] = str(session_hash)
                    else:
                        values["query_params"] = "{}"
                        values["path_params"] = "{}"
                        values["session_hash"] = ""

                    cursor.execute(insert_statement, values)
                    self.connection.commit()
        except psycopg2.Error as e:
            # Don't use logger on purpose to avoid endless loops
            print(f"Error logging to Postgres: {e}")
            # Could do:
            # self.handleError(record)


def save_vote_to_db(data):
    from languia.config import db as dsn

    logger = logging.getLogger("languia")
    if not dsn:
        logger.warn("Cannot log to db: no db configured")
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
    logger = logging.getLogger("languia")
    from languia.config import get_model_system_prompt

    chosen_model_name = get_chosen_model_name(which_model_radio, conversations)
    both_equal = chosen_model_name is None
    conversation_a_messages = messages_to_dict_list(conversations[0].messages)
    conversation_b_messages = messages_to_dict_list(conversations[1].messages)

    t = datetime.datetime.now()

    model_pair_name = sorted(filter(None, [conversations[0].model_name, conversations[1].model_name]))

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
        "system_prompt_b": get_model_system_prompt(conversations[1].model_name),        "conversation_pair_id": conversations[0].conv_id
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
            f'preferences_a: {details["prefs_a"]}',
            extra={"request": request},
        )
        logger.info(
            f'preferences_b: {details["prefs_b"]}',
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
    logger = logging.getLogger("languia")
    from languia.config import db as dsn

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
            country, 
            city, 
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
            %(country)s, 
            %(city)s, 
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
            country = EXCLUDED.country,
            city = EXCLUDED.city,
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

        # TODO:
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
    logger = logging.getLogger("languia")
    from languia.config import db as dsn

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

        # if "comment" in data:
        #     print("comment:")
        #     print(data["comment"])

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
            question_content = chatbot[chatbot_index-1]['content']
        elif role == "b":
            question_content = chatbot[chatbot_index-2]['content']
        else:
            # if no role available: alternatively, if message before is a bot's, then it's the message even before
            if chatbot[chatbot_index-1]['role'] == "bot":
                question_content = chatbot[chatbot_index-2]['content']
            else:
                question_content = chatbot[chatbot_index-1]['content']
        
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
        "country": "",
        "city": "",
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
    # print(json.dumps(data))
    upsert_reaction_to_db(data=data, request=request)

    return data


def upsert_conv_to_db(data):

    from languia.config import db as dsn

    logger = logging.getLogger("languia")
    if not dsn:
        logger.warn("Cannot log to db: no db configured")
        return

    conn = None
    cursor = None

    try:
        conn = psycopg2.connect(dsn)
        cursor = conn.cursor()
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
                country,
                city,
                model_pair_name,
                opening_msg,
                selected_category,
                is_unedited_prompt,
                mode,
                custom_models_selection 
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
                %(country)s,
                %(city)s,
                %(model_pair_name)s,
                %(opening_msg)s,
                %(selected_category)s,
                %(is_unedited_prompt)s,
                %(mode)s,
                %(custom_models_selection)s
            )
            ON CONFLICT (conversation_pair_id)
            DO UPDATE SET
                conversation_a = EXCLUDED.conversation_a,
                conversation_b = EXCLUDED.conversation_b,
                conv_turns = EXCLUDED.conv_turns
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


# TODO: save the beginning of conversation (i.e. when first user msg is sent) instead of time of first db insertion
def record_conversations(
    app_state_scoped,
    conversations,
    request: gr.Request,
):
    from languia.config import get_model_system_prompt
    # logger = logging.getLogger("languia")

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
        "country": "",
        "city": "",
        "model_pair_name": model_pair_name,
        "mode": str(mode),
        "custom_models_selection": json.dumps(custom_models_selection)
    }

    conv_log_filename = f"conv-{conv_pair_id}.json"
    conv_log_path = os.path.join(LOGDIR, conv_log_filename)

    # Always rewrite the file
    with open(conv_log_path, "w") as fout:
        fout.write(json.dumps(data) + "\n")
    # print(json.dumps(data))
    upsert_conv_to_db(data=data)

    return data
