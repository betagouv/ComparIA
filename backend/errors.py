from fastapi import HTTPException, status
from fastapi.responses import JSONResponse

from utils.database.models import BotPos, ErrorCode

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
    """Raised when an error occurs during chat.

    `message` is one of the fixed codes from `error_code()`, not the provider's
    own wording: it is sent to the browser and stored on the comparison, and a
    provider error string would tell a voter which model they are voting for.
    """

    message: ErrorCode
    pos: BotPos
    is_timeout: bool

    def __init__(
        self, message: ErrorCode, pos: BotPos, is_timeout: bool = False
    ) -> None:
        super().__init__(message)
        self.message = message
        self.pos = pos
        self.is_timeout = is_timeout

    def __str__(self):
        return self.message


class AnonymousRequiredError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="anonymous_required"
        )


class AuthRequiredError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="auth_required"
        )


# Used in middleware, can't raise HTTPException
AUTH_REQUIRED_RESPONSE = JSONResponse(
    {"detail": "auth_required"}, status_code=status.HTTP_401_UNAUTHORIZED
)


class RoleRequiredError(HTTPException):
    def __init__(self, role: str = "admin") -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN, detail=f"{role}_required"
        )
