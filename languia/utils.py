import numpy as np
import os

from gradio import Request
import gradio as gr

import logging

import requests

from custom_components.customchatbot.backend.gradio_customchatbot.customchatbot import (
    ChatMessage,
)


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


def messages_to_dict_list(messages):
    return [
        {
            "role": message.role,
            "content": message.content,
            **({"reasoning": message.reasoning} if message.reasoning else {}),
            **(
                {"metadata": metadata_to_dict(message.metadata)}
                if metadata_to_dict(message.metadata)
                else {}
            ),
        }
        for message in messages
    ]


with open("./templates/welcome-modal.html", encoding="utf-8") as welcome_modal_file:
    welcome_modal_html = welcome_modal_file.read()

with open("./templates/header-arena.html", encoding="utf-8") as header_file:
    header_html = header_file.read()
    if os.getenv("GIT_COMMIT"):
        git_commit = os.getenv("GIT_COMMIT")
        header_html += f"<!-- Git commit: {git_commit} -->"

with open("./templates/footer.html", encoding="utf-8") as footer_file:
    footer_html = footer_file.read()


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

def get_endpoint(model_id):
    from languia.config import api_endpoint_info

    for endpoint in api_endpoint_info:
        if endpoint.get("model_id") == model_id:
            return endpoint

    return None


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


# TODO: refacto to expose "all_models" to choose from them if constraints can't be respected
def choose_among(
    models,
    excluded,
):
    all_models = models
    models_pool = [
        model_name for model_name in all_models if model_name not in excluded
    ]
    logger = logging.getLogger("languia")
    logger.debug("chosing from:" + str(models_pool))
    logger.debug("excluded:" + str(excluded))
    if len(models_pool) == 0:
        # TODO: tell user in a toast notif that we couldn't respect prefs
        logger.warning("Couldn't respect exclusion prefs")
        if len(all_models) == 0:
            logger.critical("No model to choose from")

            raise gr.Error(
                duration=0,
                message="Le comparateur a un problème et aucun des modèles parmi les sélectionnés n'est disponible, veuillez réessayer un autre mode ou revenir plus tard.",
            )
        else:
            models_pool = all_models

    chosen_idx = np.random.choice(len(models_pool), p=None)
    chosen_model_name = models_pool[chosen_idx]
    return chosen_model_name


def pick_models(mode, custom_models_selection, unavailable_models):
    from languia.config import models_extra_info
    from languia.config import models as models_names

    small_models = [
        model["id"]
        for model in models_extra_info
        if model["friendly_size"] in ["XS", "S", "M"]
        and model["id"] not in unavailable_models
    ]
    big_models = [
        model["id"]
        for model in models_extra_info
        if model["friendly_size"] in ["L", "XL"]
        and model["id"] not in unavailable_models
    ]
    reasoning_models = [
        model["id"] for model in models_extra_info if model.get("reasoning", False)
    ]

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
                models=models_names,
                excluded=[custom_models_selection[0]] + unavailable_models,
            )

        elif len(custom_models_selection) == 2:

            model_left_name = custom_models_selection[0]
            model_right_name = custom_models_selection[1]

    else:  # assume random mode
        model_left_name = choose_among(models=models_names, excluded=unavailable_models)
        model_right_name = choose_among(
            models=models_names, excluded=[model_left_name] + unavailable_models
        )

    swap = random.randint(0, 1)
    if swap == 1:
        model_right_name, model_left_name = model_left_name, model_right_name

    return [model_left_name, model_right_name]


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
        if lower <= params <= upper:
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


def build_model_extra_info(name: str, all_models_extra_info_toml: dict):

    std_name = name.lower()
    model = all_models_extra_info_toml.get(std_name, {"id": std_name})

    model["id"] = model.get("id", std_name)
    model["simple_name"] = model.get("simple_name", std_name)
    model["icon_path"] = model.get("icon_path", "huggingface.svg")
    # model["release_date"] = model.get("release_date", None)

    model["license"] = model.get("license", "MIT")
    model["distribution"] = get_distrib_clause_from_license(model["license"])
    model["conditions"] = get_conditions_from_license(model["license"])

    # TODO: dict for organisation = "DeepSeek" => icon_path = "deepseek.webp"

    if not any(model.get(key) for key in ("friendly_size", "params", "total_params")):
        model["params"] = 100

    # Determine params if not listed explicitly
    if "params" not in model:
        PARAMS_SIZE_MAP = {"XS": 3, "S": 7, "M": 35, "L": 70, "XL": 200}
        model["params"] = model.get(
            "total_params",
            PARAMS_SIZE_MAP.get(model.get("friendly_size"), 100),
        )

    # Determine friendly size if not listed explicitly
    model["friendly_size"] = model.get(
        "friendly_size", params_to_friendly_size(model["params"])
    )

    if "excerpt" not in model and "description" in model:
        if len(model["description"]) > 190:
            model["excerpt"] = model["description"][0:190] + "[…]"
        else:
            model["excerpt"] = model["description"]

    if model.get("quantization", None) == "q8":
        model["required_ram"] = model["params"] * 2
    else:
        # We suppose from q4 to fp16
        model["required_ram"] = model["params"]

    return model


def get_model_extra_info(name: str, models_extra_info: list):
    std_name = name.lower()
    for model in models_extra_info:
        if model["id"] == std_name:
            return model
    # if not found return minimalistic dict
    return {"id": name}


import json


def get_model_names_list(api_endpoint_info):
    logger = logging.getLogger("languia")

    models = [model_dict.get("model_id") for model_dict in api_endpoint_info]
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


def refresh_unavailable_models(previous_unavailable_models, controller_url):
    logger = logging.getLogger("languia")
    try:
        response = requests.get(controller_url + "/unavailable_models/", timeout=1)
    except Exception as e:
        logger.warning("controller_inaccessible: " + str(e))
        return previous_unavailable_models
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
        return previous_unavailable_models


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

    objective = 70000

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
