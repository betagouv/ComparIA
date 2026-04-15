#!/bin/bash
set -e

echo "Checking for backup file..."

if [ ! -f /backup/backup.dump ]; then
    echo "WARNING: No backup.dump file found in ./data/ directory"
    echo "Skipping restore - empty database will be created"
    exit 0
fi

echo "Backup file found, starting restore..."

# Wait for postgres to be ready
until pg_isready -U postgres; do
    echo "Waiting for PostgreSQL to be ready..."
    sleep 2
done

echo "PostgreSQL is ready, restoring backup..."

# Restore the custom format backup
# -U postgres: user
# -d languia: database
# -v: verbose
# --no-owner: skip ownership restoration
# --no-acl: skip access privileges restoration
pg_restore -U postgres -d languia -v --no-owner --no-acl /backup/backup.dump || {
    echo "WARNING: pg_restore exited with errors. This may be normal if some objects already exist."
    echo "Database restore completed with warnings."
}

echo "Backup restoration completed successfully!"
