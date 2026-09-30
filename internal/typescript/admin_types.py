from backend.admin.router import (
    AdminLegalDocument,
    PublishLegalDocumentBody,
    UpdateLegalPresentationBody,
)
from utils.database.models.app_settings import AppSettingsPatch, AppSettingsPublic
from utils.database.models.auth import UserPublic, UserUpsert
from utils.database.models.llms import (
    LLMData,
    LLMEndpoint,
    LLMEndpointPublic,
    LLMLab,
    LLMLabPublic,
    LLMLicense,
)
from utils.database.models.prompt_check import PromptCheckPatch, PromptCheckStatus
from utils.database.models.publish import (
    AdminPublishDestination,
    AdminPublishDestinationsResponse,
    AdminPublishRun,
    AdminPublishStatus,
    PublishDestinationUpsert,
)
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
    VoteTagOrder,
    VoteTagUpdate,
)
