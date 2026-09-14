import logging

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import select

from utils.database.models.auth import UserTotp
from utils.database.models.llms.endpoint import LLMEndpoint
from utils.database.models.prompt_check import PromptCheck
from utils.database.models.publish import PublishDestination
from utils.database.session import get_session
from utils.secrets import decrypt_secret, encrypt_secret, needs_reencryption

logger = logging.getLogger("comparia.db")


async def reencrypt_secrets() -> None:
    """
    Rewrite every stored secret with the first key of COMPARIA_ENCRYPTION_KEY.

    Key rotation: put the new key first, keep the old one after a comma, run
    this, then drop the old key. The encrypted columns re-encrypt on any
    write, so touching them is enough; the authenticator secrets hold their
    tokens explicitly and are rewritten by hand.
    """
    rewritten = 0
    async with get_session() as session:
        for model, column in (
            (LLMEndpoint, "api_key"),
            (PromptCheck, "api_key"),
            (PublishDestination, "config"),
        ):
            for row in (await session.exec(select(model))).all():
                value = getattr(row, column)
                if not value:
                    continue
                # The value itself is unchanged, so the column is flagged by
                # hand; the write goes through the type and the first key.
                flag_modified(row, column)
                session.add(row)
                rewritten += 1

        for totp in (await session.exec(select(UserTotp))).all():
            for column in ("secret_encrypted", "pending_secret_encrypted"):
                token = getattr(totp, column)
                if token and needs_reencryption(token):
                    plain = decrypt_secret(token)
                    if plain is None:
                        logger.error(
                            f"[secrets] auth_totp {totp.id}.{column} cannot be decrypted, skipped"
                        )
                        continue
                    setattr(totp, column, encrypt_secret(plain))
                    session.add(totp)
                    rewritten += 1

        await session.commit()
    logger.info(f"[secrets] {rewritten} secrets rewritten with the current key")
