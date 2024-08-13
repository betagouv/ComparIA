
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

if os.getenv("LANGUIA_CONTROLLER_URL") != None:
    controller_url = os.getenv("LANGUIA_CONTROLLER_URL")
else:
    controller_url = "http://localhost:21001"

enable_moderation = False
use_remote_storage = False
prompts_table = {
    "loisirs": [
        # Voyages
        "Je prévois un séjour en Suisse et j’aimerais faire une randonnée en montagne. Quels sentiers sont adaptés pour un débutant tout en offrant de belles vues sur les Alpes suisses ?,",
        "Je me rends à Montréal au printemps. Quels festivals ou événements culturels ne devrais-je pas manquer pendant cette saison et où trouver les meilleurs lieux pour goûter à la gastronomie québécoise ?,",
        "Je planifie un voyage en Tunisie. Quels sites archéologiques et plages sont à visiter absolument à Carthage et Djerba ?,",
        "Je prépare un voyage à Dakar. Quels sont les meilleurs endroits pour découvrir la musique sénégalaise et les marchés animés tout en ayant une expérience locale authentique ?,",
        "Je souhaite explorer la Guadeloupe. Pourrais-tu me conseiller sur les plages les plus relaxantes et les activités à faire en famille ?,",
        "Je vais en Algérie pour un séjour culturel d’une semaine. Quels sont les lieux historiques et les musées à visiter à Alger pour comprendre l’histoire et la culture du pays ?,",
        "Je planifie un voyage en Martinique. Quels sont les endroits à visiter pour découvrir la culture créole et les meilleurs endroits pour déguster des plats locaux tout en profitant des plages ?,",
        "Je me rends à Genève pour affaires. Quels sont les bons endroits pour se détendre après une journée de travail, en particulier des cafés ou des parcs ?,",
        "Quels sont les lieux historiques et les activités de loisirs à explorer à Port-au-Prince pour une immersion dans la culture haïtienne ?,",
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
