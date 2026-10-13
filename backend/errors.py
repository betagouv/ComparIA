from typing import TYPE_CHECKING, Literal

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

from utils.database.models import BotPos, ErrorCode

if TYPE_CHECKING:
    from backend.arena.models import LimitKey, LimitRefusal


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


class TotpSetupRequiredError(HTTPException):
    """An admin who has not enrolled an authenticator yet."""

    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN, detail="totp_setup_required"
        )


class TotpSecretUnreadableError(HTTPException):
    """An enrolled secret that no configured encryption key opens. Not the
    caller's doing: the operator dropped a key too early."""

    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="totp_secret_unreadable",
        )


class RoleRequiredError(HTTPException):
    def __init__(self, role: str = "admin") -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN, detail=f"{role}_required"
        )


class LogoRejectedError(HTTPException):
    """The upload is not a logo we can store: wrong type, too big, or not an image."""

    def __init__(
        self, reason: Literal["logo_unsupported_type", "logo_too_large", "logo_invalid"]
    ) -> None:
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=reason)


class ActivityQueryTimeoutError(HTTPException):
    """An admin activity query that ran past its statement timeout. The admin
    can narrow the period or the filters and try again."""

    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="activity_query_timeout",
        )


class LimitReachedError(HTTPException):
    """A message refused because a limit on model use was reached. The body
    says which limit and when it lifts, see `limit_reached_handler`."""

    def __init__(self, key: "LimitKey", limit: "LimitRefusal") -> None:
        headers = (
            {"Retry-After": str(limit.resets_in)}
            if limit.resets_in is not None
            else None
        )
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=key, headers=headers
        )
        self.limit = limit


async def limit_reached_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, LimitReachedError)
    return JSONResponse(
        {"detail": exc.detail, "limit": exc.limit.model_dump(mode="json")},
        status_code=exc.status_code,
        headers=exc.headers,
    )
