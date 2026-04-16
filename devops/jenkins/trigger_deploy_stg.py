#!/usr/bin/env python3
"""
Script pour lancer le job de déploiement stg
Utilise un token API pour l'authentification (méthode recommandée)
"""

import sys
import logging
from jenkins_common import JenkinsDeployJobTrigger, JenkinsJobTrigger

# Configuration du logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

DEFAULT_JOB_NAME = "atnum/stg/languia/deploy-stg"


def main():
    """Fonction principale"""
    parser = JenkinsJobTrigger.create_argument_parser(
        description="Lance le job de déploiement stg sur Jenkins",
        epilog="""
Exemples d'utilisation:
  # Avec variables d'environnement
  export JENKINS_URL="https://ogehguvsgm-jenkins.services.clever-cloud.com"
  export JENKINS_USERNAME="admin"
  export JENKINS_API_TOKEN="votre_token_ici"
  python trigger_deploy_stg.py --image-tag abc123def

  # Avec arguments en ligne de commande
  python trigger_deploy_stg.py --url https://ogehguvsgm-jenkins.services.clever-cloud.com --username admin --token votre_token --image-tag abc123def

  # Avec force delete et attente
  python trigger_deploy_stg.py --image-tag abc123def --force-delete --wait
        """,
        default_job_name=DEFAULT_JOB_NAME,
    )

    # Arguments spécifiques au déploiement
    parser.add_argument(
        "--image-tag", required=True, help="Tag de l'image (commit hash)"
    )
    parser.add_argument(
        "--force-delete",
        action="store_true",
        help="Forcer la suppression des ressources avant déploiement",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Attendre la fin du déploiement et afficher le résultat",
    )

    args = parser.parse_args()

    # Validation commune
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
        image_tag=args.image_tag,
        force_delete=args.force_delete,
        wait=args.wait
    )

    trigger.execute_main_workflow(
        result,
        success_message="Déploiement lancé avec succès!",
        error_message="Échec du lancement du déploiement"
    )


if __name__ == "__main__":
    main()
