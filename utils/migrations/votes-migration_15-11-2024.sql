INSERT INTO
    votes (
        timestamp,
        model_a_name,
        model_b_name,
        chosen_model_name,
        opening_msg,
        conversation_a,
        conversation_b,
        conv_turns,
        template,
        selected_category,
        is_unedited_prompt,
        conversation_pair_id,
        session_hash,
        visitor_id,
        ip,
        conv_comments_a,
        conv_comments_b,
        -- Add any other new fields here
        conv_useful_a,
        conv_useful_b,
        conv_creative_a,
        conv_creative_b,
        conv_clear_formatting_a,
        conv_clear_formatting_b,
        conv_incorrect_a,
        conv_incorrect_b,
        conv_superficial_a,
        conv_superficial_b,
        conv_instructions_not_followed_a,
        conv_instructions_not_followed_b,
        model_pair_name
    )
SELECT
    tstamp AS timestamp,
    -- Mapping `tstamp` to `timestamp`
    model_a_name,
    model_b_name,
    chosen_model_name,
    opening_prompt AS opening_msg,
    -- Renaming `opening_prompt` to `opening_msg`
    conversation_a,
    conversation_b,
    turns AS conv_turns,
    -- Mapping `turns` to `conv_turns`
    template,
    selected_category,
    is_unedited_prompt,
    uuid AS conversation_pair_id,
    -- Mapping old `uuid` to `conversation_pair_id`
    session_hash,
    visitor_uuid AS visitor_id,
    ip,
    comments_a AS conv_comments_a,
    -- Renaming `comments_a` to `conv_comments_a`
    comments_b AS conv_comments_b,
    -- Renaming `comments_b` to `conv_comments_b`
    -- Parsing details_a and details_b to populate boolean fields
    -- For `details_a`, assuming it contains a comma-separated string of values like 'useful,creative,incorrect'
    CASE
        WHEN details_a_positive LIKE '%useful%' THEN TRUE
        ELSE FALSE
    END AS conv_useful_a,
    CASE
        WHEN details_b_positive LIKE '%useful%' THEN TRUE
        ELSE FALSE
    END AS conv_useful_b,
    CASE
        WHEN details_a_positive LIKE '%creative%' THEN TRUE
        ELSE FALSE
    END AS conv_creative_a,
    CASE
        WHEN details_b_positive LIKE '%creative%' THEN TRUE
        ELSE FALSE
    END AS conv_creative_b,
    CASE
        WHEN details_a_positive LIKE '%clear-formatting%' THEN TRUE
        ELSE FALSE
    END AS conv_clear_formatting_a,
    CASE
        WHEN details_b_positive LIKE '%clear-formatting%' THEN TRUE
        ELSE FALSE
    END AS conv_clear_formatting_b,
    CASE
        WHEN details_a_negative LIKE '%hallucinations%' THEN TRUE
        WHEN details_a_negative LIKE '%incorrect%' THEN TRUE
        ELSE FALSE
    END AS conv_incorrect_a,
    CASE
        WHEN details_b_negative LIKE '%hallucinations%' THEN TRUE
        WHEN details_b_negative LIKE '%incorrect%' THEN TRUE
        ELSE FALSE
    END AS conv_incorrect_b,
    CASE
        WHEN details_a_negative LIKE '%superficial%' THEN TRUE
        ELSE FALSE
    END AS conv_superficial_a,
    CASE
        WHEN details_b_negative LIKE '%superficial%' THEN TRUE
        ELSE FALSE
    END AS conv_superficial_b,
    CASE
        WHEN details_a_negative LIKE '%instructions-not-followed%' THEN TRUE
        ELSE FALSE
    END AS conv_instructions_not_followed_a,
    CASE
        WHEN details_b_negative LIKE '%instructions-not-followed%' THEN TRUE
        ELSE FALSE
    END AS conv_instructions_not_followed_b,
    ARRAY [
    jsonb_object_keys(model_pair_name)::TEXT
] AS model_pair_name
FROM
    old_votes;