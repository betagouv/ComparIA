import numpy as np
import os

import gradio as gr

# from jinja2 import Template
from jinja2 import Environment, FileSystemLoader

import json
import psycopg2
from psycopg2 import sql

# from fastchat.utils import (
#     moderation_filter,
# )

import logging

import datetime

import requests

from ecologits.tracers.utils import llm_impacts, compute_llm_impacts, electricity_mixes

from slugify import slugify

import traceback

LOGDIR = os.getenv("LOGDIR", "./data")


class ContextTooLongError(ValueError):
    def __str__(self):
        return "Context too long."

    pass


class EmptyResponseError(RuntimeError):
    def __init__(self, response=None, *args: object) -> None:
        super().__init__(*args)
        self.response = response

    def __str__(self):
        msg = "Empty response"
        return msg


class JSONFormatter(logging.Formatter):
    def format(self, record):

        msg = super().format(record)

        # Parse the message as JSON
        # try:
        #     log_data = json.loads(msg)
        # except json.JSONDecodeError:
        # Handle cases where the message isn't valid JSON
        log_data = {"message": msg}

        # if 'request' in record.args:
        if hasattr(record, "request"):
            # log_data = record.request
            # request_dict = record.request.kwargs
            log_data["query_params"] = dict(record.request.query_params)
            log_data["path_params"] = dict(record.request.path_params)
            # TODO: remove IP?
            log_data["ip"] = get_ip(record.request)
            log_data["session_hash"] = record.request.session_hash
            # if isinstance(request_dict, dict):
            #     request_json = json.dumps(request_dict)
            # delattr(record, 'request')
        if hasattr(record, "extra"):
            log_data["extra"] = record.extra
        # Add the args dictionary to the JSON payload
        # log_data.update(record.args)
        # Convert the updated dictionary back to JSON
        return json.dumps(log_data)


class PostgresHandler(logging.Handler):
    def __init__(self, db_config):
        super().__init__()
        self.db_config = db_config
        self.connection = None

    def connect(self):
        if not self.connection or self.connection.closed:
            try:
                self.connection = psycopg2.connect(**self.db_config)
            except psycopg2.Error as e:
                print(f"Error connecting to database: {e}")
                stacktrace = traceback.format_exc()
                print(f"Stacktrace: {stacktrace}")

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
            stacktrace = traceback.format_exc()
            print(f"Stacktrace: {stacktrace}")
            # Could do:
            # self.handleError(record)


def get_ip(request: gr.Request):
    # 'x-real-ip': '178.33.22.30', 'x-forwarded-for': '178.33.22.30', 'x-forwarded-host': 'languia.stg.cloud.culture.fr' 'x-original-forwarded-for': '88.185.32.248','cloud-protector-client-ip': '88.185.32.248', )
    if "cloud-protector-client-ip" in request.headers:
        ip = request.headers["cloud-protector-client-ip"]
    elif "x-original-forwarded-for" in request.headers:
        ip = request.headers["x-original-forwarded-for"]
    elif "x-forwarded-for" in request.headers:
        ip = request.headers["x-forwarded-for"]
    else:
        ip = request.client.host
    return ip


def get_chosen_model(which_model_radio):
    if which_model_radio in ["model-a", "model-b"]:
        chosen_model = which_model_radio
    else:
        chosen_model = None
    return chosen_model


def get_matomo_tracker_from_cookies(cookies):
    logger = logging.getLogger("languia")
    for cookie in cookies:
        if cookie[0].startswith("_pk_id."):
            logger.debug(f"Found matomo cookie: {cookie[0]}: {cookie[1]}")
            return cookie[1]
    return None


def get_chosen_model_name(which_model_radio, conversations):
    if which_model_radio == "model-a":
        chosen_model_name = conversations[0].model_name
    elif which_model_radio == "model-b":
        chosen_model_name = conversations[1].model_name
    else:
        chosen_model_name = None
    return chosen_model_name


def count_turns(messages):
    return len(messages) // 2


def is_unedited_prompt(opening_prompt, category):
    if not category:
        return False
    from languia.config import prompts_table

    return opening_prompt in prompts_table[category]


def save_vote_to_db(data):
    from languia.config import db as db_config

    logger = logging.getLogger("languia")
    if not db_config:
        logger.warn("Cannot log to db: no db configured")
        return
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()
    try:
        insert_statement = sql.SQL(
            """
            INSERT INTO votes (tstamp, model_a_name, model_b_name, model_pair_name, chosen_model_name, both_equal, opening_prompt, conversation_a, conversation_b, turns, selected_category, is_unedited_prompt, template, uuid, ip, session_hash, visitor_uuid, comments_a, extra, comments_b, details_a_positive, details_a_negative, details_b_positive, details_b_negative)
            VALUES (%(tstamp)s, %(model_a_name)s, %(model_b_name)s, %(model_pair_name)s, %(chosen_model_name)s, %(both_equal)s, %(opening_prompt)s, %(conversation_a)s, %(conversation_b)s, %(turns)s, %(selected_category)s, %(is_unedited_prompt)s, %(template)s, %(uuid)s, %(ip)s, %(session_hash)s, %(visitor_uuid)s, %(comments_a)s, %(extra)s, %(comments_b)s, %(details_a_positive)s, %(details_a_negative)s, %(details_b_positive)s, %(details_b_negative)s)

        """
        )
        # TODO: refacto, values should equal data
        values = {
            "tstamp": (data["tstamp"]),
            "model_a_name": str(data["model_a_name"]),
            "model_b_name": str(data["model_b_name"]),
            "model_pair_name": json.dumps(sorted(data["model_pair_name"])),
            "chosen_model_name": (data["chosen_model_name"]),
            "both_equal": (data["both_equal"]),
            "opening_prompt": str(data["opening_prompt"]),
            "conversation_a": json.dumps(data["conversation_a"]),
            "conversation_b": json.dumps(data["conversation_b"]),
            "turns": int(data["turns"]),
            "selected_category": (data["selected_category"]),
            "is_unedited_prompt": data["is_unedited_prompt"],
            "template": json.dumps(data["template"]),
            "uuid": str(data["uuid"]),
            "ip": str(data["ip"]),
            "session_hash": str(data["session_hash"]),
            "visitor_uuid": (data["visitor_uuid"]),
            "details_a_positive": (data["details_a_positive"]),
            "details_a_negative": (data["details_a_negative"]),
            "details_b_positive": (data["details_b_positive"]),
            "details_b_negative": (data["details_b_negative"]),
            "comments_a": (data["comments_a"]),
            "comments_b": (data["comments_b"]),
            "extra": json.dumps(data["extra"]),
        }
        cursor.execute(insert_statement, values)
        conn.commit()
    except Exception as e:
        logger.error(f"Error saving vote to db: {e}")
        stacktrace = traceback.format_exc()
        logger.error(f"Stacktrace: {stacktrace}", exc_info=True)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def upsert_reaction_to_db(data, request):
    logger = logging.getLogger("languia")
    from languia.config import db as db_config

    # Ensure database configuration exists
    if not db_config:
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
            template, 
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
            creative, 
            clear_formatting, 
            incorrect, 
            superficial, 
            instructions_not_followed, 
            model_pair_name, 
            msg_rank,
            chatbot_index
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
            %(template)s, 
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
            %(creative)s, 
            %(clear_formatting)s, 
            %(incorrect)s, 
            %(superficial)s, 
            %(instructions_not_followed)s, 
            %(model_pair_name)s, 
            %(msg_rank)s,
            %(chatbot_index)s
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
            template = EXCLUDED.template,
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
            creative = EXCLUDED.creative,
            clear_formatting = EXCLUDED.clear_formatting,
            incorrect = EXCLUDED.incorrect,
            superficial = EXCLUDED.superficial,
            instructions_not_followed = EXCLUDED.instructions_not_followed,
            model_pair_name = EXCLUDED.model_pair_name,
            msg_rank = EXCLUDED.msg_rank,
            chatbot_index = EXCLUDED.chatbot_index;
        """
        )
        
        # TODO:
        #     RETURNING
        # (CASE
        #     WHEN (pg_trigger_depth() = 0) THEN 'inserted'
        #     ELSE 'updated'
        # END) AS operation;

        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute(query, data)
        conn.commit()
        logger.info("Reaction data successfully saved to DB.")

    except Exception as e:
        logger.error(f"Error saving reaction to DB: {e}")
        logger.error(f"SQL: {query}")
        stacktrace = traceback.format_exc()
        logger.error(f"Stacktrace: {stacktrace}")

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return data


def delete_reaction_in_db(msg_index, refers_to_conv_id):
    logger = logging.getLogger("languia")
    from languia.config import db as db_config

    # Ensure database configuration exists
    if not db_config:
        logger.warning("Cannot log to db: no db configured")
        return

    conn = None
    cursor = None
    data = {"msg_index": msg_index, "refers_to_conv_id": refers_to_conv_id}
    try:
        conn = psycopg2.connect(**db_config)
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
        stacktrace = traceback.format_exc()
        logger.error(f"Stacktrace: {stacktrace}")

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return data


def messages_to_dict_list(messages):
    return [{"role": message.role, "content": message.content} for message in messages]


def vote_last_response(
    conversations,
    which_model_radio,
    category,
    details: list,
    request: gr.Request,
):
    logger = logging.getLogger("languia")

    chosen_model_name = get_chosen_model_name(which_model_radio, conversations)
    # intensity = get_intensity(which_model_radio)
    both_equal = chosen_model_name is None
    conversation_a_messages = messages_to_dict_list(conversations[0].messages)
    conversation_b_messages = messages_to_dict_list(conversations[1].messages)

    # >>> import geoip2.database
    # >>>
    # >>> # This creates a Reader object. You should use the same object
    # >>> # across multiple requests as creation of it is expensive.
    # >>> with geoip2.database.Reader('/path/to/GeoLite2-City.mmdb') as reader:
    # >>>
    # >>>     # Replace "city" with the method corresponding to the database
    # >>>     # that you are using, e.g., "country".
    # >>>     response = reader.city('203.0.113.0')
    # >>>
    # >>>     response.country.iso_code
    # 'US'
    # >>>     response.country.name
    # 'United States'
    # >>>     response.country.names['zh-CN']

    t = datetime.datetime.now()
    model_pair_name = sorted([conversations[0].model_name, conversations[1].model_name])
    opening_prompt = conversations[0].messages[0].content
    data = {
        "tstamp": str(t),
        "model_a_name": conversations[0].model_name,
        "model_b_name": conversations[1].model_name,
        # sorted
        "model_pair_name": model_pair_name,
        "chosen_model_name": chosen_model_name,
        "both_equal": both_equal,
        # "intensity": None,
        "opening_prompt": opening_prompt,
        "conversation_a": conversation_a_messages,
        "conversation_b": conversation_b_messages,
        "turns": count_turns((conversations[0].messages)),
        "selected_category": category,
        "is_unedited_prompt": (is_unedited_prompt(opening_prompt, category)),
        "template": (
            []
            if conversations[0].template_name == "zero_shot"
            else conversations[0].template
        ),
        "uuid": conversations[0].conv_id + "-" + conversations[1].conv_id,
        # Warning: IP is a PII
        "ip": str(get_ip(request)),
        "session_hash": str(request.session_hash),
        "visitor_uuid": (get_matomo_tracker_from_cookies(request.cookies)),
        "details_a_positive": (details["positive_a"]),
        "details_a_negative": (details["negative_a"]),
        "details_b_positive": (details["positive_b"]),
        "details_b_negative": (details["negative_b"]),
        "comments_a": details["comments_a"],
        "comments_b": details["comments_b"],
        # For redundance
        "extra": {
            "cookies": dict(request.cookies),
            "query_params": dict(request.query_params),
            "path_params": dict(request.path_params),
        },
    }
    vote_string = chosen_model_name or "both_equal"
    vote_log_filename = f"vote-{t.year}-{t.month:02d}-{t.day:02d}-{t.hour:02d}-{t.minute:02d}-{request.session_hash}.json"
    vote_log_path = os.path.join(LOGDIR, vote_log_filename)
    with open(vote_log_path, "a") as fout:
        logger.info(f"vote: {vote_string}", extra={"request": request, "data": data})
        logger.info(
            f'preferences_a: {details["positive_a"]},{details["negative_a"]}',
            extra={"request": request},
        )
        logger.info(
            f'preferences_b: {details["positive_b"]},{details["negative_b"]}',
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

        # Alternative:
        # Index is from the 3-way chatbot, can associate it to conv a or conv b w/
        # role_index = chatbot_index % 3
        # FIXME: don't forget to offset template messages if any
        # TODO: save it as msg metadata instead?
        bot_msg_rank = chatbot_index // 3
        # skip rank * 2 past messages + 1 to get the bot message and not the user one
        msg_index = bot_msg_rank * 2 + 1

        record_reaction(
            conversations=[conv_a, conv_b],
            model_pos=role,
            msg_index=msg_index,
            chatbot_index=chatbot_index,
            response_content=data["value"],
            reaction=reaction,
            request=request,
        )


def record_reaction(
    conversations,
    model_pos,
    msg_index,
    chatbot_index,
    response_content,
    reaction,
    request: gr.Request,
):
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

    if current_conversation.messages[msg_index].content.strip() != response_content:
        logger.warning(
            f"Incoherent content for liked message: '{response_content}' and '{current_conversation.messages[msg_index].content.strip()}'"
        )
        logger.warning(f"Calculated index: {msg_index}")

    model_pair_name = sorted([conversations[0].model_name, conversations[1].model_name])
    opening_prompt = conversations[0].messages[0].content
    conv_turns = count_turns((conversations[0].messages))
    t = datetime.datetime.now()
    refers_to_model = current_conversation.model_name
    # rank begins at zero
    msg_rank = msg_index // 2
    question_content = current_conversation.messages[msg_rank * 2].content

    liked = reaction == "liked"
    disliked = reaction == "disliked"

    data = {
        # id
        # "timestamp": t,
        "model_a_name": conversations[0].model_name,
        "model_b_name": conversations[1].model_name,
        "refers_to_model": refers_to_model,  # (model name)
        "msg_index": msg_index,
        "opening_msg": opening_prompt,
        "conversation_a": json.dumps(conversation_a_messages),
        "conversation_b": json.dumps(conversation_b_messages),
        "model_pos": model_pos,
        # conversation can be longer if like is on older messages
        "conv_turns": conv_turns,
        "template": json.dumps(
            []
            if conversations[0].template_name == "zero_shot"
            else conversations[0].template
        ),
        "conversation_pair_id": conversations[0].conv_id
        + "-"
        + conversations[1].conv_id,
        "conv_a_id": conversations[0].conv_id,
        "conv_b_id": conversations[1].conv_id,
        "session_hash": str(request.session_hash),
        "visitor_id": (get_matomo_tracker_from_cookies(request.cookies)),
        "refers_to_conv_id": current_conversation.conv_id,
        # Warning: IP is a PII
        "ip": str(get_ip(request)),
        "country": "",
        "city": "",
        "comment": None,
        "response_content": response_content,
        "question_content": question_content,
        "liked": liked,
        "disliked": disliked,
        "useful": None,
        "creative": None,
        "clear_formatting": None,
        "incorrect": None,
        "superficial": None,
        "instructions_not_followed": None,
        # Not asked:
        "chatbot_index": chatbot_index,
        "msg_rank": msg_rank,
        "model_pair_name": json.dumps(model_pair_name),
    }

    reaction_log_filename = f"reaction-{t.year}-{t.month:02d}-{t.day:02d}-{t.hour:02d}-{t.minute:02d}-{request.session_hash}.json"
    reaction_log_path = os.path.join(LOGDIR, reaction_log_filename)
    with open(reaction_log_path, "a") as fout:
        fout.write(json.dumps(data) + "\n")
    # print(json.dumps(data))
    upsert_reaction_to_db(data=data, request=request)

    return data


with open("./templates/welcome-modal.html", encoding="utf-8") as welcome_modal_file:
    welcome_modal_html = welcome_modal_file.read()

with open("./templates/header-arena.html", encoding="utf-8") as header_file:
    header_html = header_file.read()
    if os.getenv("GIT_COMMIT"):
        git_commit = os.getenv("GIT_COMMIT")
        header_html += f"<!-- Git commit: {git_commit} -->"

with open("./templates/footer.html", encoding="utf-8") as footer_file:
    footer_html = footer_file.read()


def get_sample_weight(model, broken_endpoints, sampling_weights, sampling_boost_models):
    if model in broken_endpoints:
        return 0
    # Give a 1 weight if model not in weights
    weight = sampling_weights.get(model, 1)
    # weight = sampling_weights.get(model, 0)
    if model in sampling_boost_models:
        weight *= 5
    return weight


def pick_endpoint(model_id, broken_endpoints):
    from languia.config import api_endpoint_info
    logger = logging.getLogger("languia")

    for endpoint in api_endpoint_info:
        api_id = endpoint.get("api_id")
        if (
            endpoint.get("model_id") == model_id
            and api_id not in broken_endpoints
        ):
            logger.debug(f"got_endpoint: {api_id} for {model_id}")
            return endpoint
    return None


def get_endpoint(endpoint_id):
    from languia.config import api_endpoint_info

    for endpoint in api_endpoint_info:
        if endpoint.get("api_id") == endpoint_id:
            return endpoint
    return None


def get_endpoints(model_id, broken_endpoints):

    from languia.config import api_endpoint_info

    endpoints = []
    for endpoint in api_endpoint_info:
        if (
            endpoint.get("model_id") == model_id
            and endpoint.get("api_id") not in broken_endpoints
        ):
            endpoints.append(endpoint)
    return endpoints


def get_unavailable_models(broken_endpoints, all_model_ids):
    unavailable_models = []
    logger = logging.getLogger("languia")
    for model_id in all_model_ids:
        if get_endpoints(model_id, broken_endpoints) == []:
            unavailable_models.append(model_id)
    logger.debug(f"unavailable_models: {unavailable_models}")
    return unavailable_models


# TODO: add to broken_endpoints for next n min when detected an error
# TODO: simplify battle targets formula
def get_battle_pair(
    all_models,
    battle_targets,
    broken_endpoints,
    sampling_weights,
    sampling_boost_models,
):

    unavailable_models = get_unavailable_models(broken_endpoints, all_models)
    models = [model for model in all_models if model not in unavailable_models]
    logger = logging.getLogger("languia")
    if len(models) == 0:
        logger.critical("Model list doesn't contain any model")
        # Maybe sleep then kill container?
        raise gr.Error(
            duration=0,
            message="Le comparateur a un problème et aucun des modèles n'est disponible, veuillez revenir plus tard.",
        )
        # os.kill(os.getpid(), signal.SIGINT)
        # parent = psutil.Process(psutil.Process(os.getpid()).ppid())
        # parent.kill()

    if len(models) == 1:
        logger.warn("Only one model configured! Making it fight with itself")
        return models[0], models[0]

    # model_weights = []
    # for model in models:
    #     weight = get_sample_weight(
    #         model, broken_endpoints, sampling_weights, sampling_boost_models
    #     )
    #     model_weights.append(weight)
    # total_weight = np.sum(model_weights)
    # model_weights = model_weights / total_weight
    # chosen_idx = np.random.choice(len(models), p=model_weights)
    chosen_idx = np.random.choice(len(models), p=None)
    chosen_model = models[chosen_idx]
    # for p, w in zip(models, model_weights):
    #     print(p, w)

    rival_models = []
    # rival_weights = []
    for model in models:
        if model == chosen_model:
            continue
        # weight = get_sample_weight(
        #     model, broken_endpoints, sampling_weights, sampling_boost_models
        # )
        # if (
        #     weight != 0
        #     and chosen_model in battle_targets
        #     and model in battle_targets[chosen_model]
        # ):
        #     # boost to 50% chance
        #     weight = total_weight / len(battle_targets[chosen_model])
        rival_models.append(model)
        # rival_weights.append(weight)
    # for p, w in zip(rival_models, rival_weights):
    #     print(p, w)
    # rival_weights = rival_weights / np.sum(rival_weights)
    rival_idx = np.random.choice(len(rival_models), p=None)
    # rival_idx = np.random.choice(len(rival_models), p=rival_weights)
    rival_model = rival_models[rival_idx]

    swap = np.random.randint(2)
    if swap == 0:
        return chosen_model, rival_model
    else:
        return rival_model, chosen_model


def get_matomo_js(matomo_url, matomo_id):
    js = """
    <!-- Matomo -->
<script>
  var _paq = window._paq = window._paq || [];
  /* tracker methods like "setCustomDimension" should be called before "trackPageView" */
  _paq.push(['setConsentGiven']);
  _paq.push(['enableLinkTracking']);
  _paq.push(['HeatmapSessionRecording::enable']);
  _paq.push(['trackPageView']);
  (function() {"""
    js += f"""
    var u="{matomo_url}/";
    _paq.push(['setTrackerUrl', u+'matomo.php']);
    _paq.push(['setSiteId', '{os.getenv("MATOMO_ID")}']);
    var d=document, g=d.createElement('script'), s=d.getElementsByTagName('script')[0];
    g.async=true; g.src=u+'matomo.js'; s.parentNode.insertBefore(g,s);"""
    js += """           
  })();
</script>"""
    js += f"""
<noscript><p><img referrerpolicy="no-referrer-when-downgrade" src="{matomo_url}/matomo.php?idsite={matomo_id}&amp;rec=1" style="border:0;" alt="" /></p></noscript>
<!-- End Matomo Code -->
    """
    return js


size_desc = {
    "XS": "Les modèles très petits, avec moins de 7 milliards de paramètres, sont les moins complexes et les plus économiques en termes de ressources, offrant des performances suffisantes pour des tâches simples comme la classification de texte.",
    "S": "Un modèle de petit gabarit est moins complexe et coûteux en ressources par rapport aux modèles plus grands, tout en offrant une performance suffisante pour diverses tâches (résumé, traduction, classification de texte...)",
    "M": "Les modèles moyens offrent un bon équilibre entre complexité, coût et performance : ils sont beaucoup moins consommateurs de ressources que les grands modèles tout en étant capables de gérer des tâches complexes telles que l'analyse de sentiment ou le raisonnement.",
    "L": "Les grands modèles nécessitent des ressources significatives, mais offrent les meilleures performances pour des tâches avancées comme la rédaction créative, la modélisation de dialogues et les applications nécessitant une compréhension fine du contexte.",
    "XL": "Ces modèles dotés de plusieurs centaines de milliards de paramètres sont les plus complexes et avancés en termes de performance et de précision. Les ressources de calcul et de mémoire nécessaires pour déployer ces modèles sont telles qu’ils sont destinés aux applications les plus avancées et aux environnements hautement spécialisés.",
}

license_desc = {
    "MIT": "La licence MIT est une licence de logiciel libre permissive : elle permet à quiconque de réutiliser, modifier et distribuer le modèle, même à des fins commerciales, sous réserve d'inclure la licence d'origine et les mentions de droits d'auteur.",
    "Apache 2.0": "Cette licence permet d'utiliser, modifier et distribuer librement, même à des fins commerciales. Outre la liberté d’utilisation, elle garantit la protection juridique en incluant une clause de non-atteinte aux brevets et la transparence : toutes les modifications doivent être documentées et sont donc traçables.",
    "Gemma": "Cette licence est conçue pour encourager l'utilisation, la modification et la redistribution des logiciels mais inclut une clause stipulant que toutes les versions modifiées ou améliorées doivent être partagée avec la communauté sous la même licence, favorisant ainsi la collaboration et la transparence dans le développement logiciel.",
    "Llama 3 Community": "Cette licence permet d'utiliser, modifier et distribuer librement le code avec attribution, mais impose des restrictions pour les opérations dépassant 700 millions d'utilisateurs mensuels et interdit la réutilisation du code ou des contenus générés pour l’entraînement ou l'amélioration de modèles concurrents, protégeant ainsi les investissements technologiques et la marque de Meta.",
    "Llama 3.1": "Cette licence permet d'utiliser, reproduire, modifier et distribuer librement le code avec attribution, mais impose des restrictions pour les opérations dépassant 700 millions d'utilisateurs mensuels. La réutilisation du code ou des contenus générés pour l’entraînement ou l'amélioration de modèles dérivés est autorisée à condition d’afficher “built with llama” et d’inclure “Llama” dans leur nom pour toute distribution.",
    "CC-BY-NC-4.0": "Cette licence permet de partager et adapter le contenu à condition de créditer l'auteur, mais interdit toute utilisation commerciale. Elle offre une flexibilité pour les usages non commerciaux tout en protégeant les droits de l'auteur.",
    "propriétaire Gemini": "Le modèle est disponible sous licence payante et accessible via l'API Gemini disponible sur les plateformes Google AI Studio et Vertex AI, nécessitant un paiement à l'utilisation basé sur le nombre de tokens traités",
    "propriétaire Liquid": "Le modèle est disponible sous licence payante et accessible via API sur les plateformes de la société Liquid AI, nécessitant un paiement à l'utilisation basé sur le nombre de tokens traités",
    "Mistral AI Non-Production": "Cette licence permet de partager et adapter le contenu à condition de créditer l'auteur, mais interdit toute utilisation commerciale. Elle offre une flexibilité pour les usages non commerciaux tout en protégeant les droits de l'auteur.",
}

license_attrs = {
    # Utilisation commerciale
    # Modification autorisée
    # Attribution requise
    # "MIT": {"commercial": True, "can_modify": True, "attribution": True},
    # "Apache 2.0": {"commercial": True, "can_modify": True, "attribution": True},
    # "Gemma": {"copyleft": True},
    "Llama 3 Community": {"warning_commercial": True},
    "Llama 3.1": {"warning_commercial": True},
    "CC-BY-NC-4.0": {"prohibit_commercial": True},
    "Mistral AI Non-Production": {"prohibit_commercial": True},
}


def calculate_lightbulb_consumption(impact_energy_value):
    """
    Calculates the energy consumption of a 5W LED light and determines the most sensible time unit.

    Args:
      impact_energy_value: Energy consumption in kilowatt-hours (kWh).

    Returns:
      A tuple containing:
        - An integer representing the consumption time.
        - A string representing the most sensible time unit ('days', 'hours', 'minutes', or 'seconds').
    """

    # Calculate consumption time using Wh
    watthours = impact_energy_value * 1000
    consumption_hours = watthours / 5
    consumption_days = watthours / (5 * 24)
    consumption_minutes = watthours * 60 / (5)
    consumption_seconds = watthours * 60 * 60 / (5)

    # Determine the most sensible unit based on magnitude
    if consumption_days >= 1:
        return int(consumption_days), "j"
    elif consumption_hours >= 1:
        return int(consumption_hours), "h"
    elif consumption_minutes >= 1:
        return int(consumption_minutes), "min"
    else:
        return int(consumption_seconds), "s"


def calculate_streaming_hours(impact_gwp_value):
    """
    Calculates equivalent streaming hours and determines a sensible time unit.

    Args:
      impact_gwp_value: CO2 emissions in kilograms.

    Returns:
      A tuple containing:
        - An integer representing the streaming hours.
        - A string representing the most sensible time unit ('days', 'hours', 'minutes', or 'seconds').
    """

    # Calculate streaming hours: https://impactco2.fr/outils/usagenumerique/streamingvideo
    streaming_hours = (impact_gwp_value * 10000) / 317

    # Determine sensible unit based on magnitude
    if streaming_hours >= 24:  # 1 day in hours
        return int(streaming_hours / 24), "j"
    elif streaming_hours >= 1:
        return int(streaming_hours), "h"
    elif streaming_hours * 60 >= 1:
        return int(streaming_hours * 60), "min"
    else:
        return int(streaming_hours * 60 * 60), "s"


def build_reveal_html(conv_a, conv_b, which_model_radio):
    from languia.config import models_extra_info

    logger = logging.getLogger("languia")

    model_a = get_model_extra_info(conv_a.model_name, models_extra_info)
    model_b = get_model_extra_info(conv_b.model_name, models_extra_info)
    logger.debug("output_tokens: " + str(conv_a.output_tokens))
    logger.debug("output_tokens: " + str(conv_b.output_tokens))

    # TODO: Improve fake token counter: 4 letters by token: https://genai.stackexchange.com/questions/34/how-long-is-a-token
    model_a_tokens = (
        conv_a.output_tokens
        if conv_a.output_tokens and conv_a.output_tokens != 0
        else count_output_tokens(conv_a.messages)
    )

    model_b_tokens = (
        conv_b.output_tokens
        if conv_b.output_tokens and conv_b.output_tokens != 0
        else count_output_tokens(conv_b.messages)
    )

    # TODO:
    # request_latency_a = conv_a.conv.finish_tstamp - conv_a.conv.start_tstamp
    # request_latency_b = conv_b.conv.finish_tstamp - conv_b.conv.start_tstamp
    model_a_impact = get_llm_impact(model_a, conv_a.model_name, model_a_tokens, None)
    model_b_impact = get_llm_impact(model_b, conv_b.model_name, model_b_tokens, None)

    env = Environment(loader=FileSystemLoader("templates"))

    template = env.get_template("reveal.html")
    chosen_model = get_chosen_model(which_model_radio)
    lightbulb_a, lightbulb_a_unit = calculate_lightbulb_consumption(
        model_a_impact.energy.value
    )
    lightbulb_b, lightbulb_b_unit = calculate_lightbulb_consumption(
        model_b_impact.energy.value
    )

    streaming_a, streaming_a_unit = calculate_streaming_hours(model_a_impact.gwp.value)
    streaming_b, streaming_b_unit = calculate_streaming_hours(model_b_impact.gwp.value)

    return template.render(
        model_a=model_a,
        model_b=model_b,
        chosen_model=chosen_model,
        model_a_impact=model_a_impact,
        model_b_impact=model_b_impact,
        size_desc=size_desc,
        license_desc=license_desc,
        license_attrs=license_attrs,
        model_a_tokens=model_a_tokens,
        model_b_tokens=model_b_tokens,
        streaming_a=streaming_a,
        streaming_a_unit=streaming_a_unit,
        streaming_b=streaming_b,
        streaming_b_unit=streaming_b_unit,
        lightbulb_a=lightbulb_a,
        lightbulb_a_unit=lightbulb_a_unit,
        lightbulb_b=lightbulb_b,
        lightbulb_b_unit=lightbulb_b_unit,
    )


def build_model_extra_info(name: str, all_models_extra_info_toml: dict):
    # Maybe put orgs countries in an array here
    std_name = slugify(name.lower())
    logger = logging.getLogger("languia")
    if std_name in all_models_extra_info_toml:
        model = all_models_extra_info_toml[std_name]
        # TODO: Should use a dict instead
        model["id"] = std_name
        if "excerpt" not in model and "description" in model:
            if len(model["description"]) > 190:
                model["excerpt"] = model["description"][0:190] + "[…]"
            else:
                model["excerpt"] = model["description"]

        if "params" not in model:
            if "total_params" in model:
                model["params"] = model["total_params"]
            else:
                logger.warn(
                    "Params not found for model "
                    + std_name
                    + ", infering from friendly size (when closed model for example)"
                )
                size_to_params = {"XS": 3, "S": 7, "M": 35, "L": 70, "XL": 200}
                model["params"] = size_to_params[model["friendly_size"]]

        # We suppose from q4 to fp16
        model["required_ram"] = model["params"]

        return model
        # To fix this, please complete `models-extra-info.json` to register your model
    return {
        "id": "other",
        "simple_name": "Autre",
        "organisation": "Autre",
        "params": 7,
        "required_ram": 7,
        "friendly_size": "M",
        "distribution": "open-weights",
        "conditions": "restricted",
        "description": "Un modèle open source disponible via Hugging Face.",
        "excerpt": "Un modèle open source",
        "icon_path": "huggingface.svg",
        "license": "Autre",
    }


def get_model_extra_info(name: str, models_extra_info: list):
    std_name = slugify(name.lower())
    for model in models_extra_info:
        if model["id"] == std_name:
            return model
    return {
        "id": "other",
        "params": 7,
        "required_ram": 7,
        "simple_name": "Autre",
        "organisation": "Autre",
        "friendly_size": "M",
        "distribution": "open-weights",
        "conditions": "copyleft",
        "description": "Un modèle open source disponible via Hugging Face.",
        "excerpt": "Un modèle open source",
        "icon_path": "huggingface.svg",
        "license": "Autre",
    }


def get_model_list(_controller_url, api_endpoint_info):
    logger = logging.getLogger("languia")

    # Add models from the controller
    # if controller_url:
    #     ret = requests.post(controller_url + "/refresh_all_workers")
    #     assert ret.status_code == 200

    #     ret = requests.post(controller_url + "/list_language_models")
    #     models = ret.json()["models"]
    # else:
    models = []
    # Add models from the API providers
    models.extend(
        model_id
        for model_dict in api_endpoint_info
        if (model_id := model_dict.get("model_id")) is not None
        and model_id not in models
    )
    logger.debug(f"All models: {models}")
    return models


def is_limit_reached(model_name, ip):
    # FIXME:
    # monitor_url = "http://localhost:9090"
    # try:
    #     ret = requests.get(
    #         f"{monitor_url}/is_limit_reached?model={model_name}&user_id={ip}", timeout=1
    #     )
    #     obj = ret.json()
    #     return obj
    # except Exception as e:
    #     logging.info(f"monitor error: {e}")
    return None


def count_output_tokens(messages) -> int:
    """Count output tokens (assuming 4 letters per token)."""

    total_messages = sum(
        len(msg.content) for msg in messages if msg.role == "assistant"
    )
    return int(total_messages / 4)


def get_llm_impact(
    model_extra_info, model_name: str, token_count: int, request_latency: float
) -> dict:
    """Compute or fallback to estimated impact for an LLM."""
    logger = logging.getLogger("languia")
    # TODO: add request latency
    # FIXME: most of the time, won't appear in venv/lib64/python3.11/site-packages/ecologits/data/models.csv, should use compute_llm_impacts instead
    # model_active_parameter_count: ValueOrRange,
    # model_total_parameter_count: ValueOrRange,
    impact = llm_impacts("huggingface_hub", model_name, token_count, request_latency)
    if impact is None:

        logger.debug("impact is None for " + model_name + ", deducing from params")
        if "active_params" in model_extra_info and "total_params" in model_extra_info:
            # TODO: add request latency
            # FIXME: multiply by 1_000_000?
            model_active_parameter_count = int(model_extra_info["active_params"])
            model_total_parameter_count = int(model_extra_info["total_params"])
        else:
            if "params" in model_extra_info:
                # TODO: add request latency
                model_active_parameter_count = int(model_extra_info["params"])
                model_total_parameter_count = int(model_extra_info["params"])
            else:
                logger.error(
                    "impact is None for "
                    + model_name
                    + ", and no params, closed model did not match ecologits list?"
                )
                return None

        # TODO: move to config.py
        electricity_mix_zone = "WOR"
        electricity_mix = electricity_mixes.find_electricity_mix(
            zone=electricity_mix_zone
        )
        if_electricity_mix_adpe = electricity_mix.adpe
        if_electricity_mix_pe = electricity_mix.pe
        if_electricity_mix_gwp = electricity_mix.gwp

        impact = compute_llm_impacts(
            model_active_parameter_count=model_active_parameter_count,
            model_total_parameter_count=model_total_parameter_count,
            output_token_count=token_count,
            if_electricity_mix_adpe=if_electricity_mix_adpe,
            if_electricity_mix_pe=if_electricity_mix_pe,
            if_electricity_mix_gwp=if_electricity_mix_gwp,
        )
    return impact


def gen_prompt(category):
    from languia.config import prompts_table

    prompts = prompts_table[category]
    # [category]
    # for category in get_categories(prompts_pool):
    # prompts.extend([(prompt, category) for prompt in prompts_table[category]])
    return prompts[np.random.randint(len(prompts))]


def refresh_outages(previous_outages, controller_url):
    logger = logging.getLogger("languia")
    try:
        response = requests.get(controller_url + "/outages/", timeout=1)
    except Exception as e:
        logger.error("controller_inaccessible: " + str(e))
        return previous_outages
    # Check if the request was successful
    if response.status_code == 200:
        # Parse the JSON response
        data = response.json()
        logger.debug("refreshed outage models:" + str(data))
        return data
    else:
        logger.warning(
            f"Failed to retrieve outage data. Status code: {response.status_code}"
        )
        return previous_outages


# def add_outage_model(controller_url, model_name, endpoint_name, reason):
#     logger = logging.getLogger("languia")

#     try:
#         response = requests.post(
#             params={
#                 "reason": str(reason),
#                 "model_name": model_name,
#                 "endpoint": endpoint_name,
#             },
#             # params={"reason": str(reason), "model_name": model_name, "endpoint": endpoint_name},
#             url=f"{controller_url}/outages/",
#             timeout=2,
#         )
#     except Exception:
#         pass


def test_endpoint(controller_url, api_id):
    return requests.get(
        # params={"model_name": model_name},
        url=f"{controller_url}/outages/{api_id}",
        timeout=2,
    )


def on_endpoint_error(controller_url, api_id, reason):
    logger = logging.getLogger("languia")
    try:
        return test_endpoint(controller_url, api_id)
        # await test_model(controller_url, model_name)
        # return True
    except Exception as e:
        logger.warning("Failed to request endpoint testing: " + str(e))
        return False
        # pass

    # if response.status_code == 201:
    #     logger.info(f"endpoint_desactive: {model_name} at {endpoint_name}")
    # else:
    #     logger.error(f"Failed to post outage data. Status code: {response.status_code}")


def to_threeway_chatbot(conversations):
    threeway_chatbot = []
    for msg_a, msg_b in zip(conversations[0].messages, conversations[1].messages):
        if msg_a.role == "user":
            # Could even test if msg_a == msg_b
            if msg_b.role != "user":
                raise IndexError
            threeway_chatbot.append(msg_a)
        else:
            if msg_a:
                threeway_chatbot.append(
                    {
                        "role": "assistant",
                        "content": msg_a.content,
                        # TODO: add duration here?
                        "metadata": {"bot": "a"},
                    }
                )
            if msg_b:
                threeway_chatbot.append(
                    {
                        "role": "assistant",
                        "content": msg_b.content,
                        "metadata": {"bot": "b"},
                    }
                )
    return threeway_chatbot
