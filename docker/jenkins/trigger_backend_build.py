#!/usr/bin/env python3
"""
Script pour lancer le job de build de l'image Docker backend
Utilise un token API pour l'authentification (méthode recommandée)
"""

import os
import sys
import argparse
import logging
from typing import Optional, Dict, Any
import time

try:
    import jenkins
except ImportError:
    print("ERREUR: La librairie 'python-jenkins' n'est pas installée.")
    print("Installez-la avec: pip install python-jenkins")
    sys.exit(1)


# Configuration du logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class JenkinsBackendBuilder:
    """Classe pour lancer le build du backend Docker sur Jenkins"""

    def __init__(
        self,
        jenkins_url: str,
        username: str,
        api_token: str,
        job_name: str = "atnum/dev/languia/languia-dev-image-backend",
        timeout: int = 30,
    ):
        self.jenkins_url = jenkins_url.rstrip("/")
        self.username = username
        self.api_token = api_token
        self.job_name = job_name
        self.timeout = timeout
        self.server = None

    def connect(self) -> bool:
        """Établit la connexion à Jenkins"""
        try:
            logger.info(f"Connexion à {self.jenkins_url}...")

            self.server = jenkins.Jenkins(
                self.jenkins_url,
                username=self.username,
                password=self.api_token,
                timeout=self.timeout,
            )

            # Test de connexion
            user = self.server.get_whoami()
            logger.info(f"✅ Connecté en tant que: {user.get('fullName', 'N/A')}")

            return True

        except jenkins.JenkinsException as e:
            logger.error(f"❌ Erreur Jenkins: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Erreur de connexion: {e}")
            return False

    def trigger_build(
        self, ref_to_build: str = "develop", wait: bool = False
    ) -> Optional[int]:
        """
        Lance le build du backend Docker

        Args:
            ref_to_build: Branche ou ref Git à builder (défaut: develop)
            wait: Si True, attend la fin du build (défaut: False)

        Returns:
            Numéro du build lancé ou None en cas d'erreur
        """
        if not self.server:
            logger.error("❌ Pas de connexion établie")
            return None

        try:
            # Vérifie que le job existe
            job_info = self.server.get_job_info(self.job_name)
            logger.info(f"Job trouvé: {self.job_name}")

            # Paramètres du build
            parameters = {"REF_TO_BUILD": ref_to_build}

            # Lance le build
            logger.info(f"Lancement du build avec REF_TO_BUILD='{ref_to_build}'...")
            queue_number = self.server.build_job(self.job_name, parameters=parameters)

            # Récupère le numéro du build à partir de la queue
            logger.info(f"Build en queue: #{queue_number}")

            if wait:
                build_number = self._wait_for_build_start(queue_number)
                if build_number:
                    logger.info(f"Build #{build_number} démarré")
                    self._monitor_build(build_number)
                    return build_number
            else:
                logger.info(
                    f"✅ Build lancé (queue #{queue_number}). Utilisez --wait pour suivre la progression."
                )

            return queue_number

        except jenkins.JenkinsException as e:
            logger.error(f"❌ Erreur Jenkins lors du build: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Erreur lors du lancement du build: {e}")
            return None

    def _wait_for_build_start(
        self, queue_number: int, max_wait: int = 300
    ) -> Optional[int]:
        """Attend que le build sorte de la queue et récupère son numéro"""
        logger.info("En attente du démarrage du build...")
        start_time = time.time()

        while time.time() - start_time < max_wait:
            try:
                queue_item = self.server.get_queue_item(queue_number)

                # Si le build est sorti de la queue
                if "executable" in queue_item:
                    build_number = queue_item["executable"]["number"]
                    return build_number

                # Si encore en queue
                if queue_item.get("blocked") or queue_item.get("stuck"):
                    logger.info(
                        f"  Build en attente (raison: {queue_item.get('why', 'N/A')})"
                    )

                time.sleep(5)

            except jenkins.NotFoundException:
                # Le job n'est plus en queue, cherche le dernier build
                job_info = self.server.get_job_info(self.job_name)
                if job_info.get("lastBuild"):
                    return job_info["lastBuild"]["number"]

            except Exception as e:
                logger.warning(f"Erreur lors de la vérification de la queue: {e}")
                time.sleep(5)

        logger.warning(f"Timeout: le build n'a pas démarré après {max_wait}s")
        return None

    def _monitor_build(self, build_number: int):
        """Surveille la progression d'un build"""
        logger.info(f"Surveillance du build #{build_number}...")

        while True:
            try:
                build_info = self.server.get_build_info(self.job_name, build_number)

                if build_info["building"]:
                    # En cours
                    duration = build_info.get("duration", 0) / 1000  # ms vers s
                    logger.info(f"  Build en cours... ({duration:.0f}s)")
                    time.sleep(10)
                else:
                    # Terminé
                    result = build_info.get("result", "UNKNOWN")
                    duration = build_info.get("duration", 0) / 1000

                    if result == "SUCCESS":
                        logger.info(
                            f"✅ Build #{build_number} réussi! (durée: {duration:.0f}s)"
                        )
                    else:
                        logger.error(
                            f"❌ Build #{build_number} échoué: {result} (durée: {duration:.0f}s)"
                        )

                    # URL du build
                    build_url = build_info.get("url", "N/A")
                    logger.info(f"   URL: {build_url}")
                    break

            except Exception as e:
                logger.error(f"❌ Erreur lors de la surveillance: {e}")
                break

    def get_last_build_info(self) -> Optional[Dict[str, Any]]:
        """Récupère les informations du dernier build"""
        if not self.server:
            logger.error("❌ Pas de connexion établie")
            return None

        try:
            job_info = self.server.get_job_info(self.job_name)
            if job_info.get("lastBuild"):
                build_number = job_info["lastBuild"]["number"]
                build_info = self.server.get_build_info(self.job_name, build_number)

                logger.info(f"Dernier build: #{build_number}")
                logger.info(f"  Statut: {build_info.get('result', 'N/A')}")
                logger.info(f"  URL: {build_info.get('url', 'N/A')}")

                return build_info
            else:
                logger.info("Aucun build trouvé pour ce job")
                return None

        except Exception as e:
            logger.error(f"❌ Erreur lors de la récupération du dernier build: {e}")
            return None


def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(
        description="Lance le job de build Docker backend sur Jenkins",
        formatter_class=argparse.RawDescriptionHelpFormatter,
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
    )

    parser.add_argument(
        "--url",
        default=os.getenv("JENKINS_URL"),
        help="URL du serveur Jenkins (ex: http://localhost:8080)",
    )
    parser.add_argument(
        "--username",
        default=os.getenv("JENKINS_USERNAME"),
        help="Nom d'utilisateur Jenkins",
    )
    parser.add_argument(
        "--token", default=os.getenv("JENKINS_API_TOKEN"), help="Token API Jenkins"
    )
    parser.add_argument(
        "--job",
        default="atnum/dev/languia/languia-dev-image-backend",
        help="Nom du job Jenkins (défaut: atnum/dev/languia/languia-dev-image-backend)",
    )
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
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Timeout de connexion en secondes (défaut: 30)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Mode verbeux")

    args = parser.parse_args()

    # Configuration du niveau de log
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validation des arguments
    if not args.url:
        logger.error("❌ L'URL Jenkins est requise (--url ou variable JENKINS_URL)")
        sys.exit(1)

    if not args.username:
        logger.error(
            "❌ Le nom d'utilisateur est requis (--username ou variable JENKINS_USERNAME)"
        )
        sys.exit(1)

    if not args.token:
        logger.error(
            "❌ Le token API est requis (--token ou variable JENKINS_API_TOKEN)"
        )
        logger.error(
            "   Pour générer un token: Jenkins > [Votre utilisateur] > Configure > Add new Token"
        )
        sys.exit(1)

    # Création du builder
    builder = JenkinsBackendBuilder(
        jenkins_url=args.url,
        username=args.username,
        api_token=args.token,
        job_name=args.job,
        timeout=args.timeout,
    )

    # Connexion
    if not builder.connect():
        logger.error("❌ Impossible de se connecter à Jenkins")
        sys.exit(1)

    # Affichage des infos du dernier build seulement
    if args.last_build_info:
        builder.get_last_build_info()
        sys.exit(0)

    # Lancement du build
    logger.info("=" * 50)
    build_result = builder.trigger_build(ref_to_build=args.ref, wait=args.wait)

    if build_result:
        logger.info("=" * 50)
        logger.info("🎯 Build lancé avec succès!")
        sys.exit(0)
    else:
        logger.error("=" * 50)
        logger.error("❌ Échec du lancement du build")
        sys.exit(1)


if __name__ == "__main__":
    main()
