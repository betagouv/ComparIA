import logging

from linkup import LinkupClient, LinkupSearchResults, LinkupSearchTextResult

from backend.config import WEB_SEARCH_INTRO, settings

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


def merge_web_search_with_content(
    content: str, web_search_results: list[LinkupSearchTextResult]
) -> str:
    return "\n\n".join(
        [
            content,
            WEB_SEARCH_INTRO,
            "\n\n---\n\n".join(
                [
                    f"Source: {result.name} ({result.url})\n{result.content}".strip()
                    for result in web_search_results
                ]
            ),
        ]
    )
