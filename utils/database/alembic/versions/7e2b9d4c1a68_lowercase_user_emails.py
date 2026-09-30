"""lowercase user emails

Revision ID: 7e2b9d4c1a68
Revises: 5c8bd69940b5
Create Date: 2026-09-30 14:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '7e2b9d4c1a68'
down_revision: Union[str, Sequence[str], None] = '5c8bd69940b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Two accounts that differ only by case can't be merged safely from here
    # (each has its own sessions, consents, comparisons): stop and list them,
    # before anything is rewritten, so they can be merged by hand first.
    duplicates = op.get_bind().execute(
        sa.text(
            'SELECT lower(email) AS email, array_agg(email ORDER BY email) AS spellings '
            'FROM auth_user GROUP BY lower(email) HAVING count(*) > 1 '
            'ORDER BY lower(email)'
        )
    ).all()
    if duplicates:
        listing = '\n'.join(f'  {row.email}: {", ".join(row.spellings)}' for row in duplicates)
        raise RuntimeError(
            'auth_user has emails that differ only by case, merge or delete '
            f'these accounts before migrating:\n{listing}'
        )

    op.execute('UPDATE auth_user SET email = lower(email) WHERE email <> lower(email)')
    op.drop_constraint('auth_user_email_key', 'auth_user', type_='unique')
    op.create_index(
        'uq_auth_user_email_lower', 'auth_user', [sa.text('lower(email)')], unique=True
    )


def downgrade() -> None:
    # The lowercased addresses stay lowercased: their original spelling is not
    # kept anywhere.
    op.drop_index('uq_auth_user_email_lower', table_name='auth_user')
    op.create_unique_constraint('auth_user_email_key', 'auth_user', ['email'])
