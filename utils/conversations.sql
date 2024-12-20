

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
    template JSONB,
    --     -- Template data (JSONB format)
    conversation_pair_id VARCHAR,
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