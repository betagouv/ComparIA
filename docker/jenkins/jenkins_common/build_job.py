#!/usr/bin/env python3
"""
Trigger pour jobs de build Docker (backend/frontend)
"""

from typing import Optional, Dict, Any
from .base import JenkinsJobTrigger, logger


class JenkinsBuildJobTrigger(JenkinsJobTrigger):
    """Classe pour lancer des builds Docker sur Jenkins"""

    def trigger(
        self,
        ref_to_build: str = "develop",
        wait: bool = False
    ) -> Optional[int]:
        """
        Lance le build Docker

        Args:
            ref_to_build: Branche ou ref Git à builder
            wait: Si True, attend la fin du build

        Returns:
            Numéro du build lancé ou None en cas d'erreur
        """
        parameters = self.get_job_parameters(ref_to_build=ref_to_build)
        return self._execute_job(parameters, wait, action_name="build")

    def get_job_parameters(self, ref_to_build: str, **kwargs) -> Dict[str, Any]:
        """Retourne les paramètres du job de build"""
        return {"REF_TO_BUILD": ref_to_build}

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
