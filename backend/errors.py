from backend.arena.models import BotPos

# from enum import StrEnum
# TODO raise errors with error keys and add i18n on front
# class Errors(StrEnum):
#     RATE_LIMITED = "rate_limited"  # "Vous avez trop sollicité les modèles parmi les plus onéreux, veuillez réessayer dans quelques heures. Vous pouvez toujours solliciter des modèles plus petits."


class ContextTooLongError(ValueError):
    """Raised when the context window of a model is exceeded."""

    def __str__(self):
        return "Context too long."


class EmptyResponseError(RuntimeError):
    """Raised when a model API returns an empty response."""

    def __init__(self, response=None, *args: object) -> None:
        super().__init__(*args)
        self.response = response

    def __str__(self):
        msg = "Empty response"
        return msg


class ChatError(RuntimeError):
    """Raised when an error occurs during chat."""

    message: str
    pos: BotPos
    is_timeout: bool

    def __init__(self, message: str, pos: BotPos, is_timeout: bool = False) -> None:
        super().__init__(message)
        self.message = message
        self.pos = pos
        self.is_timeout = is_timeout

    def __str__(self):
        return self.message
