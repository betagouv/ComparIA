import logging

from sqlalchemy import text

from utils.utils import db_connection

from ..utils import TABLE_NAMES, TableName

logger = logging.getLogger("comparia.db")


RENAME_QUERY: dict[TableName, str] = {
    "conversations": """
        -- Allow migration of model name (rename model from old name to new name)
        UPDATE 
            conversations
        SET
            -- Replace either old name with the new name in model_a_name
            model_a_name = CASE
                WHEN model_a_name = '{old_name}' THEN '{new_name}'
                ELSE model_a_name
            END,

            -- Replace either old name with the new name in model_b_name
            model_b_name = CASE
                WHEN model_b_name = '{old_name}' THEN '{new_name}'
                ELSE model_b_name
            END,

            -- REPLACE old name in model_pair_name string
            model_pair_name = REPLACE(model_pair_name, '{old_name}', '{new_name}')
        WHERE
            model_a_name = '{old_name}' 
            OR model_b_name = '{old_name}' 
            OR model_pair_name LIKE '%{old_name}%';
""",
    "votes": """
        UPDATE votes
        SET
            -- Replace either old name with the new name in chosen_model_name
            chosen_model_name = CASE
                WHEN chosen_model_name = '{old_name}' THEN '{new_name}'
                ELSE chosen_model_name
            END
        WHERE chosen_model_name = '{old_name}';
""",
    "reactions": """
        UPDATE reactions
        SET
            -- Replace either old name with the new name in refers_to_model
            refers_to_model = CASE
                WHEN refers_to_model = '{old_name}' THEN '{new_name}'
                ELSE refers_to_model
            END
        WHERE refers_to_model = '{old_name}';
""",
}


def rename_llm(old_name: str, new_name: str, *, commit: bool = False):
    """
    Rename an LLM id in all conversations, votes and reactions tables.
    Will update columns:
      - 'model_a_name', 'model_b_name' and 'model_pair_name' on conversations
      - 'chosen_model_name' on votes
      - 'refers_to_model' on reactions
    """
    logger.debug(f"Try to rename LLM {old_name} to {new_name} in database.")

    with db_connection() as conn:
        for table_name in TABLE_NAMES:
            results = conn.execute(
                text(
                    RENAME_QUERY[table_name].format(
                        old_name=old_name, new_name=new_name
                    )
                )
            )

            if not results.rowcount:
                logger.info(f"No {table_name} with LLM '{old_name}' to rename found!")
            elif commit:
                conn.commit()
                logger.info(
                    f"Successfully renamed LLM '{old_name}' to '{new_name}' in {results.rowcount} {table_name}."
                )
            else:
                logger.warning(
                    f"Would have renamed LLM '{old_name}' to '{new_name}' in {results.rowcount} {table_name}."
                )
