import numpy as np
import os

import gradio as gr

# from jinja2 import Template
from jinja2 import Environment, FileSystemLoader

import logging

import requests

from ecologits.tracers.utils import llm_impacts, compute_llm_impacts, electricity_mixes


from slugify import slugify



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



def messages_to_dict_list(messages):
    return [{"role": message.role, "content": message.content} for message in messages]



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
    "propriétaire Gemini": "Le modèle est disponible sous licence payante et accessible via l'API Gemini disponible sur les plateformes Google AI Studio et Vertex AI, nécessitant un paiement à l'utilisation basé sur le nombre de tokens traités.",
    "propriétaire Liquid": "Le modèle est disponible sous licence payante et accessible via API sur les plateformes de la société Liquid AI, nécessitant un paiement à l'utilisation basé sur le nombre de tokens traités.",
    "propriétaire OpenAI": "Le modèle est disponible sous licence payante et accessible via API sur les plateformes de la société OpenAI, nécessitant un paiement à l'utilisation basé sur le nombre de tokens traités.",
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


def determine_choice_badge(reactions):
    your_choice_badge = None
    reactions = [reaction for reaction in reactions if reaction]
    # Case: Only one reaction exists
    if len(reactions) == 1:

        print("reaction")
        print(reactions)
        if reactions[0].get("liked") == True:
            # Assign "a" if the reaction is for the first message
            your_choice_badge = "model-a" if reactions[0].get("index") == 1 else "model-b"

    # Case: Two reactions exist
    elif len(reactions) == 2:
        print("reactions")
        print(reactions)

        # Ensure one reaction is "liked" and the other is different
        if (
            reactions[0].get("liked") == True
            and reactions[0].get("liked") != reactions[1].get("liked")
        ) or (
            reactions[1].get("liked") == True
            and reactions[1].get("liked") != reactions[0].get("liked")
        ):
            # Assign "a" or "b" based on the liked reaction's index
            your_choice_badge = (
                "model-a" if reactions[0]["liked"] and reactions[0].get("index") == 1 else "model-b"
            )

    return your_choice_badge
