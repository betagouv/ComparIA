CREATE TABLE logs (
    time TIMESTAMP NOT NULL,
    level VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    query_params JSONB,
    path_params JSONB,
    session_hash VARCHAR(255),
    extra JSONB
);
