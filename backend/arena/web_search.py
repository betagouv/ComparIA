"""
Web search function and cache utils.
"""

import json
import logging
from typing import Any, Final, cast
from urllib.parse import urlsplit

from linkup import LinkupClient, LinkupSearchResults, LinkupSearchTextResult

from backend.config import WEB_SEARCH_INTRO, settings
from utils.storage.redis import REDIS_WEB_SEARCH_KEY, get_redis_client, hash_content

logger = logging.getLogger("languia")

# How much of each result goes to the models, and is checked. A search answer
# needs a passage, not the page: past this, a result is a way to send the
# models text that no one typed into the prompt.
RESULT_CHARS: Final[int] = 3_000

# Hosts whose pages anyone writes in seconds and no search needs. A result from
# one is someone's chosen text, not a source.
PASTE_HOSTS: Final[frozenset[str]] = frozenset(
    {
        "paste.rs",
        "pastebin.com",
        "rentry.co",
        "rentry.org",
        "hastebin.com",
        "dpaste.org",
        "dpaste.com",
        "paste.ee",
        "pastes.dev",
        "termbin.com",
        "controlc.com",
        "justpaste.it",
        "0x0.st",
        "gist.githubusercontent.com",
    }
)


async def search_web(
    content: str, use_cache: bool = True
) -> list[LinkupSearchTextResult] | None:
    """
    Search the web using Linkup.

    Returns None if no results found or if API key is not configured.
    """
    if not settings.LINKUP_API_KEY:
        logger.error("LINKUP_API_KEY not configured, skipping web search")
        return None

    if use_cache:
        if cached_results := get_cached_web_search(content):
            return cached_results

    try:
        client = LinkupClient(api_key=settings.LINKUP_API_KEY)
        response: LinkupSearchResults = await client.async_search(
            query=content,
            depth="standard",
            output_type="searchResults",
            include_images=False,
        )
        results = [
            result
            for result in response.results
            # Only use text results (skip images)
            if result.type == "text" and result.content
        ]

        if use_cache:
            store_cached_search_results(content, results)

        return results

    except Exception:
        logger.exception("Linkup web search failed")
        return None


def _page_key(url: str) -> tuple[str, str]:
    """Host without `www.` and path without its trailing slash."""
    parts = urlsplit(url if "://" in url else f"//{url}")
    host = (parts.hostname or "").removeprefix("www.")
    return host, parts.path.rstrip("/")


def keep_search_results(
    prompt: str, results: list[LinkupSearchTextResult]
) -> list[LinkupSearchTextResult]:
    """
    Keep the results that are sources, cut to what an answer needs.

    Linkup reads the pages a prompt names, so a prompt listing links has the
    models read pages its author wrote, past every check on the prompt. Such
    pages are dropped, as are paste sites; a bare site name ("lemonde.fr") is
    still a search hint. What is left is cut to `RESULT_CHARS`.
    """
    lowered = prompt.lower()
    kept = []
    for result in results:
        host, path = _page_key(result.url)
        if host in PASTE_HOSTS or (path and f"{host}{path}".lower() in lowered):
            continue
        content = result.content or ""
        if len(content) > RESULT_CHARS:
            result = result.model_copy(update={"content": content[:RESULT_CHARS]})
        kept.append(result)

    if dropped := len(results) - len(kept):
        logger.warning(f"[WEB SEARCH] Dropped {dropped} result(s) named or pasted")
    return kept


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


def get_cached_web_search(prompt: str) -> list[LinkupSearchTextResult] | None:
    """
    Try to get a cached web search results for this prompt.
    """
    if not settings.CACHE_ENABLED:
        return None

    try:
        client = get_redis_client()
        key = REDIS_WEB_SEARCH_KEY.format(prompt_hash=hash_content(prompt))
        data = cast(Any, client.get(key))
        if not data:
            return None

        results: list[dict[str, Any]] = json.loads(data)
        if not results:
            return None

        logger.info("[CACHE] Web search cache hit.")
        return [LinkupSearchTextResult.model_construct(**result) for result in results]

    except Exception as e:
        logger.warning(f"[CACHE] Error reading web search cache: {e}")
        return None


def store_cached_search_results(
    prompt: str, web_search_results: list[LinkupSearchTextResult]
) -> None:
    """
    Store web search results in the cache for this prompt.
    """
    if not settings.CACHE_ENABLED:
        return

    try:
        client = get_redis_client()
        key = REDIS_WEB_SEARCH_KEY.format(prompt_hash=hash_content(prompt))

        client.setex(
            key,
            settings.CACHE_TTL,
            json.dumps([result.model_dump() for result in web_search_results]),
        )
        logger.info("[CACHE] Stored web search cache.")

    except Exception as e:
        logger.warning(f"[CACHE] Error storing web search cache: {e}")
