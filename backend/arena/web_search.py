import logging

from linkup import LinkupClient

from backend.config import settings

logger = logging.getLogger("languia")


async def search_web(query: str) -> str | None:
    """
    Search the web using Linkup and return formatted context string.

    Returns None if no results found or if API key is not configured.
    """
    if not settings.LINKUP_API_KEY:
        logger.warning("LINKUP_API_KEY not configured, skipping web search")
        return None

    try:
        client = LinkupClient(api_key=settings.LINKUP_API_KEY)
        response = await client.async_search(
            query=query,
            depth="standard",
            output_type="searchResults",
            include_images=False,
        )
    except Exception:
        logger.exception("Linkup web search failed")
        return None

    if not response.results:
        return None

    context_parts = []
    for result in response.results:
        # Only use text results (skip images)
        if hasattr(result, "content") and result.content:
            source_line = f"Source: {result.name} ({result.url})" if result.url else ""
            context_parts.append(f"{source_line}\n{result.content}".strip())

    if not context_parts:
        return None

    return "\n\n---\n\n".join(context_parts)
