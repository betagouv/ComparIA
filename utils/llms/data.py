from pydantic import BaseModel

from utils.database.models.llms import LLMDataUpsert, LLMLabUpsert, LLMLicenseUpsert


class LLMImportData(BaseModel):
    licenses: list[LLMLicenseUpsert]
    labs: list[LLMLabUpsert]
    llms: list[LLMDataUpsert]
