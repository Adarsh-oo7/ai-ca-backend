#!/bin/bash

# Study Commander AI — Database and Media Backup Script
# Targets: Linux host environment.

set -e

BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="studycommander_backup_${TIMESTAMP}"
DB_CONTAINER="studycommander_db_prod"

echo "==> Starting Study Commander AI Backup..."
mkdir -p "$BACKUP_DIR"

# Read database env settings
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

DB_NAME=${DB_NAME:-studycommander}
DB_USER=${DB_USER:-postgres}
DB_PASS=${DB_PASSWORD:-postgres}

# 1. Export Postgres Database
echo "  1. Dumping database schema & records..."
docker exec -t "$DB_CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" > "${BACKUP_DIR}/${BACKUP_NAME}.sql"

# 2. Package database dump and user uploaded libraries
echo "  2. Packing files & reference libraries into archive..."
tar -czf "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz" \
    -C "$BACKUP_DIR" "${BACKUP_NAME}.sql" \
    -C "../backend" "media" || true

# 3. Clean up the raw SQL file
rm "${BACKUP_DIR}/${BACKUP_NAME}.sql"

echo "==> Backup completed successfully!"
echo "    Archive file: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"

# Optional: keep only the last 10 backups
cd "$BACKUP_DIR"
ls -t *.tar.gz | tail -n +11 | xargs rm -- {} 2>/dev/null || true
echo "    Maintained rotation (kept last 10 backup archives)."
