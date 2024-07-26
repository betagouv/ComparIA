import numpy as np
import os

import gradio as gr

import time

from random import randrange

import json

from fastchat.serve.remote_logger import get_remote_logger

from fastchat.utils import (
    build_logger,
    # moderation_filter,
)

import datetime
from fastchat.constants import LOGDIR
import requests

from ecologits.tracers.utils import llm_impacts, compute_llm_impacts

from slugify import slugify

logger = build_logger("gradio_web_server_multi", "gradio_web_server_multi.log")


def get_ip(request: gr.Request):
    if "cf-connecting-ip" in request.headers:
        ip = request.headers["cf-connecting-ip"]
    elif "x-forwarded-for" in request.headers:
        ip = request.headers["x-forwarded-for"]
    else:
        ip = request.client.host
    return ip


def vote_last_response(
    conversations_state,
    vote_type,
    # _model_selectors,
    details: list,
    request: gr.Request,
):
    logger.info(f"{vote_type}_vote (anony). ip: {get_ip(request)}")
    details_str = json.dumps(details)
    logger.info(f"details: {details_str}")

    with open(get_conv_log_filename(), "a") as fout:
        data = {
            "tstamp": round(time.time(), 4),
            "type": vote_type,
            "models": [x.model_name for x in conversations_state],
            "conversations_state": [x.dict() for x in conversations_state],
            "ip": get_ip(request),
        }
        if details != []:
            data.update(details=details),
        logger.info(json.dumps(data))
        fout.write(json.dumps(data) + "\n")

    get_remote_logger().log(data)

    # names = (
    #     "### Model A: " + conversations_state[0].model_name,
    #     "### Model B: " + conversations_state[1].model_name,
    # )
    return data
    # yield names + ("",)


def stepper_html(title, step, total_steps):
    return f"""
    <div class="fr-stepper">
    <h2 class="fr-stepper__title">
        {title}
        <span class="fr-stepper__state">Étape {step} sur {total_steps}</span>
    </h2>
    <div class="fr-stepper__steps" data-fr-current-step="{step}" data-fr-steps="{total_steps}"></div>

</div>"""


# Use starlette's jinja templating? Or static files
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


def get_battle_pair(
    models, battle_targets, outage_models, sampling_weights, sampling_boost_models
):

    if len(models) == 0:
        raise ValueError("Model list doesn't contain any model")

    if len(models) == 1:
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
    "L": "Les grands modèles, avec plus de 70 milliards de paramètres, sont les plus complexes et nécessitent des ressources significatives, mais offrent les meilleures performances pour des tâches avancées comme la rédaction créative, la modélisation de dialogues et les applications nécessitant une compréhension fine du contexte.",
}
license_desc = {
    "MIT": "La licence MIT est une licence de logiciel libre permissive : elle permet à quiconque de réutiliser, modifier et distribuer le modèle, même à des fins commerciales, sous réserve d'inclure la licence d'origine et les mentions de droits d'auteur.",
    "Apache 2.0": "Cette licence permet d'utiliser, modifier et distribuer librement, même à des fins commerciales. Outre la liberté d’utilisation, elle garantit la protection juridique en incluant une clause de non-atteinte aux brevets et la transparence : toutes les modifications doivent être documentées et sont donc traçables.",
    "Gemma": "Cette licence est conçue pour encourager l'utilisation, la modification et la redistribution des logiciels mais inclut une clause stipulant que toutes les versions modifiées ou améliorées doivent être partagée avec la communauté sous la même licence, favorisant ainsi la collaboration et la transparence dans le développement logiciel.",
    "Llama 3 Community": "Cette licence permet d'utiliser, modifier et distribuer librement le code avec attribution, mais impose des restrictions pour les opérations dépassant 700 millions d'utilisateurs mensuels et interdit la réutilisation du code ou des contenus générés pour l’entraînement ou l'amélioration de modèles concurrents, protégeant ainsi les investissements technologiques et la marque de Meta.",
    "CC-BY-NC-4.0": "Cette licence permet de partager et adapter le contenu à condition de créditer l'auteur, mais interdit toute utilisation commerciale. Elle offre une flexibilité pour les usages non commerciaux tout en protégeant les droits de l'auteur.",
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
    chosen_model = None
    if which_model_radio == "leftvote":
        chosen_model = "model-a"
    if which_model_radio == "rightvote":
        chosen_model = "model-b"

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
    energy_in_kJ = impact.energy.value / 0.2777777778
    # running 1 km at 10 km/h with a weight of 70 kg
    running_eq = energy_in_kJ / 294
    # in km
    return running_eq


def get_conv_log_filename(is_vision=False, has_csam_image=False):
    t = datetime.datetime.now()
    random = randrange(10000)
    conv_log_filename = f"{t.year}-{t.month:02d}-{t.day:02d}-{t.hour:02d}-{t.minute:02d}-{t.second:02d}-{t.microsecond:02d}-{random}-conv.json"
    name = os.path.join(LOGDIR, conv_log_filename)

    return name


def build_model_extra_info(name: str, all_models_extra_info_json: dict):
    # Maybe put orgs countries in an array here
    std_name = slugify(name.lower())
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
                size_to_params = {"XS": 3, "S": 7, "M": 35, "L": 70}
                model["params"] = size_to_params[model["friendly_size"]]

        # Let's suppose q8
        # TODO: give a range?
        # FIXME: Fix for MoE
        model["required_ram"] = model["params"]

        return model
        # To fix this, please complete `models-extra-info.json` to register your model
    return (
        {
            "id": "other",
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
        },
    )


def get_model_extra_info(name: str, models_extra_info: list):
    std_name = slugify(name.lower())
    for model in models_extra_info:
        if model["id"] == std_name:
            return model


def get_model_list(controller_url, register_api_endpoint_file, vision_arena):

    # Add models from the controller
    if controller_url:
        ret = requests.post(controller_url + "/refresh_all_workers")
        assert ret.status_code == 200

        if vision_arena:
            ret = requests.post(controller_url + "/list_multimodal_models")
            models = ret.json()["models"]
        else:
            ret = requests.post(controller_url + "/list_language_models")
            models = ret.json()["models"]
    else:
        models = []

    # Add models from the API providers
    if register_api_endpoint_file:
        api_endpoint_info = json.load(open(register_api_endpoint_file))
        for mdl, mdl_dict in api_endpoint_info.items():
            mdl_vision = mdl_dict.get("vision-arena", False)
            mdl_text = mdl_dict.get("text-arena", True)
            if vision_arena and mdl_vision:
                models.append(mdl)
            if not vision_arena and mdl_text:
                models.append(mdl)

    # Remove anonymous models
    models = list(set(models))
    visible_models = models.copy()
    for mdl in models:
        if mdl not in api_endpoint_info:
            continue
        mdl_dict = api_endpoint_info[mdl]
        if mdl_dict["anony_only"]:
            visible_models.remove(mdl)

    # Sort models and add descriptions
    # priority = {k: f"___{i:03d}" for i, k in enumerate(model_info)}
    # models.sort(key=lambda x: priority.get(x, x))
    # visible_models.sort(key=lambda x: priority.get(x, x))
    logger.info(f"All models: {models}")
    logger.info(f"Visible models: {visible_models}")
    return visible_models, models


def is_limit_reached(model_name, ip):
    monitor_url = "http://localhost:9090"
    try:
        ret = requests.get(
            f"{monitor_url}/is_limit_reached?model={model_name}&user_id={ip}", timeout=1
        )
        obj = ret.json()
        return obj
    except Exception as e:
        logger.info(f"monitor error: {e}")
        return None


def count_output_tokens(roles,  messages) -> int:
    """Count output tokens (assuming 4 per message)."""

    return sum(
        len(msg[1]) * 4
        for msg in messages
        if msg[0] == roles[1]
    )


def get_llm_impact(model_extra_info, model_name: str, token_count: int) -> dict:
    """Compute or fallback to estimated impact for an LLM."""
    # TODO: add request latency
    # FIXME: most of the time, won't appear in venv/lib64/python3.11/site-packages/ecologits/data/models.csv, should use compute_llm_impacts instead
    # model_active_parameter_count: ValueOrRange,
    # model_total_parameter_count: ValueOrRange,
    impact = llm_impacts("huggingface_hub", model_name, token_count, None)
    if impact is None:
        # logger.info("impact is None for " + model_name + ", deducing from params")
        if "active_params" in model_extra_info and "total_params" in model_extra_info:    
            # TODO: add request latency
            impact = compute_llm_impacts(
                model_active_parameter_count=model_extra_info["active_params"],
                model_total_parameter_count=model_extra_info["total_params"],
                output_token_count=token_count,
            )
        else:
            if "params" in model_extra_info:
                # TODO: add request latency
                impact = compute_llm_impacts(
                    model_active_parameter_count=model_extra_info["params"],
                    model_total_parameter_count=model_extra_info["params"],
                    output_token_count=token_count,
                )
            else:
                logger.warn("impact is None for " + model_name + ", and no params, closed model did not match ecologits list?")
    return impact


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
