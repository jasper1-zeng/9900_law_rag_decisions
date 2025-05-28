#!/bin/bash
set -e

# Path to the dump file
DUMP_FILE=/dumps/satdata.dump

# Check if dump file exists
if [ ! -f "$DUMP_FILE" ]; then
    echo "Dump file not found at $DUMP_FILE. Skipping restore."
    exit 0
fi

# Database connection details - use the local socket since we're in the same container
export PGHOST=/var/run/postgresql
export PGUSER=postgres
export PGPASSWORD=postgres
export PGDATABASE=satdata

# Wait until PostgreSQL is ready
until pg_isready; do
    echo "Postgres is unavailable - sleeping"
    sleep 1
done

echo "Restoring database from $DUMP_FILE..."
pg_restore -v --no-owner --no-privileges --clean --if-exists -d satdata "$DUMP_FILE"

echo "Database restore completed." 