"""add_survey

Revision ID: 3dd0208cf1b8
Revises: c24f368ecff0
Create Date: 2026-08-10 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "3dd0208cf1b8"
down_revision: Union[str, Sequence[str], None] = "c24f368ecff0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "survey_question",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("key", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("triggers", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("input_type", sa.String(), nullable=False),
        sa.Column("labels", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("options", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("published", sa.Boolean(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("archived_at", postgresql.TIMESTAMP(), nullable=True),
        sa.Column("archived_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["archived_by"], ["auth_user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_survey_question_key"), "survey_question", ["key"], unique=True
    )
    op.create_index(
        op.f("ix_survey_question_archived_at"),
        "survey_question",
        ["archived_at"],
        unique=False,
    )

    op.create_table(
        "survey_answer",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column(
            "option_key", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False
        ),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "anonymous_user_hash",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=True,
        ),
        sa.Column("question_revision", sa.Integer(), nullable=False),
        sa.Column("terms_version", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("answered_at", postgresql.TIMESTAMP(), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["survey_question.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["auth_user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_survey_answer_question_id"),
        "survey_answer",
        ["question_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_survey_answer_user_id"), "survey_answer", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_survey_answer_anonymous_user_hash"),
        "survey_answer",
        ["anonymous_user_hash"],
        unique=False,
    )

    op.create_table(
        "survey_prompt_log",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "anonymous_user_hash",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=True,
        ),
        sa.Column("shown_count", sa.Integer(), nullable=False),
        sa.Column("last_shown_at", postgresql.TIMESTAMP(), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["survey_question.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["auth_user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_survey_prompt_log_question_id"),
        "survey_prompt_log",
        ["question_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_survey_prompt_log_user_id"),
        "survey_prompt_log",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_survey_prompt_log_anonymous_user_hash"),
        "survey_prompt_log",
        ["anonymous_user_hash"],
        unique=False,
    )

    op.add_column(
        "app_settings",
        sa.Column(
            "survey_reask_after_days",
            sa.Integer(),
            nullable=False,
            server_default="7",
        ),
    )
    op.alter_column("app_settings", "survey_reask_after_days", server_default=None)


def downgrade() -> None:
    op.drop_column("app_settings", "survey_reask_after_days")

    op.drop_index(
        op.f("ix_survey_prompt_log_anonymous_user_hash"), table_name="survey_prompt_log"
    )
    op.drop_index(op.f("ix_survey_prompt_log_user_id"), table_name="survey_prompt_log")
    op.drop_index(
        op.f("ix_survey_prompt_log_question_id"), table_name="survey_prompt_log"
    )
    op.drop_table("survey_prompt_log")

    op.drop_index(
        op.f("ix_survey_answer_anonymous_user_hash"), table_name="survey_answer"
    )
    op.drop_index(op.f("ix_survey_answer_user_id"), table_name="survey_answer")
    op.drop_index(op.f("ix_survey_answer_question_id"), table_name="survey_answer")
    op.drop_table("survey_answer")

    op.drop_index(op.f("ix_survey_question_archived_at"), table_name="survey_question")
    op.drop_index(op.f("ix_survey_question_key"), table_name="survey_question")
    op.drop_table("survey_question")
