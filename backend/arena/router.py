import logging

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from backend.config import (
    BLIND_MODE_INPUT_CHAR_LEN_LIMIT,
    DEFAULT_SELECTION_MODE,
    SelectionMode,
)
from backend.errors import Errors
from backend.language_models.data import get_models
from backend.session import is_ratelimited
from backend.utils.user import get_ip

logger = logging.getLogger("languia")

router = APIRouter(
    prefix="/arena",
    tags=["arena"],
)


def assert_not_rate_limited(request: Request) -> None:
    ip = get_ip(request)

    if is_ratelimited(ip):
        logger.error(
            f"Too much text submitted to pricey models for ip {ip}",
            extra={"request": request},
        )
        raise Exception(Errors.RATE_LIMITED.name)


class AddFirstTextBody(BaseModel):
    prompt_value: str = Field(min_length=1, max_length=BLIND_MODE_INPUT_CHAR_LEN_LIMIT)
    mode: SelectionMode = DEFAULT_SELECTION_MODE
    custom_models_selection: tuple[str] | tuple[str, str] | None = None


@router.post("/add_first_text", dependencies=[Depends(assert_not_rate_limited)])
def add_first_text(args: AddFirstTextBody, locale: str, request: Request):
    """
    Process user's first message and initiate model comparison.

    This is the main handler for the send button click. It:
    1. Extracts user input and mode selection
    2. Selects two models to compare
    3. Calls both models in parallel
    4. Handles rate limiting and validation

    Args:
        app_state_scoped: Current app state
        model_dropdown_scoped: User's model selection (mode + custom choices)
        locale: Country portal (FR, DA, etc.)
        request: Gradio request for logging

    Returns:
        tuple: Updated UI components (conversations, chatbot, app_state, etc.)

    Raises:
        gr.Error: If input validation fails or rate limiting triggered
    """
    logger.info(f"locale: {locale}", extra={"request": request})
    logger.info("chose mode: " + args.mode, extra={"request": request})
    logger.info(
        "custom_models_selection: " + str(args.custom_models_selection),
        extra={"request": request},
    )

    models = get_models()
    model_a, model_b = models.pick_two(args.mode, args.custom_models_selection)
