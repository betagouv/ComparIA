"""
Pseudonymous voter ids for the raw dataset.

A voter is whoever a comparison belongs to: an account when the person was
signed in, an anonymous session otherwise. The raw dataset can carry an id per
voter so that whoever analyses it can group one person's comparisons, to leave
out someone who replays the same prompt or runs experiments.

Off by default (AppSettings.dataset_voter_ids): the id lets whoever holds the
raw dataset link one person's conversations together, which an instance has to
decide to allow, and cover in its terms, before turning it on. The open dataset
never carries it: it drops extra_metadata, where the id lives.

The id is an HMAC of the internal identifier under a key that is made once per
instance and kept, so:

- the same voter has the same id from one publication to the next;
- it cannot be traced back to an account or a session without the key, which
  never leaves the database;
- it disappears when the identifiers do: on account erasure, and once the
  retention period blanks them (utils/database/retention.py).

An anonymous visitor who later signs in and merges their history gets the
account's id on those comparisons from the next publication on.
"""

import hashlib
import hmac
import logging
import secrets
import uuid
from dataclasses import dataclass
from typing import Literal

from utils.database.models.app_settings import AppSettings
from utils.database.session import get_session
from utils.secrets import decrypt_secret, encrypt_secret
from utils.storage.redis import REDIS_APP_SETTINGS_KEY, invalidate_cache

logger = logging.getLogger("comparia.dataset")

VoterType = Literal["account", "anonymous"]

# 128 bits: plenty to keep voters apart, short enough to read in a table.
_ID_HEX_LENGTH = 32


def voter_key(
    user_id: uuid.UUID | None, anonymous_user_hash: str | None
) -> tuple[str, VoterType] | None:
    """
    The internal identifier of a comparison's voter, None when it has none.

    The account wins when both are set: that is how a comparison reads once an
    anonymous history was merged into the account.
    """
    if user_id is not None:
        return f"user:{user_id}", "account"
    if anonymous_user_hash:
        return f"anon:{anonymous_user_hash}", "anonymous"
    return None


@dataclass(frozen=True)
class VoterPseudonyms:
    key: bytes

    def __call__(
        self, user_id: uuid.UUID | None, anonymous_user_hash: str | None
    ) -> tuple[str | None, VoterType | None]:
        found = voter_key(user_id, anonymous_user_hash)
        if found is None:
            return None, None
        identifier, voter_type = found
        digest = hmac.new(self.key, identifier.encode(), hashlib.sha256).hexdigest()
        return digest[:_ID_HEX_LENGTH], voter_type


async def load_voter_pseudonyms() -> VoterPseudonyms | None:
    """
    The pseudonyms to put in this build's raw dataset, None when the instance
    has not turned them on.

    Read from the database rather than the cached settings: the job runs for
    days and must see a change made in the panel since, and the key has no
    business sitting in Redis.
    """
    async with get_session() as session:
        row = await session.get(AppSettings, 1, with_for_update=True)
        if row is None or not row.dataset_voter_ids:
            return None
        encrypted = row.dataset_voter_key_encrypted
        if encrypted is None:
            # Locked above, so two builds starting together agree on one key.
            encrypted = encrypt_secret(secrets.token_hex(32)).encode()
            row.dataset_voter_key_encrypted = encrypted
            session.add(row)
            await session.commit()
            invalidate_cache(REDIS_APP_SETTINGS_KEY)
            logger.info("Made the key for the raw dataset's voter ids.")
    return VoterPseudonyms(decrypt_secret(encrypted.decode()).encode())
