#!/usr/bin/env bash
# ============================================================
# SupportPilot AI — GCP Compute Engine Deployment Script
# Target: Ubuntu 24.04 LTS on Google Compute Engine
# ============================================================
#
# Usage (from the GCE VM after cloning repo):
#   chmod +x scripts/deploy_gcp.sh
#   sudo ./scripts/deploy_gcp.sh
#
# Or run via startup-script on instance creation (see GCP_DEPLOYMENT.md)
# ============================================================

set -euo pipefail

# ── Colors ───────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()    { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }
section() { echo -e "\n${GREEN}══════════════════════════════════════${NC}"; info "$*"; }

# ── Config (override via environment) ────────────────────────
APP_DIR="${APP_DIR:-/opt/supportpilot}"
GIT_REPO="${GIT_REPO:-https://github.com/Subhranshu-sekhar-Patra/SupportPilot-AI.git}"
GCP_PROJECT_ID="${GCP_PROJECT_ID:-}"
GCS_BUCKET_NAME="${GCS_BUCKET_NAME:-}"
GCP_SA_EMAIL="${GCP_SA_EMAIL:-}"        # Service account e-mail
SECRET_NAME_PREFIX="${SECRET_NAME_PREFIX:-supportpilot}"
DOMAIN_APP="${DOMAIN_APP:-app.yourdomain.com}"
DOMAIN_API="${DOMAIN_API:-api.yourdomain.com}"
DOMAIN_N8N="${DOMAIN_N8N:-n8n.yourdomain.com}"
ACME_EMAIL="${ACME_EMAIL:-admin@yourdomain.com}"

# ── Root check ───────────────────────────────────────────────
[[ "$EUID" -ne 0 ]] && error "Please run as root (sudo)."

# ══════════════════════════════════════════════════════════════
# PHASE 1 — System Preparation
# ══════════════════════════════════════════════════════════════
section "Phase 1: System Preparation"

apt-get update -q
apt-get install -y --no-install-recommends \
  curl wget git ca-certificates gnupg lsb-release ufw \
  jq python3 python3-pip apt-transport-https

# Configure swap if RAM <= 8GB
TOTAL_RAM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
if [[ $TOTAL_RAM_KB -lt 8388608 ]]; then
  if ! swapon --show | grep -q /swapfile; then
    info "Adding 4 GB swap space..."
    fallocate -l 4G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    info "Swap configured."
  fi
fi

# ── UFW Firewall ─────────────────────────────────────────────
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP (Caddy ACME challenge)
ufw allow 443/tcp   # HTTPS
ufw --force enable
info "UFW configured: allow 22, 80, 443."

# ══════════════════════════════════════════════════════════════
# PHASE 2 — Docker Engine
# ══════════════════════════════════════════════════════════════
section "Phase 2: Docker Engine"

if ! command -v docker &>/dev/null; then
  info "Installing Docker..."
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
    gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -q
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker
  info "Docker $(docker --version) installed."
else
  info "Docker already installed: $(docker --version)"
fi

# ══════════════════════════════════════════════════════════════
# PHASE 3 — Google Cloud SDK (gcloud)
# ══════════════════════════════════════════════════════════════
section "Phase 3: Google Cloud SDK"

if ! command -v gcloud &>/dev/null; then
  info "Installing gcloud CLI..."
  curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | \
    gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
  echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" \
    > /etc/apt/sources.list.d/google-cloud-sdk.list
  apt-get update -q && apt-get install -y google-cloud-cli
  info "gcloud installed."
fi

# ══════════════════════════════════════════════════════════════
# PHASE 4 — Clone / Update Repository
# ══════════════════════════════════════════════════════════════
section "Phase 4: Repository Setup"

if [[ -d "${APP_DIR}/.git" ]]; then
  info "Repository exists — pulling latest changes..."
  git -C "${APP_DIR}" pull --rebase origin main
else
  info "Cloning repository to ${APP_DIR}..."
  git clone "${GIT_REPO}" "${APP_DIR}"
fi

chown -R root:docker "${APP_DIR}" 2>/dev/null || true
chmod -R g+rw "${APP_DIR}" 2>/dev/null || true

# ══════════════════════════════════════════════════════════════
# PHASE 5 — Pull Secrets from Google Secret Manager
# ══════════════════════════════════════════════════════════════
section "Phase 5: Secrets from Google Secret Manager"

SECRETS_DIR="${APP_DIR}/secrets"
mkdir -p "${SECRETS_DIR}"
chmod 700 "${SECRETS_DIR}"

# Helper function to fetch a secret
fetch_secret() {
  local secret_name="$1"
  local env_var="$2"
  local value
  value=$(gcloud secrets versions access latest \
    --secret="${secret_name}" \
    --project="${GCP_PROJECT_ID}" 2>/dev/null) || {
    warn "Secret '${secret_name}' not found in Secret Manager."
    return 1
  }
  echo "${env_var}=${value}"
}

if [[ -n "$GCP_PROJECT_ID" ]]; then
  info "Fetching secrets from Secret Manager (project: ${GCP_PROJECT_ID})..."
  ENV_GCP="${APP_DIR}/.env.gcp"
  cp "${APP_DIR}/.env.gcp.example" "${ENV_GCP}" 2>/dev/null || touch "${ENV_GCP}"
  chmod 600 "${ENV_GCP}"

  declare -A secret_map=(
    ["${SECRET_NAME_PREFIX}-secret-key"]="SECRET_KEY"
    ["${SECRET_NAME_PREFIX}-db-password"]="POSTGRES_PASSWORD"
    ["${SECRET_NAME_PREFIX}-gemini-api-key"]="GEMINI_API_KEY"
    ["${SECRET_NAME_PREFIX}-n8n-api-key"]="N8N_API_KEY"
    ["${SECRET_NAME_PREFIX}-n8n-encryption-key"]="N8N_ENCRYPTION_KEY"
    ["${SECRET_NAME_PREFIX}-n8n-basic-auth-pw"]="N8N_BASIC_AUTH_PASSWORD"
  )

  for secret_name in "${!secret_map[@]}"; do
    env_var="${secret_map[$secret_name]}"
    value=$(gcloud secrets versions access latest \
      --secret="${secret_name}" \
      --project="${GCP_PROJECT_ID}" 2>/dev/null) || { warn "Secret '${secret_name}' not found."; continue; }
    # Set or replace in .env.gcp
    if grep -q "^${env_var}=" "${ENV_GCP}"; then
      sed -i "s|^${env_var}=.*|${env_var}=${value}|" "${ENV_GCP}"
    else
      echo "${env_var}=${value}" >> "${ENV_GCP}"
    fi
    info "Loaded: ${secret_name} → ${env_var}"
  done

  # Inject GCS and project variables
  sed -i "s|^GCP_PROJECT_ID=.*|GCP_PROJECT_ID=${GCP_PROJECT_ID}|" "${ENV_GCP}"
  [[ -n "$GCS_BUCKET_NAME" ]] && sed -i "s|^GCS_BUCKET_NAME=.*|GCS_BUCKET_NAME=${GCS_BUCKET_NAME}|" "${ENV_GCP}"

  # Inject domains
  sed -i "s|^DOMAIN_APP=.*|DOMAIN_APP=${DOMAIN_APP}|" "${ENV_GCP}"
  sed -i "s|^DOMAIN_API=.*|DOMAIN_API=${DOMAIN_API}|" "${ENV_GCP}"
  sed -i "s|^DOMAIN_N8N=.*|DOMAIN_N8N=${DOMAIN_N8N}|" "${ENV_GCP}"
  sed -i "s|^ACME_EMAIL=.*|ACME_EMAIL=${ACME_EMAIL}|" "${ENV_GCP}"
  sed -i "s|^NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=https://${DOMAIN_API}|" "${ENV_GCP}"

  info "Environment file written: ${ENV_GCP}"

  # Download service account key if SA email provided
  if [[ -n "$GCP_SA_EMAIL" ]]; then
    info "Note: Service account key must be pre-placed at ${SECRETS_DIR}/gcp-sa-key.json"
    info "To create a new key: gcloud iam service-accounts keys create ${SECRETS_DIR}/gcp-sa-key.json --iam-account=${GCP_SA_EMAIL}"
  fi
else
  warn "GCP_PROJECT_ID not set — skipping Secret Manager fetch. Ensure .env.gcp is configured manually."
fi

# ══════════════════════════════════════════════════════════════
# PHASE 6 — Build and Launch Docker Compose Stack
# ══════════════════════════════════════════════════════════════
section "Phase 6: Build & Launch Docker Compose"

cd "${APP_DIR}"

info "Building images..."
docker compose -f docker-compose.gcp.yml build --pull

info "Starting services..."
docker compose -f docker-compose.gcp.yml up -d

info "Waiting 30s for PostgreSQL to become healthy..."
sleep 30

info "Running database migrations..."
docker compose -f docker-compose.gcp.yml exec -T backend python -m alembic upgrade head

info "Creating Super Admin account..."
docker compose -f docker-compose.gcp.yml exec -T backend \
  python -m app.scripts.create_superadmin \
  --email "${SUPERADMIN_EMAIL:-admin@yourdomain.com}" \
  --password "${SUPERADMIN_PASSWORD:-ChangeMe123!}" \
  --name "Platform Administrator" 2>/dev/null || warn "Super admin may already exist — skipping."

# ══════════════════════════════════════════════════════════════
# PHASE 7 — Configure Automated Backups
# ══════════════════════════════════════════════════════════════
section "Phase 7: Automated Backups (Cron)"

chmod +x "${APP_DIR}/scripts/backup_gcs.sh"

CRON_LINE="0 2 * * * GCS_BUCKET_NAME=${GCS_BUCKET_NAME} GCP_PROJECT_ID=${GCP_PROJECT_ID} POSTGRES_USER=${POSTGRES_USER:-supportpilot_admin} POSTGRES_DB=${POSTGRES_DB:-supportpilot_prod} ${APP_DIR}/scripts/backup_gcs.sh >> /var/log/supportpilot_backup.log 2>&1"

(crontab -l 2>/dev/null | grep -v "backup_gcs.sh"; echo "${CRON_LINE}") | crontab -
info "Daily backup cron configured (02:00 UTC → gs://${GCS_BUCKET_NAME:-YOUR_BUCKET}/postgres-backups/)."

# ══════════════════════════════════════════════════════════════
# PHASE 8 — Verification
# ══════════════════════════════════════════════════════════════
section "Phase 8: Deployment Verification"

sleep 15
info "Container status:"
docker compose -f "${APP_DIR}/docker-compose.gcp.yml" ps

info "Health check:"
docker compose -f "${APP_DIR}/docker-compose.gcp.yml" exec -T backend \
  curl -sf http://localhost:8000/health && echo "" || warn "Backend health check failed — check logs."

echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  SupportPilot AI deployed successfully on GCP!         ${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo ""
echo "  Frontend   : https://${DOMAIN_APP}"
echo "  Backend API: https://${DOMAIN_API}"
echo "  n8n        : https://${DOMAIN_N8N}"
echo "  Swagger    : https://${DOMAIN_API}/docs (dev mode only)"
echo ""
echo "  Logs       : docker compose -f ${APP_DIR}/docker-compose.gcp.yml logs -f"
echo "  Update     : git -C ${APP_DIR} pull && docker compose -f ${APP_DIR}/docker-compose.gcp.yml up -d --build"
echo "  Backup now : ${APP_DIR}/scripts/backup_gcs.sh"
echo ""
