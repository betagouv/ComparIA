from enum import StrEnum


class Errors(StrEnum):
    RATE_LIMITED = "rate_limited"  # "Vous avez trop sollicité les modèles parmi les plus onéreux, veuillez réessayer dans quelques heures. Vous pouvez toujours solliciter des modèles plus petits."
