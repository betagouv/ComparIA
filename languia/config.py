import os
import sentry_sdk
import json5
import tomli
from slugify import slugify
from languia.utils import get_model_list, get_matomo_js, build_model_extra_info

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

from languia.utils import JSONFormatter, PostgresHandler

if any(
    os.getenv(var)
    for var in [
        "LANGUIA_DB_NAME",
        "LANGUIA_DB_USER",
        "LANGUIA_DB_PASSWORD",
        "LANGUIA_DB_HOST",
        "LANGUIA_DB_PORT",
    ]
):
    db = {
        "dbname": os.getenv("LANGUIA_DB_NAME", "languia"),
        "user": os.getenv("LANGUIA_DB_USER", "languia"),
        "password": os.getenv("LANGUIA_DB_PASSWORD", ""),
        "host": os.getenv("LANGUIA_DB_HOST", "languia-db"),
        "port": os.getenv("LANGUIA_DB_PORT", 5432),
    }
else:
    db = None


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

if os.getenv("GIT_COMMIT"):
    git_commit = os.getenv("GIT_COMMIT")
else:
    git_commit = None

if not debug:
    assets_absolute_path = "/app/assets"
else:
    assets_absolute_path = os.path.dirname(__file__) + "/assets"

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
        project_root=os.getcwd()
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
    #     + """
    # <script type="text/javascript">
    #     function handleRetryOrRedirect(event) {
    #         // Prevent the default action of the link
    #         event.preventDefault();
    #         // Look for the retry button
    #         var retryButton = document.getElementById('retry-modal-btn');
    #         if (retryButton) {
    #         // If the retry button exists, simulate a click on it
    #         retryButton.click();
    #         } else {
    #         // If the retry button does not exist, redirect to the main page
    #         window.location.href = event.target.href || event.target.closest('a').href;
    #         }
    #     }
    # </script>
    # """
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
with open("./assets/dark.css", encoding="utf-8") as css_file:
    darkfixes_css = css_file.read()

css = css_dsfr + custom_css + darkfixes_css


api_endpoint_info = json5.load(open(register_api_endpoint_file))

models = get_model_list(None, api_endpoint_info)

all_models_extra_info_toml = {
    slugify(k.lower()): v
    for k, v in tomli.load(open("./models-extra-info.toml", "rb")).items()
}
# TODO: refacto?
models_extra_info = [
    build_model_extra_info(model, all_models_extra_info_toml) for model in models
]

models_extra_info.sort(key=lambda x: x["simple_name"])

headers = {"User-Agent": "FastChat Client"}

if os.getenv("LANGUIA_CONTROLLER_URL") != None:
    controller_url = os.getenv("LANGUIA_CONTROLLER_URL")
else:
    controller_url = "http://localhost:21001"

enable_moderation = False
use_remote_storage = False


prompts_table = {
    # category expression
    # "summaries": [
    #     # résumé
    #     """Ecris un résumé du roman "L'Étranger" d'Albert Camus en mettant l'accent sur le contexte social de l'Algérie coloniale.""",
    #     """Résumez "La Rue Cases-Nègres" de Joseph Zobel en soulignant les éléments liés à la vie en Martinique dans les années 1930.""",
    #     """Résume l'œuvre "Une si longue lettre" de Mariama Bâ, en tenant compte de la condition des femmes au Sénégal.""",
    #     """Faites un résumé du "Petit Prince" d'Antoine de Saint-Exupéry en expliquant comment l'œuvre est perçue dans le monde francophone.""",
    #     """Résumez le roman québécois "Bonheur d'occasion" de Gabrielle Roy, en mentionnant l'impact de la Deuxième Guerre mondiale sur la société québécoise.""",
    #     """Résumez "La Peste" d'Albert Camus en expliquant l'analogie entre l'épidémie et le contexte de l'Occupation en France.""",
    #     """Résumez "L'Aventure ambiguë" de Cheikh Hamidou Kane, en expliquant comment l'œuvre reflète les tensions entre tradition et modernité au Sénégal.""",
    #     """Faites un résumé de "Léon l'Africain" d'Amin Maalouf en précisant la dimension interculturelle de l'œuvre.""",
    #     """Résumez "La vie devant soi" de Romain Gary (Émile Ajar) en insistant sur la diversité culturelle du Paris des années 1970.""",
    #     """Donnez un résumé de "Texaco" de Patrick Chamoiseau en insistant sur les particularités de la langue créole dans l'œuvre.""",
    #     """Résumez le roman "Un dimanche à la piscine à Kigali" de Gil Courtemanche en expliquant l'impact du génocide rwandais sur l'intrigue.""",
    #     """Résumez "La Joueuse de go" de Shan Sa, en mentionnant la complexité des relations sino-japonaises durant l'invasion japonaise.""",
    #     """Résumez "L'Enfant noir" de Camara Laye en expliquant l'importance des rites initiatiques dans la culture malinké.""",
    #     """Faites un résumé du livre "Le Monde s'effondre" de Chinua Achebe en tenant compte de la confrontation entre la culture igbo et la colonisation britannique.""",
    #     """Résumez "Les Soleils des indépendances" d'Ahmadou Kourouma, en mentionnant les défis des États africains post-indépendance.""",
    #     """Résumez "Les Trois Mousquetaires" d'Alexandre Dumas en expliquant son influence sur l'imaginaire collectif de la France.""",
    #     """Faites un résumé de "L'Acacia" de Claude Simon en précisant comment l'œuvre reflète la mémoire de la Première Guerre mondiale en France.""",
    #     "Faites un résumé du roman “Les Gommes” d’Alain Robbe-Grillet en expliquant les partis pris stylistiques de l’œuvre.",
    #     """Fais un résumé du recueil "Cahier d'un retour au pays natal" d'Aimé Césaire en expliquant le concept de négritude.""",
    #     """Résumez "Éthiopiques" de Léopold Sédar Senghor en expliquant comment la culture sérère influence son écriture poétique.""",
    #     """Explique moi le poème "Souffles" de Birago Diop en soulignant l'importance des traditions orales africaines.""",
    #     """Résumez "L’Écume des jours" de Boris Vian en expliquant l'impact du jazz et de la culture américaine sur sa poésie.""",
    #     """Donnez un résumé du poème "L'Aube à l'Antique" d'Émile Nelligan en expliquant l'influence du symbolisme québécois.""",
    #     """Résumez "Pays sans chapeau" de Dany Laferrière en expliquant comment le contexte haïtien est représenté dans sa poésie.""",
    #     """Résumez "Le sel noir" d'Edouard Glissant en soulignant l'importance de l'identité antillaise et de la créolité dans ses poèmes.""",
    #     """Donnez un résumé du recueil "L’homme rapaillé" de Gaston Miron en expliquant comment il reflète la quête identitaire québécoise.""",
    #     """Résumez la pièce "Les Fourberies de Scapin" de Molière en expliquant comment elle reflète la société française du XVIIe siècle.""",
    #     """Donnez un résumé de "La Tragédie du roi Christophe" d'Aimé Césaire en expliquant son lien avec l'histoire d'Haïti.""",
    #     """Faites un résumé de "Antigone" de Jean Anouilh en expliquant comment le contexte de l'Occupation en France influence la pièce.""",
    #     """Résumez "Une tempête" d'Aimé Césaire en expliquant comment la pièce réinterprète "La Tempête" de Shakespeare dans un contexte postcolonial.""",
    #     """Donnez un résumé de "Le Tartuffe" de Molière en expliquant comment la pièce critique l'hypocrisie religieuse dans la société française du XVIIe siècle et quelles résonnances existent avec nos sociétés contemporaines.""",
    #     """Résumez "La Mort de Bessie Smith" de Tennessee Williams en expliquant comment le racisme américain est abordé dans la pièce et sa résonance en Afrique francophone.""",
    #     """Faites un résumé de "Amédée ou Comment s'en débarrasser" d’Eugène Ionesco en expliquant comment la pièce reflète l'angoisse existentielle de l'après-guerre.""",
    #     """Résumez "Les Nègres" de Jean Genet en expliquant comment la pièce aborde la question de l'identité et du racisme dans un contexte colonial.""",
    #     """Résumez "Les Paravents" de Jean Genet en expliquant comment la pièce aborde la question de l'identité et du racisme dans un contexte colonial.""",
    #     """Résumez "Le Mariage de Figaro" de Beaumarchais en expliquant comment la pièce anticipe les bouleversements sociaux de la Révolution française.""",
    #     """Faites un résumé de "La Dame aux camélias" d'Alexandre Dumas fils en expliquant comment la pièce reflète les tensions morales et sociales de la société bourgeoise du XIXe siècle.""",
    # ],
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
        "Tu es conteur professionnel, crée une histoire du trois minutes à raconter à mes deux enfants en bas âges. Utilise un langage riche et imaginatif et des figures de style pour stimuler l’imagination et susciter des émotions.",
        "Je suis parent et je cherche une histoire du soir à raconter à mes enfants. Choisis trois objets sans rapport apparent et utilise-les comme base pour créer une histoire de 100 mots.",
        "Tu es écrivain de fantasy, élabore un système magique avec des règles et des limitations spécifiques, puis décris comment cette magie façonne la société dans ce monde imaginaire.",
    ],
    # category vie-professionnelle
    # "fixing": [
    #     # correction
    #     "Expliquez comment automatiser le calcul des pourcentages dans Excel en créant des formules simples et en les copiant vers d'autres cellules.",
    #     "Détaillez le processus de correction et d'amélioration des graphiques Excel pour illustrer efficacement les tendances des données.",
    #     "Expliquez comment utiliser la mise en forme conditionnelle dans Excel pour mettre en évidence automatiquement les valeurs importantes.",
    #     "Indiquez les étapes pour normaliser les formats de date dans Excel, en tenant compte des différences régionales de formatage.",
    #     "Expliquez comment créer un tableau croisé dynamique dans Excel pour résumer les données et extraire des informations clés.",
    #     "Détaillez le processus pour vérifier et corriger les totaux et sous-totaux dans Excel en utilisant des formules comme SOMME et SOUS.TOTAL.",
    #     "Expliquez comment convertir des données brutes en un tableau Excel organisé et trié par ordre alphabétique.",
    #     "Décrivez comment utiliser des filtres dans Excel pour isoler les données les plus pertinentes et affiner l'analyse.",
    #     "Indiquez comment ajouter des annotations dans Excel pour expliquer les formules complexes et faciliter la compréhension des autres utilisateurs.",
    #     "Expliquez comment créer un graphique à secteurs dans Excel pour visualiser la répartition des catégories de données.",
    #     "Expliquez comment créer une macro dans Excel pour automatiser une tâche répétitive, en détaillant les étapes de l'enregistrement à l'exécution.",
    #     "Indiquez comment vérifier et corriger les références de cellules dans les formules Excel pour éviter les erreurs, comme les références circulaires.",
    #     "Expliquez comment réorganiser les colonnes dans Excel pour améliorer la lisibilité du tableau et faciliter l'accès aux informations essentielles.",
    #     "Expliquez comment créer un tableau de bord interactif dans Excel en utilisant des graphiques et des filtres pour suivre les indicateurs clés de performance.",
    #     "Détaillez les étapes pour relier différentes feuilles Excel afin de permettre une mise à jour automatique des données interconnectées.",
    #     """J’ai un tableau excel contenant [*des données sur les ventes, notamment le nom du vendeur dans la colonne A, la catégorie de produits dans la colonne B, le montant des ventes dans la colonne C et la date de la vente dans la colonne D*]. Je souhaite calculer [*le montant total des ventes pour chaque vendeur, mais uniquement pour les ventes de produits de la catégorie "Électronique" qui ont eu lieu au mois de janvier*]. Peux tu m’aider à trouver la formule Excel qui me permettra d'y parvenir ? Explique en détail la formule Excel qui permettrait d'obtenir le résultat souhaité. Décompose la formule en ses différents éléments, en expliquant l'objectif et la fonction de chacun d'entre eux et la manière dont ils fonctionnent ensemble. Enfin, fournis tout contexte ou conseil nécessaire à l'utilisation efficace de la formule dans une feuille de calcul Excel.""",
    #     "Corrigez le paragraphe attaché en vérifiant la cohérence des dates et des chiffres.",
    #     "Relisez et reformulez ce paragraphe pour qu'il respecte un ton formel adapté à une réunion avec des partenaires internationaux.",
    #     "Revoyez la structure de ce paragraphe pour s'assurer qu'il est logique et bien organisé.",
    #     "Corrigez les erreurs de grammaire et de syntaxe dans ce paragraphe, tout en conservant le style d'origine.",
    #     "Revoir ce projet de paragraphe pour vous assurer qu'il est conforme aux standards de l'administration française.",
    #     "Revoyez ce paragraphe et assurez-vous qu'il est inclusif et non-discriminatoire.",
    #     "Corrigez les erreurs typographiques et vérifiez que le ton est approprié pour une communication interne.",
    #     "Réécrivez ce paragraphe pour qu'il soit compréhensible par un public non-expert.",
    #     "Améliorez ce paragraphe pour qu'il soit plus percutant pour un public nord-américain.",
    #     "Assurez-vous que ce plan stratégique est clair et concis, en évitant le jargon inutile.",
    #     "Corrigez et simplifiez ce paragraphe pour qu'il soit facile à traduire en plusieurs langues.",
    #     "Relisez et ajustez ce paragraphe pour qu'il soit plus direct et assertif",
    #     "Reformulez ce paragraphe en utilisant un langage simple et accessible, adapté à une communication gouvernementale.",
    #     "Améliorez ce paragraphe en y ajoutant des exemples concrets pour illustrer les points clés.",
    #     "Corrigez et adaptez ce paragraphe pour une audience multiculturelle, en évitant les références trop spécifiques à une seule culture.",
    #     "Revoyez ce paragraphe pour vous assurer qu'il est conforme aux normes de style en vigueur dans les publications académiques.",
    # ],
    # "editing": [
    #     # rédaction
    #     "J'ai besoin de ton aide pour rédiger un message d'absence du bureau. . Tu sais rédiger des messages clairs et faciles à lire. Crée un mail d'absence du bureau qui inclut les informations importantes à mentionner. Sois concis. Le ton doit être poli, direct et simple.",
    #     "Ta tâche consiste à examiner les notes de réunion fournies et à créer un résumé concis qui capture les informations essentielles, en te concentrant sur les points clés et les actions assignées à des personnes ou à des départements spécifiques au cours de la réunion. Utilise un langage clair et professionnel et structure le résumé de manière logique en utilisant un formatage approprié tel que des titres, des sous-titres et des puces. Veille à ce que le résumé soit concis, facile à comprendre et qu'il donne un aperçu complet mais succinct du contenu de la réunion, en veillant tout particulièrement à indiquer clairement qui est responsable de chaque mesure à prendre.",
    #     "Ta tâche consiste à rédiger une note de synthèse complète sur la base des points clés fournis. La note doit être rédigée sur un ton professionnel, en abordant toutes les informations pertinentes de manière claire et concise. Utilise un formatage approprié, tel que des titres, des sous-titres et des puces, pour organiser le contenu de manière efficace. Veille à ce que la note soit bien structurée, cohérente et facile à comprendre pour le public visé.",
    #     "Aide-moi à améliorer la note d’intention pour une nouvelle idée de produit. L’objectif est d'analyser le contenu et de proposer des commentaires constructifs et des suggestions en adoptant le point de vue du financeur.",
    #     "Identifie les forces et les faiblesses de la proposition du point de vue du financeur. 2. Réfléchis aux informations manquantes ou peu claires qui seraient importantes pour le décideur.",
    #     "Dresse la liste des réactions que le financeur pourrait avoir",
    #     "Formule trois suggestions spécifiques pour améliorer le document d'une page afin de mieux répondre aux besoins et aux préoccupations du financeur.",
    #     "Tu es un rédacteur en chef doté d'un sens aigu du détail et d'une connaissance approfondie de la langue, du style et de la grammaire française. Ta tâche consiste à m'aider à affiner et améliorer le contenu écrit en fonction des étapes suivantes : 1. Identifier les points à améliorer en termes de grammaire, de ponctuation, d'orthographe et de style. 2. Fournir des suggestions réalisables pour affiner le texte, en expliquant le raisonnement derrière chaque suggestion. 3 Proposer des alternatives pour le choix des mots, la structure des phrases et la formulation afin d'améliorer la clarté, la concision et l'impact. 4. Veiller à ce que le ton et la voix de l'écrit soient cohérents et adaptés au public et à l'objectif visés. 5. Vérifier la logique, la cohérence et l'organisation, et suggérer des améliorations si nécessaire. 6. Fournir un retour sur l'efficacité globale de l'écrit, en soulignant les points forts et les domaines à développer. 7. Enfin, à la fin du projet, produire une version entièrement révisée qui tient compte de toutes les suggestions.",
    #     "Rédigez une lettre officielle demandant une extension de délai pour la soumission d'un rapport d'audit externe.",
    #     "Élaborez un compte-rendu détaillé de la dernière réunion de suivi de projet, en veillant à inclure toutes les décisions prises et les actions assignées.",
    #     "Rédigez un plan de communication interne pour annoncer un changement majeur dans la politique de l'entreprise.",
    #     "Préparez un discours pour le directeur général à présenter lors de la cérémonie annuelle de remise des prix de l'entreprise.",
    #     "Rédigez un email de relance pour un fournisseur qui n'a pas encore livré les documents requis pour le projet en cours.",
    #     "Rédigez un rapport de situation hebdomadaire à destination des équipes opérationnelles, en soulignant les priorités pour la semaine suivante.",
    #     "Rédigez un rapport de mission à envoyer au ministère de tutelle, en détaillant les résultats obtenus et les recommandations futures.",
    #     "Préparez une note de service pour informer l'ensemble des employés de la mise en place d'un nouveau protocole de sécurité.",
    #     "Rédigez un rapport d'incident à destination du département de la sécurité, en détaillant les faits, les causes probables et les mesures prises.",
    #     "Élaborez un projet de discours pour le maire à l'occasion de l'inauguration d'un nouveau centre culturel.",
    #     "Préparez un courrier formel pour inviter un représentant d'une organisation internationale à participer à une conférence organisée par votre administration.",
    #     "Rédigez une réponse à une plainte déposée par un citoyen concernant un service public, en veillant à maintenir un ton respectueux et professionnel.",
    #     "Élaborez un dossier de presse pour le lancement d'un nouveau programme gouvernemental, en incluant tous les éléments clés à communiquer.",
    #     "Rédigez une présentation PowerPoint pour la réunion mensuelle de suivi de performance, en intégrant des graphiques et des données clés.",
    #     "Préparez un document de synthèse sur les meilleures pratiques internationales dans votre domaine (à préciser) pour un groupe de travail intergouvernemental.",
    #     "Rédigez une lettre de remerciement à envoyer à un partenaire institutionnel après la conclusion d'un accord de coopération.",
    #     "Rédigez un communiqué de presse pour annoncer le lancement d'un nouveau produit sur le marché.",
    #     "Élaborez un script de vidéo promotionnelle de 2 minutes pour une campagne de marketing digital.",
    #     "Rédigez une série de trois publications pour les réseaux sociaux visant à promouvoir un événement d'entreprise.",
    #     "Rédigez un email marketing destiné à fidéliser les clients existants avec une offre spéciale.",
    #     "Élaborez un plan de communication pour le lancement d'une campagne publicitaire dans un nouveau marché géographique.",
    #     "Préparez une présentation PowerPoint pour une réunion avec des investisseurs, en mettant l'accent sur les opportunités de croissance.",
    #     "Rédigez une landing page pour une campagne de marketing en ligne, optimisée pour les conversions.",
    #     "Élaborez un dossier de presse pour une campagne de sensibilisation menée par l'entreprise.",
    #     "Rédigez un post LinkedIn destiné à annoncer une collaboration stratégique entre votre entreprise et un autre acteur du marché.",
    #     "Préparez un email de remerciement pour les participants d'un webinaire organisé par votre entreprise.",
    #     "Rédigez un script pour un podcast de 10 minutes destiné à promouvoir une nouvelle gamme de produits.",
    #     "Élaborez un plan de communication de crise pour anticiper les réactions à un incident majeur.",
    #     "Élaborez un calendrier éditorial pour le blog de l'entreprise, en tenant compte des événements saisonniers et des temps forts du secteur.",
    #     "Rédigez une proposition de partenariat à présenter à un groupe de presse locale pour une campagne de promotion dans leur journal.",
    #     "Rédigez un rapport d'analyse sur les performances d'une récente campagne publicitaire, incluant des recommandations pour les futures actions.",
    #     "Préparez un guide de style pour l'utilisation cohérente de la marque dans tous les supports de communication.",
    # ],
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
    # "job": [
    #     # Emploi
    #     "Propose-moi 2 à 3 phrases pour remercier la personne qui m’a reçu, en réaffirmant mon intérêt pour le poste proposé. Le ton ne doit pas être trop formel ni d’un enthousiasme débordant.",
    #     "Rédige une lettre de recommandation professionnelle pour un ancien collègue, en détaillant ses compétences, son attitude au travail, et les projets réussis ensemble.",
    #     "Comment évaluer les compétences techniques d'un candidat sans biais culturel pendant les tests de compétence ?",
    #     "Quels critères utiliser pour évaluer l'adaptabilité d'un candidat dans un environnement de travail multiculturel ?",
    #     "Dans le cadre d’un processus de recrutement, comment aborderiez-vous une question sur les échecs professionnels lors d'un entretien dans un pays où l'échec est stigmatisé ?",
    #     "Jusqu’à présent j’ai travaillé en France et en Europe, je cherche à trouver un travail aux Etats Unis ou au Canada, comment dois-je adapter mon CV et ma lettre de motivation?",
    #     "Jusqu’à présent j’ai travaillé en France et en Europe, je postule pour des postes en Asie, comment dois-je adapter mon CV et ma lettre de motivation?",
    #     "Vous êtes expert RH en recrutement, comment expliqueriez-vous un changement de carrière important dans un contexte où les parcours non linéaires sont mal vus ?",
    #     "Comment ajuster les processus de recrutement pour attirer des candidats dans un environnement de travail multiculturel ?",
    #     "Pour m’aider à me projeter dans ma candidature à un nouveau poste, réponds à ma question comme si tu étais à ma place. En tant que candidat pour un poste de responsable du département des relations publiques, décrivez une expérience où vous avez dû acquérir rapidement de nouvelles compétences pour un poste. Comment cela pourrait-il vous préparer pour le rôle que vous visez ?",
    #     "En tant que recruteur dans un processus de recrutement, quelles questions d'entretien posez-vous pour évaluer la capacité d’un candidat à travailler sous pression ?",
    #     "En tant que recruteur dans un processus de recrutement, comment évaluez-vous les compétences en communication d’un candidat lors d'un entretien ?",
    #     "En tant que recruteur dans un processus de recrutement, quels sont les meilleurs indicateurs dans une lettre de motivation pour évaluer l'engagement d'un candidat envers le poste ?",
    #     "En tant que recruteur dans un processus de recrutement, quels aspects de la personnalité d’un candidat sont les plus importants pour un rôle de leadership dans une culture de travail collaborative ?",
    #     "****En tant que recruteur dans un processus de recrutement, quels sont les signes que vous recherchez pour déterminer si un candidat est proactif et autonome ?",
    #     "En tant que candidat dans un processus de recrutement, quelle est la meilleure façon de préparer des réponses à des questions comportementales pour un entretien dans un secteur spécifique ?",
    #     "Comment, en tant que candidat, adapteriez-vous votre CV pour refléter vos compétences transférables alors qu’il y a un écart entre vos expériences passées et le poste que vous visez ?",
    #     "En tant que recruteur dans un processus de recrutement, quels éléments spécifiques d’un CV considérez-vous comme les plus révélateurs de la capacité d’un candidat à évoluer dans un nouvel environnement de travail ?",
    #     "Quelles méthodes peuvent aider à réduire les biais culturels et les biais de genre lors de l'évaluation des candidatures pour un poste de direction ?",
    #     """Je suis en train de recruter un candidat pour un poste de responsable de communication dans une institution culturelle. Le candidat idéal doit avoir de l'expérience dans le développement et l'exécution de campagnes de communication multicanal, de solides compétences analytiques et la capacité de collaborer efficacement avec des équipes. Il doit également être passionné par les dernières tendances et technologies en matière de communication. Ta tâche consiste à **générer une série de dix questions** réfléchies et ouvertes à poser en entretien sur la base du contexte donné. Les questions doivent être conçues de manière à susciter des réponses perspicaces et détaillées de la part de la personne interrogée, lui permettant de mettre en valeur ses connaissances, son expérience et son esprit critique. Évite les questions de type "oui/non" ou celles dont les réponses sont évidentes. Privilégie plutôt les questions qui encouragent la réflexion, l'auto-évaluation et le partage d'exemples ou d'anecdotes spécifiques.""",
    # ],
    # # category loisirs
    # "travel": [
    #     # Voyages
    #     "Je prévois un séjour en Suisse et j’aimerais faire une randonnée en montagne. Quels sentiers sont adaptés pour un débutant tout en offrant de belles vues sur les Alpes suisses ?",
    #     "Je me rends à Montréal au printemps. Quels festivals ou événements culturels ne devrais-je pas manquer pendant cette saison et où trouver les meilleurs lieux pour goûter à la gastronomie québécoise ?",
    #     "Je planifie un voyage en Tunisie. Quels sites archéologiques et plages sont à visiter absolument à Carthage et Djerba ?",
    #     "Je prépare un voyage à Dakar. Quels sont les meilleurs endroits pour découvrir la musique sénégalaise et les marchés animés tout en ayant une expérience locale authentique ?",
    #     "Je souhaite explorer la Guadeloupe. Pourrais-tu me conseiller sur les plages les plus relaxantes et les activités à faire en famille ?",
    #     "Je vais en Algérie pour un séjour culturel d’une semaine. Quels sont les lieux historiques et les musées à visiter à Alger pour comprendre l’histoire et la culture du pays ?",
    #     "Je planifie un voyage en Martinique. Quels sont les endroits à visiter pour découvrir la culture créole et les meilleurs endroits pour déguster des plats locaux tout en profitant des plages ?",
    #     "Je me rends à Genève pour affaires. Quels sont les bons endroits pour se détendre après une journée de travail, en particulier des cafés ou des parcs ?",
    #     "Quels sont les lieux historiques et les activités de loisirs à explorer à Port-au-Prince pour une immersion dans la culture haïtienne ?",
    #     "Je prévois un voyage de deux semaines en Côte d’Ivoire. Peux-tu me donner un itinéraire ?",
    #     "Je prévois un week-end à Bruxelles. Peux-tu me donner un itinéraire en dehors des grandes attractions touristiques ?",
    #     "Je prévois un voyage de trois jours à Paris. Peux-tu me donner un itinéraire en dehors des sentiers battus ? Je m’intéresse à l’architecture moderne.",
    #     "Je prévois un voyage de 4 jours à Genève. Peux-tu me donner un itinéraire en dehors des sentiers battus ?",
    #     "Quels sont les essentiels à inclure dans un voyage de trois jours à Paris pour maximiser la découverte des attractions principales tout en évitant les foules ?",
    #     "Quels sont les meilleurs quartiers pour trouver des logements temporaires à Bruxelles, et quels critères de sélection sont importants pour choisir un bon emplacement ?",
    #     "Quels sont les sites de location de voiture les plus fiables à La Réunion pour explorer l'île, et quels sont les conseils pour conduire en toute sécurité ?",
    #     "Quels sont les types de pass ou de cartes de transport disponibles pour les visiteurs à Genève ?",
    #     "Quelles sont les activités culturelles et les visites surprenantes à Bruxelles et Bruges qui sortent des sentiers battus, tout en découvrant l’histoire et la gastronomie locales ?",
    #     "Quels sont les sites historiques moins connus mais nécessaires à explorer dans la ville pour comprendre l’évolution de Québec au-delà des attractions touristiques principales ?",
    #     "Je pars en Tunisie une semaine, quels sont les sites archéologiques, les plages et les villes médiévales à ne pas louper ?",
    #     "Je rêve de visiter le Maroc en automne. Pourrais-tu me conseiller sur les meilleures villes à explorer et les activités à faire à Marrakech et Fès ?",
    #     "Je prévois un voyage de 4 jours à Montréal. Peux-tu me donner un itinéraire en dehors des grandes attractions touristiques ?",
    #     "Je prévois un voyage de 4 jours à Québec. Peux-tu me donner un itinéraire en dehors des grandes attractions touristiques ?",
    # ],
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
        "Vous demandez un permis de séjour ? Travaillons ensemble pour rédiger une lettre de motivation convaincante qui met en valeur votre éligibilité et respecte toutes les directives officielles.",
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
        """"Wann ich dir so schwätz, verstehsch mich? Réponds en alsacien.""",
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
