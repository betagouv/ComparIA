
CREATE TABLE logs (
    tstamp TIMESTAMP NOT NULL,
    level VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    query_params JSONB,
    path_params JSONB,
    session_hash VARCHAR(255),
    extra JSONB
);

 CREATE TABLE votes (
            tstamp TIMESTAMP NOT NULL,
            model_a_name VARCHAR NOT NULL,
            model_b_name VARCHAR NOT NULL,
            model_pair_name JSONB NOT NULL,
            chosen_model_name VARCHAR NOT NULL,
            intensity VARCHAR NOT NULL,
            opening_prompt VARCHAR NOT NULL,
            conversation_a JSONB NOT NULL,
            conversation_b JSONB NOT NULL,
            turns INT NOT NULL,
            selected_category VARCHAR NOT NULL,
            is_unedited_prompt BOOLEAN NOT NULL,
            template JSONB NOT NULL,
            uuid UUID NOT NULL,
            ip VARCHAR NOT NULL,
            session_hash VARCHAR NOT NULL,
            visitor_uuid UUID NOT NULL,
            relevance INT NOT NULL,
            form INT NOT NULL,
            style INT NOT NULL,
            comments TEXT NOT NULL
        );

CREATE TABLE profiles (
    tstamp TIMESTAMP NOT NULL,
    chatbot_use VARCHAR NOT NULL,
    gender VARCHAR NOT NULL,
    age VARCHAR NOT NULL,
    profession VARCHAR NOT NULL,
    session_hash VARCHAR NOT NULL,
    extra JSONB NOT NULL
);
