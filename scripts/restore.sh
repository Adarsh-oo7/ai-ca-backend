#!/bin/bash

# Study Commander AI — Restore Script
# Usage: ./scripts/restore.sh ./backups/studycommander_backup_YYYYMMDD_HHMMSS.tar.gz

set -e

BACKUP_FILE=$1
DB_CONTAINER="studycommander_db_prod"
TEMP_DIR="./restore_temp"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <path-to-backup-tar-gz>"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "[ERROR] Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "==> Restoring Study Commander AI from $BACKUP_FILE..."

# Load DB environments
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

DB_NAME=${DB_NAME:-studycommander}
DB_USER=${DB_USER:-postgres}

# Create temp dir
mkdir -p "$TEMP_DIR"

# 1. Unpack archive
echo "  1. Unpacking backup archive..."
tar -xzf "$BACKUP_FILE" -C "$TEMP_DIR"

# Find SQL file
SQL_FILE=$(find "$TEMP_DIR" -name "*.sql" | head -n 1)

if [ -z "$SQL_FILE" ]; then
    echo "[ERROR] No SQL database dump file found in the archive!"
    rm -rf "$TEMP_DIR"
    exit 1
fi

# 2. Restore Database
echo "  2. Restoring database tables..."
# Terminate other connections to enable db drop/recreate
docker exec -t "$DB_CONTAINER" psql -U "$DB_USER" -d postgres -c "SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = '$DB_NAME' AND pid <> pg_backend_pid();" || true
docker exec -t "$DB_CONTAINER" dropdb -U "$DB_USER" --if-exists "$DB_NAME" || true
docker exec -t "$DB_CONTAINER" createdb -U "$DB_USER" "$DB_NAME" || true

docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" < "$SQL_FILE"

# 3. Restore Media uploaded files
if [ -d "${TEMP_DIR}/media" ]; then
    echo "  3. Restoring media libraries..."
    # Copy files directly to django container or back to host media path
    docker cp "${TEMP_DIR}/media" studycommander_backend_prod:/app/
fi

# Clean up
echo "  4. Cleaning temporary records..."
rm -rf "$TEMP_DIR"

echo "==> System successfully restored and online!"
