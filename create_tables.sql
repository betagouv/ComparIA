CREATE TABLE logs (
    time TIMESTAMP NOT NULL,
    level VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    query_params JSONB,
    path_params JSONB,
    session_hash VARCHAR(255),
    extra JSONB
);

-- CREATE TABLE
--     old_votes (
--         tstamp TIMESTAMP NOT NULL,
--         model_a_name VARCHAR(255) NOT NULL,
--         model_b_name VARCHAR(255) NOT NULL,
--         model_pair_name JSONB NOT NULL,
--         chosen_model_name VARCHAR(255),
--         both_equal BOOLEAN NOT NULL,
--         opening_prompt text NOT NULL,
--         conversation_a JSONB NOT NULL,
--         conversation_b JSONB NOT NULL,
--         turns INT,
--         selected_category VARCHAR(255),
--         is_unedited_prompt BOOLEAN,
--         template JSONB,
--         uuid VARCHAR NOT NULL,
--         ip VARCHAR(255),
--         session_hash VARCHAR(255),
--         visitor_uuid VARCHAR(255),
--         details_a_positive VARCHAR(500),
--         details_a_negative VARCHAR(500),
--         details_b_positive VARCHAR(500),
--         details_b_negative VARCHAR(500),
--         comments_a TEXT,
--         comments_b TEXT,
--         extra JSONB
--     );
CREATE TABLE votes (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- Timestamp of the vote
    model_a_name VARCHAR(500) NOT NULL,
    model_b_name VARCHAR(500) NOT NULL,
    -- model_pair_name JSONB NOT NULL,
    chosen_model_name VARCHAR(500),
    opening_msg text NOT NULL,
    -- both_equal BOOLEAN NOT NULL,
    conversation_a JSONB NOT NULL,
    conversation_b JSONB NOT NULL,
    conv_turns INT,
    template JSONB,
    selected_category VARCHAR(255),
    is_unedited_prompt BOOLEAN,
    conversation_pair_id VARCHAR NOT NULL,
    session_hash VARCHAR(255),
    visitor_id VARCHAR(255),
    ip VARCHAR(255),
    conv_comments_a TEXT,
    conv_comments_b TEXT conv_useful_a BOOLEAN,
    conv_useful_b BOOLEAN,
    conv_creative_a BOOLEAN,
    conv_creative_b BOOLEAN,
    conv_clear_formatting_a BOOLEAN,
    conv_clear_formatting_b BOOLEAN,
    conv_incorrect_a BOOLEAN,
    conv_incorrect_b BOOLEAN,
    conv_superficial_a BOOLEAN,
    conv_superficial_b BOOLEAN,
    conv_instructions_not_followed_a BOOLEAN,
    conv_instructions_not_followed_b BOOLEAN,
);

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
    -- Message rank (optional, could be an integer or rating)
    CONSTRAINT unique_conversation_pair UNIQUE (refers_to_conv_id, msg_index)
);

GRANT USAGE, SELECT ON SEQUENCE reactions_id_seq TO "languia-dev";

-- Don't forget to add rights on sequences

-- GRANT USAGE, SELECT ON SEQUENCE votes_id_seq TO "languia-dev";