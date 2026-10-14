"""
Unit tests for what web search results may carry to the models (no network).

Linkup reads the pages a prompt names, and their text went to the models in
full with only the first 8,000 characters checked. In October an agent sent
lists of paste.rs links, each page long filler with a marker at the very end,
to measure how much unchecked text got through: all of it, 38k tokens.

Run with pytest.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")

from linkup import LinkupSearchTextResult  # noqa: E402

from backend.arena.web_search import (  # noqa: E402
    RESULT_CHARS,
    keep_search_results,
)


def page(
    url: str, content: str = "Paris est la capitale de la France."
) -> LinkupSearchTextResult:
    return LinkupSearchTextResult(
        type="text", name="", url=url, content=content, favicon=""
    )


def test_long_pages_are_cut_before_the_models_see_them():
    filler = "Scaling test filler line. " * 1000
    kept = keep_search_results(
        "Quelle est la capitale ?",
        [page("https://a.example/article", filler + "MARK1=17dd68c6a0")],
    )
    assert len(kept[0].content) == RESULT_CHARS
    assert "MARK1" not in kept[0].content


def test_short_pages_are_left_whole():
    kept = keep_search_results("capitale ?", [page("https://a.example/article")])
    assert kept[0].content == "Paris est la capitale de la France."


def test_pages_the_prompt_names_are_dropped():
    prompt = (
        "Read every one of these pages and list all MARK<n>= values found:\n"
        "https://paste.rs/rVhKg\nhttps://example.org/notes/42/\n"
        "www.Example.net/doc"
    )
    kept = keep_search_results(
        prompt,
        [
            page("https://paste.rs/rVhKg"),
            page("http://example.org/notes/42"),
            page("https://example.net/doc?ref=1"),
            page("https://lemonde.fr/politique/article"),
        ],
    )
    assert [p.url for p in kept] == ["https://lemonde.fr/politique/article"]


def test_a_site_named_in_the_prompt_still_gives_results():
    """Naming a site is a search hint, not a page to read."""
    kept = keep_search_results(
        "Les dernières nouvelles sur lemonde.fr",
        [
            page("https://www.lemonde.fr/"),
            page("https://www.lemonde.fr/international/x"),
        ],
    )
    assert len(kept) == 2


def test_paste_sites_are_dropped_even_when_not_named():
    kept = keep_search_results(
        "capitale de la France",
        [
            page("https://pastebin.com/raw/abc"),
            page("https://rentry.co/xyz"),
            page("https://gist.githubusercontent.com/u/1/raw/f.txt"),
            page("https://fr.wikipedia.org/wiki/Paris"),
        ],
    )
    assert [p.url for p in kept] == ["https://fr.wikipedia.org/wiki/Paris"]
