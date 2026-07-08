import logging

from cyclopts import App

from utils.logger import configure_logger

from .actions import (
    maintenance_disconnect_db,
    maintenance_off,
    maintenance_on,
    maintenance_status,
)

cli_maintenance = App(name="maintenance", help="Maintenance mode utilities.")
cli_maintenance.command(maintenance_on, name="on")
cli_maintenance.command(maintenance_off, name="off")
cli_maintenance.command(maintenance_status, name="status")
cli_maintenance.command(maintenance_disconnect_db, name="disconnect-db")


if __name__ == "__main__":
    configure_logger(logging.getLogger("comparia"))
    cli_maintenance()
