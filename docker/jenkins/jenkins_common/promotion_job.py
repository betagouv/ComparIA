#!/usr/bin/env python3
"""
Trigger pour job de promotion d'images
"""

from typing import Optional, Dict, Any
from .base import JenkinsJobTrigger


class JenkinsPromotionJobTrigger(JenkinsJobTrigger):
    """Classe pour lancer la promotion d'images sur Jenkins"""

    def trigger(
        self,
        source_tag: str,
        target_tag: str,
        wait: bool = True
    ) -> Optional[int]:
        """
        Lance la promotion d'images

        Args:
            source_tag: Tag source (commit hash dans atnum)
            target_tag: Tag cible (commit hash dans atnum-release)
            wait: Si True, attend la fin de la promotion

        Returns:
            Numéro du build lancé ou None en cas d'erreur
        """
        parameters = self.get_job_parameters(
            source_tag=source_tag,
            target_tag=target_tag
        )
        return self._execute_job(parameters, wait, action_name="promotion")

    def get_job_parameters(
        self,
        source_tag: str,
        target_tag: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Retourne les paramètres du job de promotion"""
        return {
            "SOURCE_TAG": source_tag,
            "TARGET_TAG": target_tag
        }
