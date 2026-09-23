from fastapi import HTTPException, Request, status

from backend.auth.dependencies import OptionalUser
from backend.survey.services import signup_questions_answered

# Arena writes that do not produce anything the answers describe. Claiming the
# conversations a visitor had before signing in only changes who owns them, and
# the sign-in form runs it before the questions, so gating it would lose the
# merge whenever the questions are closed unanswered.
UNGATED_ENDPOINTS = frozenset({"merge_comparisons"})


async def require_answered_questions(user: OptionalUser, request: Request):
    """
    Route guard for other requests than GET asserting logged user answered survey questions.
    """
    if request.method == "GET" or user is None:
        return
    route = request.scope.get("route")
    if getattr(route, "name", None) in UNGATED_ENDPOINTS:
        return
    if not await signup_questions_answered(user_id=user.id, anonymous_user_hash=None):
        raise HTTPException(
            status.HTTP_428_PRECONDITION_REQUIRED,
            detail="require_answered_questions",
        )
