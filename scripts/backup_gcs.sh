#!/usr/bin/env bash
# ============================================================
# SupportPilot AI — GCP Database Backup Script
# Backs up PostgreSQL to Google Cloud Storage
# ============================================================
# Usage:
#   ./scripts/backup_gcs.sh [GCS_BUCKET_NAME] [GCP_PROJECT_ID]
#
# Environment variables (can also be set in .env.gcp):
#   GCS_BUCKET_NAME   - GCS bucket for backups
#   GCP_PROJECT_ID    - GCP project ID
#   POSTGRES_USER     - PostgreSQL username (default: supportpilot_admin)
#   POSTGRES_DB       - PostgreSQL database name (default: supportpilot_prod)
# ============================================================

set -euo pipefail

# ── Config ───────────────────────────────────────────────────
GCS_BUCKET="${1:-${GCS_BUCKET_NAME:-}}"
GCP_PROJECT="${2:-${GCP_PROJECT_ID:-}}"
PG_CONTAINER="${POSTGRES_CONTAINER:-supportpilot_postgres_gcp}"
PG_USER="${POSTGRES_USER:-supportpilot_admin}"
PG_DB="${POSTGRES_DB:-supportpilot_prod}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="supportpilot_postgres_${TIMESTAMP}.sql.gz"
LOCAL_TMP="/tmp/${BACKUP_FILE}"

# ── Validation ───────────────────────────────────────────────
if [[ -z "$GCS_BUCKET" ]]; then
  echo "ERROR: GCS_BUCKET_NAME is required (env var or first argument)." >&2
  exit 1
fi

echo "==> [$(date -u '+%Y-%m-%dT%H:%M:%SZ')] Starting PostgreSQL backup..."
echo "    Container : ${PG_CONTAINER}"
echo "    Database  : ${PG_DB}"
echo "    GCS target: gs://${GCS_BUCKET}/postgres-backups/${BACKUP_FILE}"

# ── Dump ─────────────────────────────────────────────────────
docker exec -t "${PG_CONTAINER}" pg_dump \
  -U "${PG_USER}" \
  -d "${PG_DB}" \
  --clean --if-exists --no-owner --no-privileges \
  | gzip -9 > "${LOCAL_TMP}"

BACKUP_SIZE=$(du -sh "${LOCAL_TMP}" | cut -f1)
echo "    Backup size: ${BACKUP_SIZE}"

# ── Upload to GCS ────────────────────────────────────────────
gcloud storage cp "${LOCAL_TMP}" \
  "gs://${GCS_BUCKET}/postgres-backups/${BACKUP_FILE}" \
  ${GCP_PROJECT:+--project="${GCP_PROJECT}"}

echo "    Uploaded: gs://${GCS_BUCKET}/postgres-backups/${BACKUP_FILE}"

# ── ChromaDB Vector Backup ────────────────────────────────────
CHROMA_BACKUP="supportpilot_chromadb_${TIMESTAMP}.tar.gz"
CHROMA_LOCAL_TMP="/tmp/${CHROMA_BACKUP}"

echo ""
echo "==> Backing up ChromaDB vector store..."
docker run --rm \
  --volumes-from supportpilot_chromadb_gcp \
  alpine tar -czf - -C /chroma chroma > "${CHROMA_LOCAL_TMP}" 2>/dev/null || {
    echo "    WARNING: ChromaDB backup failed — skipping (container may be restarting)"
  }

if [[ -f "${CHROMA_LOCAL_TMP}" ]]; then
  gcloud storage cp "${CHROMA_LOCAL_TMP}" \
    "gs://${GCS_BUCKET}/chromadb-backups/${CHROMA_BACKUP}" \
    ${GCP_PROJECT:+--project="${GCP_PROJECT}"}
  echo "    Uploaded: gs://${GCS_BUCKET}/chromadb-backups/${CHROMA_BACKUP}"
  rm -f "${CHROMA_LOCAL_TMP}"
fi

# ── Cleanup local temp ────────────────────────────────────────
rm -f "${LOCAL_TMP}"

# ── Prune old backups (keep 30 days) ─────────────────────────
echo ""
echo "==> Pruning backups older than 30 days..."
CUTOFF_DATE=$(date -d "30 days ago" +%Y%m%d 2>/dev/null || date -v -30d +%Y%m%d 2>/dev/null || echo "")
if [[ -n "$CUTOFF_DATE" ]]; then
  gcloud storage ls "gs://${GCS_BUCKET}/postgres-backups/" 2>/dev/null | while read -r uri; do
    fname=$(basename "$uri")
    file_date=$(echo "$fname" | grep -oP '\d{8}' | head -1 || echo "")
    if [[ -n "$file_date" && "$file_date" < "$CUTOFF_DATE" ]]; then
      gcloud storage rm "$uri" && echo "    Deleted: $uri"
    fi
  done
fi

echo ""
echo "==> [$(date -u '+%Y-%m-%dT%H:%M:%SZ')] Backup complete."
