import logging

from rich.logging import RichHandler


def configure_logger(logger: logging.Logger) -> logging.Logger:
    logger.setLevel(logging.DEBUG)
    console_handler = RichHandler()
    console_handler.setFormatter(
        logging.Formatter(
            "%(name)s - %(funcName)s - %(message)s",
            datefmt="|",
        )
    )
    logger.addHandler(console_handler)

    return logger
