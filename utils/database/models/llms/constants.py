from typing import Literal

LLMArchKind = Literal["moe", "matformer", "dense", "maybe-moe", "maybe-dense", "na"]
LLMLicenseKind = Literal["proprietary", "open-weights", "open-source"]
LLMStatus = Literal["archived", "disabled", "enabled"]
