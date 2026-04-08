import logging
from datetime import datetime

import polars as pl

from utils.utils import db_connection

from ..utils import archive

logger = logging.getLogger("comparia.database")


def archive_duplicate_votes(*, commit: bool = False) -> None:
    archived_at = datetime.now()
    query = """
        SELECT
            id,
            timestamp,
            conversation_pair_id
        FROM votes 
        WHERE archived IS NULL;
    """

    with db_connection(stream=True) as conn:
        results = pl.read_database(query=query, connection=conn)
        dups = results.filter(pl.col("conversation_pair_id").is_duplicated())
        dups_ids_count = dups["conversation_pair_id"].count()
        dups_unique_ids_count = dups["conversation_pair_id"].unique().count()

        if dup_count := dups_ids_count - dups_unique_ids_count:
            logger.warning(
                f"Found {dup_count} duplicated votes on {dups_unique_ids_count} conversations."
            )
            ids: list[int] = []
            for id, df in dups.group_by("conversation_pair_id"):
                *rest_ids, last_id = df.sort("timestamp")["id"].to_list()
                ids += rest_ids

            archive("votes", ids, "duplicate", archived_at, id_key="id", commit=commit)
        else:
            logger.info("No duplicate votes found!")


def archive_duplicate_reactions(*, commit: bool = False):
    query = """
        SELECT
            id,
            timestamp,
            conversation_pair_id,
            msg_index,
            refers_to_conv_id
        FROM reactions 
        WHERE archived IS NULL;
    """
    archived_at = datetime.now()

    with db_connection(stream=True) as conn:
        results = pl.read_database(query=query, connection=conn)
        ids: list[int] = []

        for id, df in results.group_by(
            "conversation_pair_id", "msg_index", "refers_to_conv_id"
        ):
            if len(df) > 1:
                *rest_ids, last_id = df.sort("timestamp")["id"].to_list()
                ids += rest_ids

        if not ids:
            logger.info(f"No duplicated reactions found!")
        else:
            logger.warning(f"Found {len(ids)} duplicated 'reactions'.")

            archive(
                "reactions", ids, "duplicate", archived_at, id_key="id", commit=commit
            )


def archive_reactions_with_vote(*, commit: bool = False):
    query = "SELECT id, conversation_pair_id, timestamp FROM {table_name} WHERE archived IS NULL"
    archived_at = datetime.now()

    with db_connection(stream=True) as conn:
        votes = pl.read_database(
            query=query.format(table_name="votes"), connection=conn
        )
        reactions = pl.read_database(
            query=query.format(table_name="reactions"), connection=conn
        )
        ids: list[int] = []
        votes_with_reactions = votes.join(
            reactions, on="conversation_pair_id", suffix="_reaction"
        ).group_by("conversation_pair_id")

        for _, df in votes_with_reactions:
            ids += df["id_reaction"].to_list()

        if not ids:
            logger.info(f"No vote reactions found!")
        else:
            logger.warning(
                f"Found {len(ids)} reactions on conversations with already a vote."
            )

            archive(
                "reactions",
                ids,
                "duplicate_has_vote",
                archived_at,
                id_key="id",
                commit=commit,
            )


def archive_duplicate(*, commit: bool = False):
    """
    Archive votes and reaction duplicates, keeping only the last one.
    Also archive reactions for conversations that also have a vote.
    """
    logger.info("Searching for duplicate data")

    archive_duplicate_votes(commit=commit)
    archive_duplicate_reactions(commit=commit)
    archive_reactions_with_vote(commit=commit)
