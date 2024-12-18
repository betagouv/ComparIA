-- This is a Materialized view: it needs to be refreshed manually!
DROP MATERIALIZED VIEW matview_questions;

CREATE MATERIALIZED VIEW matview_questions AS
SELECT
    ROW_NUMBER() OVER () AS id,
    c.id AS conversation_id,
    c.timestamp AS timestamp,
    c.model_a_name AS model_a_name,
    c.model_b_name AS model_b_name,
    q.msg ->> 'content' AS question_content,
    -- Extract the user's question
    a.msg ->> 'content' AS response_a_content,
    -- Model A's response
    b.msg ->> 'content' AS response_b_content,
    -- Model B's response
    c.conversation_a AS conversation_a,
    -- Full JSON for conversation A
    c.conversation_b AS conversation_b,
    -- Full JSON for conversation B
    c.conv_turns AS conv_turns,
    c.template AS template,
    c.conversation_pair_id AS conversation_pair_id,
    c.conversation_pair_id || '-' || (q.turn / 2) :: TEXT AS question_id,
    c.conv_a_id AS conv_a_id,
    c.conv_b_id AS conv_b_id,
    c.session_hash AS session_hash,
    c.visitor_id AS visitor_id,
    c.ip AS ip,
    c.country AS country,
    c.city AS city,
    (q.turn / 2) :: INT AS msg_rank,
    c.model_pair_name AS model_pair_name,
    NULL AS chatbot_index -- Placeholder for chatbot index
FROM
    conversations c -- Extract the questions from both conversations
    LEFT JOIN LATERAL (
        SELECT
            msg,
            turn
        FROM
            jsonb_array_elements(c.conversation_a) WITH ORDINALITY AS m(msg, turn)
        WHERE
            m.msg ->> 'role' = 'user' -- Filter for user questions
    ) q ON true -- Extract the responses from conversation_a
    LEFT JOIN LATERAL (
        SELECT
            msg,
            turn
        FROM
            jsonb_array_elements(c.conversation_a) WITH ORDINALITY AS m(msg, turn)
        WHERE
            m.msg ->> 'role' = 'assistant' -- Filter for assistant responses
    ) a ON (q.turn / 2) :: INT + 1 = a.turn -- Match response to the corresponding question
    LEFT JOIN LATERAL (
        SELECT
            msg,
            turn
        FROM
            jsonb_array_elements(c.conversation_b) WITH ORDINALITY AS m(msg, turn)
        WHERE
            m.msg ->> 'role' = 'assistant' -- Filter for assistant responses
    ) b ON (q.turn / 2) :: INT + 1 = b.turn -- Match response to the corresponding question
WHERE
    NOT c.archived;

-- Grant permissions
GRANT
SELECT
    ON TABLE matview_questions TO "languia-ro-stg";

GRANT ALL PRIVILEGES ON TABLE matview_questions TO "languia-stg";