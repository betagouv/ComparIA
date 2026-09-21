import logging

from sqlalchemy.orm.attributes import flag_modified

from utils.database.models.auth import UserTotp
from utils.database.secrets import (
    ENCRYPTED_COLUMNS,
    TOTP_COLUMNS,
    load_secret_rows,
    unreadable_secrets,
)
from utils.database.session import get_session
from utils.secrets import decrypt_secret, encrypt_secret, needs_reencryption

logger = logging.getLogger("comparia.db")


class UnreadableSecretsError(Exception):
    """A stored secret the configured keys do not open. Raised before any
    write: rewriting such a row would replace a token an older key could
    still recover with nothing."""


async def reencrypt_secrets() -> None:
    """
    Rewrite every stored secret with the first key of COMPARIA_ENCRYPTION_KEY.

    Key rotation: put the new key first, keep the old one after a comma, run
    this, then drop the old key. Every secret is read first; if one cannot
    be, nothing is written and the command fails. The encrypted columns
    re-encrypt on any write, so touching them is enough; the authenticator
    secrets hold their tokens explicitly and are rewritten by hand. One
    transaction, with the rows locked for its duration.
    """
    counts: dict[str, int] = {}
    async with get_session() as session:
        rows = await load_secret_rows(session, lock=True)

        unreadable = unreadable_secrets(rows)
        if unreadable:
            for ref in unreadable:
                logger.error(
                    f"[secrets] {ref} cannot be decrypted with the configured keys"
                )
            raise UnreadableSecretsError(
                f"{len(unreadable)} stored secrets cannot be decrypted with "
                "COMPARIA_ENCRYPTION_KEY, nothing was changed. Put the key they "
                "were written with back in the list and run again."
            )

        for model, column in ENCRYPTED_COLUMNS:
            for row in rows[model]:
                if not getattr(row, column):
                    continue
                # The value itself is unchanged, so the column is flagged by
                # hand; the write goes through the type and the first key.
                flag_modified(row, column)
                session.add(row)
                counts[model.__tablename__] = counts.get(model.__tablename__, 0) + 1

        for totp in rows[UserTotp]:
            for column in TOTP_COLUMNS:
                token = getattr(totp, column)
                if token and needs_reencryption(token):
                    setattr(totp, column, encrypt_secret(decrypt_secret(token)))
                    session.add(totp)
                    counts[UserTotp.__tablename__] = (
                        counts.get(UserTotp.__tablename__, 0) + 1
                    )

        await session.commit()

    for table, count in counts.items():
        logger.info(f"[secrets] {table}: {count} rows rewritten")
    logger.info(
        f"[secrets] {sum(counts.values())} secrets rewritten with the current key"
    )
