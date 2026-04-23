#!/usr/bin/env python3
"""
Classe de base abstraite pour tous les triggers Jenkins
"""

import argparse
import logging
import os
import sys
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

try:
    import jenkins
except ImportError:
    print("ERREUR: La librairie 'python-jenkins' n'est pas installée.")
    print("Installez-la avec: pip install python-jenkins")
    sys.exit(1)

logger = logging.getLogger(__name__)


class JenkinsJobTrigger(ABC):
    """Classe de base abstraite pour déclencher des jobs Jenkins"""

    def __init__(
        self,
        jenkins_url: str,
        username: str,
        api_token: str,
        job_name: str,
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

    @abstractmethod
    def trigger(self, wait: bool = False, **kwargs) -> Optional[int]:
        """
        Lance le job Jenkins

        Args:
            wait: Si True, attend la fin du job
            **kwargs: Paramètres spécifiques au job

        Returns:
            Numéro du build lancé ou None en cas d'erreur
        """

    @abstractmethod
    def get_job_parameters(self, **kwargs) -> Dict[str, Any]:
        """Retourne les paramètres du job Jenkins"""

    def _execute_job(
        self, parameters: Dict[str, Any], wait: bool, action_name: str = "job"
    ) -> Optional[int]:
        """
        Logique commune d'exécution d'un job

        Args:
            parameters: Paramètres du job
            wait: Attendre la fin du job
            action_name: Nom de l'action (pour les logs)

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

            # Lance le job
            params_str = ", ".join(f"{k}='{v}'" for k, v in parameters.items())
            logger.info(f"Lancement du {action_name} avec {params_str}...")
            queue_number = self.server.build_job(self.job_name, parameters=parameters)

            logger.info(f"Build en queue: #{queue_number}")

            if wait:
                build_number = self._wait_for_build_start(queue_number)
                if build_number:
                    logger.info(f"Build #{build_number} démarré")
                    success = self._monitor_build(build_number)
                    return build_number if success else None
            else:
                logger.info(
                    f"✅ {action_name.capitalize()} lancé (queue #{queue_number}). "
                    "Utilisez --wait pour suivre la progression."
                )

            return queue_number

        except jenkins.JenkinsException as e:
            logger.error(f"❌ Erreur Jenkins lors du {action_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Erreur lors du lancement du {action_name}: {e}")
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

    def _monitor_build(self, build_number: int) -> bool:
        """Surveille la progression d'un build et retourne True si succès"""
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

                    # URL du build
                    build_url = build_info.get("url", "N/A")
                    logger.info(f"   URL: {build_url}")

                    if result == "SUCCESS":
                        logger.info(
                            f"✅ Build #{build_number} réussi! (durée: {duration:.0f}s)"
                        )
                        return True
                    else:
                        logger.error(
                            f"❌ Build #{build_number} échoué: {result} (durée: {duration:.0f}s)"
                        )
                        return False

            except Exception as e:
                logger.error(f"❌ Erreur lors de la surveillance: {e}")
                return False

    @staticmethod
    def create_argument_parser(
        description: str,
        epilog: str,
        default_job_name: str,
    ):
        """Crée un parser d'arguments avec les options communes"""
        parser = argparse.ArgumentParser(
            description=description,
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=epilog,
        )

        # Arguments communs
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
            default=default_job_name,
            help=f"Nom du job Jenkins (défaut: {default_job_name})",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=30,
            help="Timeout de connexion en secondes (défaut: 30)",
        )
        parser.add_argument("--verbose", "-v", action="store_true", help="Mode verbeux")

        return parser

    @staticmethod
    def validate_common_args(args):
        """Valide les arguments communs et configure le logging"""
        # Configuration du niveau de log
        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)

        # Validation
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

    def execute_main_workflow(
        self, trigger_result: Optional[int], success_message: str, error_message: str
    ):
        """Workflow standard de fin d'exécution"""
        if trigger_result:
            logger.info("=" * 50)
            logger.info(f"🎯 {success_message}")
            sys.exit(0)
        else:
            logger.error("=" * 50)
            logger.error(f"❌ {error_message}")
            sys.exit(1)
