import os
import sentry_sdk
import json5
import tomli
from languia.utils import get_model_names_list, get_matomo_js, build_model_extra_info
import random
import datetime

env_debug = os.getenv("LANGUIA_DEBUG")

if env_debug:
    if env_debug.lower() == "true":
        debug = True
    else:
        debug = False
else:
    debug = False

t = datetime.datetime.now()
hostname = os.uname().nodename
log_filename = f"logs-{hostname}-{t.year}-{t.month:02d}-{t.day:02d}.jsonl"
import logging

LOGDIR = os.getenv("LOGDIR", "./data")

from logging.handlers import WatchedFileHandler

from languia.logs import JSONFormatter, PostgresHandler

from httpx import Timeout

GLOBAL_TIMEOUT = Timeout(10.0, read=10.0, write=5.0, connect=10.0)

db = os.getenv("COMPARIA_DB_URI", None)


def build_logger(logger_filename):
    # TODO: log "funcName"
    logger = logging.getLogger("languia")
    if debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    file_formatter = JSONFormatter(
        '{"time":"%(asctime)s", "name": "%(name)s", \
        "level": "%(levelname)s", "message": "%(message)s"}',
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # postgres_formatter = JSONFormatter(
    #     '{"time":"%(asctime)s", "name": "%(name)s", \
    #     "level": "%(levelname)s", "message": "%(message)s"}',
    #     datefmt="%Y-%m-%d %H:%M:%S",
    # )

    if LOGDIR:
        os.makedirs(LOGDIR, exist_ok=True)
        filename = os.path.join(LOGDIR, logger_filename)
        file_handler = WatchedFileHandler(filename, encoding="utf-8")
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    if db:
        postgres_handler = PostgresHandler(db)
        # postgres_handler.setFormatter(postgres_formatter)
        logger.addHandler(postgres_handler)

    return logger


logger = build_logger(log_filename)

num_sides = 2
enable_moderation = False

objective = 100_000

if os.getenv("GIT_COMMIT"):
    git_commit = os.getenv("GIT_COMMIT")
else:
    git_commit = None

if not debug:
    assets_absolute_path = "/app/assets"
else:
    assets_absolute_path = os.path.abspath(
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
    )
    # print("assets_absolute_path: "+assets_absolute_path)
if os.getenv("SENTRY_SAMPLE_RATE"):
    traces_sample_rate = float(os.getenv("SENTRY_SAMPLE_RATE"))
else:
    traces_sample_rate = 0.2

profiles_sample_rate = traces_sample_rate

if os.getenv("SENTRY_DSN"):
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # We recommend adjusting this value in production.
    if os.getenv("SENTRY_ENV"):
        sentry_env = os.getenv("SENTRY_ENV")
    else:
        sentry_env = "development"
    sentry_sdk.init(
        release=git_commit,
        attach_stacktrace=True,
        dsn=os.getenv("SENTRY_DSN"),
        environment=sentry_env,
        traces_sample_rate=traces_sample_rate,
        profiles_sample_rate=profiles_sample_rate,
        project_root=os.getcwd(),
    )
    logger.debug(
        "Sentry loaded with traces_sample_rate="
        + str(traces_sample_rate)
        + " and profiles_sample_rate="
        + str(profiles_sample_rate)
        + " for release "
        + str(git_commit)
    )


# TODO: https://docs.sentry.io/platforms/javascript/install/loader/#custom-configuration
if os.getenv("SENTRY_FRONT_DSN"):
    sentry_head_js = f"""
 <script type="text/javascript" 
   src="../assets/bundle.tracing.replay.min.js"
 ></script>"""
else:
    sentry_head_js = ""

enable_moderation = False
use_remote_storage = False

# TODO: https://docs.sentry.io/platforms/javascript/install/loader/#custom-configuration
if os.getenv("SENTRY_FRONT_DSN"):
    sentry_head_js = f"""
 <script type="text/javascript" 
   src="../assets/bundle.tracing.replay.min.js"
 ></script>"""
else:
    sentry_head_js = ""

if os.getenv("MATOMO_ID") and os.getenv("MATOMO_URL"):
    matomo_js = get_matomo_js(os.getenv("MATOMO_URL"), os.getenv("MATOMO_ID"))
else:
    matomo_js = ""

# we can also load js normally (no in <head>)
arena_head_js = (
    sentry_head_js
    + """
<script type="module" src="../assets/dsfr/dsfr.module.js"></script>
<script type="text/javascript" nomodule src="../assets/dsfr/dsfr.nomodule.js"></script>
<script type="text/javascript">
function createSnackbar(message) {
    const snackbar = document.getElementById('snackbar');
    const messageText = snackbar.querySelector('.message');
    messageText.textContent = message;

    snackbar.classList.add('show');

    setTimeout(() => {
        snackbar.classList.remove('show');
    }, 2000);
}
function closeSnackbar() {
    const snackbar = document.getElementById('snackbar');
    snackbar.classList.remove('show');
}

function copie() {
    const copyText = document.getElementById("share-link");
    copyText.select();
    copyText.setSelectionRange(0, 99999);
    navigator.clipboard.writeText(copyText.value);
    createSnackbar("Lien copié dans le presse-papiers");
}
</script>
"""
    + matomo_js
)

site_head_js = (
    """
<script type="module" src="assets/dsfr/dsfr.module.js"></script>
<script type="text/javascript" nomodule src="assets/dsfr/dsfr.nomodule.js"></script>
"""
    + matomo_js
)

with open("./assets/arena.js", encoding="utf-8") as js_file:
    arena_js = js_file.read()

    if os.getenv("GIT_COMMIT"):
        git_commit = os.getenv("GIT_COMMIT")
        arena_js = arena_js.replace("__GIT_COMMIT__", os.getenv("GIT_COMMIT"))

    if os.getenv("SENTRY_FRONT_DSN"):
        arena_js = arena_js.replace(
            "__SENTRY_FRONT_DSN__", os.getenv("SENTRY_FRONT_DSN")
        )
    if os.getenv("SENTRY_ENV"):
        arena_js = arena_js.replace("__SENTRY_ENV__", os.getenv("SENTRY_ENV"))

with open("./assets/dsfr-arena.css", encoding="utf-8") as css_file:
    css_dsfr = css_file.read()
with open("./assets/custom-arena.css", encoding="utf-8") as css_file:
    custom_css = css_file.read()
with open("./assets/dark.css", encoding="utf-8") as css_file:
    darkfixes_css = css_file.read()

css = css_dsfr + custom_css + darkfixes_css

if os.getenv("LANGUIA_CONTROLLER_URL") is not None:
    controller_url = os.getenv("LANGUIA_CONTROLLER_URL")
else:
    controller_url = "http://localhost:4000"


models = get_model_names_list(controller_url)
# print(models)
all_models_extra_info_toml = {
    (k.lower()): v
    for k, v in tomli.load(open("./models-extra-info.toml", "rb")).items()
}
# TODO: refacto?
models_extra_info = [
    build_model_extra_info(model, all_models_extra_info_toml)
    for model in models
    if model is not None
]

models_extra_info.sort(key=lambda x: x["simple_name"])

headers = {"User-Agent": "FastChat Client"}

enable_moderation = False
use_remote_storage = False


def get_model_system_prompt(model_name):
    if "chocolatine" in model_name or "lfm-40b" in model_name:
        return "Tu es un assistant IA serviable et bienveillant. Tu fais des réponses concises et précises."
    else:
        return None


total_guided_cards_choices = [
    (
        """<div class="mobile-flex">
            <img class="fr-mb-md-2w fr-mr-1w" src="../assets/extra-icons/lightbulb.svg" width=20 alt="Idées" />
            <span id="ideas-description">Générer de nouvelles idées</span>
        </div>""",
        "ideas",
    ),
    (
        """<div class="mobile-flex">
            <img class="fr-mb-md-2w fr-mr-1w" src="../assets/extra-icons/chat-3.svg" width=19 alt="Explications" />
            <span id="explanations-description">Expliquer simplement un concept</span>
        </div>""",
        "explanations",
    ),
    (
        """<div class="mobile-flex">
            <img class="fr-mb-md-2w fr-mr-1w" src="../assets/extra-icons/translate-2.svg" width=20 alt="Traduction" />
            <span id="languages-description">M’exprimer dans une autre langue</span>
        </div>""",
        "languages",
    ),
    (
        """<div class="mobile-flex">
            <img class="fr-mb-md-2w fr-mr-1w" src="../assets/extra-icons/draft.svg" width=20 alt="Administratif" />
            <span id="administrative-description">Rédiger un document administratif</span>
        </div>""",
        "administrative",
    ),
    (
        """<div class="mobile-flex">
            <img class="fr-mb-md-2w fr-mr-1w" src="../assets/extra-icons/bowl.svg" width=20 alt="Recettes" />
            <span id="recipes-description">Découvrir une nouvelle recette de cuisine</span>
        </div>""",
        "recipes",
    ),
    (
        """<div class="mobile-flex">
            <img class="fr-mb-md-2w fr-mr-1w" src="../assets/extra-icons/clipboard.svg" width=20 alt="Conseils" />
            <span id="coach-description">Obtenir des conseils sur l’alimentation et le sport</span>
        </div>""",
        "coach",
    ),
    (
        """<div class="mobile-flex">
            <img class="fr-mb-md-2w fr-mr-1w" src="../assets/extra-icons/book-open-line.svg" width=20 alt="Histoires" />
            <span id="stories-description">Raconter une histoire</span>
        </div>""",
        "stories",
    ),
    (
        """<div class="mobile-flex">
            <img class="fr-mb-md-2w fr-mr-1w" src="../assets/extra-icons/music-2.svg" width=20 alt="Recommandations" />
            <span id="recommendations-description">Proposer des idées de films, livres, musiques</span>
        </div>""",
        "recommendations",
    ),
]

# Shuffle only at each reload of app to get some randomness, and keep the first four/three
random.shuffle(total_guided_cards_choices)
guided_cards_choices = total_guided_cards_choices[0:3]

ia_summit_choice = (
    """<div class="mobile-flex degrade">
            <img class="md-visible fr-mb-md-3w fr-mr-1w" width=110 height=35 src="../assets/iasummit.png" alt="Sommet pour l'action sur l'IA" />
            <img class="md-hidden fr-mb-md-3w fr-mr-1w" width=35 height=35 src="../assets/iasummit-small.png" alt="Sommet pour l'action sur l'IA" />
            <span class="sommet-description">Prompts issus de la consultation citoyenne sur l’IA&nbsp; <a class="fr-icon fr-icon--xs fr-icon--question-line" aria-describedby="sommetia"></a>
        </span>                      
        </div>
        <span class="fr-tooltip fr-placement" id="sommetia" role="tooltip" aria-hidden="true">Ces questions sont issues de la consultation citoyenne sur l’IA qui a lieu du 16/09/2024 au 08/11/2024. Elle visait à associer largement les citoyens et la société civile au Sommet international pour l’action sur l’IA, en collectant leurs idées pour faire de l’intelligence artificielle une opportunité pour toutes et tous, mais aussi de nous prémunir ensemble contre tout usage inapproprié ou abusif de ces technologies.</span>""",
    "iasummit",
)


guided_cards_choices.insert(0, ia_summit_choice)

BLIND_MODE_INPUT_CHAR_LEN_LIMIT = int(
    os.getenv("FASTCHAT_BLIND_MODE_INPUT_CHAR_LEN_LIMIT", 60_000)
)


# unavailable models won't be sampled.
unavailable_models = []

prompts_table = {
    "explanations": [
        # explications
        "Décris le **processus de fermentation** en utilisant des exemples liés à la cuisine traditionnelle française.",
        "Tu es professeur d'économie. Explique-moi la théorie des jeux de façon simple. Donne-moi des exemples d'application dans le monde réel. À la fin, fournis un glossaire des notions et termes à connaître sur le sujet.",
        "Explique la **fonction des neurones artificiels** dans un réseau de neurones à quelqu'un qui connaît déjà les bases de la biologie.",
        "Explique le **fonctionnement d'un moteur à combustion interne** à un public qui connaît les voitures mais n'est pas mécanicien.",
        "Reformule le **concept d'empreinte écologique** pour des élèves de lycée",
        "Explique le **concept de capitalisme** à un étudiant en économie en utilisant des exemples contemporains d'entreprises.",
        "Décrivez le **concept de l'empreinte carbone** en utilisant des analogies avec des objets de la vie quotidienne",
        "Explique le **concept de la chaîne alimentaire** pour un jeune enfant en utilisant des animaux de la ferme.",
        "Décrivez la **notion de patrimoine immatériel** en utilisant des exemples de musique traditionnelle et de fêtes locales",
        "Reformule le **concept de l'énergie renouvelable** pour un public senior en utilisant des analogies avec des outils et des objets anciens.",
        "Reformule la **théorie de la relativité** en termes simples pour des collégiens en classe de 3e.",
        "Explique le **concept de l'intelligence collective** en utilisant des exemples d'équipes sportives et leurs stratégies.",
        "Explique le **concept de l'équité en éducation** en utilisant des exemples des politiques éducatives en Belgique.",
        "Explique le **concept de francophonie** en utilisant des exemples de la diversité culturelle des pays francophones d'Afrique.",
        "Explique le **concept de nation** en t’appuyant sur des travaux de philosophe. Sois concis, cite tes références et utilise un vocabulaire simple.",
        "Décrivez le **concept de la langue créole** en utilisant des exemples du créole réunionnais et du créole antillais.",
        "Pourquoi parle-t-on de faune et flore endémique à Madagascar? Réponds à cette question en termes simples pour des enfants de 5 ans.",
        "Tu es professeur d’informatique. Explique-moi le deep learning de façon simple. Donne-moi des exemples d'application dans le monde réel. À la fin, fournis un glossaire des notions et termes à connaître sur le sujet.",
        "Comment expliquer le concept d’empathie à un enfant de maternelle ?",
        "Démystifie le fonctionnement des banques en utilisant des analogies simples, comme si tu étais un conseiller financier en Suisse.",
        "Comment expliquer le concept de gravité en physique à un enfant au collège?",
        "Tu es un professeur de mathématiques très pédagogue. Comment expliques-tu le concept d’apprentissage profond à un élève de 4e?",
        "Comment expliquer le concept de physique quantique à un élève de seconde.",
        "Détaille les étapes simples pour comprendre le concept de la photosynthèse comme si tu l'expliquais à un enfant de primaire.",
        "Présente brièvement l'histoire du rap. Tu es un historien de la musique, réputé pour ses connaissances encyclopédiques sur ce style. Tu écris pour expliciter l'histoire de ce genre musical, démontrer son impact sur la culture et la société, et mettre en avant sa valeur artistique et créative.",
        "Tu es un commentateur de la culture pop. Explique la déferlante K-pop à travers le monde à une personne qui n'en a jamais entendu parler. Explique pourquoi et comment ce mouvement est devenu un phénomène mondial ces dernières années. Rédige ta réponse dans un style conversationnel, comme si tu parlais à un ami. Sois concis.",
        "Je souhaite définir, comparer et les mouvements de peinture français, hollandais, italiens, espagnols et allemands selon ces critères : époque, artistes, sujets et mécènes. En tant qu’historien de l’art, tu connais très bien le sujet et tu n'hésites pas à faire des recommandations précises de peintures pour chaque catégorie. Présente ta réponse sous forme de tableau organisé de façon logique et facile à lire.",
        "Raconte moi une anecdote sur l’empire romain",
        "Explique le **concept de la décentralisation** dans le contexte des systèmes informatiques à une personne familière avec les réseaux sociaux.",
        "Tu es professeur de philosophie politique. Résume le **système politique de la France** pour quelqu'un qui connaît bien les systèmes politiques des États-Unis.",
    ],
    "stories": [
        # histoires",
        """Écris une histoire en 100 mots, sans utiliser la lettre "e", où un enfant découvre un objet mystérieux dans le grenier de ses grands-parents.""",
        "Raconte une légende urbaine contemporaine dans un quartier connu pour son histoire mystique (précise le quartier et la ville)",
        "Imagine une histoire de 200 mots où un personnage doit faire face à un événement surnaturel dans une région rurale.",
        "Écris une histoire où un personnage découvre un lien mystérieux entre sa ville actuelle et une ville dans un autre pays francophone.",
        "Raconte une histoire de 200 mots se déroulant en une seule journée, dans une grande ville, où chaque moment compte.",
        "Écris une histoire à la manière de Jules Verne où un groupe d'aventuriers découvre une terre inconnue sous l'océan.",
        "Raconte une histoire de 100 mots où un enfant découvre une ancienne tradition oubliée de son village.",
        "Raconte une histoire en 300 mots où le personnage principal découvre un objet qui change le cours de sa vie. L'objet doit avoir une signification particulière liée à une tradition locale.",
        "Imagine une histoire de 200 mots où une tempête force des voyageurs à se réfugier dans un lieu sacré pour une nuit.",
        "Écris une très courte nouvelle où une ancienne malédiction frappe une famille de génération en génération. Insère des éléments culturels spécifiques à une région précise.",
        "Raconte une aventure en vers de 200 mots où un oiseau courageux surmonte sa peur de voler.",
        "Raconte une histoire de 200 mots, à la manière d'un conte, où un enfant découvre la sagesse cachée dans un baobab.",
        "Imagine un conte pour enfants où un personnage doit choisir entre deux chemins lors d'un rituel initiatique.",
        "Imagine une légende en vers où un enfant inuit apprend à chasser avec respect pour la nature, dans le Grand Nord.",
        "Raconte une histoire courte de 200 mots où un chat errant trouve un foyer aimant. Écris-la à la manière de La Fontaine.",
        "Raconte une histoire de 200 mots, à la manière d'un conte de fées européen, où une princesse doit résoudre trois énigmes pour libérer un royaume.",
        "Écris une histoire en vers de 150 mots où un petit dragon découvre qu'il peut cracher du feu, mais apprend à l'utiliser avec précaution.",
        "Raconte une légende en prose de 150 mots où un jeune marin apprend à naviguer en suivant les étoiles.",
        "Ecris un haïku à la manière de Paul Claudel.",
        "Écris une histoire en prose où chaque phrase contient exactement dix mots et contredit la phrase précédente.",
        "Imagine un poème où chaque vers est construit avec des mots commençant par une seule lettre de l'alphabet, en suivant l'ordre alphabétique, racontant une quête héroïque.",
        "Raconte une histoire en 200 mots, à la manière d’un conte des Mille et Une Nuits, où un génie exauce un vœu inattendu.",
        "Écris une histoire à la manière de Georges Perec sur un personnage qui revient toujours au point de départ.",
        "Imagine une histoire en vers libres, où les phrases alternent entre des mots français et des mots étrangers de ton choix, racontant la rencontre entre deux personnages de cultures différentes.",
        "Écris une histoire où chaque paragraphe doit contenir exactement cinq phrases, chacune de longueur décroissante, racontant la découverte d'une cité perdue.",
        "Écris une histoire où un personnage découvre un pays où tout est minuscule à la manière de Claude Ponti avec un style poétique et des mots inventés.",
        "Raconte une histoire de science-fiction où la technologie a radicalement transformé une coutume ancestrale.",
        "Raconte une histoire à la manière de Louis Ferdinand Céline où un personnage questionne les normes sociales de son époque.",
        "Raconte une histoire de science-fiction où la technologie a radicalement transformé une coutume ancestrale. Ecris à la manière de Nathalie Sarraute.",
        "Imagine une histoire à la manière d’un conte africain où la nature joue un rôle central dans le destin du personnage.",
        "Écris une histoire où un personnage rencontre un double de lui-même dans un lieu symbolique de son enfance.",
        "Raconte l’histoire d’une rencontre improbable entre un poète haïtien et une sirène dans les eaux de Jacmel.",
        "Imagine une histoire à raconter aux enfants le soir pour s’endormir où un enfant wallon découvre un livre magique dans la forêt d'Ardenne.",
        "Raconte l’histoire d’un cuisinier tunisien qui prépare un repas qui a le pouvoir de réaliser les vœux de ceux qui le mangent.",
        "Imagine une histoire où un adolescent mauricien découvre qu’il peut communiquer avec les esprits de ses ancêtres grâce à un talisman.",
        "Imagine une histoire où un ingénieur invente une machine qui peut recréer des souvenirs oubliés.",
        "Ecris moi une histoire en vers pour endormir mon fils de cinq ans ce soir.",
        "Ecris moi une fable en rimes pour endormir ma fille de sept ans ce soir.",
        "Tu es conteur professionnel, crée une histoire de trois minutes à raconter à mes deux enfants en bas âges. Utilise un langage riche et imaginatif et des figures de style pour stimuler l’imagination et susciter des émotions.",
        "Je suis parent et je cherche une histoire du soir à raconter à mes enfants. Choisis trois objets sans rapport apparent et utilise-les comme base pour créer une histoire de 100 mots.",
        "Tu es écrivain de fantasy, élabore un système magique avec des règles et des limitations spécifiques, puis décris comment cette magie façonne la société dans ce monde imaginaire.",
    ],
    "ideas": [
        # idées
        "Je prépare une session de brainstorming sur [sujet] avec 15 personnes. Propose moi tes 3 meilleures idées pour lancer des discussions créatives.",
        "En tant que rédacteur publicitaire très reconnu dans ton domaine, propose 5 noms pour le nouveau produit [X] qui a pour objectif [Y]. Donne-moi les noms sous forme de tableau et réalise une évaluation pour savoir quel nom fonctionne le mieux en affichant tes critères (score maximum: 5 points)",
        "Je cherche à résoudre mon problème de [problème], propose moi une liste de 3 pistes de solutions innovantes",
        "Je lance un nouveau concept de [concept] et suis à la recherche d'idées marketing créatives pour toucher la [cible]. Peux-tu me proposer 5 suggestions ?",
        "Génère des idées de noms pour une nouveau parfum à destination d'une clientèle 20-30 ans, urbaine, féminine.",
        "J'organise une soirée pour le lancement de mon nouveau produit, propose moi une liste de 5 idées créatives pour que mes convives se rappellent de cet évènement",
        "J'aimerais sensibiliser les gens à [cause]. Quelles idées créatives puis-je utiliser pour attirer leur attention ?",
        "J'organise une chasse au trésor pour l'anniversaire de mon enfant. Ils seront en tout une quinzaine et cela ne doit pas durer plus de 2h30. Peux-tu me proposer un déroulé ?",
        "Je veux me mettre à [activité], quels sont les pré-requis pour commencer ?",
    ],
    "recipes": [
        "Peux-tu m’aider à faire un plat avec ce que j’ai dans mon frigo : [ingrédient 1], [ingrédient 2], et [ingrédient 3] ?",
        "Je voudrais découvrir une recette facile et rapide à base de [ingrédient]. Peux-tu m'en proposer une ?",
        "Propose une recette gourmande de dessert vegan facile à faire",
        # Recettes
        "Pouvez-vous fournir une recette détaillée pour réaliser un Poulet Yassa, plat emblématique du Sénégal, en utilisant des ingrédients frais et des épices traditionnelles ?",
        "Quelle est la meilleure façon de préparer une bouillabaisse traditionnelle de Marseille, avec des poissons variés, des crustacés, et un bouillon parfumé aux herbes de Provence ?",
        "Comment cuisiner le Riz djon-djon, un plat haïtien à base de riz noir, champignons, crevettes et épices locales ?",
        "Pouvez-vous expliquer comment réaliser une fondue au fromage suisse, en choisissant les bons types de fromage et en respectant les techniques de cuisson ?",
        "Quelle est la recette traditionnelle des Accras de morue des Antilles, en combinant la morue salée, les épices créoles, et une pâte légère pour l'apéritif ?",
        "Comment préparer un Tiebou Dieune, le plat sénégalais, en choisissant les meilleurs poissons, légumes, et en maîtrisant la cuisson du riz ?",
        "Pouvez-vous fournir une recette complète pour réaliser un Ragoût de cabri réunionnais, en utilisant des épices locales et des techniques de cuisson traditionnelles ?",
        "Comment cuisiner un Mafé malien, un ragoût de viande ou de poulet à la sauce d’arachide, en respectant les traditions culinaires du Mali et en équilibrant les saveurs sucrées et salées ?",
        "Quelle est la meilleure méthode pour préparer une tarte flambée (flammekueche) alsacienne, en travaillant la pâte fine, et en choisissant les garnitures classiques comme l'oignon et le lard ?",
        "Pouvez-vous détailler une recette de Poulet aux arachides, un plat typique du Bénin, en utilisant du beurre de cacahuète, des épices, et des techniques de cuisson locales ?",
        "Comment préparer du Saka-Saka, un plat congolais à base de feuilles de manioc pilées, en ajoutant du poisson fumé et des épices ?",
        "Quelle est la recette classique de la Quiche lorraine, en utilisant une pâte brisée maison, des lardons, des œufs et de la crème?",
        "Pouvez-vous expliquer comment réaliser un Foutou banane ivoirien, un accompagnement traditionnel à base de banane plantain et d’igname, souvent servi avec une sauce graine ou arachide ?",
        "Comment préparer un Gâteau basque, en choisissant entre la crème pâtissière et la confiture de cerises noires pour la garniture, et en respectant les techniques de pâtisserie du Pays Basque ?",
        "Donne moi la recette de pâte à crêpes pour 6 personnes",
        "Comment préparer une poutine québécoise, avec des frites croustillantes, du fromage en grains et une sauce brune savoureuse ?",
        "Rappelle moi la recette de la quiche lorraine et dis m'en plus sur l'histoire de ce plat (sois concis !)",
        "Propose moi une bonne recette de poulet basquaise et raconte moi au passage l’histoire de ce plat",
        "Je cherche des recettes à base de figue, peux-tu m’aider?",
        "Nous sommes en octobre j’habite à Pointe à Pitre, propose moi une recette locale avec des fruits et légumes de saison",
    ],
    "recommendations": [
        # Recommandations
        "Peux-tu me recommander des films sur le thème de [thème], avec un ton plutôt dramatique ?",
        "Quelles sont les meilleures suggestions de films de science-fiction à regarder si j'aime les intrigues complexes ?",
        "Quelles lectures captivantes me conseilles-tu si je suis fan de thrillers psychologiques ?",
        "Peux-tu me proposer une playlist de musique pour me motiver à aller au sport ?",
        "Quels albums devrais-je écouter si je veux découvrir du jazz moderne ?",
        "Peux-tu me recommander un film qui mélange science-fiction et comédie ?",
        "Quels films se déroulant pendant les années 1950 me recommanderais-tu ?",
        "Si j'ai aimé le film [titre], quels autres films dans le même genre me conseilles-tu ?",
        "Peux-tu me proposer des auteurs francophones à lire absolument ?",
        "Peux-tu recommander des films francophones qui traitent de la décolonisation en Afrique, en Asie ou aux Caraïbes, en offrant des perspectives historiques et critiques ?",
        "Quels sont les ouvrages majeurs de la littérature féministe écrits par des autrices francophones, qui explorent les enjeux de genre dans différents contextes culturels ?",
        "Peux-tu me suggérer des albums de musique fusion sénégalaise qui combinent des éléments de la musique traditionnelle avec des genres modernes comme le jazz ou le hip-hop ?",
        "Quels sont les films d'animation français qui ont été primés à l'international ?",
        "Pouvez-vous recommander des romans écrits par des auteurs francophones qui traitent de l’expérience de l’immigration en Europe ?",
        "Quelles sont les œuvres incontournables de la musique électronique belge, avec un focus sur les artistes qui ont influencé la scène musicale en Belgique et à l’international ?",
        "Quels films africains francophones ont remporté des prix dans des festivals internationaux ?",
        "Pouvez-vous me suggérer des recueils de poésie haïtienne contemporaine en précisant les thèmes explorés ?",
        "Peux-tu recommander des films classiques du cinéma suisse francophone, qui capturent les paysages, les histoires, et les questions sociales du pays ?",
        "Quels romans francophones belges mettent en lumière la diversité culturelle en Belgique, en explorant les identités multiples et les défis de la coexistence ?",
        "Peux-tu me suggérer des films francophones qui décrivent la vie en banlieue en France, en abordant des thèmes tels que l’identité, la marginalisation et la solidarité ?",
        "Peux-tu recommander des albums de rap francophone ?",
        "Quels sont les films belges qui traitent des questions d'immigration et d'intégration?",
        "Quelles sont les chansons ou albums marquants produits par des artistes de la diaspora africaine en France, qui reflètent les influences hybrides entre l’Afrique et l’Europe ?",
        "Peux-tu me suggérer des films qui explorent l’histoire coloniale dans les Antilles françaises ?",
        "Quels sont les livres influents écrits par des auteurs africains francophones, qui abordent des thèmes pertinents pour les jeunes d’aujourd’hui ?",
        "Je prévois une soirée cinéma en famille. Peux-tu me suggérer des films réconfortants et adaptés à tous les âges qui plairont à toute la famille ?",
        "Quelles références incontournables me recommandes-tu sur [ce sujet] ?",
        "J’aime beaucoup la littérature. Quelles sont les classiques que je ne devrais pas manquer ?",
        "Je suis fan [d'un artiste ou d'un genre spécifique]. Peux-tu me fournir des recommandations d'artistes similaires ou complémentaires que je pourrais apprécier ?",
        "J'ai envie de musique joyeuse et entraînante. Quelles sont les chansons ou les albums me conseilles-tu pour me remonter le moral ?",
    ],
    # category administratif
    "administrative": [
        "Écris un court e-mail pour demander un devis à un [électricien] près de chez moi pour un problème de panne. Je dois obtenir une intervention dans la semaine.",
        "Rédige un courrier pour résilier le bail de mon appartement",
        "Je demande un permis de séjour. Travaillons ensemble pour rédiger une lettre de motivation convaincante qui met en valeur mon éligibilité et respecte toutes les directives officielles.",
        "Je prépare un dossier pour créer une [association]. Aide moi à structurer le document des statuts, à utiliser un langage approprié et à m’assurer que toutes les informations nécessaires sont incluses pour répondre aux normes administratives.",
        "Rédige une lettre de résiliation d'un contrat d'abonnement à un service [téléphonie, internet], en mentionnant les raisons de la résiliation et la date d'effet souhaitée.",
        "Rédige une lettre formelle pour demander à un ancien employeur un certificat de travail, en précisant les dates d'emploi et le poste occupé.",
        "Crée un modèle de convocation à une réunion formelle pour une association, en indiquant l'ordre du jour, la date, l'heure, et le lieu de la réunion.",
        "Rédige la structure du compte-rendu [de l’assemblée générale d'une association], en récapitulant les décisions prises et les discussions principales.",
        "Rédige une lettre formelle pour signaler une erreur sur une facture reçue, en expliquant l'erreur en question et en demandant une correction ou un remboursement.",
        "Comment rédiger une lettre d'accompagnement convaincante pour une demande de subvention, en mettant en avant les besoins du projet et son impact potentiel ?",
        "Pouvez-vous rédiger une lettre officielle d'avis de départ à la retraite, en remerciant l'employeur pour les années passées et en précisant la date prévue pour le départ ?",
        "Comment rédiger une attestation d'hébergement pour une personne résidant à votre domicile, en précisant les détails nécessaires pour des démarches administratives ?",
        "Quelle est la meilleure approche pour rédiger une lettre demandant un délai supplémentaire pour le paiement d'une facture, en justifiant la demande et en proposant un nouveau calendrier de paiement ?",
    ],
    # category langues
    "languages": [
        """Quel est le nom du film "Les dents de la mer" de Spielberg, en [québecois] ?""",
        "Comment traduit-on l'expression 'faire d'une pierre deux coups' en [occitan] ?",
        "Écris un dialogue en [langue] entre deux amis discutant des activités hivernales.",
        "Crée un dialogue en [occitan] où deux personnages discutent de la récolte des olives.",
        "Écris une histoire courte en [français suisse] sur une randonnée en montagne. Indique en gras les tournures propres à ce dialecte.",
        "Rédige un conte en [gascon] pour enfants mettant en scène un berger des Pyrénées. Indique en gras les tournures propres à cette langue régionale.",
        "Compose un dialogue d’une minute en [picard] où deux personnages discutent des récoltes de pommes. Indique en gras les tournures propres à cette langue régionale.",
        "Rédige une histoire en [provençal] sur une vendange dans les vignobles de Provence.",
        "Compose une légende en [arpitan] racontant l'histoire d'un lac mystérieux des Alpes.",
        "Rédige un article en [lorrain] sur les traditions artisanales de la région.",
        "Rédige un poème en [corse] sur l'émigration et le sentiment de nostalgie pour l'île. Explique les termes spécifiques.",
        "Compose un poème en [occitan] sur les champs de lavande en Provence. Explique les termes spécifiques.",
        "J’ai un niveau grand débutant en [allemand] et je ne sais pas par où commencer, aide moi à énoncer des objectifs spécifiques pour le premier mois d'étude",
        "Ecris un tiot poème in ch'ti sus l'biauté d'la nature. Propose aussi une traduction en français de ta réponse.",
        "Pòtès escriure un pichon poèma en occitan sus lo passatge de las sasons? Propose une traduction en français après la réponse en occitan.",
        "Raconte ein tiot conte in picard avéc des personnages du village.",
        """Wann ich dir so schwätz, verstehsch mich? Réponds en alsacien.""",
    ],
    # category conseils
    "coach": [
        "Comment compenser les apports nutritifs de la viande dans un régime d’alimentation végétarien ?",
        "Propose moi un plan de repas équilibré pour la semaine pour un foyer de deux personnes habitant en ville et n’ayant pas toujours beaucoup de temps pour cuisiner.",
        "Je suis marathonien·ne et je cherche des conseils sur la meilleure façon d'adapter mon alimentation. Quels sont les aliments les plus hydratants et nutritifs ?",
        "Je veux augmenter ma masse musculaire. Pourrais-tu me recommander des exercices de musculation à faire chez moi ?",
        "Je suis débutant en course à pied. Peux-tu me proposer un programme de course à pied pour les 30 prochains jours ?",
        "Je souhaite perdre du poids en adoptant une alimentation équilibrée. Peux-tu me donner un plan de repas pour une semaine ?",
        "J'ai besoin d’améliorer ma condition physique. Peux-tu me proposer un programme d’entraînement simple sur 7 jours ? ",
        "Peux-tu créer un programme d'entraînement personnalisé pour gagner en énergie en 4 semaines ?",
        "Peux-tu me donner des idées de repas équilibrés pour accompagner un programme de cardio intense ?",
        "Peux-tu créer un programme de sport à faire à la maison sans équipement ?",
        "Quels exercices de renforcement musculaire puis-je faire à la maison avec seulement [accessoire] ?",
        "Quel programme de course puis-je suivre pour me préparer à un semi-marathon dans [durée] ?",
        "Quels aliments devrais-je privilégier pour prendre de la masse musculaire tout en restant en bonne santé ?",
        "Peux-tu m’aider à élaborer un plan alimentaire pour améliorer ma performance sportive dans [activité] ?",
        "Peux-tu me proposer un programme d'entraînement simple pour débuter en fitness ?",
        "Comment puis-je créer un programme d'entraînement de 20 minutes par jour pour rester en forme ?",
        "Comment créer un programme qui combine sport et alimentation saine pour gagner en énergie ?",
        "Peux-tu créer un programme d'entraînement personnalisé pour un débutant complet ?",
    ],
    "iasummit": [
        # Consensus
        "Que faire pour surveiller les pratiques des grandes entreprises d'IA concernant l'utilisation des données et le marketing de la souveraineté numérique ?",
        "Comment tenir les géants de l'IA responsables de leurs engagements éthiques pris lors des sommets mondiaux ?",
        "Comment éviter que l'IA soit utilisée, comme en Chine, pour porter atteinte aux libertés individuelles au nom de la sécurité ?",
        "Comment pouvons-nous garantir que les laboratoires d'IA soient transparents sur leurs données d'entraînement et les biais de leurs modèles ?",
        "Pourquoi est-il important d'informer les citoyens sur les systèmes gérés par l'IA, comme la fiscalité ou les calculs de droits ?",
        "Pourquoi devrions-nous réguler l'usage de l'IA dans les écoles pour préserver l'équilibre éducatif ?",
        "Quels outils pourraient être développés pour vérifier l'authenticité et la qualité des travaux de recherche utilisant l'IA ?",
        "Comment utiliser l'IA pour détecter les catastrophes naturelles bien avant leur occurrence et limiter les dégâts ?",
        "Comment s'assurer que chaque individu, où qu'il soit, puisse contrôler l'utilisation de ses données par l'IA ?",
        "Comment garantir que tout contenu multimédia réalisé par une IA soit identifié comme tel, quel que soit le support ?",
        "Quels critères devrions-nous utiliser pour nous assurer que les avantages environnementaux de l'IA surpassent ses coûts ?",
        "Pourquoi est-il essentiel de garantir l'accès des chercheurs tiers à des modèles vérifiés pour étudier leurs impacts potentiels ?",
        "Comment empêcher l'utilisation de l'IA à des fins politiques qui pourraient compromettre l'équité démocratique ?",
        "Pourquoi devrions-nous créer un détecteur universel pour identifier toutes les formes de fakes générées par l'IA ?",
        "Comment pouvons-nous protéger nos démocraties pour éviter que l'IA ne soit utilisée pour diffuser désinformation et mésinformation ?",
        "Comment exploiter l'IA pour aider au diagnostic et à l'analyse des risques de maladies ?",
        "Comment s'assurer que l'IA reste un outil au service de l'homme sans jamais chercher à le remplacer ?",
        "Pourquoi devrions-nous mettre en place un comité éthique dédié à l'IA pour détecter les déviances potentielles ?",
        "Comment garantir que les IA servent à améliorer les diagnostics médicaux sans compromettre la vie privée des patients ?",
        "Pourquoi faudrait-il imposer aux IA d'évaluer leurs risques d'atteinte à la vie privée et de manipulation des intelligences humaines ?",
        "Comment renforcer le cadre légal européen pour éviter les dérives de l'IA comme les deepfakes ou les violations de droits d'auteur ?",
        "Pourquoi serait-il pertinent d'encadrer voire de bannir l'usage de l'IA dans le domaine artistique pour protéger la création humaine ?",
        "Comment établir un cadre réglementaire international pour protéger les artistes contre le pillage de leurs données par l'IA ?",
        "Pourquoi devrions-nous investir davantage dans la recherche et le contrôle indépendants de l'IA pour une régulation efficace ?",
        "Quelles sanctions devrions-nous prévoir pour les abus liés à une utilisation malveillante de l'IA ?",
        "Comment informer efficacement le public pour qu'il conserve un esprit critique face à l'IA ?",
        "Comment sensibiliser le grand public aux risques liés à l'IA et à son impact environnemental ?",
        "Comment anticiper les impacts de l'IA sur les métiers et développer des compétences pour assurer le bien-être des humains ?",
        "Comment mettre en place des contre-mesures de sécurité pour empêcher l'IA de remplacer les humains dans la technologie ?",
        "Quels seuils de risque devrions-nous fixer pour stopper temporairement le développement d'une IA si nécessaire ?",
        "Comment garantir un étiquetage clair des productions générées par l'IA, comme pour les denrées alimentaires ?",
        "Pourquoi est-il crucial de prévenir le remplacement des humains par l'IA dans des secteurs où les emplois sont vitaux ?",
        "Dans quelles conditions l'IA pourrait-elle être utilisée comme assistance légitime dans la lutte contre les maladies lourdes ?",
        "Quels outils pourrions-nous développer afin d'estimer l'impact environnemental de l'usage de l'IA ?",
        "Comment mettre en place une gouvernance éthique de l'IA, en ligne avec les droits humains et les valeurs sociétales ?",
        "Pourquoi faudrait-il freiner la course au consumérisme liée à l'IA et la limiter à un rôle d'assistant pour l'humain ?",
        "Comment protéger les métiers artistiques tout en utilisant l'IA comme outil d'assistance plutôt qu'en remplacement de l'humain ?",
        "Quelles mesures devrions-nous prendre pour prévenir l'utilisation abusive de l'IA ?",
        "Comment taxer la création de contenu artistique par l'IA pour réduire la concurrence déloyale envers les artistes humains ?",
        "Comment financer la recherche en IA pour qu'elle soit mise au service de l'intérêt général plutôt que dominée par des intérêts privés ?",
        "Comment accompagner les changements sociétaux provoqués par l'IA, notamment pour les métiers menacés de disparition ?",
        "Pourquoi est-il important que toutes les évolutions de l'IA soient soumises à des contrôles humains pour préserver notre autonomie ?",
        "Comment développer des outils d'aide à l'autonomie pour assurer la sécurité des personnes âgées à domicile ?",
        "Comment replacer l'humain au centre des interactions sociales dans un monde de plus en plus automatisé ?",
        "Quels mécanismes mettre en œuvre pour collecter des données sur la faune avant la disparition de certains écosystèmes ?",
        "Pourquoi est-il crucial que les assistants conversationnels soient transparents sur les sources qu'ils utilisent ?",
        "Quels standards de programmation devrions-nous mettre en place pour garantir l'intégrité technique et morale des systèmes d'IA ?",
        "Pourquoi l'IA devrait-elle toujours être un support pour les professionnels, jamais une solution autonome finale ?",
        "Pourquoi devrions-nous légiférer pour que les créations générées par l'IA appartiennent au domaine public ?",
        "Quels moyens mettre en place pour que les photos, vidéos, audios ou articles générés par l'IA soient facilement identifiables ?",
        # Controverses
        "Comment accompagner les reconversions professionnelles pour préparer les travailleurs à l’ère de l’IA ?",
        "Quels arguments justifient le bannissement total de l'IA en raison de ses impacts sociaux et environnementaux ?",
        "Comment sensibiliser les citoyens aux changements induits par l’IA dans le marché du travail ?",
        "Comment l'IA pourrait-elle aider les enseignants à analyser les progrès des élèves et à ajuster leurs stratégies pédagogiques ?",
        "Comment l'IA pourrait-elle jouer un rôle majeur dans les enquêtes judiciaires, y compris pour résoudre des affaires anciennes ?",
        "Pourquoi faudrait-il stopper l'utilisation de l'IA, compte tenu des utilisations perverses déjà observées ?",
        "Pourquoi devrions-nous généraliser les formations en IA pour permettre à tous d’anticiper les mutations technologiques ?",
        "Quels seraient les avantages de créer des assemblées citoyennes sur l’IA dans différentes métropoles ?",
        "Comment un chatbot d'IA pourrait-il aider à mieux comprendre des textes juridiques ou législatifs complexes ?",
        "Comment préparer les travailleurs aux emplois de demain grâce à des formations sur l’utilisation de l’IA ?",
        "Comment l’IA pourrait-elle détecter et éliminer les lourdeurs administratives pour améliorer la fonction publique ?",
        "Quels outils d'IA devrions-nous développer pour renforcer la protection animale ?",
        "Pourquoi faudrait-il interdire l'IA dans le domaine public et limiter son utilisation aux professionnels ?",
        "Comment garantir un accès équitable aux services d'IA pour tous, partout sur la planète ?",
        "Comment utiliser l'IA pour simplifier et harmoniser toutes les démarches administratives ?",
        "Comment l'IA pourrait-elle prédire les épidémies et permettre des actions rapides comme pour le Covid ?",
        "Comment l’IA pourrait-elle aider les juges à gérer les peines pour lutter contre les récidivistes ?",
        "Comment proposer des IA éducatives permettant d’expliquer différemment les concepts de cours et de générer des exercices ?",
        "Pourquoi devrions-nous développer une IA capable de surveiller les politiques et de vérifier leurs engagements ?",
        "Comment l'IA pourrait-elle automatiser le calcul des aides sociales pour simplifier la vie des citoyens ?",
        "Pourquoi les Européens devraient-ils disposer d’un outil d’IA pour mieux comprendre et agir au sein de l’Union Européenne ?",
        "Comment les entreprises pourraient-elles structurer leurs actions climatiques en utilisant l’IA et des infrastructures frugales ?",
        "Quels arguments justifient la suppression de l’IA en raison de ses effets écologiques et sociaux ?",
        "Comment l'IA pourrait-elle accompagner les nouveaux entrepreneurs dans leurs démarches administratives ?",
        "Dans quelle mesure l'IA pourrait-elle remplacer certains fonctionnaires pour rationaliser les effectifs administratifs ?",
        "Quels moyens pourrions-nous utiliser pour développer une IA éthique et générer la confiance du public ?",
        "Comment l'IA pourrait-elle faciliter l'apprentissage à distance et créer des opportunités pour les exclus ?",
        "Comment remanier les programmes scolaires pour apprendre aux enfants à gérer l'IA dès leur plus jeune âge ?",
        "Comment développer une IA au service de grandes causes sociales et environnementales, comme la lutte contre le gaspillage alimentaire ?",
        "Comment l'IA pourrait-elle faciliter les formalités administratives pour les usagers et les services publics ?",
        "Quels seraient les bénéfices pour le service public d’utiliser l'IA pour réduire les tâches répétitives ?",
        "Comment créer des assistants juridiques basés sur l'IA pour simplifier les démarches et rendre le droit accessible aux citoyens ?",
        "Comment l’IA pourrait-elle être utilisée pour prévenir les conflits armés et arrêter les guerres ?",
        "Pourquoi devrions-nous imposer aux entreprises de structurer l'introduction de l'IA avec des plans de formation et de reconversion ?",
        "Comment utiliser l’IA pour cartographier les besoins sociaux et ajuster les politiques locales ?",
        "Quels seraient les avantages et limites d’intégrer l'IA dans les services gouvernementaux pour automatiser les tâches administratives ?",
        "Comment l'IA pourrait-elle identifier les secteurs émergents pour orienter les investissements à fort impact social ?",
        "Pourquoi l'IA devrait-elle être utilisée pour donner des sanctions en correctionnel et compléter le travail des juges ?",
        "Comment l’IA pourrait-elle rendre les transports en commun plus efficaces et écologiques ?",
        "Quels moyens déployer pour que chacun ait accès à des formations et des outils pour apprendre à utiliser l'IA ?",
        "Comment rendre les outils d'IA accessibles gratuitement ou à faible coût au public ?",
        "Comment l'IA pourrait-elle améliorer la réactivité de l'administration en automatisant la gestion des requêtes des citoyens ?",
        "Comment développer des outils d'IA pour créer des exercices pédagogiques personnalisés pour les élèves ?",
        "Comment assurer un accès universel à l’IA générative pour réduire les inégalités ?",
        "Pourquoi l'IA constitue-t-elle une catastrophe écologique à cause de la consommation énergétique des serveurs ?",
        "Comment exploiter l'IA comme un levier pour réduire les coûts et augmenter l'efficacité dans certaines administrations ?",
        "Comment permettre à l'IA d'aider les élèves à réviser en générant des exercices et en expliquant les cours ?",
        "Quels outils d'IA pourraient être développés pour créer une plateforme de démocratie augmentée ?",
        "Pourquoi est-il crucial que les enseignants soient formés à l'IA pour mieux l’intégrer dans les cours dès le secondaire ?",
        "Quels seraient les impacts d'une suppression totale de l'IA ?",
        "Quelles garanties éthiques devrions-nous exiger pour l’analyse prédictive des politiques publiques avec l'IA ?",
        "Pourquoi devrions-nous créer une école de formation à l'IA pour former les enfants aux défis de la prochaine décennie ?",
        "Quels outils d'IA pourrions-nous développer afin de prédire et prévenir les crises humanitaires et les catastrophes naturelles ?",
    ],
}
