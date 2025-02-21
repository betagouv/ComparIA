import numpy as np
import os

from gradio import Request

import logging

import requests


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
        return (len(messages)-1) // 2
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


def pick_endpoint(model_id, broken_endpoints):
    from languia.config import api_endpoint_info

    logger = logging.getLogger("languia")

    for endpoint in api_endpoint_info:
        api_id = endpoint.get("api_id")
        if endpoint.get("model_id") == model_id and api_id not in broken_endpoints:
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


class AppState:
    def __init__(
        self, awaiting_responses=False, model_left=None, model_right=None, category=None
    , custom_models_selection =None, mode="random"):
        self.awaiting_responses = awaiting_responses
        self.model_left = model_left
        self.model_right = model_right
        self.category = category
        self.mode = mode
        self.custom_models_selection = custom_models_selection
        self.reactions = []

    # def to_dict(self) -> dict:
    #     return self.__dict__.copy()

# TODO: add to broken_endpoints for next n min when detected an error
# TODO: simplify battle targets formula
# TODO: merge w/ pick_model
def get_battle_pair(
    all_models,
    broken_endpoints,
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

    chosen_idx = np.random.choice(len(models), p=None)
    chosen_model = models[chosen_idx]

    rival_models = []
    for model in models:
        if model == chosen_model:
            continue
        rival_models.append(model)

    rival_idx = np.random.choice(len(rival_models), p=None)
    rival_model = rival_models[rival_idx]

    swap = np.random.randint(2)
    if swap == 0:
        return chosen_model, rival_model
    else:
        return rival_model, chosen_model


def pick_model(mode, custom_models_selection, outages):
    small_models = [
        model
        for model in config.models_extra_info
        if model["friendly_size"] in ["XS", "S", "M"]
    ]
    big_models = [
        model
        for model in config.models_extra_info
        if model["friendly_size"] in ["L", "XL"]
    ]

    # mode = model_dropdown_scoped["mode"]

    # logger.info("chose mode: " + mode, extra={"request": request})

    import random

    if mode == "big-vs-small":
        first_model = big_models[random.randint(len(big_models))]
        second_model = small_models[random.randint(len(small_models))]

        swap = random.randint(2)
        if swap == 0:
            model_left_name = first_model["id"]
            model_right_name = second_model["id"]
        else:
            model_left_name = second_model["id"]
            model_right_name = first_model["id"]

    elif mode == "small-models":
        first_model = small_models[random.randint(len(small_models))]
        small_models.remove(first_model)
        if small_models == []:
            # If there was just one small model :o
            second_model = first_model
        else:
            second_model = small_models[random.randint(len(small_models))]
        model_left_name = first_model["id"]
        model_right_name = second_model["id"]

        # Custom mode
    elif mode == "custom" and len(custom_models_selection) > 0:
        # custom_models_selection = model_dropdown_scoped["custom_models_selection"]
        #  FIXME: input sanitization
        # if any(mode[1], not in models):
        #     raise Exception(f"Model choice from value {str(model_dropdown_scoped)} not among possibilities")
        swap = random.randint(2)
        # FIXME: more test and randomize
        if len(custom_models_selection) == 1:
            if swap == 0:
                model_left_name = custom_models_selection[0]
                model_right_name = (
                    get_battle_pair()
                )  # FIXME: chose at random except chosen
                # conv_b_scoped.model_name = the random one
            else:
                conv_b_scoped = set_conv_state(
                    conv_b_scoped,
                    model_name=custom_models_selection[0],
                    endpoint=pick_endpoint(custom_models_selection[0], config.outages),
                )
                # FIXME: chose at random except chosen
                # conv_b_scoped.model_name = the random one
        elif len(custom_models_selection) == 2:

            if swap == 0:
                conv_a_scoped = set_conv_state(
                    conv_a_scoped,
                    model_name=custom_models_selection[0],
                    endpoint=pick_endpoint(custom_models_selection[0], config.outages),
                )
                conv_b_scoped = set_conv_state(
                    conv_b_scoped,
                    model_name=custom_models_selection[1],
                    endpoint=pick_endpoint(custom_models_selection[1], config.outages),
                )
            else:
                conv_a_scoped = set_conv_state(
                    conv_a_scoped,
                    model_name=custom_models_selection[1],
                    endpoint=pick_endpoint(custom_models_selection[1], config.outages),
                )
                conv_b_scoped = set_conv_state(
                    conv_b_scoped,
                    model_name=custom_models_selection[0],
                    endpoint=pick_endpoint(custom_models_selection[0], config.outages),
                )
        app_state_scoped.custom_models_selection = custom_models_selection
        logger.info(
            "custom_models_selection: " + str(custom_models_selection),
            extra={"request": request},
        )

    else:  # assume random mode
        model_left, model_right = get_battle_pair(
            config.models,
            BATTLE_TARGETS,
            config.outages,
            SAMPLING_WEIGHTS,
            SAMPLING_BOOST_MODELS,
        )
        endpoint_left = pick_endpoint(model_left, config.outages)
        endpoint_right = pick_endpoint(model_right, config.outages)
        # TODO: replace by class method
        conv_a_scoped = set_conv_state(
            conv_a_scoped, model_name=model_left, endpoint=endpoint_left
        )
        conv_b_scoped = set_conv_state(
            conv_b_scoped, model_name=model_right, endpoint=endpoint_right
        )

    if mode in ["random", "custom", "small-models", "big-vs-small"]:
        app_state_scoped.mode = mode

    logger.info(
        "picked model a: " + conv_a_scoped.model_name,
        extra={"request": request},
    )
    logger.info(
        "picked model b: " + conv_b_scoped.model_name,
        extra={"request": request},
    )
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


def build_model_extra_info(name: str, all_models_extra_info_toml: dict):
    # Maybe put orgs countries in an array here
    std_name = name.lower()
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

        if model.get("quantization", None) == "q8":
            model["required_ram"] = model["params"]*2
        else:
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
        "description": "Un modèle open weights disponible via Hugging Face.",
        "excerpt": "Un modèle open weights",
        "icon_path": "huggingface.svg",
        "license": "Autre",
    }


def get_model_extra_info(name: str, models_extra_info: list):
    std_name = name.lower()
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
        "description": "Un modèle open weights disponible via Hugging Face.",
        "excerpt": "Un modèle open weights",
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


def shuffle_prompt(guided_cards, request):
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


def refresh_outages(previous_outages, controller_url):
    logger = logging.getLogger("languia")
    try:
        response = requests.get(controller_url + "/outages/", timeout=1)
    except Exception as e:
        logger.warning("controller_inaccessible: " + str(e))
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
    conv_a_messages = [message for message in conversations[0].messages if message.role != "system"]
    conv_b_messages = [message for message in conversations[1].messages if message.role != "system"]
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
                        # TODO: add duration here?
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
                        "metadata": msg_b.metadata,
                    }
                )
    return threeway_chatbot


def messages_to_dict(messages):
    try:
        return [
            {"role": message.role, "content": message.content} for message in messages
        ]
    except:
        raise TypeError(f"Expected ChatMessage object, got {type(messages)}")


def mode_banner_html(mode):
    modes = {
        "custom": [
            "Mode Sélection",
            "Les modèles restent anonymes pour éviter tout biais",
            "glass.svg",
        ],
        "big-vs-small": [
            "Mode Petit contre Grand",
            "Un petit et un grand modèle choisis au hasard",
            "ruler.svg",
        ],
        "random": [
            "Mode Aléatoire",
            "Deux modèles choisis au hasard parmi toute la liste",
            "dice.svg",
        ],
        "small-models": [
            "Mode Économe",
            "Deux petits modèles choisis au hasard",
            "leaf.svg",
        ],
    }
    return f"""
    <div class="fr-container--fluid text-center mode-banner fr-py-1w fr-text--xs"><img class="inline" height="20" src="../assets/extra-icons/{modes.get(mode)[2]}" />&nbsp;<strong>{modes.get(mode)[0]}</strong>&nbsp;: <span class="text-grey">{modes.get(mode)[1]}</span></div>
    """


def get_gauge_count():
    import psycopg2
    from psycopg2 import sql
    from languia.config import db as db_config

    logger = logging.getLogger("languia")
    if not db_config:
        logger.warn("Cannot log to db: no db configured")
        return 40000
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()
    try:
        select_statement = sql.SQL(
            """
        SELECT
  (SELECT COUNT(*) FROM reactions) + (SELECT COUNT(*) FROM votes) AS total_count;
    """
        )
        cursor.execute(select_statement)
        res = cursor.fetchone()
    except Exception as e:
        logger.error(f"Error getting vote numbers from db: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    if res[0]:
        return res[0]
    else:
        return 40000


# def gauge_banner_html():
#     gauge_count = get_gauge_count()
#     objective = 40000
#     ratio = 100 * get_gauge_count() / objective
#     gauge = """
#     <div class="fr-container--fluid mode-banner"><span class="legende">Nombre total de votes&nbsp;<a class="fr-icon fr-icon--xs fr-icon--question-line" aria-describedby="gauge"></a></span>
#     <div class="linear-gauge">
#   <div class="linear-gauge-fill"><span class="votes">""" + str(gauge_count) + """</span></div></div><span class="objectif">Objectif : """ + str(objective) + """</span>
#     </div>
#     <span class="fr-tooltip fr-placement" id="gauge" role="tooltip" aria-hidden="true">Discutez, votez et aidez-nous à atteindre cet objectif !<br />
# <strong>Vos votes sont importants</strong> : ils alimentent le jeu de données compar:IA mis à disposition librement pour affiner les prochains modèles sur le français.<br />
# Ce commun numérique contribue au meilleur <strong>respect de la diversité linguistique et culturelle des futurs modèles de langue.</strong></span>
#     <style>
#     .legende {
#             font-size: 0.875em;
#             color: #161616 !important;
#             font-weight: bold;

#     }
#     .legende a {
#     top: 10px;
#     position: relative;
#     }
#     .votes {
#         font-size: 0.75em;
# font-weight: bold;
# color: #695240 !important;
# position: absolute;
#   margin-left: 5px;
#     bottom: 0;
#   height: inherit;
# }
#     .objectif {
#     font-weight: 500;
#     font-size: 0.75em;
#     color: #7F7F7F !important   ;
#     }
# .linear-gauge-fill {
#     width: """ + str(int(ratio)) + """%;
#   height: 100%;
#   background: var(--yellow-tournesol-925-125);
#   transition: width 0.3s ease-in-out;
# }

# .linear-gauge {
#   width: 300px;
#   height: 20px;
#   background: #FFF;
#   border-radius: 3px;
#   border: 1px solid #CCCCCC;
#   overflow: hidden;
# }
# .mode-banner {
# display: flex;
# align-items: center;
# justify-content: center;
# gap: 1em;
# }

#   @media (max-width: 48em) {

#     .mode-banner {
#       padding-top: 0;
#       padding-bottom: 1em;
#       display: grid;
#       height: auto;
#       grid-template: "a c"
#       "b b";
#     }

#     .votes {
#       position: relative;
#       top: -13px;
#     }
#     .legende {
#       grid-area: a;

#     }

#     .objectif {
#       grid-area: c;
#       order: 0;
#       display: block;
#     }
#     .linear-gauge {
#       width: auto;
#       margin-top: -10px;
#       order: 2;
#       grid-area: b;
#     }
#   }

#     </style>
#     """
#     return gauge
