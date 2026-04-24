#!/usr/bin/env python3
"""
Trigger pour jobs de déploiement (dev/stg/prd)
"""

from typing import Any, Dict, Optional

from .base import JenkinsJobTrigger


class JenkinsDeployJobTrigger(JenkinsJobTrigger):
    """Classe pour lancer des déploiements sur Jenkins"""

    def trigger(
        self, image_tag: str, force_delete: bool = False, wait: bool = False
    ) -> Optional[int]:
        """
        Lance le déploiement

        Args:
            image_tag: Tag de l'image (commit hash)
            force_delete: Forcer la suppression des ressources avant déploiement
            wait: Si True, attend la fin du déploiement

        Returns:
            Numéro du build lancé ou None en cas d'erreur
        """
        parameters = self.get_job_parameters(
            image_tag=image_tag, force_delete=force_delete
        )
        return self._execute_job(parameters, wait, action_name="déploiement")

    def get_job_parameters(
        self, image_tag: str, force_delete: bool, **kwargs
    ) -> Dict[str, Any]:
        """Retourne les paramètres du job de déploiement"""
        return {"IMAGE_TAG": image_tag, "FORCE_DELETE": force_delete}
