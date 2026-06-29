import logging

import polars as pl
from sqlmodel import and_, col, delete, or_, select

from utils.utils import LLMS_GENERATED_DATA_FILE, read_json

from ..models import Comparison
from ..session import get_session
from ..utils import archive

logger = logging.getLogger("comparia.db")


async def archive_unknown_llms(*, commit: bool = False) -> None:
    """
    Archive comparisons that refers to an unknown LLM (not in LLM list).
    """
    logger.info(f"Searching for unknown LLMs.")
    llm_ids = list(set(read_json(LLMS_GENERATED_DATA_FILE)["models"].keys()))

    async with get_session() as session:
        query = select(Comparison.id, Comparison.llm_id_a, Comparison.llm_id_b).where(
            and_(
                col(Comparison.archived) == None,
                or_(
                    col(Comparison.llm_id_a).not_in(llm_ids),
                    col(Comparison.llm_id_b).not_in(llm_ids),
                ),
            )
        )

        data = pl.DataFrame((await session.exec(query)).all())

    ids = data["id"].to_list() if not data.is_empty() else []
    if not ids:
        logger.info("No comparisons with unknown LLM ids found!")
        return

    logger.warning(f"Found {len(ids)} comparisons with unknown LLM ids:")

    unknown_llm_ids = set(
        data["llm_id_a"].append(data["llm_id_b"]).unique().to_list()
    ).difference(llm_ids)

    for id in unknown_llm_ids:
        count = len(
            data.filter((pl.col("llm_id_a") == id) | (pl.col("llm_id_b") == id))
        )
        logger.warning(f"{count:4} comparisons with unknown LLM id: '{id}'")

    await archive(ids, "unknown_llm", commit=commit)


async def delete_unknown_llms_comparisons(*, commit: bool = False) -> None:
    """
    Delete comparisons that refers to an unknown LLM (not in LLM list).
    """
    logger.info(f"Searching for unknown LLMs.")
    llm_ids = list(
        set(
            [
                id
                for id, data in read_json(LLMS_GENERATED_DATA_FILE)["models"].items()
                if data["status"] in ("enabled", "archived", "disabled")
            ]
        )
    )

    async with get_session() as session:
        query = select(Comparison).where(
            or_(
                col(Comparison.llm_id_a).not_in(llm_ids),
                col(Comparison.llm_id_b).not_in(llm_ids),
            )
        )

        results = (await session.exec(query)).all()

        extra_ids = set(
            [c.llm_id_a for c in results] + [c.llm_id_b for c in results]
        ).difference(llm_ids)

        def count(id: str):
            return len([c for c in results if c.llm_id_a == id or c.llm_id_b == id])

        logger.warning(
            f"Found {len(extra_ids)} unknown llm ids:\n{"\n".join(f" - {count(id)}: '{id}'" for id in extra_ids)}"
        )

        if not commit:
            logger.warning(f"Would have removed {len(results)} comparisons.")
        else:
            logger.warning(f"Will remove {len(results)} comparisons.")
            for r in results:
                await session.delete(r)
            await session.commit()
