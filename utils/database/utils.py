import logging
from datetime import datetime
from typing import Literal, Sequence, get_args

from sqlalchemy import text

from utils.utils import db_connection

TableName = Literal["conversations", "votes", "reactions"]
TABLE_NAMES: tuple[TableName, ...] = get_args(TableName)

ArchivedReason = Literal["corrupted", "spam", "unknown_llm", "unknown"]

logger = logging.getLogger("comparia.database")


def archive(
    table_name: TableName,
    ids: Sequence[str],
    archived_reason: ArchivedReason,
    archived_at: datetime,
    id_key: str = "conversation_pair_id",
    commit: bool = False,
) -> int:
    """
    Archive given table related ids objects with reason and archive date.
    Log only by default what would have been archive, set 'commit' to True to
    actually archive those.
    """
    query = """
        UPDATE {table_name} 
        SET 
            archived = TRUE,
            archived_reason = '{archived_reason}',
            archived_at = '{archived_at}'
        WHERE
            {id_key} IN ({ids});
    """.format(
        table_name=table_name,
        archived_reason=archived_reason,
        archived_at=archived_at,
        ids=", ".join([f"'{id}'" for id in ids]),
        id_key=id_key,
    )

    with db_connection() as conn:
        results = conn.execute(text(query))

        if commit:
            conn.commit()
            logger.info(
                f"Successfully archived {results.rowcount} '{archived_reason}' {table_name}."
            )
        else:
            logger.error(
                f"{results.rowcount} '{archived_reason}' {table_name} should be archived."
            )

        return results.rowcount
