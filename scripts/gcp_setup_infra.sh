#!/usr/bin/env bash
# ============================================================
# SupportPilot AI — GCP Infrastructure Provisioning Script
# Creates GCP resources: GCS bucket, service account, secrets
# Run once from your local machine or Cloud Shell.
# ============================================================
# Usage:
#   chmod +x scripts/gcp_setup_infra.sh
#   GCP_PROJECT_ID=my-project ./scripts/gcp_setup_infra.sh
# ============================================================

set -euo pipefail

# ── Config ───────────────────────────────────────────────────
PROJECT_ID="${GCP_PROJECT_ID:?GCP_PROJECT_ID required}"
REGION="${GCP_REGION:-us-central1}"
SA_NAME="${SA_NAME:-supportpilot-sa}"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
BUCKET_NAME="${GCS_BUCKET_NAME:-${PROJECT_ID}-supportpilot-documents}"
BACKUP_BUCKET="${GCS_BACKUP_BUCKET:-${PROJECT_ID}-supportpilot-backups}"
KEY_DIR="${KEY_DIR:-./secrets}"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[gcp-infra]${NC} $*"; }
warn()  { echo -e "${YELLOW}[gcp-infra]${NC} $*"; }

# ── Set active project ────────────────────────────────────────
gcloud config set project "${PROJECT_ID}"

# ── Enable required GCP APIs ─────────────────────────────────
info "Enabling GCP APIs..."
gcloud services enable \
  compute.googleapis.com \
  storage.googleapis.com \
  secretmanager.googleapis.com \
  iam.googleapis.com \
  cloudresourcemanager.googleapis.com

# ── Create GCS buckets ───────────────────────────────────────
info "Creating GCS buckets..."

for bucket in "${BUCKET_NAME}" "${BACKUP_BUCKET}"; do
  if ! gcloud storage buckets describe "gs://${bucket}" --project="${PROJECT_ID}" &>/dev/null; then
    gcloud storage buckets create "gs://${bucket}" \
      --project="${PROJECT_ID}" \
      --location="${REGION}" \
      --uniform-bucket-level-access
    info "Created bucket: gs://${bucket}"
  else
    info "Bucket gs://${bucket} already exists."
  fi
done

# Set lifecycle policy: auto-delete backups after 30 days
cat > /tmp/backup_lifecycle.json <<'EOF'
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {"age": 30}
      }
    ]
  }
}
EOF
gcloud storage buckets update "gs://${BACKUP_BUCKET}" \
  --lifecycle-file=/tmp/backup_lifecycle.json
info "Backup bucket lifecycle: auto-delete after 30 days."

# ── Create Service Account ────────────────────────────────────
info "Creating service account: ${SA_EMAIL}..."

if ! gcloud iam service-accounts describe "${SA_EMAIL}" --project="${PROJECT_ID}" &>/dev/null; then
  gcloud iam service-accounts create "${SA_NAME}" \
    --display-name="SupportPilot AI Application SA" \
    --project="${PROJECT_ID}"
  info "Service account created: ${SA_EMAIL}"
else
  info "Service account already exists."
fi

# ── Grant Least-Privilege IAM Roles ──────────────────────────
info "Granting IAM roles..."

for role in \
  "roles/storage.objectAdmin" \
  "roles/secretmanager.secretAccessor"; do
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="${role}" \
    --condition=None --quiet
  info "Granted: ${role} → ${SA_EMAIL}"
done

# Restrict storage admin to SupportPilot buckets only
for bucket in "${BUCKET_NAME}" "${BACKUP_BUCKET}"; do
  gcloud storage buckets add-iam-policy-binding "gs://${bucket}" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/storage.objectAdmin"
done

# ── Create Service Account Key ────────────────────────────────
mkdir -p "${KEY_DIR}"
KEY_FILE="${KEY_DIR}/gcp-sa-key.json"
info "Creating service account key → ${KEY_FILE}..."
gcloud iam service-accounts keys create "${KEY_FILE}" \
  --iam-account="${SA_EMAIL}" \
  --project="${PROJECT_ID}"
chmod 600 "${KEY_FILE}"
info "Key saved. Add ${KEY_FILE} to .gitignore (never commit it)."

# ── Create Secrets in Secret Manager ─────────────────────────
info "Creating Secret Manager secrets (empty placeholders)..."

create_or_update_secret() {
  local name="$1"
  local value="$2"
  if ! gcloud secrets describe "${name}" --project="${PROJECT_ID}" &>/dev/null; then
    echo -n "${value}" | gcloud secrets create "${name}" \
      --data-file=- \
      --project="${PROJECT_ID}"
    info "Created secret: ${name}"
  else
    warn "Secret '${name}' already exists — update it manually with:"
    echo "  echo -n 'VALUE' | gcloud secrets versions add ${name} --data-file=- --project=${PROJECT_ID}"
  fi
}

create_or_update_secret "supportpilot-secret-key" "$(openssl rand -hex 32)"
create_or_update_secret "supportpilot-db-password" "$(openssl rand -base64 32 | tr -d '=+/')"
create_or_update_secret "supportpilot-n8n-api-key" "$(openssl rand -hex 24)"
create_or_update_secret "supportpilot-n8n-encryption-key" "$(openssl rand -hex 24)"
create_or_update_secret "supportpilot-n8n-basic-auth-pw" "$(openssl rand -hex 16)"
create_or_update_secret "supportpilot-gemini-api-key" "REPLACE_WITH_GEMINI_API_KEY"
create_or_update_secret "supportpilot-postgres-db" "supportpilot_prod"
create_or_update_secret "supportpilot-postgres-user" "supportpilot_admin"

echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  GCP Infrastructure provisioned successfully!          ${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo ""
echo "  SA Email    : ${SA_EMAIL}"
echo "  SA Key      : ${KEY_FILE} (never commit!)"
echo "  Doc Bucket  : gs://${BUCKET_NAME}"
echo "  Backup Bucket: gs://${BACKUP_BUCKET}"
echo ""
echo "IMPORTANT: Set the Gemini API key in Secret Manager:"
echo "  echo -n 'AIzaSy...' | gcloud secrets versions add supportpilot-gemini-api-key \\"
echo "    --data-file=- --project=${PROJECT_ID}"
echo ""
echo "Copy the SA key to your Compute Engine VM:"
echo "  gcloud compute scp ${KEY_FILE} VM_NAME:/opt/supportpilot/secrets/gcp-sa-key.json"
echo ""
