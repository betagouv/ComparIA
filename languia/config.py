import os
import sentry_sdk
import json
from slugify import slugify
from languia.utils import get_model_list, get_matomo_js, build_model_extra_info

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
    + """
<script type="text/javascript">

    function handleRetryOrRedirect(event) {
        // Prevent the default action of the link
        event.preventDefault();

        // Look for the retry button
        var retryButton = document.getElementById('retry-modal-btn');

        if (retryButton) {
        // If the retry button exists, simulate a click on it
        retryButton.click();
        } else {
        // If the retry button does not exist, redirect to the main page
        window.location.href = event.target.href || event.target.closest('a').href;
        }
    }
</script>
"""
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
models_extra_info.sort(key=lambda x: x['simple_name'])

headers = {"User-Agent": "FastChat Client"}

if os.getenv("LANGUIA_CONTROLLER_URL") != None:
    controller_url = os.getenv("LANGUIA_CONTROLLER_URL")
else:
    controller_url = "http://localhost:21001"

enable_moderation = False
use_remote_storage = False
prompts_table = {
    "expression": [
        # résumé
        """Ecris un résumé du roman "L'Étranger" d'Albert Camus en mettant l'accent sur le contexte social de l'Algérie coloniale.""",
        """Résumez "La Rue Cases-Nègres" de Joseph Zobel en soulignant les éléments liés à la vie en Martinique dans les années 1930.""",
        """Résume l'œuvre "Une si longue lettre" de Mariama Bâ, en tenant compte de la condition des femmes au Sénégal.""",
        """Faites un résumé du "Petit Prince" d'Antoine de Saint-Exupéry en expliquant comment l'œuvre est perçue dans le monde francophone.""",
        """Résumez le roman québécois "Bonheur d'occasion" de Gabrielle Roy, en mentionnant l'impact de la Deuxième Guerre mondiale sur la société québécoise.""",
        """Résumez "La Peste" d'Albert Camus en expliquant l'analogie entre l'épidémie et le contexte de l'Occupation en France.""",
        """Résumez "L'Aventure ambiguë" de Cheikh Hamidou Kane, en expliquant comment l'œuvre reflète les tensions entre tradition et modernité au Sénégal.""",
        """Faites un résumé de "Léon l'Africain" d'Amin Maalouf en précisant la dimension interculturelle de l'œuvre.""",
        """Résumez "La vie devant soi" de Romain Gary (Émile Ajar) en insistant sur la diversité culturelle du Paris des années 1970.""",
        """Donnez un résumé de "Texaco" de Patrick Chamoiseau en insistant sur les particularités de la langue créole dans l'œuvre.""",
        """Résumez le roman "Un dimanche à la piscine à Kigali" de Gil Courtemanche en expliquant l'impact du génocide rwandais sur l'intrigue.""",
        """Résumez "La Joueuse de go" de Shan Sa, en mentionnant la complexité des relations sino-japonaises durant l'invasion japonaise.""",
        """Résumez "L'Enfant noir" de Camara Laye en expliquant l'importance des rites initiatiques dans la culture malinké.""",
        """Faites un résumé du livre "Le Monde s'effondre" de Chinua Achebe en tenant compte de la confrontation entre la culture igbo et la colonisation britannique.""",
        """Résumez "Les Soleils des indépendances" d'Ahmadou Kourouma, en mentionnant les défis des États africains post-indépendance.""",
        """Résumez "Les Trois Mousquetaires" d'Alexandre Dumas en expliquant son influence sur l'imaginaire collectif de la France.""",
        """Faites un résumé de "L'Acacia" de Claude Simon en précisant comment l'œuvre reflète la mémoire de la Première Guerre mondiale en France.""",
        "Faites un résumé du roman “Les Gommes” d’Alain Robbe-Grillet en expliquant les partis pris stylistiques de l’œuvre.",
        """Fais un résumé du recueil "Cahier d'un retour au pays natal" d'Aimé Césaire en expliquant le concept de négritude.""",
        """Résumez "Éthiopiques" de Léopold Sédar Senghor en expliquant comment la culture sérère influence son écriture poétique.""",
        """Explique moi le poème "Souffles" de Birago Diop en soulignant l'importance des traditions orales africaines.""",
        """Résumez "L’Écume des jours" de Boris Vian en expliquant l'impact du jazz et de la culture américaine sur sa poésie.""",
        """Donnez un résumé du poème "L'Aube à l'Antique" d'Émile Nelligan en expliquant l'influence du symbolisme québécois.""",
        """Résumez "Pays sans chapeau" de Dany Laferrière en expliquant comment le contexte haïtien est représenté dans sa poésie.""",
        """Résumez "Le sel noir" d'Edouard Glissant en soulignant l'importance de l'identité antillaise et de la créolité dans ses poèmes.""",
        """Donnez un résumé du recueil "L’homme rapaillé" de Gaston Miron en expliquant comment il reflète la quête identitaire québécoise.""",
        """Résumez la pièce "Les Fourberies de Scapin" de Molière en expliquant comment elle reflète la société française du XVIIe siècle.""",
        """Donnez un résumé de "La Tragédie du roi Christophe" d'Aimé Césaire en expliquant son lien avec l'histoire d'Haïti.""",
        """Faites un résumé de "Antigone" de Jean Anouilh en expliquant comment le contexte de l'Occupation en France influence la pièce.""",
        """Résumez "Une tempête" d'Aimé Césaire en expliquant comment la pièce réinterprète "La Tempête" de Shakespeare dans un contexte postcolonial.""",
        """Donnez un résumé de "Le Tartuffe" de Molière en expliquant comment la pièce critique l'hypocrisie religieuse dans la société française du XVIIe siècle et quelles résonnances existent avec nos sociétés contemporaines.""",
        """Résumez "La Mort de Bessie Smith" de Tennessee Williams en expliquant comment le racisme américain est abordé dans la pièce et sa résonance en Afrique francophone.""",
        """Faites un résumé de "Amédée ou Comment s'en débarrasser" d’Eugène Ionesco en expliquant comment la pièce reflète l'angoisse existentielle de l'après-guerre.""",
        """Résumez "Les Nègres" de Jean Genet en expliquant comment la pièce aborde la question de l'identité et du racisme dans un contexte colonial.""",
        """Résumez "Les Paravents" de Jean Genet en expliquant comment la pièce aborde la question de l'identité et du racisme dans un contexte colonial.""",
        """Résumez "Le Mariage de Figaro" de Beaumarchais en expliquant comment la pièce anticipe les bouleversements sociaux de la Révolution française.""",
        """Faites un résumé de "La Dame aux camélias" d'Alexandre Dumas fils en expliquant comment la pièce reflète les tensions morales et sociales de la société bourgeoise du XIXe siècle.""",
        # explications
        "Tu es professeur d'économie. Explique-moi la théorie des jeux de façon simple. Donne-moi des exemples d'application dans le monde réel. À la fin, fournis un glossaire des notions et termes à connaître sur le sujet.",
        "Tu es professeur d’informatique. Explique-moi le deep learning de façon simple. Donne-moi des exemples d'application dans le monde réel. À la fin, fournis un glossaire des notions et termes à connaître sur le sujet.",
        "Comment expliquer le concept d’empathie à un enfant de maternelle ?",
        "Démystifie le fonctionnement des banques en utilisant des analogies simples, comme si tu étais un conseiller financier en Suisse.",
        "Comment expliquer le concept de gravité en physique à un enfant au collège ?",
        "Tu es un professeur de mathématiques très pédagogue. Comment expliques-tu le concept d’apprentissage profond à un élève de 4e ?",
        "Comment expliquer le concept de physique quantique à un élève de seconde.",
        "Détaille les étapes simples pour comprendre le concept de la photosynthèse comme si tu l'expliquais à un enfant de primaire.",
        "Présente brièvement l'histoire du rap. Tu es un historien de la musique, réputé pour ses connaissances encyclopédiques sur ce style. Tu écris pour expliciter l'histoire de ce genre musical, démontrer son impact sur la culture et la société, et mettre en avant sa valeur artistique et créative.",
        "Tu es un commentateur de la culture pop. Explique la déferlante K-pop à travers le monde à une personne qui n'en a jamais entendu parler. Explique pourquoi et comment ce mouvement est devenu un phénomène mondial ces dernières années. Rédige ta réponse dans un style conversationnel, comme si tu parlais à un ami. Sois concis.",
        "Je souhaite définir, comparer et les mouvements de peinture français, hollandais, italiens, espagnols et allemands selon ces critères : époque, artistes, sujets et mécènes. En tant qu’historien de l’art, tu connais très bien le sujet et tu n'hésites pas à faire des recommandations précises de peintures pour chaque catégorie. Présente ta réponse sous forme de tableau organisé de façon logique et facile à lire. ",
        "Raconte moi une anecdote sur l’empire romain",
        # histoires
        """Écris une histoire en 100 mots, sans utiliser la lettre "e", où un enfant découvre un objet mystérieux dans le grenier de ses grands-parents.""",
        "Raconte une légende urbaine contemporaine dans un quartier connu pour son histoire mystique (précise le quartier et la ville)",
        "Imagine une histoire de 200 mots où un personnage doit faire face à un événement surnaturel dans une région rurale.",
        "Raconte une histoire à la manière de Charles Perrault où un ancien raconte à un enfant un secret sur leur village.",
        "Écris une histoire où un personnage découvre un lien mystérieux entre sa ville actuelle et une ville dans un autre pays francophone.",
        "Raconte une histoire de 500 mots se déroulant en une seule journée, dans une grande ville, où chaque moment compte.",
        "Écris une histoire à la manière de Jules Verne où un groupe d'aventuriers découvre une terre inconnue sous l'océan.",
        "Raconte une histoire de 100 mots où un enfant découvre une ancienne tradition oubliée de son village.",
        "Raconte une histoire en 300 mots où le personnage principal découvre un objet qui change le cours de sa vie. L'objet doit avoir une signification particulière liée à une tradition locale.",
        "Imagine une histoire de 200 mots où une tempête force des voyageurs à se réfugier dans un lieu sacré pour une nuit.",
        "Écris une très courte nouvelle où une ancienne malédiction frappe une famille de génération en génération. Insère des éléments culturels spécifiques à une région précise.",
        "Raconte une aventure en vers de 200 mots où un oiseau courageux surmonte sa peur de voler.",
        "Raconte une histoire de 400 mots, à la manière d'un conte, où un enfant découvre la sagesse cachée dans un baobab.",
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
        "Écris une histoire à la manière de Georges Perec, en utilisant un palindrome de phrases, sur un personnage qui revient toujours au point de départ.",
        "Imagine une histoire en vers libres, où les phrases alternent entre des mots français et des mots étrangers de ton choix, racontant la rencontre entre deux personnages de cultures différentes.",
        "Écris une histoire où chaque paragraphe doit contenir exactement cinq phrases, chacune de longueur décroissante, racontant la découverte d'une cité perdue.",
        "Imagine une chanson où chaque phrase doit contenir au moins un mot emprunté à une autre langue (indique laquelle), exprimant les sentiments d’un amant éconduit.",
        "Compose une chanson en quatre couplets, à la manière d’une chanson folklorique bretonne, racontant une légende locale.",
        "Écris une chanson en vers de 100 mots où chaque vers contient une rime interne, racontant l'histoire d'un animal légendaire.",
        "Écris une chanson en vers de 8 syllabes, racontant l'histoire d'un héros mythologique, en intégrant des éléments du folklore local de ton choix.",
        "Écris une chanson à la manière d’un rap, en utilisant uniquement des mots d'argot, sur le thème de la révolte.",
        """Écris une chanson en vers libres où chaque strophe commence par "Si j’étais", exprimant des rêves impossibles.""",
        """Écris une chanson de 12 vers en rimes croisées où chaque mot doit commencer par la lettre "E", célébrant la beauté du pays basque (E pour euskal herria).""",
        "Compose une chanson de trois couplets et un refrain, à la manière de Jacques Brel, sur le thème du regret.",
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
    "vie-professionnelle": [
        # correction
        "Expliquez comment automatiser le calcul des pourcentages dans Excel en créant des formules simples et en les copiant vers d'autres cellules.",
        "Détaillez le processus de correction et d'amélioration des graphiques Excel pour illustrer efficacement les tendances des données.",
        "Expliquez comment utiliser la mise en forme conditionnelle dans Excel pour mettre en évidence automatiquement les valeurs importantes.",
        "Indiquez les étapes pour normaliser les formats de date dans Excel, en tenant compte des différences régionales de formatage.",
        "Expliquez comment créer un tableau croisé dynamique dans Excel pour résumer les données et extraire des informations clés.",
        "Détaillez le processus pour vérifier et corriger les totaux et sous-totaux dans Excel en utilisant des formules comme SOMME et SOUS.TOTAL.",
        "Expliquez comment convertir des données brutes en un tableau Excel organisé et trié par ordre alphabétique.",
        "Décrivez comment utiliser des filtres dans Excel pour isoler les données les plus pertinentes et affiner l'analyse.",
        "Indiquez comment ajouter des annotations dans Excel pour expliquer les formules complexes et faciliter la compréhension des autres utilisateurs.",
        "Expliquez comment créer un graphique à secteurs dans Excel pour visualiser la répartition des catégories de données.",
        "Expliquez comment créer une macro dans Excel pour automatiser une tâche répétitive, en détaillant les étapes de l'enregistrement à l'exécution.",
        "Indiquez comment vérifier et corriger les références de cellules dans les formules Excel pour éviter les erreurs, comme les références circulaires.",
        "Expliquez comment réorganiser les colonnes dans Excel pour améliorer la lisibilité du tableau et faciliter l'accès aux informations essentielles.",
        "Expliquez comment créer un tableau de bord interactif dans Excel en utilisant des graphiques et des filtres pour suivre les indicateurs clés de performance.",
        "Détaillez les étapes pour relier différentes feuilles Excel afin de permettre une mise à jour automatique des données interconnectées.",
        """J’ai un tableau excel contenant [*des données sur les ventes, notamment le nom du vendeur dans la colonne A, la catégorie de produits dans la colonne B, le montant des ventes dans la colonne C et la date de la vente dans la colonne D*]. Je souhaite calculer [*le montant total des ventes pour chaque vendeur, mais uniquement pour les ventes de produits de la catégorie "Électronique" qui ont eu lieu au mois de janvier*]. Peux tu m’aider à trouver la formule Excel qui me permettra d'y parvenir ? Explique en détail la formule Excel qui permettrait d'obtenir le résultat souhaité. Décompose la formule en ses différents éléments, en expliquant l'objectif et la fonction de chacun d'entre eux et la manière dont ils fonctionnent ensemble. Enfin, fournis tout contexte ou conseil nécessaire à l'utilisation efficace de la formule dans une feuille de calcul Excel.""",
        "Corrigez le paragraphe attaché en vérifiant la cohérence des dates et des chiffres.",
        "Relisez et reformulez ce paragraphe pour qu'il respecte un ton formel adapté à une réunion avec des partenaires internationaux.",
        "Revoyez la structure de ce paragraphe pour s'assurer qu'il est logique et bien organisé.",
        "Corrigez les erreurs de grammaire et de syntaxe dans ce paragraphe, tout en conservant le style d'origine.",
        "Revoir ce projet de paragraphe pour vous assurer qu'il est conforme aux standards de l'administration française.",
        "Revoyez ce paragraphe et assurez-vous qu'il est inclusif et non-discriminatoire.",
        "Corrigez les erreurs typographiques et vérifiez que le ton est approprié pour une communication interne.",
        "Réécrivez ce paragraphe pour qu'il soit compréhensible par un public non-expert.",
        "Améliorez ce paragraphe pour qu'il soit plus percutant pour un public nord-américain.",
        "Assurez-vous que ce plan stratégique est clair et concis, en évitant le jargon inutile.",
        "Corrigez et simplifiez ce paragraphe pour qu'il soit facile à traduire en plusieurs langues.",
        "Relisez et ajustez ce paragraphe pour qu'il soit plus direct et assertif",
        "Reformulez ce paragraphe en utilisant un langage simple et accessible, adapté à une communication gouvernementale.",
        "Améliorez ce paragraphe en y ajoutant des exemples concrets pour illustrer les points clés.",
        "Corrigez et adaptez ce paragraphe pour une audience multiculturelle, en évitant les références trop spécifiques à une seule culture.",
        "Revoyez ce paragraphe pour vous assurer qu'il est conforme aux normes de style en vigueur dans les publications académiques.",
        # rédaction
        "J'ai besoin de ton aide pour rédiger un message d'absence du bureau. . Tu sais rédiger des messages clairs et faciles à lire. Crée un mail d'absence du bureau qui inclut les informations importantes à mentionner. Sois concis. Le ton doit être poli, direct et simple.",
        "Ta tâche consiste à examiner les notes de réunion fournies et à créer un résumé concis qui capture les informations essentielles, en te concentrant sur les points clés et les actions assignées à des personnes ou à des départements spécifiques au cours de la réunion. Utilise un langage clair et professionnel et structure le résumé de manière logique en utilisant un formatage approprié tel que des titres, des sous-titres et des puces. Veille à ce que le résumé soit concis, facile à comprendre et qu'il donne un aperçu complet mais succinct du contenu de la réunion, en veillant tout particulièrement à indiquer clairement qui est responsable de chaque mesure à prendre.",
        "Ta tâche consiste à rédiger une note de synthèse complète sur la base des points clés fournis. La note doit être rédigée sur un ton professionnel, en abordant toutes les informations pertinentes de manière claire et concise. Utilise un formatage approprié, tel que des titres, des sous-titres et des puces, pour organiser le contenu de manière efficace. Veille à ce que la note soit bien structurée, cohérente et facile à comprendre pour le public visé.",
        "Aide-moi à améliorer la note d’intention pour une nouvelle idée de produit. L’objectif est d'analyser le contenu et de proposer des commentaires constructifs et des suggestions en adoptant le point de vue du financeur.",
        "Identifie les forces et les faiblesses de la proposition du point de vue du financeur. 2. Réfléchis aux informations manquantes ou peu claires qui seraient importantes pour le décideur.",
        "Dresse la liste des réactions que le financeur pourrait avoir",
        "Formule trois suggestions spécifiques pour améliorer le document d'une page afin de mieux répondre aux besoins et aux préoccupations du financeur.",
        "Tu es un rédacteur en chef doté d'un sens aigu du détail et d'une connaissance approfondie de la langue, du style et de la grammaire française. Ta tâche consiste à m'aider à affiner et améliorer le contenu écrit en fonction des étapes suivantes : 1. Identifier les points à améliorer en termes de grammaire, de ponctuation, d'orthographe et de style. 2. Fournir des suggestions réalisables pour affiner le texte, en expliquant le raisonnement derrière chaque suggestion. 3 Proposer des alternatives pour le choix des mots, la structure des phrases et la formulation afin d'améliorer la clarté, la concision et l'impact. 4. Veiller à ce que le ton et la voix de l'écrit soient cohérents et adaptés au public et à l'objectif visés. 5. Vérifier la logique, la cohérence et l'organisation, et suggérer des améliorations si nécessaire. 6. Fournir un retour sur l'efficacité globale de l'écrit, en soulignant les points forts et les domaines à développer. 7. Enfin, à la fin du projet, produire une version entièrement révisée qui tient compte de toutes les suggestions.",
        "Rédigez une lettre officielle demandant une extension de délai pour la soumission d'un rapport d'audit externe.",
        "Élaborez un compte-rendu détaillé de la dernière réunion de suivi de projet, en veillant à inclure toutes les décisions prises et les actions assignées.",
        "Rédigez un plan de communication interne pour annoncer un changement majeur dans la politique de l'entreprise.",
        "Préparez un discours pour le directeur général à présenter lors de la cérémonie annuelle de remise des prix de l'entreprise.",
        "Rédigez un email de relance pour un fournisseur qui n'a pas encore livré les documents requis pour le projet en cours.",
        "Rédigez un rapport de situation hebdomadaire à destination des équipes opérationnelles, en soulignant les priorités pour la semaine suivante.",
        "Rédigez un rapport de mission à envoyer au ministère de tutelle, en détaillant les résultats obtenus et les recommandations futures.",
        "Préparez une note de service pour informer l'ensemble des employés de la mise en place d'un nouveau protocole de sécurité.",
        "Rédigez un rapport d'incident à destination du département de la sécurité, en détaillant les faits, les causes probables et les mesures prises.",
        "Élaborez un projet de discours pour le maire à l'occasion de l'inauguration d'un nouveau centre culturel.",
        "Préparez un courrier formel pour inviter un représentant d'une organisation internationale à participer à une conférence organisée par votre administration.",
        "Rédigez une réponse à une plainte déposée par un citoyen concernant un service public, en veillant à maintenir un ton respectueux et professionnel.",
        "Élaborez un dossier de presse pour le lancement d'un nouveau programme gouvernemental, en incluant tous les éléments clés à communiquer.",
        "Rédigez une présentation PowerPoint pour la réunion mensuelle de suivi de performance, en intégrant des graphiques et des données clés.",
        "Préparez un document de synthèse sur les meilleures pratiques internationales dans votre domaine (à préciser) pour un groupe de travail intergouvernemental.",
        "Rédigez une lettre de remerciement à envoyer à un partenaire institutionnel après la conclusion d'un accord de coopération.",
        "Rédigez un communiqué de presse pour annoncer le lancement d'un nouveau produit sur le marché.",
        "Élaborez un script de vidéo promotionnelle de 2 minutes pour une campagne de marketing digital.",
        "Rédigez une série de trois publications pour les réseaux sociaux visant à promouvoir un événement d'entreprise.",
        "Rédigez un email marketing destiné à fidéliser les clients existants avec une offre spéciale.",
        "Élaborez un plan de communication pour le lancement d'une campagne publicitaire dans un nouveau marché géographique.",
        "Préparez une présentation PowerPoint pour une réunion avec des investisseurs, en mettant l'accent sur les opportunités de croissance.",
        "Rédigez une landing page pour une campagne de marketing en ligne, optimisée pour les conversions.",
        "Élaborez un dossier de presse pour une campagne de sensibilisation menée par l'entreprise.",
        "Rédigez un post LinkedIn destiné à annoncer une collaboration stratégique entre votre entreprise et un autre acteur du marché.",
        "Préparez un email de remerciement pour les participants d'un webinaire organisé par votre entreprise.",
        "Rédigez un script pour un podcast de 10 minutes destiné à promouvoir une nouvelle gamme de produits.",
        "Élaborez un plan de communication de crise pour anticiper les réactions à un incident majeur.",
        "Élaborez un calendrier éditorial pour le blog de l'entreprise, en tenant compte des événements saisonniers et des temps forts du secteur.",
        "Rédigez une proposition de partenariat à présenter à un groupe de presse locale pour une campagne de promotion dans leur journal.",
        "Rédigez un rapport d'analyse sur les performances d'une récente campagne publicitaire, incluant des recommandations pour les futures actions.",
        "Préparez un guide de style pour l'utilisation cohérente de la marque dans tous les supports de communication.",
        # idées
        "Développez une méthode pour encourager les employés à proposer des idées en dehors de leurs responsabilités habituelles.",
        "Proposez un cadre pour évaluer et prioriser les idées créatives issues de séances de brainstorming.",
        "Proposez des techniques pour surmonter les blocages créatifs lors des sessions de groupe.",
        "Imaginez un système pour intégrer des éléments de ludification afin de stimuler la génération d'idées.",
        "Imaginez une méthode pour utiliser les défis et problèmes actuels de l'entreprise comme opportunités de génération d'idées.",
        "Suggérez des techniques pour cultiver un état d'esprit innovant au sein de l'équipe.",
        "Proposez trois nouvelles idées pour améliorer l'efficacité des réunions hebdomadaires.",
        "Propose des solutions innovantes pour réduire les délais de traitement des dossiers administratifs.",
        "Proposez des stratégies pour promouvoir un environnement de travail inclusif et respectueux de la diversité.",
        "Proposez des idées pour améliorer la transparence des processus décisionnels au sein de l'administration.",
        "Propose des concepts pour une campagne de sensibilisation à l'environnement à destination des citoyens.",
        "Proposez des idées pour moderniser les outils de travail utilisés par votre équipe, en tenant compte des contraintes budgétaires.",
        "Proposez des solutions pour réduire l'empreinte écologique de mon administration, en tenant compte des contraintes légales et locales.",
        "Proposez trois nouvelles stratégies pour améliorer la productivité d'une équipe en télétravail.",
        "Donne moi cinq idées pour réduire l'empreinte carbone dans les bureaux de mon entreprise et note ces idées de 1 à 5 selon leur faisabilité et leur impact. ",
        "Suggérez des approches innovantes pour fidéliser les clients existants sur des marchés émergents.",
        "Proposez des moyens d'améliorer l'intégration des nouveaux employés dans une organisation.",
        "Proposez des idées pour renforcer la collaboration entre les départements au sein de votre entreprise.",
        "Générez trois idées pour améliorer la satisfaction des clients dans un environnement de vente en ligne.",
        "Suggérez des méthodes pour intégrer des pratiques de bien-être au quotidien des employés",
        "Proposez des stratégies pour adapter votre offre à une clientèle internationale.",
        "Imaginez des idées pour améliorer la communication interne dans une organisation multiculturelle.",
        "Proposez des idées pour intégrer les technologies émergentes dans les opérations quotidiennes.",
        "Identifiez des initiatives pour promouvoir l'innovation dans une entreprise ayant une longue tradition.",
        "En tant que professeur principal d’une classe de troisième, comment motiver les élèves dans leur apprentissage sans les noter? Donner cinq pistes sous forme de tableau avec avantages et inconvénients.",
        "En tant que rédacteur publicitaire très reconnu dans ton domaine, crée 10 titres pour le produit X, avec l’objectif Y. Donne-moi les titres sous forme de tableau numéroté et réalise une évaluation pour savoir quel titre fonctionne le mieux (score maximum: 5 points)",
        "Pourquoi les applications traditionnelles d'apprentissage des langues ne parviennent-elles pas à intéresser les jeunes publics ? Propose des idées d'outils d'apprentissage des langues alimentés par l'IA pour remédier à ces lacunes.",
        "Génère des idées de noms pour une nouveau parfum à destination d'une clientèle 20-30 ans, urbaine, féminine.",
        "Nous sommes une boutique en ligne de vêtements de sport basée en Suisse. Agis en tant que rédacteur de textes publicitaires de haut niveau. Aide-moi à trouver 5 idées de slogans publicitaires pour notre nouvelle collection de vêtements de sport. La campagne est envoyée aux abonnés à la newsletter, profil masculin, passionnés de sport, âgés de 40 à 60 ans et disposant de revenus moyens à importantes.",
        "Je lance une nouvelle application de rencontre et suis à la recherche d'idées marketing créatives pour la faire connaître dans la région parisienne pour le lancement. Peux-tu m'en suggérer une dizaine ?",
        "Donne-moi plusieurs idées créatives pour organiser un team building dans une entreprise de développement de jeu vidéo.",
        "Invente le nom d'un nouveau restaurant gastronomique spécialisé dans la cuisine provençale implanté à Nice. Tu es un rédacteur publicitaire doué pour créer des accroches marketing convaincantes. Utilise tes compétences pour créer un nom qui donnera envie de fréquenter ce restaurant. Utilise des jeux de mots, des rimes  ou tout ce qui permettra de se souvenir du lieu. Fais preuve de créativité et d'imagination.",
        # Emploi
        "Propose-moi 2 à 3 phrases pour remercier la personne qui m’a reçu, en réaffirmant mon intérêt pour le poste proposé. Le ton ne doit pas être trop formel ni d’un enthousiasme débordant.",
        "Rédige une lettre de recommandation professionnelle pour un ancien collègue, en détaillant ses compétences, son attitude au travail, et les projets réussis ensemble.",
        "Comment évaluer les compétences techniques d'un candidat sans biais culturel pendant les tests de compétence ?",
        "Quels critères utiliser pour évaluer l'adaptabilité d'un candidat dans un environnement de travail multiculturel ?",
        "Dans le cadre d’un processus de recrutement, comment aborderiez-vous une question sur les échecs professionnels lors d'un entretien dans un pays où l'échec est stigmatisé ?",
        "Jusqu’à présent j’ai travaillé en France et en Europe, je cherche à trouver un travail aux Etats Unis ou au Canada, comment dois-je adapter mon CV et ma lettre de motivation?",
        "Jusqu’à présent j’ai travaillé en France et en Europe, je postule pour des postes en Asie, comment dois-je adapter mon CV et ma lettre de motivation?",
        "Vous êtes expert RH en recrutement, comment expliqueriez-vous un changement de carrière important dans un contexte où les parcours non linéaires sont mal vus ?",
        "Comment ajuster les processus de recrutement pour attirer des candidats dans un environnement de travail multiculturel ?",
        "Pour m’aider à me projeter dans ma candidature à un nouveau poste, réponds à ma question comme si tu étais à ma place. En tant que candidat pour un poste de responsable du département des relations publiques, décrivez une expérience où vous avez dû acquérir rapidement de nouvelles compétences pour un poste. Comment cela pourrait-il vous préparer pour le rôle que vous visez ?",
        "En tant que recruteur dans un processus de recrutement, quelles questions d'entretien posez-vous pour évaluer la capacité d’un candidat à travailler sous pression ?",
        "En tant que recruteur dans un processus de recrutement, comment évaluez-vous les compétences en communication d’un candidat lors d'un entretien ?",
        "En tant que recruteur dans un processus de recrutement, quels sont les meilleurs indicateurs dans une lettre de motivation pour évaluer l'engagement d'un candidat envers le poste ?",
        "En tant que recruteur dans un processus de recrutement, quels aspects de la personnalité d’un candidat sont les plus importants pour un rôle de leadership dans une culture de travail collaborative ?",
        "****En tant que recruteur dans un processus de recrutement, quels sont les signes que vous recherchez pour déterminer si un candidat est proactif et autonome ?",
        "En tant que candidat dans un processus de recrutement, quelle est la meilleure façon de préparer des réponses à des questions comportementales pour un entretien dans un secteur spécifique ?",
        "Comment, en tant que candidat, adapteriez-vous votre CV pour refléter vos compétences transférables alors qu’il y a un écart entre vos expériences passées et le poste que vous visez ?",
        "En tant que recruteur dans un processus de recrutement, quels éléments spécifiques d’un CV considérez-vous comme les plus révélateurs de la capacité d’un candidat à évoluer dans un nouvel environnement de travail ?",
        "Quelles méthodes peuvent aider à réduire les biais culturels et les biais de genre lors de l'évaluation des candidatures pour un poste de direction ?",
        """Je suis en train de recruter un candidat pour un poste de responsable de communication dans une institution culturelle. Le candidat idéal doit avoir de l'expérience dans le développement et l'exécution de campagnes de communication multicanal, de solides compétences analytiques et la capacité de collaborer efficacement avec des équipes. Il doit également être passionné par les dernières tendances et technologies en matière de communication. Ta tâche consiste à **générer une série de dix questions** réfléchies et ouvertes à poser en entretien sur la base du contexte donné. Les questions doivent être conçues de manière à susciter des réponses perspicaces et détaillées de la part de la personne interrogée, lui permettant de mettre en valeur ses connaissances, son expérience et son esprit critique. Évite les questions de type "oui/non" ou celles dont les réponses sont évidentes. Privilégie plutôt les questions qui encouragent la réflexion, l'auto-évaluation et le partage d'exemples ou d'anecdotes spécifiques.""",
    ],
    "loisirs": [
        # Voyages
        "Je prévois un séjour en Suisse et j’aimerais faire une randonnée en montagne. Quels sentiers sont adaptés pour un débutant tout en offrant de belles vues sur les Alpes suisses ?",
        "Je me rends à Montréal au printemps. Quels festivals ou événements culturels ne devrais-je pas manquer pendant cette saison et où trouver les meilleurs lieux pour goûter à la gastronomie québécoise ?",
        "Je planifie un voyage en Tunisie. Quels sites archéologiques et plages sont à visiter absolument à Carthage et Djerba ?",
        "Je prépare un voyage à Dakar. Quels sont les meilleurs endroits pour découvrir la musique sénégalaise et les marchés animés tout en ayant une expérience locale authentique ?",
        "Je souhaite explorer la Guadeloupe. Pourrais-tu me conseiller sur les plages les plus relaxantes et les activités à faire en famille ?",
        "Je vais en Algérie pour un séjour culturel d’une semaine. Quels sont les lieux historiques et les musées à visiter à Alger pour comprendre l’histoire et la culture du pays ?",
        "Je planifie un voyage en Martinique. Quels sont les endroits à visiter pour découvrir la culture créole et les meilleurs endroits pour déguster des plats locaux tout en profitant des plages ?",
        "Je me rends à Genève pour affaires. Quels sont les bons endroits pour se détendre après une journée de travail, en particulier des cafés ou des parcs ?",
        "Quels sont les lieux historiques et les activités de loisirs à explorer à Port-au-Prince pour une immersion dans la culture haïtienne ?",
        "Je prévois un voyage de deux semaines en Côte d’Ivoire. Peux-tu me donner un itinéraire ?",
        "Je prévois un week-end à Bruxelles. Peux-tu me donner un itinéraire en dehors des grandes attractions touristiques ?",
        "Je prévois un voyage de trois jours à Paris. Peux-tu me donner un itinéraire en dehors des sentiers battus ? Je m’intéresse à l’architecture moderne.",
        "Je prévois un voyage de 4 jours à Genève. Peux-tu me donner un itinéraire en dehors des sentiers battus ?",
        "Quels sont les essentiels à inclure dans un voyage de trois jours à Paris pour maximiser la découverte des attractions principales tout en évitant les foules ?",
        "Quels sont les meilleurs quartiers pour trouver des logements temporaires à Bruxelles, et quels critères de sélection sont importants pour choisir un bon emplacement ?",
        "Quels sont les sites de location de voiture les plus fiables à La Réunion pour explorer l'île, et quels sont les conseils pour conduire en toute sécurité ?",
        "Quels sont les types de pass ou de cartes de transport disponibles pour les visiteurs à Genève ?",
        "Quelles sont les activités culturelles et les visites surprenantes à Bruxelles et Bruges qui sortent des sentiers battus, tout en découvrant l’histoire et la gastronomie locales ?",
        "Quels sont les sites historiques moins connus mais nécessaires à explorer dans la ville pour comprendre l’évolution de Québec au-delà des attractions touristiques principales ?",
        "Je pars en Tunisie une semaine, quels sont les sites archéologiques, les plages et les villes médiévales à ne pas louper ?",
        "Je rêve de visiter le Maroc en automne. Pourrais-tu me conseiller sur les meilleures villes à explorer et les activités à faire à Marrakech et Fès ?",
        "Je prévois un voyage de 4 jours à Montréal. Peux-tu me donner un itinéraire en dehors des grandes attractions touristiques ?",
        "Je prévois un voyage de 4 jours à Québec. Peux-tu me donner un itinéraire en dehors des grandes attractions touristiques ?",
        # Recettes
        "Pouvez-vous fournir une recette détaillée pour réaliser un Poulet Yassa, plat emblématique du Sénégal, en utilisant des ingrédients frais et des épices traditionnelles ?",
        "Quelle est la meilleure façon de préparer une bouillabaisse traditionnelle de Marseille, avec des poissons variés, des crustacés, et un bouillon parfumé aux herbes de Provence ?",
        "Comment cuisiner le Riz djon-djon, un plat haïtien à base de riz noir, champignons, crevettes et épices locales, pour capturer les saveurs authentiques d’Haïti ?",
        "Pouvez-vous expliquer comment réaliser une fondue au fromage suisse, en choisissant les bons types de fromage et en respectant les techniques de cuisson pour obtenir une texture parfaite ?",
        "Quelle est la recette traditionnelle des Accras de morue des Antilles, en combinant la morue salée, les épices créoles, et une pâte légère pour un apéritif croustillant ?",
        "Comment préparer un Tiebou Dieune, le plat national sénégalais, en choisissant les meilleurs poissons, légumes, et en maîtrisant la cuisson du riz parfumé ?",
        "Pouvez-vous fournir une recette complète pour réaliser un Ragoût de cabri réunionnais, en utilisant des épices locales et des techniques de cuisson traditionnelles pour un plat riche en saveurs ?",
        "Comment cuisiner un Mafé malien, un ragoût de viande ou de poulet à la sauce d’arachide, en respectant les traditions culinaires du Mali et en équilibrant les saveurs sucrées et salées ?",
        "Quelle est la meilleure méthode pour préparer une tarte flambée (flammekueche) alsacienne, en travaillant la pâte fine, et en choisissant les garnitures classiques comme l'oignon et le lard ?",
        "Pouvez-vous détailler une recette de Poulet aux arachides, un plat typique du Bénin, en utilisant du beurre de cacahuète, des épices, et des techniques de cuisson locales ?",
        "Comment préparer du Saka-Saka, un plat congolais à base de feuilles de manioc pilées, en ajoutant du poisson fumé et des épices pour un repas traditionnel et nourrissant ?",
        "Quelle est la recette classique de la Quiche lorraine, en utilisant une pâte brisée maison, des lardons, des œufs et de la crème?",
        "Pouvez-vous expliquer comment réaliser un Foutou banane ivoirien, un accompagnement traditionnel à base de banane plantain et d’igname, souvent servi avec une sauce graine ou arachide ?",
        "Comment préparer un Gâteau basque traditionnel, en choisissant entre la crème pâtissière et la confiture de cerises noires pour la garniture, et en respectant les techniques de pâtisserie du Pays Basque ?",
        "Donne moi la recette de pâte à crêpes pour 6 personnes",
        "Comment préparer une authentique poutine québécoise à la maison, avec des frites croustillantes, du fromage en grains et une sauce brune savoureuse ?",
        "Rappelle moi la recette de la quiche lorraine et dis m'en plus sur l'histoire de ce plat (sois concis!)",
        "Propose moi une bonne recette de poulet basquaise et raconte moi au passage l’histoire de ce plat",
        "Je cherche des recettes à base de figue, peux-tu m’aider?",
        "Nous sommes en octobre j’habite à Pointe à Pitre, propose moi une recette locale avec des fruits et légumes de saison",
        # recommandations
        "Pouvez-vous recommander des films francophones qui traitent de la décolonisation en Afrique, en Asie ou aux Caraïbes, en offrant des perspectives historiques et critiques ?",
        "Quels sont les ouvrages majeurs de la littérature féministe écrits par des autrices francophones, qui explorent les enjeux de genre dans différents contextes culturels ?",
        "Pouvez-vous me suggérer des albums de musique fusion sénégalaise qui combinent des éléments de la musique traditionnelle avec des genres modernes comme le jazz ou le hip-hop ?",
        "Quels sont les meilleurs films d'animation français qui ont été primés à l'international?",
        "Pouvez-vous recommander des romans écrits par des auteurs francophones qui traitent de l’expérience de l’immigration en Europe, avec un regard critique et humain ?",
        "Quelles sont les œuvres incontournables de la musique électronique belge, avec un focus sur les artistes qui ont influencé la scène musicale en Belgique et à l’international ?",
        "Quels films africains francophones ont remporté des prix dans des festivals internationaux ?",
        "Pouvez-vous me suggérer des recueils de poésie haïtienne contemporaine qui explorent les thèmes de l’identité, de la résilience, et de l’histoire d’Haïti ?",
        "Quelles sont les chansons les plus marquantes créées par des artistes de la diaspora maghrébine en France, qui mélangent musique traditionnelle et influences modernes ?",
        "Pouvez-vous recommander des films classiques du cinéma suisse francophone, qui capturent les paysages, les histoires, et les questions sociales du pays ?",
        "Quels romans francophones belges mettent en lumière la diversité culturelle en Belgique, en explorant les identités multiples et les défis de la coexistence ?",
        "Quelles sont les œuvres phares de la musique traditionnelle malgache, qui mettent en avant les instruments et les rythmes propres à Madagascar ?",
        "Pouvez-vous me suggérer des films francophones qui décrivent la vie en banlieue en France, en abordant des thèmes tels que l’identité, la marginalisation et la solidarité ?",
        "Quels sont les auteurs contemporains des Caraïbes francophones qui explorent des thèmes tels que l’exil, la mémoire et l’identité à travers leurs romans ?",
        "Pouvez-vous recommander des albums de rap francophone ?",
        "Quels sont les films belges qui traitent des questions d'immigration et d'intégration?",
        "Quels sont les meilleurs livres de cuisine qui compilent des recettes traditionnelles de différents pays francophones?",
        "Quelles sont les chansons ou albums marquants produits par des artistes de la diaspora africaine en France, qui reflètent les influences hybrides entre l’Afrique et l’Europe ?",
        "Pouvez-vous me suggérer des films qui explorent l’histoire coloniale dans les Antilles françaises?",
        "Pouvez-vous recommander des artistes ou des albums de musique congolaise contemporaine, en particulier ceux qui réinventent la rumba ou explorent des genres modernes comme l’afrobeat ?",
        "Quels sont les livres pour jeunes adultes les plus populaires et influents écrits par des auteurs africains francophones, qui abordent des thèmes pertinents pour les jeunes d’aujourd’hui ?",
        "Pouvez-vous me suggérer des chansons haïtiennes qui sont connues pour leur contenu engagé et leur rôle dans les mouvements de protestation et de revendication sociale ?",
        "Je prévois une soirée cinéma en famille. Pouvez-vous me suggérer des films réconfortants et adaptés à tous les âges qui plairont à toute la famille ?",
        "Je suis passionné de non-fiction et je souhaite en apprendre davantage sur un sujet spécifique. Quels sont les livres bien documentés et informatifs que vous me recommanderiez sur [insérer le sujet] ?",
        "J’aime beaucoup la littérature. Quelles sont les classiques que je ne devrais pas manquer ?",
        "Je suis fan d'un artiste ou d'un genre spécifique. Pouvez-vous me fournir des recommandations d'artistes similaires ou complémentaires que je pourrais apprécier ?",
        "J'ai envie de musique joyeuse et entraînante. Quelles sont les chansons ou les albums que vous me conseilleriez pour me remonter le moral ?",
    ],
    "administratif": [
        "Écris un court e-mail pour demander un devis à des électriciens près de chez moi pour un problème de panne. Je dois obtenir une intervention dans la semaine.",
        "Rédige un courrier pour résilier le bail de mon appartement",
        "Comment rédiger une lettre de contestation d'une amende pour excès de vitesse, en expliquant les raisons pour lesquelles l'amende devrait être annulée ou revue ?",
        "Je lance une nouvelle entreprise et je me débats avec les formalités administratives. Aide-moi à préparer un plan d'affaires complet qui répond à toutes les exigences administratives.",
        "Je demande un permis de séjour, travaillons ensemble pour rédiger une lettre de motivation convaincante qui met en valeur mon éligibilité et respecte toutes les directives officielles.",
        "Vous devez rédiger une demande formelle d'informations auprès d'une agence gouvernementale ? Je vous aiderai à rédiger une lettre claire et concise qui respecte les protocoles administratifs appropriés.",
        "Je prépare un dossier pour créer une association. Aide moi à structurer le document des statuts, à utiliser un langage approprié et à m’assurer que toutes les informations nécessaires sont incluses pour répondre aux normes administratives.",
        "Crée un modèle de contrat de prestation de services entre un prestataire indépendant et un client, en précisant les obligations de chaque partie, les modalités de paiement, les conditions de résiliation, et les clauses de confidentialité.",
        "Rédige une lettre de résiliation d'un contrat d'abonnement à un service (ex : téléphonie, internet), en mentionnant les raisons de la résiliation et la date d'effet souhaitée.",
        "Rédige une lettre formelle pour demander à un ancien employeur un certificat de travail, en précisant les dates d'emploi et le poste occupé.",
        "Crée un modèle de convocation à une réunion formelle pour une association, en indiquant l'ordre du jour, la date, l'heure, et le lieu de la réunion.",
        "Rédige une lettre de demande de logement social, en expliquant la situation financière, les besoins en logement, et les raisons justifiant la demande.",
        "Rédige le procès-verbal d'une assemblée générale d'une association, en récapitulant les décisions prises, les votes, et les discussions principales.",
        "Rédige une lettre de demande de visa touristique à l'attention d'une ambassade, en expliquant les raisons du voyage, les dates prévues, et les garanties financières pour le séjour.",
        "Rédige une lettre de demande de congé sabbatique adressée à un employeur, en expliquant les raisons de la demande et les projets prévus durant ce congé.",
        "Rédige une lettre formelle pour signaler une erreur sur une facture reçue, en expliquant l'erreur en question et en demandant une correction ou un remboursement.",
        "Comment rédiger une lettre d'accompagnement convaincante pour une demande de subvention, en mettant en avant les besoins du projet et son impact potentiel ?",
        "Pouvez-vous rédiger un modèle de contrat de location d'un bien immobilier entre un propriétaire et un locataire, en précisant les termes essentiels comme la durée, le montant du loyer, et les obligations de chaque partie ?",
        "Pouvez-vous créer un exemple de testament, en veillant à ce que toutes les dispositions légales soient respectées ?",
        "Aide moi à rédiger une lettre de demande de modification des termes d'un contrat d'assurance, par exemple pour augmenter ou réduire la couverture ?",
        "Pouvez-vous rédiger une lettre officielle d'avis de départ à la retraite, en remerciant l'employeur pour les années passées et en précisant la date prévue pour le départ ?",
        "Comment rédiger une attestation d'hébergement pour une personne résidant à votre domicile, en précisant les détails nécessaires pour des démarches administratives ?",
        "Quelle est la meilleure approche pour rédiger une lettre demandant un délai supplémentaire pour le paiement d'une facture, en justifiant la demande et en proposant un nouveau calendrier de paiement ?",
    ],
    "langues": [
        # Regional
        'Traduis cette phrase en occitan et explique les nuances culturelles : "Je vais chez le boulanger."',
        "Écris une conversation en français canadien entre deux amis discutant des activités hivernales.",
        "Rédige un conte pour enfants en créole martiniquais mettant en scène des animaux de la région.",
        "Crée un dialogue en occitan où deux personnages discutent de la récolte des olives.",
        "Traduis une chanson populaire malienne du bambara au français.",
        "Écris une histoire courte en français suisse sur une randonnée en montagne. Indique en gras les tournures propres au français suisse.",
        "Rédige un court article en français louisianais sur les traditions du Mardi Gras. Indique en gras les tournures spécifiques au français louisianais.",
        "Écris un dialogue en créole réunionnais entre deux personnages discutant des dernières récoltes de canne à sucre.",
        "Traduis un conte berbère du kabyle au français, en expliquant les nuances culturelles.",
        "Écris une carte postale en basque décrivant une fête locale.",
        "Compose une chanson en ch'ti (picard) qui célèbre la vie dans le nord de la France.",
        "Écris une lettre en breton à un ami pour l'inviter à une fête de la Saint-Yves (Gouel Erwan).",
        "Rédige un conte en gascon pour enfants mettant en scène un berger des Pyrénées. Indique en gras les tournures propres au gascon.",
        "Compose un dialogue d’une minute en picard où deux personnages discutent des récoltes de pommes. Indique en gras les tournures propres au picard.",
        "Rédige une histoire en provençal sur une vendange dans les vignobles de Provence.",
        "Compose une légende en arpitan racontant l'histoire d'un lac mystérieux des Alpes.",
        "Écris un dialogue en solognot entre deux chasseurs discutant de la saison de la chasse. Explique les tournures propres au solognot.",
        "Rédige un article en lorrain sur les traditions artisanales de la région.",
        "Rédige un discours en franco-provençal pour une fête de village en Savoie.",
        "Écris une lettre en poitevin-saintongeais à un ami pour lui parler des marais de la région.",
        "Rédige un poème en corse sur l'émigration et le sentiment de nostalgie pour l'île. Explique les termes spécifiques.",
        "Compose un poème en occitan sur les champs de lavande en Provence. Explique les termes spécifiques.",
        "Rédige un conte en occitan pour enfants qui raconte les aventures d'un chevalier cathare.",
        "J’ai un niveau grand débutant en breton et je ne sais pas par où commencer, aide moi à énoncer des objectifs spécifiques pour le premier mois d'étude",
        "Ecris un tiot poème in ch'ti sus l'biauté d'la nature. Propose aussi une traduction en français de ta réponse.",
        "Pòtès escriure un pichon poèma en occitan sus lo passatge de las sasons? Propose une traduction en français après la réponse en occitan.",
        "Raconte ein tiot conte in picard avéc des personnages du village.",
        '"Wann ich dir so schwätz, verstehsch mich?" Réponds en alsacien',
        # Argot
        "Être un « pive » en Suisse, c’est quoi le bail ?",
        "Si tu dis « ndeko », tu parles à qui au Congo ? / Quand tu dis « ndeko » au Congo, tu parles de qui exactement ?",
        "« J’ai le seum », t’as capté ou t’es largué ?",
        "Cocorico en louchebem ça donne quoi?",
        "« Tèt chaje » , t’as capté ou t’es largué ?",
        "« wakh dem » , t’as capté ou t’es largué ?",
        "Quoque ch'est qu'te berdoules ? Réponds en Chtimi.",
        "C’est quoi les mots qui font que t’as l’air 100% québécois, tabarnak ?",
        "Comment « tèt chaje » fait passer ton stress haïtien pour du cool ?",
        """Explique moi cette strophe de la chanson "Wesh alors" de Jul: "Wesh le sang, wesh la honda / Mes sons tournent à la Jonque' / Tu m'as trahis mais t'es un bon gars / J'suis en fumette mais j'me trompe pas”""",
        "En quoi l'argot belge, avec des expressions comme « zwanze », diffère-t-il du reste de la francophonie ?",
        "Quels sont les contextes d’utilisation des expressions « wakh dem » et « jaay foné » à Dakar ?",
        "Comment l’expression « être un pive » s’intègre-t-elle dans l’argot suisse romand et que signifie-t-elle exactement ?",
        "Pouvez-vous décrire l’usage de « tèt chaje » dans le quotidien haïtien et ses nuances ?",
        "Quels sont les contextes sociaux derrière l’utilisation de « ndeko » et « bokilo » au Congo ?",
        "Comment l’argot camerounais, avec des termes comme « nyanga », reflète-t-il les dynamiques culturelles du pays ?",
        "Quels sont les usages courants de « choper » et « c'est pas sorcier » dans l’argot néo-calédonien ?",
        "Comment des expressions comme « folikè » et « gbass » ont-elles évolué dans l'argot guinéen contemporain ?",
        "Quelle est l’histoire derrière des expressions comme « gone » et « bouchon » dans l’argot lyonnais ?",
        "Quelle est l’origine des termes « kpakpatoya » et « se défouler » au Cameroun, et comment ces expressions sont-elles intégrées dans la vie de tous les jours ?",
        """Comment « calou » et « roder » peuvent-ils transformer ton quotidien à La Réunion, et te faire paraître comme un local, même si tu ne sais pas ce qu'est un "rhum arrangé" ?""",
        "Comment éviter de se faire rire au nez à Dakar en utilisant « wakh dem » et « yaye »?",
        "Quelle est la magie derrière « zorey » et « bonbon » pour éviter les faux pas aux Antilles (et ne pas te retrouver à danser le zouk tout seul) ?",
        "Comment « kolat » et « nécro » peuvent-ils te faire passer pour un insider au Congo, même si tu ne comprends pas tout à fait ce qu’est un « nganda » ?",
        """Explique le terme "FOMO". Imagine que tu es de la génération Z et que tu expliques ce terme à tes grands-parents. Détaille l'acronyme, explique son origine et donne quelques exemples d'utilisation. Sois concis.""",
    ],
    "conseils": [
        "Comment adapter une alimentation sportive dans un pays où la viande est majoritairement consommée crue ?",
        "Quels plats traditionnels sont les plus adaptés à un régime équilibré après une séance de musculation ?",
        "Quels sont les avantages et inconvénients de la consommation de manioc dans un régime sportif ?",
        "Comment adapter son régime alimentaire à un entraînement en altitude dans les Alpes françaises ?",
        "Quels sont les superaliments les plus efficaces pour augmenter l'endurance en marathon au Sénégal ?",
        "Quelle est la meilleure approche nutritionnelle pour un programme de musculation intense en Belgique ?",
        "Quel est le rôle du foufou dans un régime sportif en République démocratique du Congo ?",
        "Quels plats à base de poisson sont les plus recommandés pour la récupération musculaire ?",
        "Quels sont les meilleurs snacks pour un sportif en déplacement en Afrique de l’ouest ?",
        "J'ai besoin d’améliorer ma condition physique. Peux-tu me proposer un programme d’entraînement simple sur 7 jours ?",
        "Je souhaite perdre du poids en adoptant une alimentation équilibrée. Peux-tu me donner un plan de repas pour une semaine ?",
        "Je veux augmenter ma masse musculaire. Pourrais-tu me recommander des exercices de musculation à faire chez moi ?",
        "Je suis débutant en course à pied. Peux-tu me proposer un programme de course à pied pour les 30 prochains jours ?",
        "Je suis marathonien(ne) en Côte d'Ivoire et je cherche des conseils sur la meilleure façon d'adapter mon alimentation pendant la saison chaude et humide. Quels sont les aliments les plus hydratants et nutritifs ?",
        "Quels sont les avantages et inconvénients de la consommation de riz dans un régime sportif ?",
        "Quels plats locaux privilégier pour un régime équilibré lors d’un voyage en Europe ?",
        "Écris un guide d'initiation à la natation. Tu es un expert compétent et tu sais quelles informations donner aux personnes qui découvrent cette activité. Détaille ce qu'elles doivent savoir pour commencer. Sois concis.",
        "Écris un guide d'initiation à la course à pied. Tu es un expert compétent et tu sais quelles informations donner aux personnes qui découvrent cette activité. Détaille ce qu'elles doivent savoir pour commencer. Sois concis.",
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
