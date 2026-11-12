from typing import Literal, get_args

LLMArchKind = Literal[
    "moe", "matformer", "dense", "maybe-moe", "maybe-matformer", "maybe-dense", "na"
]
LLMLicenseKind = Literal["proprietary", "open-weights", "open-source"]
LLMStatus = Literal["archived", "disabled", "enabled"]

# Here rather than next to their scales in backend/llms/models.py: selection
# mode filters name them, and those live with the database models.
SizeClass = Literal["XS", "S", "M", "L", "XL"]
SIZE_CLASSES: tuple[SizeClass, ...] = get_args(SizeClass)
EnergyClass = Literal["A", "B", "C", "D", "E", "F"]
ENERGY_CLASSES: tuple[EnergyClass, ...] = get_args(EnergyClass)
