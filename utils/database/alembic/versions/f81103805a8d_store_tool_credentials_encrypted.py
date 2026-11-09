"""store tool credentials encrypted

Revision ID: f81103805a8d
Revises: e5a91c73f2d8
Create Date: 2026-10-08 11:50:25.766285

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql

from utils.secrets import decrypt_secret, encrypt_secret

# revision identifiers, used by Alembic.
revision: str = "f81103805a8d"
down_revision: Union[str, Sequence[str], None] = "e5a91c73f2d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "tool",
        sa.Column(
            "allowed_functions", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
    )
    op.add_column(
        "tool",
        sa.Column(
            "allowed_domains", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
    )
    op.add_column(
        "tool",
        sa.Column(
            "blocked_domains", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
    )
    op.add_column(
        "tool",
        sa.Column(
            "secret_encrypted", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
    )

    # A header stored in clear moves to the encrypted column as it is: the
    # arena reads a 'Name: value' credential the same way it read the header.
    connection = op.get_bind()
    rows = connection.execute(
        sa.text("SELECT id, auth_header FROM tool WHERE auth_header IS NOT NULL")
    ).all()
    for row_id, header in rows:
        connection.execute(
            sa.text("UPDATE tool SET secret_encrypted = :secret WHERE id = :id"),
            {"secret": encrypt_secret(header), "id": row_id},
        )

    op.drop_column("tool", "auth_header")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "tool",
        sa.Column("auth_header", sa.VARCHAR(), autoincrement=False, nullable=True),
    )

    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            "SELECT id, secret_encrypted FROM tool "
            "WHERE kind = 'mcp' AND secret_encrypted IS NOT NULL"
        )
    ).all()
    for row_id, token in rows:
        connection.execute(
            sa.text("UPDATE tool SET auth_header = :header WHERE id = :id"),
            {"header": decrypt_secret(token), "id": row_id},
        )

    op.drop_column("tool", "secret_encrypted")
    op.drop_column("tool", "blocked_domains")
    op.drop_column("tool", "allowed_domains")
    op.drop_column("tool", "allowed_functions")
