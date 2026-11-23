#!/usr/bin/env bash
# ============================================================
# SupportPilot AI — PostgreSQL Automated Backup Script
# Usage: ./scripts/backup_db.sh [backup_dir]
# ============================================================
set -euo pipefail

BACKUP_DIR="${1:-./backups/postgres}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/supportpilot_backup_${TIMESTAMP}.sql.gz"

CONTAINER_NAME="${POSTGRES_CONTAINER:-supportpilot_postgres_prod}"
DB_USER="${POSTGRES_USER:-supportpilot_admin}"
DB_NAME="${POSTGRES_DB:-supportpilot_prod}"
RETENTION_DAYS=14

mkdir -p "${BACKUP_DIR}"

echo "==> [$(date)] Starting SupportPilot PostgreSQL backup..."
echo "    Container: ${CONTAINER_NAME}"
echo "    Database:  ${DB_NAME}"
echo "    Target:    ${BACKUP_FILE}"

# Stream pg_dump via docker exec through gzip compression
docker exec -t "${CONTAINER_NAME}" pg_dump \
  -U "${DB_USER}" \
  -d "${DB_NAME}" \
  --clean \
  --if-exists \
  --no-owner \
  --no-privileges | gzip -9 > "${BACKUP_FILE}"

BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
echo "==> Backup completed successfully (${BACKUP_SIZE}): ${BACKUP_FILE}"

# Prune older backups beyond retention window
echo "==> Pruning backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -name "supportpilot_backup_*.sql.gz" -mtime +${RETENTION_DAYS} -delete

echo "==> Backup procedure finished."
