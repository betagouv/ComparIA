#!/usr/bin/env python3
"""
Script pour lancer le job de build de l'image Docker backend
Utilise un token API pour l'authentification (méthode recommandée)
"""

import sys
import logging
from jenkins_common import JenkinsBuildJobTrigger, JenkinsJobTrigger

# Configuration du logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

DEFAULT_JOB_NAME = "atnum/dev/languia/languia-dev-image-backend"


def main():
    """Fonction principale"""
    parser = JenkinsJobTrigger.create_argument_parser(
        description="Lance le job de build Docker backend sur Jenkins",
        epilog="""
Exemples d'utilisation:
  # Avec variables d'environnement
  export JENKINS_URL="https://ogehguvsgm-jenkins.services.clever-cloud.com"
  export JENKINS_USERNAME="admin"
  export JENKINS_API_TOKEN="votre_token_ici"
  python trigger_backend_build.py

  # Avec arguments en ligne de commande
  python trigger_backend_build.py --url https://ogehguvsgm-jenkins.services.clever-cloud.com --username admin --token votre_token

  # Builder une branche spécifique et attendre la fin
  python trigger_backend_build.py --ref feature/my-branch --wait

  # Voir les informations du dernier build
  python trigger_backend_build.py --last-build-info
        """,
        default_job_name=DEFAULT_JOB_NAME,
    )

    # Arguments spécifiques au build
    parser.add_argument(
        "--ref",
        default="develop",
        help="Branche ou ref Git à builder (défaut: develop)",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Attendre la fin du build et afficher le résultat",
    )
    parser.add_argument(
        "--last-build-info",
        action="store_true",
        help="Afficher les informations du dernier build (sans lancer de nouveau build)",
    )

    args = parser.parse_args()

    # Validation commune
    JenkinsJobTrigger.validate_common_args(args)

    # Création du trigger
    trigger = JenkinsBuildJobTrigger(
        jenkins_url=args.url,
        username=args.username,
        api_token=args.token,
        job_name=args.job,
        timeout=args.timeout,
    )

    # Connexion
    if not trigger.connect():
        logger.error("❌ Impossible de se connecter à Jenkins")
        sys.exit(1)

    # Cas spécial : last-build-info
    if args.last_build_info:
        trigger.get_last_build_info()
        sys.exit(0)

    # Lancement du build
    logger.info("=" * 50)
    result = trigger.trigger(ref_to_build=args.ref, wait=args.wait)

    trigger.execute_main_workflow(
        result,
        success_message="Build lancé avec succès!",
        error_message="Échec du lancement du build"
    )


if __name__ == "__main__":
    main()
