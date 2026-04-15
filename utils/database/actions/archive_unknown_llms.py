import logging
from datetime import datetime

import polars as pl

from utils.utils import LLMS_GENERATED_DATA_FILE, db_connection, read_json

from ..utils import TABLE_NAMES, archive

logger = logging.getLogger("comparia.db")

UNKNOWN_LLM_IDS_CONVERSATIONS_QUERY = """
SELECT 
    conversation_pair_id,
    model_a_name,
    model_b_name,
    timestamp
FROM 
    conversations 
WHERE 
    (archived IS NULL OR archived IS FALSE)
    AND (
        model_a_name NOT IN ({llm_ids})
        OR model_b_name NOT IN ({llm_ids})
    );
"""


def archive_unknown_llms(*, commit: bool = False) -> None:
    """
    Archive conversations, votes and reactions that refers to an unknown LLM
    (not in LLM list).
    """
    logger.info(f"Searching for unknown LLMs.")
    llm_ids = set(read_json(LLMS_GENERATED_DATA_FILE)["models"].keys())

    with db_connection() as conn:
        data = pl.read_database(
            UNKNOWN_LLM_IDS_CONVERSATIONS_QUERY.format(
                llm_ids=", ".join([f"'{id}'" for id in llm_ids])
            ),
            conn,
        )

    ids = data["conversation_pair_id"].to_list()
    if not ids:
        logger.info("No conversations with unknown LLM ids found!")
        return

    logger.warning(f"Found {len(ids)} conversations with unknown LLM ids:")

    unknown_llm_ids = set(
        data["model_a_name"].append(data["model_b_name"]).unique().to_list()
    ).difference(llm_ids)

    for id in unknown_llm_ids:
        count = len(
            data.filter((pl.col("model_a_name") == id) | (pl.col("model_b_name") == id))
        )
        logger.warning(f"    {count} conversations with unknown LLM id: '{id}'")

    archived_at = datetime.now()
    for table_name in TABLE_NAMES:
        # archive corrupted 'conversations' and related 'votes' + 'reactions'
        archive(table_name, ids, "unknown_llm", archived_at, commit=commit)
