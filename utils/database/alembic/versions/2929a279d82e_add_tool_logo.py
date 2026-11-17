"""add tool logo

Revision ID: 2929a279d82e
Revises: a375433e6a93
Create Date: 2026-11-16 15:14:55.168522

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "2929a279d82e"
down_revision: Union[str, Sequence[str], None] = "a375433e6a93"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("tool", sa.Column("logo", sa.LargeBinary(), nullable=True))
    op.add_column(
        "tool",
        sa.Column(
            "logo_content_type", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("tool", "logo_content_type")
    op.drop_column("tool", "logo")
