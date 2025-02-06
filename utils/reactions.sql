CREATE TABLE reactions (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- Timestamp of the vote
    model_a_name VARCHAR(500) NOT NULL,
    -- Model A name
    model_b_name VARCHAR(500) NOT NULL,
    -- Model B name
    refers_to_model VARCHAR(500),
    -- Refers to model name (optional)
    msg_index INT NOT NULL,
    -- Message rank (optional, could be an integer or rating)
    opening_msg TEXT NOT NULL,
    -- Opening message (prompt)
    conversation_a JSONB NOT NULL,
    -- Conversation A (JSONB format for the conversation's messages)
    conversation_b JSONB NOT NULL,
    -- Conversation B (JSONB format for the conversation's messages)
    model_pos CHAR(1) CHECK (model_pos IN ('a', 'b')),
    -- Indicates the model position ('a' or 'b')
    conv_turns INT NOT NULL,
    -- Number of turns in the conversation
    template JSONB,
    -- Template data (JSONB format)
    conversation_pair_id VARCHAR NOT NULL,
    -- Unique identifier for the pair of conversations
    conv_a_id VARCHAR(500) NOT NULL,
    -- Conversation A ID
    conv_b_id VARCHAR(500) NOT NULL,
    -- Conversation B ID
    refers_to_conv_id VARCHAR(500) NOT NULL,
    -- Conversation B ID
    session_hash VARCHAR(255),
    -- Session hash (for tracking)
    visitor_id VARCHAR(255),
    -- Visitor UUID (tracked user)
    ip VARCHAR(255),
    -- IP Address (user's IP)
    country VARCHAR(500),
    -- Country (optional, could be extracted from IP or provided)
    city VARCHAR(500),
    -- City (optional, could be extracted from IP or provided)
    response_content TEXT,
    -- Content of the model's response (optional)
    question_content TEXT,
    -- Content of the question (optional)
    liked BOOLEAN,
    -- Like button (optional)
    disliked BOOLEAN,
    -- Dislike button (optional)
    comment TEXT,
    -- Free text comment (optional)
    useful BOOLEAN,
    -- Is the conversation useful? (boolean)
    creative BOOLEAN,
    -- Is the conversation creative? (boolean)
    clear_formatting BOOLEAN,
    -- Does the conversation have clear formatting? (boolean)
    incorrect BOOLEAN,
    -- Is the conversation incorrect? (boolean)
    superficial BOOLEAN,
    -- Is the conversation superficial? (boolean)
    instructions_not_followed BOOLEAN,
    -- Did the conversation not follow instructions? (boolean)
    model_pair_name JSONB,
    msg_rank INT NOT NULL,
    -- Message rank (optional, could be an integer or rating)
    chatbot_index INT NOT NULL,
    question_id VARCHAR(500),
    archived BOOLEAN DEFAULT FALSE,
    CONSTRAINT unique_conversation_pair UNIQUE (refers_to_conv_id, msg_index)
);

GRANT USAGE,
SELECT
    ON SEQUENCE reactions_id_seq TO "languia-dev";