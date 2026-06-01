import logging
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status

from backend.arena.session import (
    ComparisonMetadata,
    is_ratelimited,
    retreive_comparison_metadata,
)
from backend.utils.user import get_ip

logger = logging.getLogger("languia")


def assert_not_rate_limited(request: Request) -> None:
    """Dependency to check rate limiting based on IP address."""
    ip = get_ip(request)

    if is_ratelimited(ip):
        logger.error(
            f"Too much text submitted to pricey models for ip {ip}",
            extra={"request": request},
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Vous avez trop sollicité les modèles parmi les plus onéreux, veuillez réessayer dans quelques heures. Vous pouvez toujours solliciter des modèles plus petits.",
        )


RateLimitGuard = Depends(assert_not_rate_limited)


def get_comparison_id(id: UUID = Header(..., alias="X-Comparison-Id")) -> UUID:
    """
    Dependency to extract and validate comparison id from headers.

    Args:
        id: Comparison identifier from X-Comparison-Id header

    Returns:
        str: Validated comparison id

    Raises:
        HTTPException: If comparison id is missing or invalid
    """
    if not id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing comparison id"
        )
    return id


def get_comparison_metadata(
    id: UUID = Depends(get_comparison_id),
) -> ComparisonMetadata:
    try:
        metadata = retreive_comparison_metadata(id)
    except Exception as e:
        # FIXME raise different errors depending on problem
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Comparison '{id}' couldn't be found or parsed: {str(e)}",
        )

    # For any arena view, raise error if chat responses are not yet finished
    if metadata.is_streaming:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Veuillez attendre la fin de la réponse des modèles.",
        )

    return metadata


ComparisonMetadataAnno = Annotated[ComparisonMetadata, Depends(get_comparison_metadata)]
