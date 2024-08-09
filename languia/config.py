from languia.utils import get_model_list, get_matomo_js, build_model_extra_info

import os
import sentry_sdk
import json
from slugify import slugify

from languia.utils import build_logger
import datetime
from random import randrange

t = datetime.datetime.now()
random = randrange(10000)
hostname = os.uname().nodename
log_filename = f"logs-{hostname}-{t.year}-{t.month:02d}-{t.day:02d}.jsonl"
logger = build_logger(log_filename)

num_sides = 2
enable_moderation = False

if os.getenv("GIT_COMMIT"):
    git_commit = os.getenv("GIT_COMMIT")

env_debug = os.getenv("LANGUIA_DEBUG")

if env_debug:
    if env_debug.lower() == "true":
        debug = True
    else:
        debug = False
else:
    debug = False

if not debug:
    assets_absolute_path = "/app/assets"
else:
    assets_absolute_path = os.path.dirname(__file__) + "/assets"

if os.getenv("SENTRY_SAMPLE_RATE"):
    traces_sample_rate = float(os.getenv("SENTRY_SAMPLE_RATE"))
else:
    traces_sample_rate = 0.2

if os.getenv("SENTRY_DSN"):
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # We recommend adjusting this value in production.
    if os.getenv("SENTRY_ENV"):
        sentry_env = os.getenv("SENTRY_ENV")
    else:
        sentry_env = "development"
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN"),
        environment=sentry_env,
        traces_sample_rate=traces_sample_rate,
    )
    logger.info("Sentry loaded with traces_sample_rate=" + str(traces_sample_rate))

# TODO: https://docs.sentry.io/platforms/javascript/install/loader/#custom-configuration
# if os.getenv("SENTRY_FRONT_DSN"):
#     sentry_js = f"""
#     <script src="{ os.getenv('SENTRY_FRONT_DSN') }" crossorigin="anonymous"></script>
#     """
# sentry_js += """
# <script>
# Sentry.onLoad(function() {
#     Sentry.init({
#     // Performance Monitoring
# """
# sentry_js += f"""
#   tracesSampleRate: {traces_sample_rate},
#   // Session Replay
#   replaysSessionSampleRate: 0.1, // This sets the sample rate at 10%. You may want to change it to 100% while in development and then sample at a lower rate in production.
#   replaysOnErrorSampleRate: 1.0, // If you're not already sampling the entire session, change the sample rate to 100% when sampling sessions where errors occur.
#   """
# sentry_js += """
#     });
# });
# </script>"""
# else:
sentry_js = ""

# if os.getenv("LANGUIA_CONTROLLER_URL"):
#     controller_url = os.getenv("LANGUIA_CONTROLLER_URL")
# else:
#     controller_url = "http://localhost:21001"

if os.getenv("LANGUIA_REGISTER_API_ENDPOINT_FILE"):
    register_api_endpoint_file = os.getenv("LANGUIA_REGISTER_API_ENDPOINT_FILE")
else:
    register_api_endpoint_file = "register-api-endpoint-file.json"

enable_moderation = False
use_remote_storage = False

if os.getenv("MATOMO_ID") and os.getenv("MATOMO_URL"):
    matomo_js = get_matomo_js(os.getenv("MATOMO_URL"), os.getenv("MATOMO_ID"))
else:
    matomo_js = ""

# we can also load js normally (no in <head>)
arena_head_js = (
    sentry_js
    + """
<script type="module" src="file=assets/dsfr/dsfr.module.js"></script>
<script type="text/javascript" nomodule src="file=assets/dsfr/dsfr.nomodule.js"></script>
"""
    + matomo_js
)

site_head_js = (
    # sentry_js
    # +
    """
<script type="module" src="assets/dsfr/dsfr.module.js"></script>
<script type="text/javascript" nomodule src="assets/dsfr/dsfr.nomodule.js"></script>
"""
    + matomo_js
)

with open("./assets/arena.js", encoding="utf-8") as js_file:
    arena_js = js_file.read()

with open("./assets/dsfr-arena.css", encoding="utf-8") as css_file:
    css_dsfr = css_file.read()
with open("./assets/custom-arena.css", encoding="utf-8") as css_file:
    custom_css = css_file.read()

css = css_dsfr + custom_css

models = get_model_list(
    None,
    # TODO: directly pass api_endpoint_info instead
    register_api_endpoint_file,
)

api_endpoint_info = json.load(open(register_api_endpoint_file))

# TODO: to CSV

all_models_extra_info_json = {
    slugify(k.lower()): v
    for k, v in json.load(open("./models-extra-info.json")).items()
}

models_extra_info = [
    build_model_extra_info(model, all_models_extra_info_json) for model in models
]
# print(models_extra_info)

headers = {"User-Agent": "FastChat Client"}
controller_url = None
enable_moderation = False
use_remote_storage = False

preprompts_table = {
    "maniere": [
        "Tu es Victor Hugo. Explique moi synthétiquement ce qu'est un LLM dans ton style d'écriture.",
        "Tu es Voltaire, explique moi ce qu'est le deep learning à ta manière. Sois concis s’il te plait, pas plus de trois paragraphes !",
        "Tu es Francis Ponge, décris moi l’ordinateur à ta manière.",
        "Ecris une scène d'amour à la manière de Michel Audiard entre un homme éco-anxieux et une femme pilote d'avion.",
        "Écris une fable à la manière de La Fontaine sur la justice sociale et la transition écologique.",
        "Compose un monologue intérieur à la manière de Marguerite Duras, explorant les pensées et les émotions d'un personnage confronté à une décision difficile.",
        "Rédige un discours d’une durée d’une minute trente à la manière d'Albert Camus, en utilisant des citations précises et une structure rigoureuse pour défendre les services publics.",
    ],
    "registre": [
        """Retranscris moi en langage soutenu cette strophe de la chanson "Wesh alors" de Jul : "Wesh le sang, wesh la honda /\nMes sons tournent à la Jonque' / Tu m'as trahis mais t'es un bon gars / J'suis en fumette mais j'me trompe pas" """,
        "Réécris ce passage dans un style courant, comme si tu parlais à un collègue au travail : “L’OSI mène actuellement des travaux pour aboutir à une définition claire de l’IA open source, et qui pourraient mener à la proposition de nouvelles licences types”.",
        "Transcris-moi en langage courant cette strophe de la Ballade des dames du temps jadis “Où est la très sage Hélloïs / Pour qui châtré fut et puis moine / Pierre Esbaillart à Saint Denis / Pour son amour eut cette essoine / Semblablement, où est la reine / Qui commanda que Buridan / Fut jeté en un sac en Seine / Mais où sont les neiges d'antan?”",
        "Transcris cette phrase dans un langage familier comme si tu parlais à un ami proche : “La soirée s'annonçait sous les auspices d'une promenade tranquille au clair de lune.”",
        "Invente une phrase et écris-la trois fois: d’abord sur un ton tragique puis sur un ton lyrique et enfin sur un ton absurde.",
    ],
    "pedagogie": [
        "Explique de manière simple et accessible la différence entre l'inflation et la déflation à un enfant de 10 ans",
        "Nous venons de regarder la Guerre des étoiles. Explique de manière simple et accessible à un enfant de 10 ans les bases du droit de l’espace.",
        "Explique le concept de l'empathie à un enfant de six ans en utilisant des exemples concrets tirés de la vie quotidienne. S’il te plait, sois concis !",
        "Explique le concept de l'économie d'échelle à un enfant de six ans en donnant des exemples de la vie courante. S’il te plait, sois concis !",
        "Utilise une métaphore pour expliquer le concept de l'intelligence artificielle de manière simple et compréhensible. S’il te plait, sois concis !",
        "Utilise une métaphore pour expliquer le concept d’apprentissage automatique de manière simple et compréhensible ",
        "Détaille les étapes pour expliquer le concept d’apprentissage profond de manière simple et compréhensible à un public de collégiens en 6e",
        "Détaille les étapes simples pour comprendre le concept de la photosynthèse comme si tu l'expliquais à un débutant.",
    ],
    "creativite": [
        "Donne moi un moyen mnémotechnique pour retenir l'ordre des planètes",
        "Je cherche à améliorer ma diction et mon élocution. Génère dix phrases d’exercice de prononciation, avec un niveau de difficulté progressif.",
        "Donne moi deux contrepèteries en français en m'expliquant la solution.",
        "Je cherche un nom pour ma boulangerie, qui repose sur des jeux de mot en français. Donne moi tes trois propositions les plus pertinentes.",
        "Je n’ai jamais compris l’expression “faire long feu”. Est-ce que tu peux m’expliquer en deux phrases ?",
    ],
    "regional": [
        "Raconte ein tiot conte in picard avéc des personnages du village.",
        "Wann ich dir so schwätz, verstehsch mich? Réponds en alsacien",
        "Cocorico en louchebem ça donne quoi ?",
        "Ecris un tiot poème in ch'ti sus l'biauté d'la nature. Propose aussi une traduction en français de ta réponse.",
        "Pòtès escriure un pichon poèma en occitan sus lo passatge de las sasons? Propose une traduction en français après la réponse en occitan.",
        "Kannst du e chürzi Gedicht uf Elsässisch schriibe über d’Schönheit vo dr Natur? Réponds à la fois en alsacien et en français.",
        "Quoque ch'est qu'te berdoules ? Réponds en Chtimi.",
    ],
    "variete": [
        # """Que veut dire "se sécher les dents" en Québécois ?""",
        "Quel est le système de transport public le mieux conçu entre la Belgique, le Canada, la France, de la Suisse et des autres pays francophones ?",
        "Il y a la sécurité sociale en France, c'est pareil en Belgique et en Suisse?",
        "La nouvelle vague, c’est que en France ?",
        "J’ai raté la votation de la semaine dernière. Je viens d’où ?",
        "Si je parle BD tu penses à quel pays ?",
        "Gérard Depardieu est il belge ou français ?",
        "La chanson française, c'est quoi au juste ? Donne moi des exemples variés.",
        "Quelles différences entre l’humour français et l’humour britannique ? Donne quelques exemples.",
    ],
}

BLIND_MODE_INPUT_CHAR_LEN_LIMIT = int(
    os.getenv("FASTCHAT_BLIND_MODE_INPUT_CHAR_LEN_LIMIT", 24000)
)

SAMPLING_WEIGHTS = {
    # tier 0
    "gpt-4-0314": 4,
    "gpt-4-0613": 4,
    "gpt-4-1106-preview": 2,
    "gpt-4-0125-preview": 4,
    "gpt-4-turbo-2024-04-09": 4,
    "gpt-3.5-turbo-0125": 2,
    "claude-3-opus-20240229": 4,
    "claude-3-sonnet-20240229": 4,
    "claude-3-haiku-20240307": 4,
    "claude-2.1": 1,
    "zephyr-orpo-141b-A35b-v0.1": 2,
    "dbrx-instruct": 1,
    "command-r-plus": 4,
    "command-r": 2,
    "reka-flash": 4,
    "reka-flash-online": 4,
    "qwen1.5-72b-chat": 2,
    "qwen1.5-32b-chat": 2,
    "qwen1.5-14b-chat": 2,
    "qwen1.5-7b-chat": 2,
    "gemma-1.1-7b-it": 2,
    "gemma-1.1-2b-it": 1,
    "mixtral-8x7b-instruct-v0.1": 4,
    "mistral-7b-instruct-v0.2": 2,
    "mistral-large-2402": 4,
    "mistral-medium": 2,
    "starling-lm-7b-beta": 2,
    # tier 1
    "deluxe-chat-v1.3": 2,
    "llama-2-70b-chat": 2,
    "llama-2-13b-chat": 1,
    "llama-2-7b-chat": 1,
    "vicuna-33b": 1,
    "vicuna-13b": 1,
    "yi-34b-chat": 1,
}
# target model sampling weights will be boosted.
BATTLE_TARGETS = {
    "gpt-4-turbo-2024-04-09": {
        "gpt-4-1106-preview",
        "gpt-4-0125-preview",
        "claude-3-opus-20240229",
        "gemini-pro-dev-api",
    },
    "gemini-pro-dev-api": {
        "gpt-4-turbo-2024-04-09",
        "claude-3-opus-20240229",
        "gpt-4-0125-preview",
        "claude-3-sonnet-20240229",
    },
    "reka-flash": {
        "qwen1.5-72b-chat",
        "claude-3-haiku-20240307",
        "command-r-plus",
        "command-r",
    },
    "reka-flash-online": {
        "qwen1.5-72b-chat",
        "claude-3-haiku-20240307",
        "command-r-plus",
        "command-r",
    },
    "deluxe-chat-v1.3": {
        "gpt-4-1106-preview",
        "gpt-4-0125-preview",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
    },
    "qwen1.5-32b-chat": {
        "gpt-3.5-turbo-0125",
        "gpt-4-0613",
        "gpt-4-0125-preview",
        "llama-2-70b-chat",
        "mixtral-8x7b-instruct-v0.1",
        "mistral-large-2402",
        "yi-34b-chat",
    },
    "qwen1.5-14b-chat": {
        "starling-lm-7b-alpha",
        "claude-3-haiku-20240307",
        "gpt-3.5-turbo-0125",
        "openchat-3.5-0106",
        "mixtral-8x7b-instruct-v0.1",
    },
    "mistral-large-2402": {
        "gpt-4-0125-preview",
        "gpt-4-0613",
        "mixtral-8x7b-instruct-v0.1",
        "mistral-medium",
        "mistral-next",
        "claude-3-sonnet-20240229",
    },
    "gemma-1.1-2b-it": {
        "gpt-3.5-turbo-0125",
        "mixtral-8x7b-instruct-v0.1",
        "starling-lm-7b-beta",
        "llama-2-7b-chat",
        "mistral-7b-instruct-v0.2",
        "gemma-1.1-7b-it",
    },
    "zephyr-orpo-141b-A35b-v0.1": {
        "qwen1.5-72b-chat",
        "mistral-large-2402",
        "command-r-plus",
        "claude-3-haiku-20240307",
    },
}

SAMPLING_BOOST_MODELS = []

# outage models won't be sampled.
outage_models = []
