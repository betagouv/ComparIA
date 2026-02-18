CREATE TABLE votes (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- Timestamp of the vote
    model_a_name VARCHAR(500) NOT NULL,
    model_b_name VARCHAR(500) NOT NULL,
    model_pair_name JSONB,
    -- model_pair_name TEXT ARRAY[2],
    chosen_model_name VARCHAR(500),
    opening_msg text NOT NULL,
    both_equal BOOLEAN,
    conversation_a JSONB NOT NULL,
    conversation_b JSONB NOT NULL,
    conv_turns INT,
    system_prompt_a TEXT,
    system_prompt_b TEXT,
    selected_category VARCHAR(255),
    is_unedited_prompt BOOLEAN,
    conversation_pair_id VARCHAR NOT NULL,
    session_hash VARCHAR(255),
    visitor_id VARCHAR(255),
    ip VARCHAR(255),
    conv_comments_a TEXT,
    conv_comments_b TEXT,
    conv_useful_a BOOLEAN,
    conv_useful_b BOOLEAN,
    conv_complete_a BOOLEAN,
    conv_complete_b BOOLEAN,
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
    archived BOOLEAN DEFAULT FALSE,
);

GRANT ALL PRIVILEGES ON TABLE votes TO "languia";
GRANT ALL PRIVILEGES ON TABLE reactions TO "languia-prd";
GRANT ALL PRIVILEGES ON TABLE logs TO "languia";
GRANT ALL PRIVILEGES ON TABLE conversations TO "languia";


GRANT USAGE, SELECT ON SEQUENCE votes_id_seq TO "languia";
