import uuid

from fastapi import APIRouter, HTTPException, Query, status

from backend.auth.dependencies import OptionalUser, RequiredAnomymous
from backend.auth.services import get_current_terms_acceptance_version
from backend.survey.services import (
    SurveyOptionUnknownError,
    SurveyQuestionNotFoundError,
    list_questions,
    list_unanswered_questions_ids,
    my_answers,
    record_shown,
    submit_answers,
)
from utils.database.models.auth import User
from utils.database.models.survey import (
    PublicSurveyResponse,
    SurveyAnswerSubmit,
    SurveyDismiss,
)
from utils.database.session import get_session

router = APIRouter(prefix="/survey", tags=["survey"])


def _respondent(
    user: User | None, anonymous_user_hash: str
) -> tuple[uuid.UUID | None, str | None]:
    """Exactly one of the two identifies a respondent, mirroring how
    `Comparison` carries ownership: a signed-in user by id, everyone else by
    their anonymous session hash."""
    if user:
        return user.id, None
    return None, anonymous_user_hash


@router.get("/", response_model=PublicSurveyResponse)
async def get_questions(
    user: OptionalUser,
    anonymous_user_hash: RequiredAnomymous,
    locale: str = Query(default="fr"),
) -> PublicSurveyResponse:
    user_id, anon_hash = _respondent(user, anonymous_user_hash)
    questions = await list_questions(locale)
    never_answered_ids = await list_unanswered_questions_ids(locale, user_id, anon_hash)
    answers = await my_answers(locale, user_id, anon_hash)

    return PublicSurveyResponse(
        questions=questions, never_answered_ids=never_answered_ids, answers=answers
    )


@router.post("/answers", status_code=status.HTTP_204_NO_CONTENT)
async def post_answers(
    payload: SurveyAnswerSubmit,
    user: OptionalUser,
    anonymous_user_hash: RequiredAnomymous,
) -> None:
    terms_version = await get_current_terms_acceptance_version(
        user_id=user.id if user else None,
        anonymous_user_hash=anonymous_user_hash,
    )
    user_id, anon_hash = _respondent(user, anonymous_user_hash)
    async with get_session() as session:
        try:
            await submit_answers(session, payload, user_id, anon_hash, terms_version)
        except SurveyQuestionNotFoundError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Unknown survey question.",
            ) from error
        except SurveyOptionUnknownError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown survey option: {error}",
            ) from error
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
            ) from error
        await session.commit()


@router.post("/dismiss", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss(
    payload: SurveyDismiss,
    user: OptionalUser,
    anonymous_user_hash: RequiredAnomymous,
) -> None:
    """Closing the popup and declining it are the same thing: both count as a
    showing, recorded exactly like an actual display would be."""
    user_id, anon_hash = _respondent(user, anonymous_user_hash)
    async with get_session() as session:
        await record_shown(session, payload.question_ids, user_id, anon_hash)
        await session.commit()
