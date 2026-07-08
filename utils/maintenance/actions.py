import logging

from utils.storage.redis import get_redis_client, maintenance_key_for_instance

logger = logging.getLogger("comparia.maintenance")


def maintenance_on(instance: str) -> None:
    """
    Enable maintenance mode for the given instance.

    Args:
        instance: Country portal to target (fr, da, ...)
    """
    get_redis_client().set(maintenance_key_for_instance(instance), "1")
    logger.info(f"Maintenance mode enabled for '{instance}'")


def maintenance_off(instance: str) -> None:
    """
    Disable maintenance mode for the given instance.

    Args:
        instance: Country portal to target (fr, da, ...)
    """
    get_redis_client().delete(maintenance_key_for_instance(instance))
    logger.info(f"Maintenance mode disabled for '{instance}'")


def maintenance_status(instance: str) -> None:
    """
    Show maintenance mode status for the given instance.

    Args:
        instance: Country portal to target (fr, da, ...)
    """
    enabled = get_redis_client().get(maintenance_key_for_instance(instance)) == "1"
    logger.info(f"'{instance}': {'enabled' if enabled else 'disabled'}")
