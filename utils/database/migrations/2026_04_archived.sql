-- Remove 'default' constraint on 'archived' on all tables
ALTER TABLE conversations ALTER COLUMN archived DROP DEFAULT;
ALTER TABLE votes ALTER COLUMN archived DROP DEFAULT;
ALTER TABLE reactions ALTER COLUMN archived DROP DEFAULT;

-- Add 'archived_reason' and 'archived_at' on all tables
ALTER TABLE conversations ADD COLUMN archived_reason VARCHAR(255);
ALTER TABLE conversations ADD COLUMN archived_at TIMESTAMP;

ALTER TABLE votes ADD COLUMN archived_reason VARCHAR(255);
ALTER TABLE votes ADD COLUMN archived_at TIMESTAMP;

ALTER TABLE reactions ADD COLUMN archived_reason VARCHAR(255);
ALTER TABLE reactions ADD COLUMN archived_at TIMESTAMP;