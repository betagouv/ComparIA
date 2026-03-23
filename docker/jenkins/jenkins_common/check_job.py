#!/usr/bin/env python3
"""
Trigger pour jobs de vérification d'images
"""

from typing import Optional, Dict, Any
from .base import JenkinsJobTrigger


class JenkinsCheckJobTrigger(JenkinsJobTrigger):
    """Classe pour lancer la vérification d'images sur Jenkins"""

    def trigger(
        self,
        commit_hash: str,
        wait: bool = True
    ) -> Optional[int]:
        """
        Lance la vérification des images

        Args:
            commit_hash: Hash du commit (tag de l'image)
            wait: Si True, attend la fin de la vérification

        Returns:
            Numéro du build lancé ou None en cas d'erreur
        """
        parameters = self.get_job_parameters(commit_hash=commit_hash)
        return self._execute_job(parameters, wait, action_name="vérification")

    def get_job_parameters(self, commit_hash: str, **kwargs) -> Dict[str, Any]:
        """Retourne les paramètres du job de vérification"""
        return {"COMMIT_HASH": commit_hash}
