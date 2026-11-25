"""drop legacy user message web search results

Revision ID: 5ecd49d77967
Revises: 474ca11099d1
Create Date: 2026-11-25 13:07:29.752734

"""

from dataclasses import dataclass
from typing import Literal, Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "5ecd49d77967"
down_revision: Union[str, Sequence[str], None] = "474ca11099d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


WEB_SEARCH_INTRO = "Here is some recent information from a web search. Use it to answer the user's question if it's relevant:\n\n"


@dataclass
class _LinkupSearchTextResult:
    """A text result from a Linkup search.

    Attributes:
        type: The type of the search result, in this case "text".
        name: The name of the search result.
        url: The URL of the search result.
        content: The text of the search result.
        favicon: The favicon URL of the search result, if available.
    """

    type: Literal["text"]
    name: str
    url: str
    content: str
    favicon: str


def merge_web_search_with_content(content: str, web_search_results: list[dict]) -> str:
    results = [_LinkupSearchTextResult(**r) for r in web_search_results]
    return "\n\n".join(
        [
            content,
            WEB_SEARCH_INTRO,
            "\n\n---\n\n".join(
                [
                    f"Source: {result.name} ({result.url})\n{result.content}".strip()
                    for result in results
                ]
            ),
        ]
    )


def upgrade() -> None:
    conn = op.get_bind()

    messages = sa.table(
        "user_message",
        sa.column("id", sa.Uuid()),
        sa.column("content", sa.Text()),
        sa.column("web_search_results", postgresql.JSONB),
    )

    rows = conn.execute(
        sa.select(
            messages.c.id, messages.c.content, messages.c.web_search_results
        ).where(messages.c.web_search_results.is_not(None))
    ).mappings()

    for row in rows:
        results = row["web_search_results"] or []
        if not results:
            continue

        merged_content = merge_web_search_with_content(row["content"], results)

        conn.execute(
            messages.update()
            .where(messages.c.id == row["id"])
            .values(content=merged_content)
        )

    op.drop_column("user_message", "web_search_results")


def downgrade() -> None:
    op.add_column(
        "user_message",
        sa.Column(
            "web_search_results",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
