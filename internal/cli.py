import logging

from cyclopts import App

from utils.logger import configure_logger

from .archs import generate_archs_i18n, generate_archs_json_schema
from .i18n import clean_locales
from .i18n_schemas import generate_admin_schemas_i18n
from .typescript.generate_frontend_types import (
    generate_frontend_constants,
    generate_frontend_types,
)


def types():
    """
    Generate types, constants and JSON schemas.
    """
    generate_frontend_types()
    generate_frontend_constants()
    generate_archs_json_schema()


def i18n():
    """
    Generate related i18n files.
    """
    clean_locales()
    generate_archs_i18n()
    generate_admin_schemas_i18n()


def run_all():
    """
    Global maintenance command (types + i18n).
    """
    types()
    i18n()


cli_internal = App(name="internal", help="Project utilities.")
cli_internal.command(types, name="types")
cli_internal.command(i18n, name="i18n")
cli_internal.command(run_all, name="all")

if __name__ == "__main__":
    configure_logger(logging.getLogger("comparia"))
    cli_internal()
