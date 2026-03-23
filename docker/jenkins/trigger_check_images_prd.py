#!/usr/bin/env python3
"""Script pour lancer le job de vérification des images prd"""
import sys
import logging
from jenkins_common import JenkinsCheckJobTrigger, JenkinsJobTrigger

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

DEFAULT_JOB_NAME = "atnum/stg/languia/check-images"


def main():
    """Fonction principale"""
    parser = JenkinsJobTrigger.create_argument_parser(
        description="Lance le job de vérification des images prd sur Jenkins",
        epilog="""
Exemples d'utilisation:
  # Avec variables d'environnement
  export JENKINS_URL="https://ogehguvsgm-jenkins.services.clever-cloud.com"
  export JENKINS_USERNAME="admin"
  export JENKINS_API_TOKEN="votre_token_ici"
  python trigger_check_images_prd.py --commit-hash abc123def

  # Avec arguments en ligne de commande
  python trigger_check_images_prd.py --url https://ogehguvsgm-jenkins.services.clever-cloud.com --username admin --token votre_token --commit-hash abc123def
        """,
        default_job_name=DEFAULT_JOB_NAME,
    )

    # Arguments spécifiques à la vérification
    parser.add_argument(
        "--commit-hash", required=True, help="Hash du commit (tag de l'image)"
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Ne pas attendre la fin de la vérification",
    )
    args = parser.parse_args()

    # Validation et configuration
    JenkinsJobTrigger.validate_common_args(args)

    # Création du trigger
    trigger = JenkinsCheckJobTrigger(
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

    # Lancement de la vérification
    logger.info("=" * 50)
    result = trigger.trigger(commit_hash=args.commit_hash, wait=not args.no_wait)

    # Affichage du résultat
    trigger.execute_main_workflow(
        result,
        success_message="Vérification lancée avec succès!",
        error_message="Échec du lancement de la vérification",
    )


if __name__ == "__main__":
    main()
