import logging

from fastapi import APIRouter, Depends

from backend.admin.activity import admin_activity_router
from backend.admin.dataset_check import router as admin_dataset_check_router
from backend.admin.legal import router as admin_legal_router
from backend.admin.llms import admin_llms_router
from backend.admin.prompt_check import router as admin_prompt_check_router
from backend.admin.publishing import router as admin_publishing_router
from backend.admin.settings import router as admin_settings_router
from backend.admin.suggestions import router as admin_suggestions_router
from backend.admin.survey import admin_survey_router
from backend.admin.tools import admin_tools_router
from backend.admin.users import admin_users_router
from backend.admin.vote_tags import admin_vote_tags_router
from backend.auth.dependencies import require_admin

logger = logging.getLogger("languia")

router = APIRouter(
    prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)]
)

router.include_router(admin_activity_router)
router.include_router(admin_dataset_check_router)
router.include_router(admin_legal_router)
router.include_router(admin_llms_router)
router.include_router(admin_prompt_check_router)
router.include_router(admin_publishing_router)
router.include_router(admin_settings_router)
router.include_router(admin_suggestions_router)
router.include_router(admin_survey_router)
router.include_router(admin_tools_router)
router.include_router(admin_users_router)
router.include_router(admin_vote_tags_router)
