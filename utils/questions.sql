CREATE TABLE IF NOT EXISTS questions (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    model_a_name VARCHAR(500),
    --     -- Model A name
    model_b_name VARCHAR(500),
    --     -- Model B name
    question_content TEXT,
    response_a_content TEXT,
    response_b_content TEXT,
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
    msg_rank INT,
    model_pair_name JSONB,
    --     -- Message rank (optional, could be an integer or rating)
    chatbot_index INT
);

GRANT USAGE,
SELECT
    ON SEQUENCE questions_id_seq TO "languia-dev";
