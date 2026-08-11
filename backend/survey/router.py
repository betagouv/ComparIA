import uuid

from fastapi import APIRouter, HTTPException, Query, status

from backend.auth.dependencies import OptionalUser, RequiredAnomymous
from backend.auth.services import get_current_terms_acceptance_version
from backend.survey.services import (
    SurveyOptionUnknownError,
    SurveyQuestionNotFoundError,
    list_questions,
    my_answers,
    questions_to_prompt,
    record_shown,
    submit_answers,
)
from utils.database.models.auth import User
from utils.database.models.survey import (
    MySurveyAnswersResponse,
    PublicSurveyQuestionsResponse,
    SurveyAnswerSubmit,
    SurveyDismiss,
    SurveyTrigger,
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


@router.get("/questions", response_model=PublicSurveyQuestionsResponse)
async def get_questions(
    trigger: SurveyTrigger,
    user: OptionalUser,
    anonymous_user_hash: RequiredAnomymous,
    locale: str = Query(default="fr"),
) -> PublicSurveyQuestionsResponse:
    async with get_session() as session:
        if trigger == "after_vote":
            user_id, anon_hash = _respondent(user, anonymous_user_hash)
            questions = await questions_to_prompt(
                session, trigger, locale, user_id, anon_hash
            )
        else:
            questions = await list_questions(session, trigger, locale)
    return PublicSurveyQuestionsResponse(questions=questions)


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


@router.get("/me", response_model=MySurveyAnswersResponse)
async def get_my_answers(
    user: OptionalUser,
    anonymous_user_hash: RequiredAnomymous,
    locale: str = Query(default="fr"),
) -> MySurveyAnswersResponse:
    user_id, anon_hash = _respondent(user, anonymous_user_hash)
    async with get_session() as session:
        answers = await my_answers(session, locale, user_id, anon_hash)
    return MySurveyAnswersResponse(answers=answers)
