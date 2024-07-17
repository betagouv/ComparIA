import numpy as np
import os

import gradio as gr

import time

import json

from fastchat.serve.remote_logger import get_remote_logger

from fastchat.utils import (
    build_logger,
    # moderation_filter,
)

import datetime
from fastchat.constants import LOGDIR
import requests

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


accept_tos_js = """
function () {
  document.cookie="languia_tos_accepted=1"
}
"""


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


def build_reveal_html(model_a, model_b, which_model_radio):
    source = open("templates/reveal.html", "r", encoding="utf-8").read()
    template = Template(source)
    chosen_model = None
    if which_model_radio == "leftvote":
        chosen_model = "model-a"
    if which_model_radio == "rigjtvote":
        chosen_model = "model-b"
    return template.render(
        model_a=model_a,
        model_b=model_b,
        chosen_model=chosen_model,
    )


def get_conv_log_filename(is_vision=False, has_csam_image=False):
    t = datetime.datetime.now()
    conv_log_filename = f"{t.year}-{t.month:02d}-{t.day:02d}-conv.json"
    if is_vision and not has_csam_image:
        name = os.path.join(LOGDIR, f"vision-tmp-{conv_log_filename}")
    elif is_vision and has_csam_image:
        name = os.path.join(LOGDIR, f"vision-csam-{conv_log_filename}")
    else:
        name = os.path.join(LOGDIR, conv_log_filename)

    return name


def get_model_extra_info(name: str, models_extra_info: dict):
    # Maybe put orgs countries in an array here
    if str.lower(name) in models_extra_info:
        model = models_extra_info[str.lower(name)]
        if "excerpt" not in model and "description" in model:
            if len(model["description"]) > 140:
                model["excerpt"] = model["description"][0:139] + "…"
            else:
                model["excerpt"] = model["description"]
        return model
    else:
        # To fix this, please complete `models-extra-info.json` to register your model
        return (
            {
                "simple_name": "Autre",
                "organisation": "Autre",
                "friendly_size": "M",
                "distribution": "open-weights",
                "dataset": "private",
                "conditions": "restricted",
                "description": "Un modèle open source, probablement disponible via Hugging Face.",
                "excerpt": "Un modèle open source",
                "icon_path": "huggingface.png",
            },
        )


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
