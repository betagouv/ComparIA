import numpy as np
import os

import gradio as gr

import time

from random import randrange

import json

from fastchat.utils import (
    moderation_filter,
)

import logging
from logging.handlers import WatchedFileHandler
import sys

import datetime

import requests

from ecologits.tracers.utils import llm_impacts, compute_llm_impacts

from slugify import slugify

# import config

LOGDIR = os.getenv("LOGDIR", "./data")


class CustomFormatter(logging.Formatter):
    def format(self, record):

        msg = super().format(record)

        # Parse the message as JSON
        try:
            log_data = json.loads(msg)
        except json.JSONDecodeError:
            # Handle cases where the message isn't valid JSON
            log_data = {"message": msg}

        # if 'request' in record.args:
        if hasattr(record, "request"):
            # log_data = record.request
            # request_dict = record.request.kwargs
            log_data["query_params"] = dict(record.request.query_params)
            log_data["path_params"] = dict(record.request.path_params)
            log_data["ip"] = get_ip(record.request)
            log_data["session_hash"] = record.request.session_hash
            # if isinstance(request_di  ct, dict):
            #     request_json = json.dumps(request_dict)
            # delattr(record, 'request')
        if hasattr(record, "prompt"):
            log_data["prompt"] = record.prompt
        if hasattr(record, "details"):
            log_data["details"] = record.details
        if hasattr(record, "models"):
            log_data["models"] = record.models
        if hasattr(record, "conversations"):
            log_data["conversations"] = record.conversations

        # Add the args dictionary to the JSON payload
        # log_data.update(record.args)
        # Convert the updated dictionary back to JSON
        return json.dumps(log_data)


def build_logger(logger_filename):
    # Get logger
    logger = logging.getLogger("languia")
    logger.setLevel(logging.INFO)

    # file_formatter = CustomFormatter(
    #     '{"time":"%(asctime)s", "name": "%(name)s", \
    #     "level": "%(levelname)s", "message": "%(message)s", \
    #     "ip": "%(ip)s", "query_params": "%(query_params)s", \
    #     "path_params": "%(path_params)s", "session_hash": "%(session_hash)s"}',
    file_formatter = CustomFormatter(
        '{"time":"%(asctime)s", "name": "%(name)s", \
        "level": "%(levelname)s", "message": "%(message)s"}',
        # defaults={"request": ""},
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # stream_formatter = logging.Formatter(
    #     fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    #     datefmt="%Y-%m-%d %H:%M:%S",
    # )
    # stream_handler = logging.StreamHandler()
    # stream_logger.addHandler(stream_handler)

    # Avoid httpx flooding POST logs
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # if LOGDIR is empty, then don't try output log to local file
    if LOGDIR != "":
        os.makedirs(LOGDIR, exist_ok=True)
        filename = os.path.join(LOGDIR, logger_filename)
        file_handler = WatchedFileHandler(filename, encoding="utf-8")
        file_handler.setFormatter(file_formatter)

        logger.addHandler(file_handler)
    return logger


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
    if which_model_radio in [-1.5, -0.5]:
        chosen_model = "model-a"
    elif which_model_radio in [0.5, 1.5]:
        chosen_model = "model-b"
    else:
        chosen_model = "invalid-vote"
        raise (ValueError)
    return chosen_model


def get_final_vote(which_model_radio):
    final_vote = {
        -1.5: "strongly-a",
        -0.5: "slightly-a",
        +0.5: "slightly-b",
        +1.5: "strongly-b",
    }
    return final_vote[which_model_radio]


def log_poll(
    conversation_a,
    conversation_b,
    which_model_radio,
    chatbot_use,
    gender,
    age,
    profession,
    request: gr.Request,
):
    logger = logging.getLogger("languia")
    # logger.info(f"poll", extra={"request": request,
    #          "chatbot_use":chatbot_use, "gender":gender, "age":age, "profession":profession
    #     },
    # )
    chosen_model = get_chosen_model(which_model_radio)
    final_vote = get_final_vote(which_model_radio)

    with open(get_conv_log_filename(), "a") as fout:
        data = {
            "tstamp": round(time.time(), 4),
            "type": "poll",
            "models": [x.model_name for x in [conversation_a, conversation_b]],
            "conversations": [x.dict() for x in [conversation_a, conversation_b]],
            "chatbot_use": chatbot_use,
            "final_vote": final_vote,
            "chosen_model": chosen_model,
            "gender": gender,
            "age": age,
            "profession": profession,
            # FIXME:
            # "ip": get_ip(request),
        }
        logger.info(json.dumps(data), extra={"request": request})
        fout.write(json.dumps(data) + "\n")

    return data


def vote_last_response(
    conversations,
    chosen_model,
    final_vote,
    details: list,
    request: gr.Request,
):
    logger = logging.getLogger("languia")
    logger.info(
        f"{final_vote}",
        extra={
            "request": request,
            "type": final_vote,
            "chosen_model": chosen_model,
            "chosen_model_name": (
                conversations[0].model_name
                if chosen_model == "model-a"
                else conversations[1].model_name
            ),
            "details": details,
            "models": [x.model_name for x in conversations],
            "conversations": [x.dict() for x in conversations],
        },
    )

    with open(get_conv_log_filename(), "a") as fout:
        data = {
            "tstamp": round(time.time(), 4),
            "vote": final_vote,
            "chosen_model": chosen_model,
            "chosen_model_name": (
                conversations[0].model_name
                if chosen_model == "model-a"
                else conversations[1].model_name
            ),
            "models": [x.model_name for x in conversations],
            "conversations": [x.dict() for x in conversations],
            # FIXME:
            "ip": get_ip(request),
        }
        if details != []:
            data.update(details=details),
        logger.info(json.dumps(data), extra={"request": request})
        fout.write(json.dumps(data) + "\n")

    return data
    # yield names + ("",)


def stepper_html(title, step, total_steps):
    return f"""
    <div class="fr-stepper fr-container fr-pb-2w fr-px-2w">
    <h2 class="fr-stepper__title">
        {title}
        <span class="fr-stepper__state">Étape {step} sur {total_steps}</span>
    </h2>
    <div class="fr-stepper__steps" data-fr-current-step="{step}" data-fr-steps="{total_steps}"></div>

</div>"""


with open("./templates/header-arena.html", encoding="utf-8") as header_file:
    header_html = header_file.read()

    if os.getenv("GIT_COMMIT"):
        git_commit = os.getenv("GIT_COMMIT")
        header_html += f"<!-- Git commit: {git_commit} -->"


with open("./templates/start-screen.html", encoding="utf-8") as start_screen_file:
    start_screen_html = start_screen_file.read()


def get_sample_weight(model, outage_models, sampling_weights, sampling_boost_models):
    if model in outage_models:
        return 0
    # Give a 1 weight if model not in weights
    weight = sampling_weights.get(model, 1)
    # weight = sampling_weights.get(model, 0)
    if model in sampling_boost_models:
        weight *= 5
    return weight


# TODO: add to outage_models for next n min when detected an error
# TODO: simplify battle targets formula
def get_battle_pair(
    models, battle_targets, outage_models, sampling_weights, sampling_boost_models
):
    models = [model for model in models if model not in outage_models]
    logger = logging.getLogger("languia")
    if len(models) == 0:
        logger.critical("Model list doesn't contain any model")
        # Maybe sleep then kill container?
        raise ValueError("Model list doesn't contain any model")

    if len(models) == 1:
        logger.warn("Only one model configured! Making it fight with itself")
        return models[0], models[0]

    model_weights = []
    for model in models:
        weight = get_sample_weight(
            model, outage_models, sampling_weights, sampling_boost_models
        )
        model_weights.append(weight)
    total_weight = np.sum(model_weights)
    model_weights = model_weights / total_weight
    chosen_idx = np.random.choice(len(models), p=model_weights)
    chosen_model = models[chosen_idx]
    # for p, w in zip(models, model_weights):
    #     print(p, w)

    rival_models = []
    rival_weights = []
    for model in models:
        if model == chosen_model:
            continue
        weight = get_sample_weight(
            model, outage_models, sampling_weights, sampling_boost_models
        )
        if (
            weight != 0
            and chosen_model in battle_targets
            and model in battle_targets[chosen_model]
        ):
            # boost to 50% chance
            weight = total_weight / len(battle_targets[chosen_model])
        rival_models.append(model)
        rival_weights.append(weight)
    # for p, w in zip(rival_models, rival_weights):
    #     print(p, w)
    rival_weights = rival_weights / np.sum(rival_weights)
    rival_idx = np.random.choice(len(rival_models), p=rival_weights)
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
  _paq.push(['trackPageView']);
  _paq.push(['enableLinkTracking']);
  _paq.push(['setConsentGiven']);

  _paq.push(['HeatmapSessionRecording::enable']);
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


from jinja2 import Template

size_desc = {
    "XS": "Les modèles très petits, avec moins de 7 milliards de paramètres, sont les moins complexes et les plus économiques en termes de ressources, offrant des performances suffisantes pour des tâches simples comme la classification de texte.",
    "S": "Un modèle de petit gabarit (7 à 20 milliards de paramètres) est moins complexe et coûteux en ressources par rapport aux modèles plus grands, tout en offrant une performance suffisante pour diverses tâches (résumé, traduction, classification de texte...)",
    "M": "Les modèles moyens, entre 20 et 70 milliards de paramètres, offrent un bon équilibre entre complexité, coût et performance : ils sont beaucoup moins consommateurs de ressources que les grands modèles tout en étant capables de gérer des tâches complexes telles que l'analyse de sentiment ou le raisonnement.",
    "L": "Les grands modèles, avec plus de 70 milliards de paramètres, nécessitent des ressources significatives, mais offrent les meilleures performances pour des tâches avancées comme la rédaction créative, la modélisation de dialogues et les applications nécessitant une compréhension fine du contexte.",
    "XL": "Ces modèles dotés de plusieurs centaines de milliards de paramètres sont les plus complexes et avancés en termes de performance et de précision. Les ressources de calcul et de mémoire nécessaires pour déployer ces modèles sont telles qu’ils sont destinés aux applications les plus avancées et aux environnements hautement spécialisés.",
}
license_desc = {
    "MIT": "La licence MIT est une licence de logiciel libre permissive : elle permet à quiconque de réutiliser, modifier et distribuer le modèle, même à des fins commerciales, sous réserve d'inclure la licence d'origine et les mentions de droits d'auteur.",
    "Apache 2.0": "Cette licence permet d'utiliser, modifier et distribuer librement, même à des fins commerciales. Outre la liberté d’utilisation, elle garantit la protection juridique en incluant une clause de non-atteinte aux brevets et la transparence : toutes les modifications doivent être documentées et sont donc traçables.",
    "Gemma": "Cette licence est conçue pour encourager l'utilisation, la modification et la redistribution des logiciels mais inclut une clause stipulant que toutes les versions modifiées ou améliorées doivent être partagée avec la communauté sous la même licence, favorisant ainsi la collaboration et la transparence dans le développement logiciel.",
    "Llama 3 Community": "Cette licence permet d'utiliser, modifier et distribuer librement le code avec attribution, mais impose des restrictions pour les opérations dépassant 700 millions d'utilisateurs mensuels et interdit la réutilisation du code ou des contenus générés pour l’entraînement ou l'amélioration de modèles concurrents, protégeant ainsi les investissements technologiques et la marque de Meta.",
    "Llama 3.1 Community": "Cette licence permet d'utiliser, reproduire, modifier et distribuer librement le code avec attribution, mais impose des restrictions pour les opérations dépassant 700 millions d'utilisateurs mensuels. La réutilisation du code ou des contenus générés pour l’entraînement ou l'amélioration de modèles dérivés est autorisée à condition d’afficher “built with llama” et d’inclure “Llama” dans leur nom pour toute distribution.",
    "CC-BY-NC-4.0": "Cette licence permet de partager et adapter le contenu à condition de créditer l'auteur, mais interdit toute utilisation commerciale. Elle offre une flexibilité pour les usages non commerciaux tout en protégeant les droits de l'auteur.",
    "propriétaire Gemini": "Le modèle est disponible sous licence payante et accessible via l'API Gemini disponible sur les plateformes Google AI Studio et Vertex AI, nécessitant un paiement à l'utilisation basé sur le nombre de tokens traités",
}


def build_reveal_html(
    model_a,
    model_b,
    which_model_radio,
    model_a_impact,
    model_b_impact,
    model_a_running_eq,
    model_b_running_eq,
):
    source = open("templates/reveal.html", "r", encoding="utf-8").read()
    template = Template(source)
    chosen_model = get_chosen_model(which_model_radio)

    return template.render(
        model_a=model_a,
        model_b=model_b,
        chosen_model=chosen_model,
        model_a_impact=model_a_impact,
        model_b_impact=model_b_impact,
        size_desc=size_desc,
        license_desc=license_desc,
        model_a_running_eq=model_a_running_eq,
        model_b_running_eq=model_b_running_eq,
    )


def running_eq(impact):
    if impact is not None:
        energy_in_kJ = impact.energy.value / 0.2777777778
        # running 1 km at 10 km/h with a weight of 70 kg
        running_eq = energy_in_kJ / 294
        # in km
        return running_eq
    return 0.0


def get_conv_log_filename(is_vision=False, has_csam_image=False):
    t = datetime.datetime.now()
    random = randrange(10000)
    conv_log_filename = f"{t.year}-{t.month:02d}-{t.day:02d}-{t.hour:02d}-{t.minute:02d}-{t.second:02d}-{t.microsecond:02d}-{random}-conv.json"
    name = os.path.join(LOGDIR, conv_log_filename)

    return name


def build_model_extra_info(name: str, all_models_extra_info_json: dict):
    # Maybe put orgs countries in an array here
    std_name = slugify(name.lower())
    logger = logging.getLogger("languia")
    if std_name in all_models_extra_info_json:
        model = all_models_extra_info_json[std_name]
        # TODO: Should use a dict instead
        model["id"] = std_name
        if "excerpt" not in model and "description" in model:
            if len(model["description"]) > 350:
                model["excerpt"] = model["description"][0:349] + "…"
            else:
                model["excerpt"] = model["description"]

        if "params" not in model:
            if "total_params" in model:
                model["params"] = model["total_params"]
            else:
                # FIXME: handle this better...
                logger.warn(
                    "Params not found for model "
                    + std_name
                    + ", infering from friendly size (when closed model for example)"
                )
                size_to_params = {"XS": 3, "S": 7, "M": 35, "L": 70, "XL": 200}
                model["params"] = size_to_params[model["friendly_size"]]

        # Let's suppose q8
        # TODO: give a range?
        # FIXME: Fix for MoE
        model["required_ram"] = model["params"]

        return model
        # To fix this, please complete `models-extra-info.json` to register your model
    return {
        "id": "other",
        "simple_name": "Autre",
        "organisation": "Autre",
        "params": "7",
        "friendly_size": "M",
        "distribution": "open-weights",
        "dataset": "private",
        "conditions": "restricted",
        "description": "Un modèle open source disponible via Hugging Face.",
        "excerpt": "Un modèle open source",
        "icon_path": "huggingface.png",
        "license": "Autre",
    }


def get_model_extra_info(name: str, models_extra_info: list):
    std_name = slugify(name.lower())
    for model in models_extra_info:
        if model["id"] == std_name:
            return model
    return {
        "id": "other",
        "params": "7",
        "simple_name": "Autre",
        "organisation": "Autre",
        "friendly_size": "M",
        "distribution": "open-weights",
        "dataset": "private",
        "conditions": "restricted",
        "description": "Un modèle open source disponible via Hugging Face.",
        "excerpt": "Un modèle open source",
        "icon_path": "huggingface.png",
        "license": "Autre",
    }


def get_model_list(controller_url, register_api_endpoint_file):
    logger = logging.getLogger("languia")

    # Add models from the controller
    if controller_url:
        ret = requests.post(controller_url + "/refresh_all_workers")
        assert ret.status_code == 200

        ret = requests.post(controller_url + "/list_language_models")
        models = ret.json()["models"]
    else:
        models = []

    # Add models from the API providers
    if register_api_endpoint_file:
        api_endpoint_info = json.load(open(register_api_endpoint_file))
        for mdl, mdl_dict in api_endpoint_info.items():
            models.append(mdl)

    models = list(set(models))

    logger.info(f"All models: {models}")
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


def count_output_tokens(roles, messages) -> int:
    """Count output tokens (assuming 4 per message)."""

    return sum(len(msg[1]) * 4 for msg in messages if msg[0] == roles[1])


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
        # logger.info("impact is None for " + model_name + ", deducing from params")
        if "active_params" in model_extra_info and "total_params" in model_extra_info:
            # TODO: add request latency
            # FIXME: multiply by 1_000_000?
            impact = compute_llm_impacts(
                model_active_parameter_count=int(model_extra_info["active_params"]),
                model_total_parameter_count=int(model_extra_info["total_params"]),
                output_token_count=token_count,
            )
        else:
            if "params" in model_extra_info:
                # TODO: add request latency
                # FIXME: multiply by 1_000_000?
                impact = compute_llm_impacts(
                    model_active_parameter_count=int(model_extra_info["params"]),
                    model_total_parameter_count=int(model_extra_info["params"]),
                    output_token_count=token_count,
                    request_latency=request_latency,
                )
            else:
                logger.warn(
                    "impact is None for "
                    + model_name
                    + ", and no params, closed model did not match ecologits list?"
                )
    return impact

def gen_prompt(category):
    from languia.config import prompts_table
    if category in [
        "expression",
        "langues",
        "conseils",
        "loisirs",
        "administratif",
        "vie-professionnelle",
    ]:
        prompts = prompts_table[category]
    else:
        raise ValueError("Invalid prompt category")
    return prompts[np.random.randint(len(prompts))]

def refresh_outage_models(controller_url):
    logger = logging.getLogger("languia")
    try:
        response = requests.get(controller_url + "/outages/")
    except:
        return []
    # Check if the request was successful
    if response.status_code == 200:
        # Parse the JSON response
        data = response.json()
        logger.info("refreshed outage models:"+str(data))
        return data
    else:
        print(f"Failed to retrieve outage data. Status code: {response.status_code}")
    return []


def add_outage_model(controller_url, model_name):
    logger = logging.getLogger("languia")

    try:
        response = requests.post(url=f"{controller_url}/outages/?model_name={model_name}")
    except:
        logger.error(f"Failed to post outage data.")
        return

    if response.status_code == 201:
        logger.info("successfully reported outage model ", model_name)
    else:
        logger.error(f"Failed to post outage data. Status code: {response.status_code}")


# Not used
# def model_worker_stream_iter(
#     conv,
#     model_name,
#     worker_addr,
#     prompt,
#     temperature,
#     repetition_penalty,
#     top_p,
#     max_new_tokens,
#     images,
# ):
#     # Make requests
#     gen_params = {
#         "model": model_name,
#         "prompt": prompt,
#         "temperature": temperature,
#         "repetition_penalty": repetition_penalty,
#         "top_p": top_p,
#         "max_new_tokens": max_new_tokens,
#         "stop": conv.stop_str,
#         "stop_token_ids": conv.stop_token_ids,
#         "echo": False,
#     }

#     logger.info(f"==== request ====\n{gen_params}")

#     if len(images) > 0:
#         gen_params["images"] = images

#     # Stream output
#     response = requests.post(
#         worker_addr + "/worker_generate_stream",
#         headers=config.headers,
#         json=gen_params,
#         stream=True,
#         timeout=WORKER_API_TIMEOUT,
#     )
#     for chunk in response.iter_lines(decode_unicode=False, delimiter=b"\0"):
#         if chunk:
#             data = json.loads(chunk.decode())
#             yield data
