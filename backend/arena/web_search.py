import logging

from linkup import LinkupClient, LinkupSearchResults, LinkupSearchTextResult

from backend.config import settings

logger = logging.getLogger("languia")


async def search_web(content: str) -> list[LinkupSearchTextResult] | None:
    """
    Search the web using Linkup.

    Returns None if no results found or if API key is not configured.
    """
    if not settings.LINKUP_API_KEY:
        logger.error("LINKUP_API_KEY not configured, skipping web search")
        return None

    try:
        client = LinkupClient(api_key=settings.LINKUP_API_KEY)
        response: LinkupSearchResults = await client.async_search(
            query=content,
            depth="standard",
            output_type="searchResults",
            include_images=False,
        )
    except Exception:
        logger.exception("Linkup web search failed")
        return None

    return [
        result
        for result in response.results
        # Only use text results (skip images)
        if result.type == "text" and result.content
    ]
