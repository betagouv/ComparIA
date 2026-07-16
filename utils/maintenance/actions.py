import logging
from datetime import datetime

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from backend.config import settings
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


def maintenance_disconnect_db() -> None:
    """
    Terminate other open connections to the database targeted by COMPARIA_DB_URI.

    Only affects that database, not other databases on the same Postgres
    server. Which instance this hits depends on which instance's env
    (COMPARIA_DB_URI) is loaded when running this command.
    """
    if not settings.COMPARIA_DB_URI:
        raise Exception("COMPARIA_DB_URI is not set")

    engine = create_engine(settings.COMPARIA_DB_URI)
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = current_database() AND pid <> pg_backend_pid()"
                )
            )
            terminated = len(result.fetchall())
            conn.commit()
        logger.info(f"Terminated {terminated} other connection(s) to the database")
    finally:
        engine.dispose()


def maintenance_backup_db() -> None:
    """
    Create a backup copy of the database targeted by COMPARIA_DB_URI.

    Runs CREATE DATABASE <dbname>_backup_<timestamp> TEMPLATE <dbname>. Postgres
    requires no open connections to the source database for this to succeed
    (see disconnect-db), and the connection issuing the command must not itself
    be connected to the source database, so this connects to 'postgres' instead.
    """
    if not settings.COMPARIA_DB_URI:
        raise Exception("COMPARIA_DB_URI is not set")

    url = make_url(settings.COMPARIA_DB_URI)
    source_db = url.database
    if not source_db:
        raise Exception("COMPARIA_DB_URI has no database name")

    backup_db = f"{source_db}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    engine = create_engine(url.set(database="postgres"))
    try:
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.execute(text(f'CREATE DATABASE "{backup_db}" TEMPLATE "{source_db}"'))
        logger.info(f"Created backup database '{backup_db}' from '{source_db}'")
    finally:
        engine.dispose()
