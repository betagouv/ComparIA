-- Init
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    model_a_name VARCHAR(500),
    --     -- Model A name
    model_b_name VARCHAR(500),
    --     -- Model B name
    conversation_a JSONB,
    --     -- Conversation A (JSONB format for the conversation's messages)
    conversation_b JSONB,
    conv_turns INT,
    --     -- Number of turns in the conversation
    system_prompt_a TEXT,
    system_prompt_b TEXT,
    conversation_pair_id VARCHAR UNIQUE,
    --     -- Unique identifier for the pair of conversations
    conv_a_id VARCHAR(500),
    --     -- Conversation A ID
    conv_b_id VARCHAR(500),
    session_hash VARCHAR(255),
    --     -- Session hash (for tracking)
    visitor_id VARCHAR(255),
    --     -- Visitor UUID (tracked user)
    ip VARCHAR(255),
    --     -- IP Address (user's IP)
    country VARCHAR(500),
    --     -- Country (optional, could be extracted from IP or provided)
    city VARCHAR(500),
    --     -- City (optional, could be extracted from IP or provided)
    model_pair_name TEXT, -- comma separated,
    opening_msg TEXT,
    selected_category VARCHAR(255),
    is_unedited_prompt BOOLEAN,
    archived BOOLEAN DEFAULT FALSE,
    -- TODO: add 'interrupted' bool field?
    mode VARCHAR(255),
    custom_models_selection JSONB,
    short_summary TEXT,
    keywords JSONB,
    categories JSONB,
    languages JSONB,
    pii_analyzed BOOLEAN DEFAULT FALSE,
    contains_pii BOOLEAN,
    conversation_a_pii_removed JSONB,
    conversation_b_pii_removed JSONB,
);

GRANT USAGE,
SELECT
    ON SEQUENCE conversations_id_seq TO "languia-dev";


GRANT USAGE,
SELECT
    ON SEQUENCE conversations_id_seq TO "languia-stg";


GRANT USAGE,
SELECT
    ON SEQUENCE conversations_id_seq TO "languia-ro-stg";

GRANT SELECT ON TABLE conversations TO "languia-ro-stg";

GRANT ALL PRIVILEGES ON TABLE conversations TO "languia-stg";


-- 02/04/2025
ALTER TABLE conversations ADD COLUMN total_conv_a_output_tokens INT;
ALTER TABLE conversations ADD COLUMN total_conv_b_output_tokens INT;
ALTER TABLE conversations ADD COLUMN model_a_params JSON;
ALTER TABLE conversations ADD COLUMN model_b_params JSON;
ALTER TABLE conversations ADD COLUMN total_conv_a_kwh FLOAT;
ALTER TABLE conversations ADD COLUMN total_conv_b_kwh FLOAT;

-- 14/04/2025
ALTER TABLE conversations ADD COLUMN ip_map VARCHAR(255);
ALTER TABLE conversations DROP COLUMN model_a_params;
ALTER TABLE conversations DROP COLUMN model_b_params;
ALTER TABLE conversations ADD COLUMN model_a_total_params FLOAT;
ALTER TABLE conversations ADD COLUMN model_a_active_params FLOAT;
ALTER TABLE conversations ADD COLUMN model_b_active_params FLOAT;
ALTER TABLE conversations ADD COLUMN model_b_total_params FLOAT;
ALTER TABLE conversations ADD COLUMN postprocess_failed BOOLEAN DEFAULT FALSE;

-- 09/10/2025
-- ALTER TABLE conversations DROP COLUMN model_a_total_params;
-- ALTER TABLE conversations DROP COLUMN model_b_total_params;
-- ALTER TABLE conversations DROP COLUMN model_a_active_params;
-- ALTER TABLE conversations DROP COLUMN model_b_active_params;
-- ALTER TABLE conversations DROP COLUMN total_conv_a_kwh;
-- ALTER TABLE conversations DROP COLUMN total_conv_b_kwh;
-- ALTER TABLE conversations DROP COLUMN total_conv_a_output_tokens;
-- ALTER TABLE conversations DROP COLUMN total_conv_b_output_tokens;
-- ALTER TABLE conversations DROP COLUMN country;
-- ALTER TABLE conversations DROP COLUMN city;

-- FIXME: fix or drop
    -- selected_category VARCHAR(255),
    -- is_unedited_prompt BOOLEAN,