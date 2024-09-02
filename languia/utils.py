import numpy as np
import os

import gradio as gr

import time

from random import randrange

import json

import psycopg2
from psycopg2 import sql

# from fastchat.utils import (
#     moderation_filter,
# )

import logging
from logging.handlers import WatchedFileHandler

import datetime

import requests

from ecologits.tracers.utils import llm_impacts, compute_llm_impacts, electricity_mixes

from slugify import slugify

import traceback

LOGDIR = os.getenv("LOGDIR", "./data")


class JSONFormatter(logging.Formatter):
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
            # if isinstance(request_dict, dict):
            #     request_json = json.dumps(request_dict)
            # delattr(record, 'request')
        if hasattr(record, "extra"):
            log_data["extra"] = record.extra
        # if hasattr(record, "prompt"):
        #     log_data["prompt"] = record.prompt
        # if hasattr(record, "details"):
        #     log_data["details"] = record.details
        # if hasattr(record, "models"):
        #     log_data["models"] = record.models
        # if hasattr(record, "conversations"):
        #     log_data["conversations"] = record.conversations

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
            except Exception as e:
                print(f"Error connecting to database: {e}")
                stacktrace = traceback.format_exc()
                print(f"Stacktrace: {stacktrace}")
                
    def emit(self, record):

        assert isinstance(record, logging.LogRecord)
        print("LoggingHandler received LogRecord: {}".format(record))

        # record = super().format(record)
        self.format(record)

        try:
            self.connect()
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
                    "query_params": json.dumps(record.__dict__.get("query_params")),
                    "path_params": json.dumps(record.__dict__.get("path_params")),
                    "session_hash": record.__dict__.get("session_hash"),
                    "extra": json.dumps(record.__dict__.get("extra")),
                }
                cursor.execute(insert_statement, values)
                self.connection.commit()
        except (psycopg2.Error, Exception) as e:
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
    if which_model_radio in [-1.5, -0.5]:
        chosen_model = "model-a"
    elif which_model_radio in [0.5, 1.5]:
        chosen_model = "model-b"
    else:
        chosen_model = "invalid-vote"
        raise (ValueError)
    return chosen_model


def get_matomo_tracker_from_cookies(cookies):
    logger = logging.getLogger("languia")
    for cookie in cookies:
        if cookie[0].startswith("_pk_id."):
            logger.info(f"Found matomo cookie: {cookie[0]}: {cookie[1]}")
            return cookie[1]


def save_profile_to_db(data):
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
            INSERT INTO profiles (tstamp, chatbot_use, gender, age, profession, confirmed, session_hash, extra)
            VALUES (%(tstamp)s, %(chatbot_use)s, %(gender)s, %(age)s, %(profession)s, %(confirmed)s, %(session_hash)s, %(extra)s)
        """
        )
        values = {
            "tstamp": int(data["tstamp"]),
            "chatbot_use": (data["chatbot_use"]),
            "gender": (data["gender"]),
            "age": (data["age"]),
            "profession": (data["profession"]),
            "confirmed": bool(data["confirmed"]),
            "session_hash": str(data["session_hash"]),
            "extra": json.dumps(data["extra"]),
        }
        cursor.execute(insert_statement, values)
        conn.commit()
        logger.info(f"Saved profile to db")
    except Exception as e:
        logger = logging.getLogger("languia")
        logger.error(f"Error saving profile to db: {e}")
        stacktrace = traceback.format_exc()
        print(f"Stacktrace: {stacktrace}")
    finally:
        cursor.close()
        if conn:
            conn.close()


def save_profile(
    conversation_a,
    conversation_b,
    which_model_radio,
    chatbot_use,
    gender,
    age,
    profession,
    confirmed,
    request: gr.Request,
):
    """
    save poll data to file
    """
    logger = logging.getLogger("languia")
    t = datetime.datetime.now()
    profile_log_filename = f"profile-{t.year}-{t.month:02d}-{t.day:02d}-{t.hour:02d}-{t.minute:02d}-{request.session_hash}.json"
    profile_log_path = os.path.join(LOGDIR, profile_log_filename)

    get_matomo_tracker_from_cookies(request.cookies)

    data = {
        "tstamp": round(time.time(), 4),
        "chatbot_use": chatbot_use,
        "gender": gender,
        "age": age,
        "profession": profession,
        "confirmed": bool(confirmed),
        "session_hash": str(request.session_hash),
        # Log redundant info to be sure
        "extra": {
            "which_model_radio": which_model_radio,
            "models": [str(x.model_name) for x in [conversation_a, conversation_b]],
            "conversations": [x.dict() for x in [conversation_a, conversation_b]],
            # "cookies": dict(request.cookies),
        },
    }
    # logger.info(f"poll", extra={"request": request,
    #          "chatbot_use":chatbot_use, "gender":gender, "age":age, "profession":profession
    #     },
    # )
    with open(profile_log_path, "a") as fout:
        fout.write(json.dumps(data) + "\n")

    save_profile_to_db(data=data)
    logger.info("profile_filled", extra={"request": request, "extra_data": data})

    return data


def get_intensity(which_model_radio):
    intensity = {
        -1.5: "strongly",
        -0.5: "slightly",
        +0.5: "slightly",
        +1.5: "strongly",
    }
    return intensity[which_model_radio]


def get_chosen_model_name(which_model_radio, conversations):
    if which_model_radio in [-1.5, -0.5]:
        chosen_model_name = conversations[0].model_name
    elif which_model_radio in [0.5, 1.5]:
        chosen_model_name = conversations[1].model_name
    else:
        chosen_model_name = "invalid-vote"
        raise (ValueError)
    return chosen_model_name


def get_opening_prompt(conversation):
    for msg in conversation.conv.messages:
        if msg[0] == "user":
            return conversation.conv.messages[0][1]
    return ValueError("No opening prompt found")


def get_messages_dict(messages):
    messages_dict = []
    for message in messages:
        if len(message) == 2:
            messages_dict.append({"role": message[0], "content": message[1]})
        else:
            raise TypeError(f"Expected (role, msg) tuple, got {str(dict(message))}")
    return messages_dict


def count_turns(messages):
    return len(messages) // 2


def is_unedited_prompt(opening_prompt, category):
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
            INSERT INTO votes (tstamp, model_a_name, model_b_name, model_pair_name, chosen_model_name, intensity, opening_prompt, conversation_a, conversation_b, turns, selected_category, is_unedited_prompt, template, uuid, ip, session_hash, visitor_uuid, relevance, form, style, comments, extra)
            VALUES (%(tstamp)s, %(model_a_name)s, %(model_b_name)s, %(model_pair_name)s, %(chosen_model_name)s, %(intensity)s, %(opening_prompt)s, %(conversation_a)s, %(conversation_b)s, %(turns)s, %(selected_category)s, %(is_unedited_prompt)s, %(template)s, %(uuid)s, %(ip)s, %(session_hash)s, %(visitor_uuid)s, %(relevance)s, %(form)s, %(style)s, %(comments)s, %(extra)s)
        """
        )
        values = {
            "tstamp": round(time.time(), 4),
            "model_a_name": str(data["model_a_name"]),
            "model_b_name": str(data["model_b_name"]),
            "model_pair_name": json.dumps(sorted(data["model_pair_name"])),
            "chosen_model_name": str(data["chosen_model_name"]),
            "intensity": str(data["intensity"]),
            "opening_prompt": str(data["opening_prompt"]),
            "conversation_a": json.dumps(data["conversation_a"]),
            "conversation_b": json.dumps(data["conversation_b"]),
            "turns": int(data["turns"]),
            "selected_category": str(data["selected_category"]),
            "is_unedited_prompt": data["is_unedited_prompt"],
            "template": json.dumps(data["template"]),
            "uuid": str(data["uuid"]),
            "ip": str(data["ip"]),
            "session_hash": str(data["session_hash"]),
            "visitor_uuid": (data["visitor_uuid"]),
            "relevance": (data["relevance"]),
            "form": (data["form"]),
            "style": (data["style"]),
            "comments": str(data["comments"]),
            "extra": json.dumps(data["extra"]),
        }
        cursor.execute(insert_statement, values)
        conn.commit()
    except Exception as e:
        logger.error(f"Error saving vote to db: {e}")
        stacktrace = traceback.format_exc()
        print(f"Stacktrace: {stacktrace}")
    finally:
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

    chosen_model_name = get_chosen_model_name(which_model_radio, conversations)
    intensity = get_intensity(which_model_radio)

    conversation_a = get_messages_dict(conversations[0].conv.messages)
    conversation_b = get_messages_dict(conversations[1].conv.messages)

    # details = {
    #         "relevance": relevance_slider,
    #         "form": form_slider,
    #         "style": style_slider,
    #         "comments": comments_text,
    #     }

    # 1-5 => 0-100
    relevance = (
        (details["relevance"] - 1) * 25 if 1 <= details["relevance"] <= 5 else None
    )
    form = (details["form"] - 1) * 25 if 1 <= details["form"] <= 5 else None
    style = (details["style"] - 1) * 25 if 1 <= details["style"] <= 5 else None

    # TODO: Put opening_prompt in app_state?
    opening_prompt = str(get_opening_prompt(conversations[0]))
    data = {
        "tstamp": round(time.time(), 4),
        "model_a_name": conversations[0].model_name,
        "model_b_name": conversations[1].model_name,
        # sorted
        "model_pair_name": sorted(
            [conversations[0].model_name, conversations[1].model_name]
        ),
        "chosen_model_name": chosen_model_name,
        "intensity": intensity,
        "opening_prompt": opening_prompt,
        "conversation_a": conversation_a,
        "conversation_b": conversation_b,
        "turns": count_turns((conversations[0].conv.messages)),
        "selected_category": category,
        "is_unedited_prompt": (
            0
            if category == "unguided"
            else (is_unedited_prompt(opening_prompt, category))
        ),
        "template": (
            []
            if conversations[0].conv.name == "zero_shot"
            # FIXME: add template if there is some template
            else [conversations[0].conv.name + ": FIXME: UNAVAILABLE TEMPLATE"]
        ),
        "uuid": conversations[0].conv_id + "-" + conversations[1].conv_id,
        # Warning: IP is a PII
        "ip": str(get_ip(request)),
        "session_hash": str(request.session_hash),
        "visitor_uuid": (get_matomo_tracker_from_cookies(request.cookies)),
        "relevance": relevance,
        "form": form,
        "style": style,
        # FIXME: further input sanitizing?
        "comments": details["comments"],
        # For redundance
        "extra": {
            "cookies": dict(request.cookies),
            "query_params": dict(request.query_params),
            "path_params": dict(request.path_params),
        },
    }

    t = datetime.datetime.now()
    vote_log_filename = f"vote-{t.year}-{t.month:02d}-{t.day:02d}-{t.hour:02d}-{t.minute:02d}-{request.session_hash}.json"
    vote_log_path = os.path.join(LOGDIR, vote_log_filename)
    with open(vote_log_path, "a") as fout:
        logger.info("vote", extra={"request": request, "data": data})
        fout.write(json.dumps(data) + "\n")

    save_vote_to_db(data=data)

    return data


def stepper_html(title, step, total_steps):
    return f"""
    <div class="fr-stepper fr-container fr-pb-2w fr-px-2w">
    <h2 class="fr-stepper__title">
        {title}
        <span class="fr-stepper__state">Étape {step} sur {total_steps}</span>
    </h2>
    <div class="fr-stepper__steps" data-fr-current-step="{step}" data-fr-steps="{total_steps}"></div>

</div>"""


with open("./templates/welcome-modal.html", encoding="utf-8") as welcome_modal_file:
    welcome_modal_html = welcome_modal_file.read()

with open("./templates/header-arena.html", encoding="utf-8") as header_file:
    header_html = header_file.read()

    if os.getenv("GIT_COMMIT"):
        git_commit = os.getenv("GIT_COMMIT")
        header_html += f"<!-- Git commit: {git_commit} -->"


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
    consumption_days = watthours / (5 * 24)
    consumption_hours = watthours / 5
    consumption_minutes = watthours / (5 * 60)
    consumption_seconds = watthours / (5 * 60 * 60)

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
    streaming_hours = impact_gwp_value * 10000 / 317

    # Determine sensible unit based on magnitude
    if streaming_hours >= 24:  # 1 day in hours
        return int(streaming_hours / 24), "j"
    elif streaming_hours >= 1:
        return int(streaming_hours), "h"
    elif streaming_hours * 60 >= 1:
        return int(streaming_hours * 60), "min"
    else:
        return int(streaming_hours * 60 * 60), "s"


def build_reveal_html(
    model_a,
    model_b,
    which_model_radio,
    model_a_impact,
    model_b_impact,
    model_a_tokens,
    model_b_tokens,
):
    source = open("templates/reveal.html", "r", encoding="utf-8").read()
    template = Template(source)
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


def build_model_extra_info(name: str, all_models_extra_info_json: dict):
    # Maybe put orgs countries in an array here
    std_name = slugify(name.lower())
    logger = logging.getLogger("languia")
    if std_name in all_models_extra_info_json:
        model = all_models_extra_info_json[std_name]
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
        with open(register_api_endpoint_file) as file:
            api_endpoint_info = json.load(file)
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

        logger.debug("impact is None for " + model_name + ", deducing from params")
        if "active_params" in model_extra_info and "total_params" in model_extra_info:
            # TODO: add request latency
            # FIXME: multiply by 1_000_000?
            model_active_parameter_count = int(model_extra_info["active_params"])
            model_total_parameter_count=int(model_extra_info["total_params"])
        else:
            if "params" in model_extra_info:
                # TODO: add request latency
                model_active_parameter_count = int(model_extra_info["params"])
                model_total_parameter_count=int(model_extra_info["params"])
            else:
                logger.error(
                    "impact is None for "
                    + model_name
                    + ", and no params, closed model did not match ecologits list?"
                )
                return None
            
        
        # TODO: move to config.py
        electricity_mix_zone = "WOR"
        electricity_mix = electricity_mixes.find_electricity_mix(zone=electricity_mix_zone)
        if_electricity_mix_adpe=electricity_mix.adpe
        if_electricity_mix_pe=electricity_mix.pe
        if_electricity_mix_gwp=electricity_mix.gwp
        
        impact = compute_llm_impacts(
            model_active_parameter_count=model_active_parameter_count,
            model_total_parameter_count=model_total_parameter_count,
            output_token_count=token_count,if_electricity_mix_adpe=if_electricity_mix_adpe,if_electricity_mix_pe=if_electricity_mix_pe,if_electricity_mix_gwp=if_electricity_mix_gwp
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


def refresh_outage_models(previous_outage_models, controller_url):
    logger = logging.getLogger("languia")
    try:
        response = requests.get(controller_url + "/outages/", timeout=2)
    except Exception as e:
        logger.error("Couldn't reach controller: " + str(e))
        return previous_outage_models
    # Check if the request was successful
    if response.status_code == 200:
        # Parse the JSON response
        data = response.json()
        logger.info("refreshed outage models:" + str(data))
        return data
    else:
        logger.warning(f"Failed to retrieve outage data. Status code: {response.status_code}")
        return previous_outage_models


def add_outage_model(controller_url, model_name, reason):
    logger = logging.getLogger("languia")

    try:
        response = requests.post(
            json={"reason": str(reason)},
            url=f"{controller_url}/outages/?model_name={model_name}",
            timeout=2,
        )
    except Exception as e:
        logger.error("Failed to post outage data: " + str(e))
        return

    if response.status_code == 201:
        logger.info("successfully reported outage model " + model_name)
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
