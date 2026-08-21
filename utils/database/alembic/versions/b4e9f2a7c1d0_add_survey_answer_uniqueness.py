"""add_survey_answer_uniqueness

Revision ID: b4e9f2a7c1d0
Revises: 3dd0208cf1b8
Create Date: 2026-08-21 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b4e9f2a7c1d0"
down_revision: Union[str, Sequence[str], None] = "3dd0208cf1b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # One row per option per respondent, enforced by the database rather than
    # only by delete-then-insert in `submit_answers`: two concurrent
    # submissions would otherwise both pass the delete and leave a duplicate.
    # Both ownership columns are nullable and Postgres treats NULL as distinct
    # in unique indexes, so each is wrapped in COALESCE to a sentinel that no
    # real row carries — exactly one of the two is ever set.
    op.create_index(
        "uq_survey_answer_respondent_option",
        "survey_answer",
        [
            "question_id",
            "option_key",
            sa.text(
                "COALESCE(user_id, '00000000-0000-0000-0000-000000000000'::uuid)"
            ),
            sa.text("COALESCE(anonymous_user_hash, '')"),
        ],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_survey_answer_respondent_option", table_name="survey_answer"
    )
