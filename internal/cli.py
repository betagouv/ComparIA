import logging

from cyclopts import App

from utils.logger import configure_logger

from .typescript.generate_frontend_types import (
    generate_frontend_constants,
    generate_frontend_types,
)

cli_internal = App(name="internal", help="Project utilities.")
cli_internal.command(generate_frontend_types, name="generate_types")
cli_internal.command(generate_frontend_constants, name="generate_constants")

if __name__ == "__main__":
    configure_logger(logging.getLogger("comparia"))
    cli_internal()
