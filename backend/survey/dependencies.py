from fastapi import HTTPException, Request, status

from backend.auth.dependencies import OptionalUser
from backend.survey.services import signup_questions_answered


async def require_answered_questions(user: OptionalUser, request: Request):
    """
    Route guard for other requests than GET asserting logged user answered survey questions.
    """
    if request.method != "GET" and user is not None:
        if not await signup_questions_answered(
            user_id=user.id, anonymous_user_hash=None
        ):

            raise HTTPException(
                status.HTTP_428_PRECONDITION_REQUIRED,
                detail="require_answered_questions",
            )
