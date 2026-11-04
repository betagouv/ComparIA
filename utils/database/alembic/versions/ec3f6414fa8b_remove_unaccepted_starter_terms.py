"""remove unaccepted starter terms

Revision ID: ec3f6414fa8b
Revises: 0783a14a0418
Create Date: 2026-11-04 14:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ec3f6414fa8b"
down_revision: Union[str, Sequence[str], None] = "0783a14a0418"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Id of the starter terms inserted by e4a8c2d9f1b7.
STARTER_TERMS_ID = "6f1b6f6e-8f4a-4c3e-9a2f-2d0d5a1f7b41"


def upgrade() -> None:
    # The platform no longer ships placeholder terms: the operator publishes
    # their own. A row someone already accepted stays, since it is the record
    # of what they agreed to.
    op.execute(sa.text("""
            DELETE FROM legal_document d
            WHERE d.id = CAST(:starter_id AS uuid)
              AND NOT EXISTS (
                SELECT 1 FROM auth_consent_log c WHERE c.document_id = d.id
              )
              AND NOT EXISTS (
                SELECT 1 FROM anonymous_consent_log a WHERE a.document_id = d.id
              )
            """).bindparams(starter_id=STARTER_TERMS_ID))


def downgrade() -> None:
    # The starter terms are not restored on purpose.
    pass
