CREATE TABLE table_counts (
    votes_count BIGINT NOT NULL DEFAULT 0,
    reactions_count BIGINT NOT NULL DEFAULT 0
);

INSERT INTO table_counts (votes_count, reactions_count)
SELECT (SELECT COUNT(*) FROM votes) AS votes_initial_count,
       (SELECT COUNT(*) FROM reactions) AS reactions_initial_count;

-- Trigger for INSERT on votes
CREATE OR REPLACE FUNCTION increment_votes_count() RETURNS TRIGGER AS $$
BEGIN
    UPDATE table_counts SET votes_count = votes_count + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER votes_insert_trigger
AFTER INSERT ON votes
FOR EACH ROW EXECUTE FUNCTION increment_votes_count();

-- Trigger for INSERT on reactions
CREATE OR REPLACE FUNCTION increment_reactions_count() RETURNS TRIGGER AS $$
BEGIN
    UPDATE table_counts SET reactions_count = reactions_count + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER reactions_insert_trigger
AFTER INSERT ON reactions
FOR EACH ROW EXECUTE FUNCTION increment_reactions_count();

-- Trigger for DELETE on reactions
CREATE OR REPLACE FUNCTION decrement_reactions_count() RETURNS TRIGGER AS $$
BEGIN
    UPDATE table_counts SET reactions_count = reactions_count - 1;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER reactions_delete_trigger
AFTER DELETE ON reactions
FOR EACH ROW EXECUTE FUNCTION decrement_reactions_count();