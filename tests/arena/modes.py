"""
The four modes the migration seeds, for arena tests that run without a
database. Kept in step with the seed in
utils/database/alembic/versions/da69fc86f2ea_add_selection_modes_and_llm_fields.py.
"""

from backend.selection_modes.services import ModeUnavailableError
from utils.database.models import ModelFilter, SelectionModeBase

SEEDED = {
    mode.key: mode
    for mode in [
        SelectionModeBase(
            key="random", label={"en": "Random"}, icon="i-ri-dice-line", is_default=True
        ),
        SelectionModeBase(
            key="small-models",
            label={"en": "Frugal"},
            icon="i-ri-leaf-line",
            pool_a=ModelFilter(params_max=60),
            position=1,
        ),
        SelectionModeBase(
            key="big-vs-small",
            label={"en": "David vs Goliath"},
            icon="i-ri-ruler-line",
            pool_a=ModelFilter(params_min=100),
            pool_b=ModelFilter(params_max=60),
            position=2,
        ),
        SelectionModeBase(
            key="custom",
            label={"en": "Manual selection"},
            icon="i-ri-search-line",
            visitor_picks=2,
            position=3,
        ),
    ]
}


async def resolve_seeded_mode(key, _locale=None, _cohorts=None) -> SelectionModeBase:
    """Stands in for `resolve_mode`, which reads the modes from the database."""
    if key is None:
        return SEEDED["random"]
    if key not in SEEDED:
        raise ModeUnavailableError(key)
    return SEEDED[key]


async def seeded_modes() -> list[SelectionModeBase]:
    """Stands in for `get_selection_modes`, which reads the database."""
    return list(SEEDED.values())
