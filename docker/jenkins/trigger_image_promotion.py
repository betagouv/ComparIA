#!/usr/bin/env python3
"""Script pour lancer le job de promotion d'images vers atnum-release"""
import sys
import logging
from jenkins_common import JenkinsPromotionJobTrigger, JenkinsJobTrigger

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

DEFAULT_JOB_NAME = "atnum/stg/languia/languia-image-promotion"


def main():
    """Fonction principale"""
    parser = JenkinsJobTrigger.create_argument_parser(
        description="Lance le job de promotion d'images sur Jenkins",
        epilog="""
Exemples d'utilisation:
  # Avec variables d'environnement
  export JENKINS_URL="https://ogehguvsgm-jenkins.services.clever-cloud.com"
  export JENKINS_USERNAME="admin"
  export JENKINS_API_TOKEN="votre_token_ici"
  python trigger_image_promotion.py --source-tag abc123 --target-tag abc123

  # Avec arguments en ligne de commande
  python trigger_image_promotion.py --url https://ogehguvsgm-jenkins.services.clever-cloud.com --username admin --token votre_token --source-tag abc123 --target-tag abc123
        """,
        default_job_name=DEFAULT_JOB_NAME,
    )

    # Arguments spécifiques à la promotion
    parser.add_argument(
        "--source-tag", required=True, help="Tag source (commit hash dans atnum)"
    )
    parser.add_argument(
        "--target-tag",
        required=True,
        help="Tag cible (commit hash dans atnum-release)",
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Ne pas attendre la fin de la promotion",
    )
    args = parser.parse_args()

    # Validation et configuration
    JenkinsJobTrigger.validate_common_args(args)

    # Création du trigger
    trigger = JenkinsPromotionJobTrigger(
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

    # Lancement de la promotion
    logger.info("=" * 50)
    result = trigger.trigger(
        source_tag=args.source_tag, target_tag=args.target_tag, wait=not args.no_wait
    )

    # Affichage du résultat
    trigger.execute_main_workflow(
        result,
        success_message="Promotion lancée avec succès!",
        error_message="Échec du lancement de la promotion",
    )


if __name__ == "__main__":
    main()
