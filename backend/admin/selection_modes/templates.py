"""
Starting points for a new selection mode. Data only: the admin loads one into
the create form and edits it before saving. Each template's title and
description are in the frontend messages, under its id.
"""

from backend.admin.selection_modes.models import (
    SelectionModeDraft,
    SelectionModeTemplate,
)
from utils.database.models import ModelFilter

TEMPLATES = [
    SelectionModeTemplate(
        id="no-tools-expert",
        mode=SelectionModeDraft(
            key="legal",
            label={"en": "Legal", "fr": "Juridique"},
            description={
                "en": "Two models chosen for legal questions",
                "fr": "Deux modèles choisis pour les questions juridiques",
            },
            icon="i-ri-scales-3-line",
            pool_a=ModelFilter(tags=["legal"]),
            tools_policy="none",
        ),
    ),
    SelectionModeTemplate(
        id="open-weights",
        mode=SelectionModeDraft(
            key="open-weights",
            label={"en": "Open weights", "fr": "Modèles ouverts"},
            description={
                "en": "Two models with public weights, chosen randomly",
                "fr": "Deux modèles aux poids publics, tirés au hasard",
            },
            icon="i-ri-open-source-line",
            pool_a=ModelFilter(public_weights=True),
        ),
    ),
    SelectionModeTemplate(
        id="european",
        mode=SelectionModeDraft(
            key="european",
            label={"en": "Hostable in Europe", "fr": "Hébergeables en Europe"},
            description={
                "en": "Two models that can run in the EU",
                "fr": "Deux modèles qui peuvent tourner dans l'UE",
            },
            icon="i-ri-map-pin-line",
            pool_a=ModelFilter(eu_hostable=True),
        ),
    ),
    SelectionModeTemplate(
        id="small-vs-big",
        mode=SelectionModeDraft(
            key="small-vs-big",
            label={"en": "Small vs big", "fr": "Petit contre grand"},
            description={
                "en": "One small model against one big model",
                "fr": "Un petit modèle contre un grand",
            },
            icon="i-ri-ruler-line",
            pool_a=ModelFilter(params_min=100),
            pool_b=ModelFilter(params_max=60),
        ),
    ),
    SelectionModeTemplate(
        id="frugal",
        mode=SelectionModeDraft(
            key="frugal",
            label={"en": "Frugal", "fr": "Frugal"},
            description={
                "en": "Two models that use little energy",
                "fr": "Deux modèles qui consomment peu",
            },
            icon="i-ri-leaf-line",
            pool_a=ModelFilter(energy_classes=["A", "B"]),
        ),
    ),
    SelectionModeTemplate(
        id="champion",
        mode=SelectionModeDraft(
            key="champion",
            label={"en": "Champion", "fr": "Champion"},
            description={
                "en": "Can a challenger beat the champion?",
                "fr": "Un challenger battra-t-il le champion ?",
            },
            icon="i-ri-trophy-line",
            pool_b=ModelFilter(),
        ),
    ),
    SelectionModeTemplate(
        id="new-models-first",
        mode=SelectionModeDraft(
            key="new-models",
            label={"en": "New models", "fr": "Nouveaux modèles"},
            description={
                "en": "Two models, the least tested first",
                "fr": "Deux modèles, les moins testés d'abord",
            },
            icon="i-ri-sparkling-line",
            sampling="fewer_votes",
        ),
    ),
    SelectionModeTemplate(
        id="fixed-pair",
        mode=SelectionModeDraft(
            key="workshop",
            label={"en": "Workshop", "fr": "Atelier"},
            description={
                "en": "The two models of the workshop",
                "fr": "Les deux modèles de l'atelier",
            },
            icon="i-ri-group-line",
        ),
    ),
    SelectionModeTemplate(
        id="visitor-picks",
        mode=SelectionModeDraft(
            key="pick-in-pool",
            label={"en": "Your selection", "fr": "Votre sélection"},
            description={
                "en": "Will you recognise the models you chose?",
                "fr": "Reconnaîtrez-vous les modèles que vous avez choisis ?",
            },
            icon="i-ri-search-line",
            visitor_picks=2,
        ),
    ),
    SelectionModeTemplate(
        id="web-search",
        mode=SelectionModeDraft(
            key="web-search",
            label={"en": "With web search", "fr": "Avec recherche web"},
            description={
                "en": "Two models that search the web",
                "fr": "Deux modèles qui cherchent sur le web",
            },
            icon="i-ri-global-line",
            tools_policy="forced",
            tool_keys=["web_search"],
        ),
    ),
    SelectionModeTemplate(
        id="specialised-vs-generalist",
        mode=SelectionModeDraft(
            key="specialised-vs-generalist",
            label={
                "en": "Specialist vs generalist",
                "fr": "Spécialiste contre généraliste",
            },
            description={
                "en": "A specialised system against a general model that searches the web",
                "fr": "Un système spécialisé contre un modèle généraliste qui cherche sur le web",
            },
            icon="i-ri-stethoscope-line",
            pool_a=ModelFilter(arena_tools=False, tags=["specialised"]),
            pool_b=ModelFilter(arena_tools=True),
            tools_policy="forced",
            tool_keys=["web_search"],
        ),
    ),
    SelectionModeTemplate(
        id="speciality-set",
        mode=SelectionModeDraft(
            key="penal-law",
            label={"en": "Penal law", "fr": "Droit pénal"},
            description={
                "en": "Two models chosen for penal law",
                "fr": "Deux modèles choisis pour le droit pénal",
            },
            icon="i-ri-scales-3-line",
            pool_a=ModelFilter(tags=["penal-law"]),
            tools_policy="none",
        ),
    ),
]
