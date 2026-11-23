#!/usr/bin/env bash
# ============================================================
# SupportPilot AI — PostgreSQL Restore Script
# Usage: ./scripts/restore_db.sh <path_to_backup_file.sql.gz>
# ============================================================
set -euo pipefail

if [ -z "${1:-}" ]; then
  echo "Error: Path to backup file required."
  echo "Usage: $0 ./backups/postgres/supportpilot_backup_YYYYMMDD_HHMMSS.sql.gz"
  exit 1
fi

BACKUP_FILE="$1"
CONTAINER_NAME="${POSTGRES_CONTAINER:-supportpilot_postgres_prod}"
DB_USER="${POSTGRES_USER:-supportpilot_admin}"
DB_NAME="${POSTGRES_DB:-supportpilot_prod}"

if [ ! -f "${BACKUP_FILE}" ]; then
  echo "Error: Backup file '${BACKUP_FILE}' not found."
  exit 1
fi

echo "WARNING: Restoring will overwrite existing data in '${DB_NAME}'."
read -p "Are you sure you want to proceed? (yes/no): " CONFIRM
if [ "${CONFIRM}" != "yes" ]; then
  echo "Restore aborted by user."
  exit 0
fi

echo "==> [$(date)] Restoring database from: ${BACKUP_FILE}..."
gunzip -c "${BACKUP_FILE}" | docker exec -i "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}"

echo "==> Database restore completed successfully."
