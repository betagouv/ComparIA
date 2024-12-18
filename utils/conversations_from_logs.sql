INSERT INTO
    conversations (
        timestamp,
        model_a_name,
        model_b_name,
        conversation_a,
        conversation_b,
        template,
        conversation_pair_id,
        session_hash,
        visitor_id,
        ip,
        country,
        city,
        opening_msg,
        selected_category,
        is_unedited_prompt,
        model_pair_name,
        conv_a_id,
        conv_b_id,
        conv_turns
    )
SELECT
    v.tstamp AS timestamp,
    v.model_a_name,
    v.model_b_name,
    v.conversation_a,
    v.conversation_b,
    v.template,
    v.uuid AS conversation_pair_id,
    v.session_hash,
    v.visitor_uuid AS visitor_id,
    v.ip,
    '' AS country,
    '' AS city,
    v.opening_prompt AS opening_msg,
    v.selected_category,
    v.is_unedited_prompt,
    CONCAT(
        LEAST(v.model_a_name, v.model_b_name),
        ',',
        GREATEST(v.model_a_name, v.model_b_name)
    ) AS model_pair_name,
    SPLIT_PART(v.uuid, '-', 1) AS conv_a_id,
    -- Extract first part of uuid
    SPLIT_PART(v.uuid, '-', 2) AS conv_b_id,
    -- Extract second part of uuid
    v.turns AS conv_turns -- Number of turns in the conversation
FROM
    votes v;

WITH temp_logs AS (
    SELECT
        time AS timestamp,
        session_hash,
        'user' AS role,
        SUBSTR(message, 10) AS message_content,
        NULL AS model,
        NULL AS response_mode
    FROM
        logs
    WHERE
        message LIKE 'msg_user:%'
    UNION
    ALL
    SELECT
        time AS timestamp,
        session_hash,
        'assistant' AS role,
        TRIM(SUBSTR(message, STRPOS(message, '):') + 2)) AS message_content,
        SUBSTR(
            message,
            STRPOS(message, '(') + 1,
            STRPOS(message, '):') - STRPOS(message, '(') - 1
        ) AS model,
        SUBSTR(message, STRPOS(message, '_modele_') + 8, 1) AS response_mode
    FROM
        logs
    WHERE
        message LIKE 'response_modele_%'
),
aggregated_logs AS (
    SELECT
        t.session_hash,
        MIN(t.timestamp) AS timestamp,
        JSONB_AGG(
            JSONB_BUILD_OBJECT(
                -- 'timestamp', t.timestamp,
                'role',
                t.role,
                'content',
                t.message_content
            )
            ORDER BY
                t.timestamp
        ) FILTER (
            WHERE
                t.response_mode = 'a'
                OR t.role = 'user'
        ) AS conversation_a,
        JSONB_AGG(
            JSONB_BUILD_OBJECT(
                -- 'timestamp', t.timestamp,
                'role',
                t.role,
                'content',
                t.message_content
            )
            ORDER BY
                t.timestamp
        ) FILTER (
            WHERE
                t.response_mode = 'b'
                OR t.role = 'user'
        ) AS conversation_b,
        MAX(
            CASE
                WHEN t.response_mode = 'a' THEN t.model
            END
        ) AS model_a_name,
        MAX(
            CASE
                WHEN t.response_mode = 'b' THEN t.model
            END
        ) AS model_b_name
    FROM
        temp_logs t
    GROUP BY
        t.session_hash
)
INSERT INTO
    conversations (
        session_hash,
        timestamp,
        conversation_a,
        conversation_b,
        model_a_name,
        model_b_name
    )
SELECT
    al.session_hash,
    al.timestamp,
    al.conversation_a,
    al.conversation_b,
    al.model_a_name,
    al.model_b_name
FROM
    aggregated_logs al
WHERE
    NOT EXISTS (
        SELECT
            1
        FROM
            conversations c
        WHERE
            c.session_hash = al.session_hash
    );

UPDATE
    conversations c
SET
    conversation_pair_id = COALESCE(c.conversation_pair_id, r.conversation_pair_id),
    conv_a_id = COALESCE(c.conv_a_id, r.conv_a_id),
    -- Assuming conv_a_id exists in reactions
    conv_b_id = COALESCE(c.conv_b_id, r.conv_b_id),
    -- Assuming conv_b_id exists in reactions
    country = COALESCE(c.country, r.country),
    city = COALESCE(c.city, r.city)
FROM
    reactions r
WHERE
    c.session_hash = r.session_hash;

-- Generate missing fields (conv id especially!!)
WITH conversation_data AS (
    SELECT
        session_hash,
        REPLACE(uuid_generate_v4() :: text, '-', '') AS conv_a_id,
        REPLACE(uuid_generate_v4() :: text, '-', '') AS conv_b_id,
        json_array_length(conversation_a :: json) / 2 AS conv_turns,
        (conversation_a :: json -> 0 ->> 'content') AS opening_msg,
        model_a_name,
        model_b_name
    FROM
        conversations
    WHERE
        conv_a_id IS NULL
        OR conv_a_id = ''
),
conversation_template AS (
    SELECT
        session_hash,
        conv_a_id,
        conv_b_id,
        CONCAT(conv_a_id, '-', conv_b_id) AS conversation_pair_id,
        model_a_name,
        model_b_name,
        conv_turns,
        opening_msg
    FROM
        conversation_data
)
UPDATE
    conversations
SET
    conv_a_id = conversation_template.conv_a_id,
    conv_b_id = conversation_template.conv_b_id,
    conversation_pair_id = conversation_template.conversation_pair_id
FROM
    conversation_template
WHERE
    conversations.session_hash = conversation_template.session_hash;

WITH conversation_data AS (
    SELECT
        session_hash,
        -- REPLACE(uuid_generate_v4() :: text, '-', '') AS conv_a_id,
        -- REPLACE(uuid_generate_v4() :: text, '-', '') AS conv_b_id,
        json_array_length(conversation_a :: json) / 2 AS conv_turns,
        (conversation_a :: json -> 0 ->> 'content') AS opening_msg,
        model_a_name,
        model_b_name
    FROM
        conversations -- WHERE
        --     (
        --         conv_a_id IS NULL
        --         OR conv_a_id = ''
        --     )
),
conversation_template AS (
    SELECT
        session_hash,
        -- conv_a_id,
        -- conv_b_id,
        -- CONCAT(conv_a_id, '-', conv_b_id) AS conversation_pair_id,
        CONCAT(model_a_name, ',', model_b_name) AS model_pair_name,
        conv_turns,
        opening_msg
    FROM
        conversation_data
)

UPDATE
    conversations
SET
    -- conv_a_id = conversation_template.conv_a_id,
    -- conv_b_id = conversation_template.conv_b_id,
    -- conversation_pair_id = conversation_template.conversation_pair_id,
    model_pair_name = conversation_template.model_pair_name,
    conv_turns = conversation_template.conv_turns,
    opening_msg = conversation_template.opening_msg,
    template = '[]' :: json
FROM
    conversation_template
WHERE
    conversations.session_hash = conversation_template.session_hash;

INSERT INTO
    conversations (ip, visitor_id)
SELECT
    CASE
        WHEN message LIKE 'init_arene%' THEN SUBSTRING(
            message
            FROM
                'IP: ([\d\.]+)'
        )
        ELSE NULL
    END AS ip,
    CASE
        WHEN message LIKE 'init_arene%' THEN SUBSTRING(
            message
            FROM
                'cookie: ([\w\d\.]+)'
        )
        ELSE NULL
    END AS visitor_id
FROM
    logs
WHERE
    (
        message LIKE 'init_arene%'
        AND (
            message LIKE 'IP: %'
            OR message LIKE 'cookie: %'
        )
    )
    AND NOT EXISTS (
        SELECT
            1
        FROM
            conversations c
        WHERE
            c.ip = SUBSTRING(
                message
                FROM
                    'IP: ([\d\.]+)'
            )
            AND c.visitor_id = SUBSTRING(
                message
                FROM
                    'cookie: ([\w\d\.]+)'
            )
    );

-- UPDATE
--     conversations
-- SET
--     archived = TRUE
-- WHERE
--     conv_turns = 0
--     OR conv_turns = '0';
--
DELETE FROM
    conversations
WHERE
    conv_turns = 0
    OR conv_turns = '0';

UPDATE
    conversations
SET
    archived = TRUE
WHERE
    timestamp < DATE '2024-10-01';