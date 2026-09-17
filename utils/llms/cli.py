import logging

from cyclopts import App

from utils.logger import configure_logger

from .actions import llms_export, llms_import

cli_llms = App(name="llms", help="LLMs data utilities.")
cli_llms.command(llms_export, name="export")
cli_llms.command(llms_import, name="import")


if __name__ == "__main__":
    configure_logger(logging.getLogger("comparia"))
    cli_llms()
