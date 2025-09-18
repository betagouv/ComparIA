import numpy as np
import os

from gradio import Request
import gradio as gr

import logging

from languia.models import Model, Endpoint


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


def filter_enabled_models(models: dict[str, Model]):
    enabled_models = {}
    for model_id, model_dict in models.items():
        if model_dict.get("status") == "enabled":
            try:
                if Endpoint.model_validate(model_dict.get("endpoint")):
                    enabled_models[model_id] = model_dict
            except:
                continue
    return enabled_models

def get_ip(request: Request):
    # 'x-real-ip': '178.33.22.30', 'x-forwarded-for': '178.33.22.30', 'x-forwarded-host': 'languia.stg.cloud.culture.fr' 'x-original-forwarded-for': '88.185.32.248','cloud-protector-client-ip': '88.185.32.248', )
    if "cloud-protector-client-ip" in request.headers:
        ip = request.headers["cloud-protector-client-ip"]
    elif "x-original-forwarded-for" in request.headers:
        ip = request.headers["x-original-forwarded-for"]
    elif "x-forwarded-for" in request.headers:
        ip = request.headers["x-forwarded-for"]
    else:
        ip = request.client.host
    # Sometimes multiple IPs are returned as a comma-separated string
    if "," in ip:
        ip = ip.split(",")[0].strip()

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

    if messages[0].role == "system":
        return (len(messages) - 1) // 2
    else:
        return len(messages) // 2


def is_unedited_prompt(opening_msg, category):
    if not category:
        return False
    from languia.config import prompts_table

    return opening_msg in prompts_table[category]


def metadata_to_dict(metadata):
    metadata_dict = dict(metadata)
    metadata_dict.pop("bot", None)
    if not metadata_dict.get("duration") or metadata_dict.get("duration") == 0:
        metadata_dict.pop("duration", None)
    if not metadata_dict.get("generation_id"):
        metadata_dict.pop("generation_id", None)
    return metadata_dict


def strip_metadata(messages):
    return [
        {"role": message["role"], "content": message["content"]} for message in messages
    ]


def messages_to_dict_list(
    messages, strip_metadata=False, concat_reasoning_with_content=False
):
    return [
        {
            "role": message.role,
            "content": (
                (message.reasoning + " ")
                if message.reasoning and concat_reasoning_with_content
                else "" + message.content
            ),
            **(
                {"reasoning": message.reasoning}
                if message.reasoning and not concat_reasoning_with_content
                else {}
            ),
            **(
                {"metadata": metadata_to_dict(message.metadata)}
                if metadata_to_dict(message.metadata) and not strip_metadata
                else {}
            ),
        }
        for message in messages
    ]


def get_user_info(request):
    if request:
        if hasattr(request, "cookies"):
            user_id = get_matomo_tracker_from_cookies(request.cookies)
        else:
            try:
                user_id = get_ip(request)
            except:
                user_id = None
        session_id = getattr(request, "session_hash", None)
    else:
        session_id = None
        user_id = None
    return user_id, session_id



class AppState:
    def __init__(
        self,
        awaiting_responses=False,
        model_left=None,
        model_right=None,
        category=None,
        custom_models_selection=None,
        mode="random",
    ):
        self.awaiting_responses = awaiting_responses
        self.model_left = model_left
        self.model_right = model_right
        self.category = category
        self.mode = mode
        self.custom_models_selection = custom_models_selection
        self.reactions = []

    # def to_dict(self) -> dict:
    #     return self.__dict__.copy()


def choose_among(
    models,
    excluded,
):
    enabled_models = models
    models_pool = [
        model_name for model_name in enabled_models if model_name not in excluded
    ]
    logger = logging.getLogger("languia")
    logger.debug("chosing from:" + str(models_pool))
    logger.debug("excluded:" + str(excluded))
    if len(models_pool) == 0:
        # TODO: tell user in a toast notif that we couldn't respect prefs
        logger.warning("Couldn't respect exclusion prefs")
        if len(enabled_models) == 0:
            logger.critical("No model to choose from")

            raise gr.Error(
                duration=0,
                message="Le comparateur a un problème et aucun des modèles parmi les sélectionnés n'est disponible, veuillez réessayer un autre mode ou revenir plus tard.",
            )
        else:
            models_pool = enabled_models

    chosen_idx = np.random.choice(len(models_pool), p=None)
    chosen_model_name = models_pool[chosen_idx]
    return chosen_model_name


def pick_models(mode, custom_models_selection, unavailable_models):

    from languia.config import big_models, small_models, reasoning_models, random_pool
    import random

    if mode == "big-vs-small":
        model_left_name = choose_among(models=big_models, excluded=unavailable_models)
        model_right_name = choose_among(
            models=small_models, excluded=unavailable_models
        )

    elif mode == "small-models":
        model_left_name = choose_among(models=small_models, excluded=unavailable_models)
        model_right_name = choose_among(
            models=small_models, excluded=unavailable_models + [model_left_name]
        )
    elif mode == "reasoning":
        model_left_name = choose_among(
            models=reasoning_models, excluded=unavailable_models
        )
        model_right_name = choose_among(
            models=reasoning_models, excluded=unavailable_models + [model_left_name]
        )
        # Custom mode
    elif mode == "custom" and len(custom_models_selection) > 0:
        # custom_models_selection = model_dropdown_scoped["custom_models_selection"]
        #  FIXME: input sanitization
        # if any(mode[1], not in models):
        #     raise Exception(f"Model choice from value {str(model_dropdown_scoped)} not among possibilities")

        if len(custom_models_selection) == 1:
            model_left_name = custom_models_selection[0]
            model_right_name = choose_among(
                models=random_pool,
                excluded=[custom_models_selection[0]] + unavailable_models,
            )

        elif len(custom_models_selection) == 2:

            model_left_name = custom_models_selection[0]
            model_right_name = custom_models_selection[1]

    else:  # assume random mode
        model_left_name = choose_among(models=random_pool, excluded=unavailable_models)
        model_right_name = choose_among(
            models=random_pool, excluded=[model_left_name] + unavailable_models
        )

    swap = random.randint(0, 1)
    if swap == 1:
        model_right_name, model_left_name = model_left_name, model_right_name

    return [model_left_name, model_right_name]

def get_api_key(endpoint: Endpoint):

    # // "api_type": "huggingface/cohere",
    # "api_base": "https://albert.api.etalab.gouv.fr/v1/",

    # "api_base": "https://router.huggingface.co/cohere/compatibility/v1/",
    if endpoint.get("api_base") and "albert.api.etalab.gouv.fr" in endpoint.get("api_base"):
        return os.environ("ALBERT_KEY")
    if endpoint.get("api_base") and "huggingface.co" in endpoint.get("api_base"):
        return os.environ("HF_INFERENCE_KEY")
    # Normally no need for OpenRouter, litellm reads OPENROUTER_API_KEY env value
    # And no need for Vertex, handled differently
    return None


def params_to_friendly_size(params):
    """
    Converts a parameter value to a friendly size description.

    Args:
        param (int): The parameter value

    Returns:
        str: The friendly size description
    """
    intervals = [(0, 7), (7, 20), (20, 70), (70, 150), (150, float("inf"))]
    sizes = ["XS", "S", "M", "L", "XL"]

    for i, (lower, upper) in enumerate(intervals):
        if lower <= params < upper:
            return sizes[i]

    return "M"


def get_conditions_from_license(license_name):
    if "propriétaire" in license_name:
        return "restricted"
    elif license_name in ["Gemma", "CC-BY-NC-4.0"]:
        return "copyleft"
    else:
        return "free"


def get_distrib_clause_from_license(license_name):
    if "propriétaire" in license_name:
        return "api-only"
    else:
        return "open-weights"


def count_output_tokens(messages) -> int:
    """Count output tokens (assuming 4 letters per token)."""

    total_messages = sum(
        len(msg.content) for msg in messages if msg.role == "assistant"
    )
    return int(total_messages / 4)


def shuffle_prompt(guided_cards, request):
    logger = logging.getLogger("languia")
    prompt = gen_prompt(guided_cards)
    logger.info(
        f"shuffle: {prompt}",
        extra={"request": request},
    )
    return prompt


def gen_prompt(category):
    from languia.config import prompts_table

    prompts = prompts_table[category]
    # [category]
    # for category in get_categories(prompts_pool):
    # prompts.extend([(prompt, category) for prompt in prompts_table[category]])
    return prompts[np.random.randint(len(prompts))]

def to_threeway_chatbot(conversations):
    threeway_chatbot = []
    conv_a_messages = [
        message for message in conversations[0].messages if message.role != "system"
    ]
    conv_b_messages = [
        message for message in conversations[1].messages if message.role != "system"
    ]
    for msg_a, msg_b in zip(conv_a_messages, conv_b_messages):
        if msg_a.role == "user":
            # Could even test if msg_a == msg_b
            if msg_b.role != "user":
                raise IndexError
            threeway_chatbot.append(msg_a)
        else:
            if msg_a:
                msg_a.metadata["bot"] = "a"
                threeway_chatbot.append(
                    {
                        "role": "assistant",
                        "content": msg_a.content,
                        "error": msg_a.error,
                        "reasoning": msg_a.reasoning,
                        "metadata": msg_a.metadata,
                    }
                )
            if msg_b:

                msg_b.metadata["bot"] = "b"
                threeway_chatbot.append(
                    {
                        "role": "assistant",
                        "content": msg_b.content,
                        "error": msg_a.error,
                        "reasoning": msg_b.reasoning,
                        "metadata": msg_b.metadata,
                    }
                )
    return threeway_chatbot


def get_gauge_count():
    import psycopg2
    from psycopg2 import sql
    from languia.config import db as dsn
    cursor = None
    conn = None
    result = 55000
    logger = logging.getLogger("languia")
    if not dsn:
        logger.warning("Cannot log to db: no db configured")
        return result
    try:
        conn = psycopg2.connect(dsn)
        cursor = conn.cursor()
        select_statement = sql.SQL(
            """
        SELECT 
(SELECT n_live_tup FROM pg_stat_user_tables WHERE relname='reactions') + 
(SELECT n_live_tup FROM pg_stat_user_tables WHERE relname='votes') 
AS total_approx;
    """
        )
        cursor.execute(select_statement)
        res = cursor.fetchone()
        result = res[0]
    except Exception as e:
        logger.error(f"Error getting vote numbers from db: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        return result


def second_header_html(step=1, mode_str="random"):

    from languia.utils import get_gauge_count
    from languia.config import objective

    gauge_count = get_gauge_count()
    gauge_count_ratio = str(int(100 * get_gauge_count() / objective))

    modes = {
        "custom": [
            "Mode Sélection",
            "Reconnaîtrez-vous les deux modèles que vous avez choisis ?",
            "glass.svg",
        ],
        "big-vs-small": [
            "Mode David contre Goliath",
            "Un petit modèle contre un grand, les deux tirés au hasard",
            "ruler.svg",
        ],
        "reasoning": [
            "Mode Raisonnement",
            "Deux modèles tirés au hasard parmi ceux optimisés pour des tâches complexes",
            "brain.svg",
        ],
        "random": [
            "Mode Aléatoire",
            "Deux modèles choisis au hasard parmi toute la liste",
            "dice.svg",
        ],
        "small-models": [
            "Mode Frugal",
            "Deux modèles tirés au hasard parmi ceux de plus petite taille",
            "leaf.svg",
        ],
    }

    mode = modes.get(mode_str)
    from jinja2 import Environment, FileSystemLoader

    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("header-chat.html")

    return template.render(
        {
            "step": step,
            "gauge_count_ratio": gauge_count_ratio,
            "gauge_count": gauge_count,
            "objective": objective,
            "mode": mode,
        }
    )
