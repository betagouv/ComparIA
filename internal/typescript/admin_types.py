from backend.admin.router import (
    AdminLegalDocument,
    PublishLegalDocumentBody,
    UpdateLegalPresentationBody,
)
from utils.database.models.app_settings import AppSettingsPatch, AppSettingsPublic
from utils.database.models.auth import UserPublic, UserUpsert
from utils.database.models.llms import LLMData, LLMEndpoint, LLMLab, LLMLicense
from utils.database.models.suggestion import (
    AdminSuggestion,
    AdminSuggestionCategory,
    SuggestionArchiveUpdate,
    SuggestionCategoryCreate,
    SuggestionCreate,
)
from utils.database.models.vote_tag import (
    AdminVoteTag,
    AdminVoteTagsResponse,
    VoteTagArchiveUpdate,
    VoteTagCreate,
    VoteTagMove,
    VoteTagUpdate,
)
