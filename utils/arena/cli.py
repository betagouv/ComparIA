import logging

from cyclopts import App

from utils.logger import configure_logger

from .actions import limits_reset, limits_show
from .calibrate import limits_calibrate

cli_arena = App(name="arena", help="Arena utilities.")
cli_limits = App(name="limits", help="Model allowances of one session or IP.")
cli_limits.command(limits_show, name="show")
cli_limits.command(limits_reset, name="reset")
cli_limits.command(limits_calibrate, name="calibrate")
cli_arena.command(cli_limits)


if __name__ == "__main__":
    configure_logger(logging.getLogger("comparia"))
    cli_arena()
