#!/usr/bin/env python3
"""Script pour lancer le job de déploiement Kustomize prd sur Jenkins"""

import logging
import sys

from jenkins_common import JenkinsDeployJobTrigger, JenkinsJobTrigger

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

DEFAULT_JOB_NAME = "atnum/prd/ComparIA/deploy-prd"


def main():
    """Fonction principale"""
    parser = JenkinsJobTrigger.create_argument_parser(
        description="Lance le job de déploiement Kustomize prd sur Jenkins",
        epilog="""
Exemples d'utilisation:
  # Avec variables d'environnement
  export JENKINS_URL="https://ogehguvsgm-jenkins.services.clever-cloud.com"
  export JENKINS_USERNAME="admin"
  export JENKINS_API_TOKEN="votre_token_ici"
  python trigger_deploy_prd.py --image-tag abc123 --wait

  # Avec arguments en ligne de commande
  python trigger_deploy_prd.py --url https://ogehguvsgm-jenkins.services.clever-cloud.com --username admin --token votre_token --image-tag abc123 --wait
        """,
        default_job_name=DEFAULT_JOB_NAME,
    )

    # Arguments spécifiques au déploiement
    parser.add_argument(
        "--image-tag", required=True, help="Tag de l'image Docker à déployer"
    )
    parser.add_argument(
        "--force-delete",
        action="store_true",
        help="Forcer la suppression des ressources avant déploiement",
    )
    parser.add_argument(
        "--wait", action="store_true", help="Attendre la fin du déploiement"
    )
    args = parser.parse_args()

    # Validation et configuration
    JenkinsJobTrigger.validate_common_args(args)

    # Création du trigger
    trigger = JenkinsDeployJobTrigger(
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

    # Lancement du déploiement
    logger.info("=" * 50)
    result = trigger.trigger(
        image_tag=args.image_tag, force_delete=args.force_delete, wait=args.wait
    )

    # Affichage du résultat
    trigger.execute_main_workflow(
        result,
        success_message="Déploiement lancé avec succès!",
        error_message="Échec du lancement du déploiement",
    )


if __name__ == "__main__":
    main()
