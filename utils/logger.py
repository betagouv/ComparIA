import logging
from typing import Any

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


def log_pydantic_parsed_errors(
    logger: logging.Logger, errors: dict[str, list[dict[str, Any]]]
) -> None:
    for name, errs in errors.items():
        logger.error(
            f"\nError in {name}:\n"
            + "\n".join(
                [
                    f"- {err['key']}: [type={err['type']}] {err['msg']} (input={err['input'] if err['type'] != 'missing' else None})"
                    for err in errs
                ]
            )
        )
