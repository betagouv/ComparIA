import uuid

from fastapi import APIRouter, HTTPException, status

from backend.auth.dependencies import RequiredAdmin
from backend.survey.services import (
    SurveyOptionUnknownError,
    SurveyOrderMismatchError,
    SurveyQuestionInUseError,
    SurveyQuestionLabelUnusableError,
    SurveyQuestionNotFoundError,
    admin_list,
    create_question,
    delete_question,
    reorder,
    set_archived,
    update_question,
)
from utils.database.models.survey import (
    AdminSurveyQuestion,
    AdminSurveyResponse,
    SurveyQuestionArchiveUpdate,
    SurveyQuestionCreate,
    SurveyQuestionOrder,
    SurveyQuestionUpdate,
)
from utils.database.session import get_session

router = APIRouter(prefix="/survey", tags=["survey"])

_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="Survey question not found"
)
_LABEL_UNUSABLE = HTTPException(
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    detail="A label must contain at least one letter or digit",
)
_OPTION_UNKNOWN = HTTPException(
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    detail="One of the options given does not belong to this question",
)
_ORDER_MISMATCH = HTTPException(
    status_code=status.HTTP_409_CONFLICT,
    detail="The order has to list every question for this trigger, and nothing else",
)
_IN_USE = HTTPException(
    status_code=status.HTTP_409_CONFLICT,
    detail="Answers already carry this question, archive it instead of deleting it",
)


async def _admin_question(session, question_id: uuid.UUID) -> AdminSurveyQuestion:
    """
    Re-reads the question through `admin_list` rather than hand-mapping the
    row a write returns: the option answer_count and respondent_count are
    aggregate reads that already live in `admin_list`, and duplicating that
    logic here would be a second place for it to drift out of sync.
    """
    response = await admin_list(session)
    for question in response.questions:
        if question.id == question_id:
            return question
    raise _NOT_FOUND


@router.get("", response_model=AdminSurveyResponse)
async def get_survey() -> AdminSurveyResponse:
    async with get_session() as session:
        return await admin_list(session)


@router.post(
    "", response_model=AdminSurveyQuestion, status_code=status.HTTP_201_CREATED
)
async def add_survey_question(
    body: SurveyQuestionCreate, current_user: RequiredAdmin
) -> AdminSurveyQuestion:
    async with get_session() as session:
        try:
            question = await create_question(session, body)
        except SurveyQuestionLabelUnusableError:
            raise _LABEL_UNUSABLE
        except SurveyOptionUnknownError:
            raise _OPTION_UNKNOWN
        return await _admin_question(session, question.id)


@router.put("/order", status_code=status.HTTP_204_NO_CONTENT)
async def set_survey_order(
    body: SurveyQuestionOrder, current_user: RequiredAdmin
) -> None:
    async with get_session() as session:
        try:
            await reorder(session, body)
        except SurveyOrderMismatchError:
            raise _ORDER_MISMATCH


@router.put("/{question_id}", response_model=AdminSurveyQuestion)
async def edit_survey_question(
    question_id: uuid.UUID, body: SurveyQuestionUpdate, current_user: RequiredAdmin
) -> AdminSurveyQuestion:
    async with get_session() as session:
        try:
            await update_question(session, question_id, body)
        except SurveyQuestionNotFoundError:
            raise _NOT_FOUND
        except SurveyQuestionLabelUnusableError:
            raise _LABEL_UNUSABLE
        except SurveyOptionUnknownError:
            raise _OPTION_UNKNOWN
        return await _admin_question(session, question_id)


@router.patch("/{question_id}", response_model=AdminSurveyQuestion)
async def patch_survey_question(
    question_id: uuid.UUID,
    body: SurveyQuestionArchiveUpdate,
    current_user: RequiredAdmin,
) -> AdminSurveyQuestion:
    async with get_session() as session:
        try:
            await set_archived(
                session,
                question_id,
                archived=body.archived,
                admin_id=current_user.id,
            )
        except SurveyQuestionNotFoundError:
            raise _NOT_FOUND
        return await _admin_question(session, question_id)


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_survey_question(
    question_id: uuid.UUID, current_user: RequiredAdmin
) -> None:
    async with get_session() as session:
        try:
            await delete_question(session, question_id)
        except SurveyQuestionNotFoundError:
            raise _NOT_FOUND
        except SurveyQuestionInUseError:
            raise _IN_USE
