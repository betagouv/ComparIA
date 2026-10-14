import logging
import time

from sqlalchemy import text
from sqlmodel import col, select

from backend.config import settings
from utils.database.models.llms import LLMData
from utils.database.session import get_session

logger = logging.getLogger("comparia.db")

PROMPTS = [
    "Comment rédiger une lettre de motivation pour un poste d'infirmier ?",
    "Explique-moi la différence entre un CDD et un CDI.",
    "Quels sont les symptômes d'une carence en fer ?",
    "Écris un poème sur la mer en alexandrins.",
    "Résume la Révolution française en cinq points.",
    "Comment calculer l'aire d'un cercle ?",
    "Donne-moi une recette de ratatouille pour quatre personnes.",
    "Quels recours ai-je si mon propriétaire ne rend pas ma caution ?",
    "Traduis en anglais : je voudrais réserver une table pour ce soir.",
    "Peux-tu m'aider à préparer un entretien d'embauche ?",
    "Qu'est-ce que l'effet de serre ?",
    "Corrige les fautes de ce texte : les enfant on manger des pomme.",
    "Écris une fonction Python qui inverse une liste.",
    "Quelle est la capitale de l'Australie ?",
    "Comment fonctionne le vote à l'Assemblée nationale ?",
    "Propose un programme de course à pied pour débutant.",
    "Que faire en cas de piqûre de guêpe ?",
    "Explique la photosynthèse à un enfant de dix ans.",
    "Quels sont les avantages du télétravail ?",
    "Comment demander un remboursement à la CAF ?",
]

ANSWER = (
    "Voici une réponse détaillée. D'abord, il faut comprendre le contexte de la "
    "question. Ensuite, plusieurs points méritent d'être examinés : les faits, "
    "les options possibles et leurs conséquences. Enfin, une conclusion courte "
    "permet de retenir l'essentiel. "
)

COMMENTS = [
    "Réponse claire et bien structurée.",
    "Il manque des sources.",
    "Trop long, je voulais juste la réponse.",
    "Erreur sur la date, c'est faux.",
    "Très utile, merci !",
]

CATEGORIES = [
    "Education",
    "Health & Wellness & Medicine",
    "Law & Justice",
    "Personal Development & Human Resources & Career",
    "Natural Science & Formal Science & Technology",
    "Food & Drink & Cooking",
    "Arts",
    "Politics & Government",
    "Daily Life & Home & Lifestyle",
    "Other",
]

STATEMENTS = [
    # One row per comparison, with every random draw it needs.
    """
    CREATE TEMP TABLE seed_comparison ON COMMIT DROP AS
    SELECT
        gen_random_uuid() AS id,
        localtimestamp - random() * make_interval(days => :days) AS created_at,
        1 + floor(power(random(), 3) * 4)::int AS turns,
        floor(random() * cardinality(CAST(:llms AS uuid[])))::int AS a_index,
        floor(random() * (cardinality(CAST(:llms AS uuid[])) - 1))::int AS b_offset,
        random() AS r_mode,
        random() AS r_flag,
        random() AS r_misc
    FROM generate_series(1, :count)
    """,
    """
    INSERT INTO comparison (
        id, created_at, updated_at, ip, mode, llm_id_a, llm_id_b, revealed,
        participation_terms_version, cohorts, error, llm_analyzed,
        contains_pii, contains_spam, categories, languages, keywords,
        short_summary, archived, archived_reason
    )
    SELECT
        id, created_at, created_at, '127.0.0.1',
        CASE WHEN r_mode < 0.7 THEN 'random'
             WHEN r_mode < 0.8 THEN 'big-vs-small'
             WHEN r_mode < 0.9 THEN 'small-models'
             ELSE 'custom' END,
        (CAST(:llms AS uuid[]))[1 + a_index],
        (CAST(:llms AS uuid[]))[
            1 + (a_index + 1 + b_offset) % cardinality(CAST(:llms AS uuid[]))
        ],
        r_misc < 0.3,
        'seed',
        CASE WHEN r_misc > 0.97 THEN 'pix' END,
        CASE WHEN r_flag > 0.97
             THEN '{"code": "timeout", "message": "timeout", "pos": "a", "is_timeout": true}'::jsonb
             ELSE 'null'::jsonb END,
        CASE WHEN r_flag < 0.8 THEN true END,
        CASE WHEN r_flag < 0.8 THEN r_flag < 0.02 END,
        CASE WHEN r_flag < 0.8 THEN r_flag BETWEEN 0.02 AND 0.03 END,
        CASE WHEN r_flag < 0.8 THEN jsonb_build_array(
            (CAST(:categories AS text[]))[
                1 + floor(r_mode * cardinality(CAST(:categories AS text[])))::int
            ]
        ) END,
        CASE WHEN r_flag < 0.8 THEN '["fr"]'::jsonb END,
        CASE WHEN r_flag < 0.8 THEN '["seed"]'::jsonb END,
        CASE WHEN r_flag < 0.8 THEN 'Conversation générée pour les tests.' END,
        r_flag < 0.03,
        CASE WHEN r_flag < 0.02 THEN 'pii' WHEN r_flag < 0.03 THEN 'spam' END
    FROM seed_comparison
    """,
    """
    CREATE TEMP TABLE seed_turn ON COMMIT DROP AS
    SELECT
        gen_random_uuid() AS id,
        c.id AS comparison_id,
        c.created_at + (n - 1) * interval '3 minutes' AS created_at,
        gen_random_uuid() AS msg_a_id,
        gen_random_uuid() AS msg_b_id,
        random() AS r_choice,
        random() AS r_tag,
        random() AS r_prompt
    FROM seed_comparison c, generate_series(1, c.turns) AS n
    """,
    """
    INSERT INTO llm_message (
        id, role, created_at, responded_at, updated_at, content, generation_id,
        tokens, is_cached
    )
    SELECT msg_id, 'assistant', created_at,
        created_at + (2 + random() * 20) * interval '1 second', created_at,
        repeat(:answer, 1 + floor(random() * 3)::int), 'seed',
        100 + floor(random() * 900)::int, false
    FROM seed_turn, LATERAL (VALUES (msg_a_id), (msg_b_id)) AS side(msg_id)
    """,
    """
    INSERT INTO turn (
        id, comparison_id, created_at, updated_at, choice, voted_at,
        llm_msg_a_id, llm_msg_b_id, keyword_annotations_a,
        keyword_annotations_b, custom_annotation_a, custom_annotation_b
    )
    SELECT id, comparison_id, created_at, created_at, choice,
        CASE WHEN choice IS NOT NULL THEN created_at + interval '1 minute' END,
        msg_a_id, msg_b_id,
        CASE WHEN r_tag < 0.4 AND choice IN ('a_better', 'both_good')
                  THEN '["useful", "clear_formatting"]'::jsonb
             WHEN r_tag < 0.4 AND choice IN ('b_better', 'both_bad')
                  THEN '["incorrect"]'::jsonb
             ELSE '[]'::jsonb END,
        CASE WHEN r_tag < 0.4 AND choice IN ('b_better', 'both_good')
                  THEN '["complete"]'::jsonb
             WHEN r_tag < 0.4 AND choice IN ('a_better', 'both_bad')
                  THEN '["superficial"]'::jsonb
             ELSE '[]'::jsonb END,
        CASE WHEN r_tag < 0.05 AND choice IS NOT NULL
             THEN (CAST(:comments AS text[]))[
                 1 + floor(r_prompt * cardinality(CAST(:comments AS text[])))::int
             ] END,
        NULL
    FROM (
        SELECT *,
            CASE WHEN r_choice < 0.45 THEN NULL
                 WHEN r_choice < 0.65 THEN 'a_better'
                 WHEN r_choice < 0.85 THEN 'b_better'
                 WHEN r_choice < 0.91 THEN 'both_good'
                 WHEN r_choice < 0.96 THEN 'both_bad'
                 ELSE 'idk' END AS choice
        FROM seed_turn
    ) AS drawn
    """,
    """
    INSERT INTO user_message (id, created_at, role, content, turn_id)
    SELECT gen_random_uuid(), created_at, 'user',
        (CAST(:prompts AS text[]))[
            1 + floor(r_prompt * cardinality(CAST(:prompts AS text[])))::int
        ],
        id
    FROM seed_turn
    """,
    """
    INSERT INTO prompt_check_result (
        id, created_at, turn_id, decision, model, latency_ms, scores,
        triggered, user_proceeded
    )
    SELECT gen_random_uuid(), created_at, id,
        CASE WHEN r_tag > 0.99 THEN 'warned'
             WHEN r_tag > 0.97 THEN 'logged'
             ELSE 'pass' END,
        'seed', 120, '{}'::jsonb, '{}'::jsonb, r_tag > 0.99
    FROM seed_turn
    """,
]


async def seed_activity(count: int = 1000, days: int = 365) -> None:
    """Fill the database with fake conversations, to try the admin activity
    panel at the size of a real instance. Refuses to run outside debug, so a
    production database never receives them."""
    if not settings.LANGUIA_DEBUG:
        raise RuntimeError("seed-activity only runs with LANGUIA_DEBUG=true")

    async with get_session() as session:
        llms = (
            await session.exec(
                select(LLMData.id).where(col(LLMData.status) == "enabled")
            )
        ).all()
        if len(llms) < 2:
            raise RuntimeError("seed-activity needs at least two enabled LLMs")

        started = time.monotonic()
        params = {
            "count": count,
            "days": days,
            "llms": list(llms),
            "categories": CATEGORIES,
            "prompts": PROMPTS,
            "comments": COMMENTS,
            "answer": ANSWER,
        }
        for statement in STATEMENTS:
            await session.execute(text(statement), params)
        await session.commit()

    logger.info(
        f"[seed] {count} comparisons over {days} days"
        f" in {time.monotonic() - started:.0f}s"
    )
