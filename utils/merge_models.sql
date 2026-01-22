-- Allow migration of old model names (rename model with old name to new name)
UPDATE "public"."conversations"
SET
    -- Replace either old name with the new name in model_a_name
    "model_a_name" = CASE
        WHEN "model_a_name" IN ('gemini-1.5-pro-001', 'gemini-1.5-pro-002') THEN 'gemini-1.5-pro'
        ELSE "model_a_name"
    END,

    -- Replace either old name with the new name in model_b_name
    "model_b_name" = CASE
        WHEN "model_b_name" IN ('gemini-1.5-pro-001', 'gemini-1.5-pro-002') THEN 'gemini-1.5-pro'
        ELSE "model_b_name"
    END,

    -- Nested REPLACE to handle both strings in model_pair_name
    "model_pair_name" = REPLACE(
        REPLACE("model_pair_name", 'gemini-1.5-pro-001', 'gemini-1.5-pro'),
        'gemini-1.5-pro-002', 'gemini-1.5-pro'
    )
WHERE
    "model_a_name" IN ('gemini-1.5-pro-001', 'gemini-1.5-pro-002') OR
    "model_b_name" IN ('gemini-1.5-pro-001', 'gemini-1.5-pro-002') OR
    "model_pair_name" LIKE '%gemini-1.5-pro-001%' OR
    "model_pair_name" LIKE '%gemini-1.5-pro-002%';


UPDATE "public"."votes"
SET
    -- Replace either old name with the new name in model_a_name
    "model_a_name" = CASE
        WHEN "model_a_name" IN ('gemini-1.5-pro-001', 'gemini-1.5-pro-002') THEN 'gemini-1.5-pro'
        ELSE "model_a_name"
    END,

    -- Replace either old name with the new name in model_b_name
    "model_b_name" = CASE
        WHEN "model_b_name" IN ('gemini-1.5-pro-001', 'gemini-1.5-pro-002') THEN 'gemini-1.5-pro'
        ELSE "model_b_name"
    END,

    -- Replace either old name with the new name in chosen_model_name
    "chosen_model_name" = CASE
        WHEN "chosen_model_name" IN ('gemini-1.5-pro-001', 'gemini-1.5-pro-002') THEN 'gemini-1.5-pro'
        ELSE "chosen_model_name"
    END
WHERE
    "model_a_name" IN ('gemini-1.5-pro-001', 'gemini-1.5-pro-002') OR
    "model_b_name" IN ('gemini-1.5-pro-001', 'gemini-1.5-pro-002') OR
    "chosen_model_name" IN ('gemini-1.5-pro-001', 'gemini-1.5-pro-002');

UPDATE "public"."reactions"
SET
    -- Replace either old name with the new name in model_a_name
    "model_a_name" = CASE
        WHEN "model_a_name" IN ('gemini-1.5-pro-001', 'gemini-1.5-pro-002') THEN 'gemini-1.5-pro'
        ELSE "model_a_name"
    END,

    -- Replace either old name with the new name in model_b_name
    "model_b_name" = CASE
        WHEN "model_b_name" IN ('gemini-1.5-pro-001', 'gemini-1.5-pro-002') THEN 'gemini-1.5-pro'
        ELSE "model_b_name"
    END,

    -- Replace either old name with the new name in refers_to_model
    "refers_to_model" = CASE
        WHEN "refers_to_model" IN ('gemini-1.5-pro-001', 'gemini-1.5-pro-002') THEN 'gemini-1.5-pro'
        ELSE "refers_to_model"
    END
WHERE
    "model_a_name" IN ('gemini-1.5-pro-001', 'gemini-1.5-pro-002') OR
    "model_b_name" IN ('gemini-1.5-pro-001', 'gemini-1.5-pro-002') OR
    "refers_to_model" IN ('gemini-1.5-pro-001', 'gemini-1.5-pro-002');