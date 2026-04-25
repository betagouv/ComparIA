from typing import Literal

from backend.config import CountryPortal

Columns = tuple[str, ...]

EXCLUDE_PPI = """
-- Filter out rows potentially containing PII or spam
AND c.pii_analyzed = TRUE
AND c.contains_pii = FALSE
AND c.contains_spam = FALSE
AND c.postprocess_failed = FALSE
"""
EXCLUDE_COHORTS = """
-- Filter out rows excluded because of their cohort (only pix for now)
AND (COALESCE(c.cohorts, '') NOT LIKE '%%pix%%')
"""
IS_COUNTRY_PORTAL = "AND c.country_portal = '{country_portal}'"
JOIN_CONVERSATIONS = (
    "JOIN conversations c ON {k}.conversation_pair_id = c.conversation_pair_id"
)


def _get_columns_fields(
    cols: (
        dict[Literal["v", "c"], Columns]
        | dict[Literal["r", "c"], Columns]
        | Columns
        | Literal["*"]
    ),
    base_name: Literal["c", "v", "r"],
) -> str:
    if cols == "*":
        return f"{base_name}.*"
    if isinstance(cols, tuple):
        return ", ".join(f"{base_name}.{col}" for col in cols)
    return ", ".join(
        ", ".join(f"{k}.{col}" for col in cols) for k, cols in cols.items()
    )


def get_conversations_filters(
    country_portal: CountryPortal | None = None,
    exclude_pii: bool = True,
    exclude_cohorts: bool = True,
    as_exists: bool = False,
    k: Literal["v", "r"] | None = None,
) -> str:
    base = f"""
    c.archived = FALSE
    {IS_COUNTRY_PORTAL.format(country_portal=country_portal) if country_portal else ""}
    {EXCLUDE_PPI if exclude_pii else ""}
    {EXCLUDE_COHORTS if exclude_cohorts else ""}
    """

    if as_exists:
        return f"""
        EXISTS (
            SELECT 1
            FROM conversations c
            WHERE
                c.conversation_pair_id = {k}.conversation_pair_id
                AND {base}
        )
        """

    return base


def get_conversations_db_query(
    columns: Columns | Literal["*"] = "*",
    country_portal: CountryPortal | None = None,
    exclude_pii: bool = True,
    exclude_cohorts: bool = True,
) -> str:
    return f"""
    SELECT
        {_get_columns_fields(columns, "c")}
    FROM
        conversations c
    WHERE
        {get_conversations_filters(country_portal, exclude_pii, exclude_cohorts)}
    ;
    """


def get_votes_db_query(
    columns: dict[Literal["v", "c"], Columns] | Columns | Literal["*"] = "*",
    country_portal: CountryPortal | None = None,
    count: bool = False,
    exclude_pii: bool = True,
    exclude_cohorts: bool = True,
) -> str:
    join = (isinstance(columns, dict) and "c" in columns) or (
        count and country_portal is not None
    )

    return f"""
    SELECT
        {"COUNT(*)" if count else _get_columns_fields(columns, "v")}
    FROM
        votes v
    {JOIN_CONVERSATIONS.format(k="v") if join else ""}
    WHERE
        v.archived = FALSE
        AND {get_conversations_filters(country_portal,exclude_pii, exclude_cohorts, as_exists=not join, k="v")}
    """


def get_reactions_db_query(
    columns: dict[Literal["r", "c"], Columns] | Columns | Literal["*"] = "*",
    country_portal: CountryPortal | None = None,
    count: bool = False,
    exclude_pii: bool = True,
    exclude_cohorts: bool = True,
) -> str:
    join = (isinstance(columns, dict) and "c" in columns) or (
        count and country_portal is not None
    )

    return f"""
    SELECT 
        {"COUNT(*)" if count else _get_columns_fields(columns, "r")}
    FROM
        reactions r
    {JOIN_CONVERSATIONS.format(k="r") if join else ""}
    WHERE
        r.archived = FALSE
        -- Filtering reactions with PII, or excluded cohorts
        AND {get_conversations_filters(country_portal,exclude_pii, exclude_cohorts, as_exists=not join, k="r")}
    """
