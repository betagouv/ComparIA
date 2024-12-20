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
    UNION ALL
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
        model_b_name,
        archived
    )
SELECT
    al.session_hash,
    al.timestamp,
    al.conversation_a,
    al.conversation_b,
    al.model_a_name,
    al.model_b_name,
    TRUE
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
    )
    AND JSON_ARRAY_LENGTH(al.conversation_a :: JSON) = 1;