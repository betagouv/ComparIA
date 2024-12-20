-- This is a Materialized view: it needs to be refreshed manually!
-- Drop the existing materialized view
DROP MATERIALIZED VIEW IF EXISTS matview_questions_only;

CREATE MATERIALIZED VIEW matview_questions_only AS
SELECT
    c.conversation_pair_id || '-' || (q.turn / 2) :: TEXT AS question_id,
    c.timestamp AS timestamp,
    q.msg ->> 'content' AS question_content,
    c.conv_turns AS conv_turns,
    c.template AS template,
    c.conversation_pair_id AS conversation_pair_id,
    c.session_hash AS session_hash,
    c.visitor_id AS visitor_id,
    c.ip AS ip,
    c.country AS country,
    c.city AS city,
    (q.turn / 2) :: INT AS msg_rank,
    c.model_pair_name AS model_pair_name,
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

-- Grant permissions
GRANT
SELECT
    ON TABLE matview_questions_only TO "languia-ro-stg";

GRANT ALL PRIVILEGES ON TABLE matview_questions_only TO "languia-stg";

CREATE OR REPLACE FUNCTION refresh_matview_questions_only()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW matview_questions_only;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

Then, grant execution rights to the user:

GRANT EXECUTE ON FUNCTION refresh_matview_questions_only() TO "languia-stg";