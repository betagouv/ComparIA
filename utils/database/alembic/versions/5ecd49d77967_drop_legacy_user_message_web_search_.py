"""drop legacy user message web search results

Revision ID: 5ecd49d77967
Revises: 474ca11099d1
Create Date: 2026-11-25 13:07:29.752734

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "5ecd49d77967"
down_revision: Union[str, Sequence[str], None] = "474ca11099d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


WEB_SEARCH_INTRO = "Here is some recent information from a web search. Use it to answer the user's question if it's relevant:\n\n"

# Appends the search results to the message, as the model received them:
#   content, intro, then "Source: name (url)\ncontent" per result,
#   joined by "\n\n" and the results by "\n\n---\n\n".
# Done in the database: reading the rows into the migration process runs it
# out of memory on production.
MERGE_WEB_SEARCH_INTO_CONTENT = r"""
UPDATE user_message AS m
SET content = m.content || E'\n\n' || :intro || E'\n\n' || s.sources
FROM (
    SELECT
        um.id,
        string_agg(
            btrim(
                'Source: ' || coalesce(r.value ->> 'name', '')
                || ' (' || coalesce(r.value ->> 'url', '') || ')' || E'\n'
                || coalesce(r.value ->> 'content', ''),
                E' \t\n\r\f\v'
            ),
            E'\n\n---\n\n' ORDER BY r.position
        ) AS sources
    FROM user_message AS um
    CROSS JOIN LATERAL jsonb_array_elements(um.web_search_results)
        WITH ORDINALITY AS r(value, position)
    WHERE jsonb_typeof(um.web_search_results) = 'array'
    GROUP BY um.id
) AS s
WHERE m.id = s.id
"""


def upgrade() -> None:
    op.get_bind().execute(
        sa.text(MERGE_WEB_SEARCH_INTO_CONTENT), {"intro": WEB_SEARCH_INTRO}
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
