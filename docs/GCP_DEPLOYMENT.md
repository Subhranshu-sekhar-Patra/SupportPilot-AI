# SupportPilot AI — Google Cloud Platform Deployment Guide

This document provides end-to-end instructions for deploying SupportPilot AI on Google Compute Engine using Ubuntu 24.04 LTS, Docker Engine, Docker Compose, Caddy reverse proxy, Google Cloud Storage for document uploads, and Google Secret Manager for secrets.

---

## 1. Architecture Overview

```
                               ┌─────────────────────────────────────────────┐
                               │          Google Cloud Platform               │
                               │                                             │
                               │   ┌───────────────────────────────────────┐  │
                               │   │    Google Compute Engine VM           │  │
                               │   │    Ubuntu 24.04 LTS + Docker Engine   │  │
                               │   │                                       │  │
                               │   │  ┌─────────────┐  port 80/443        │  │
                               │   │  │  Caddy 2    │◄── Internet         │  │
                               │   │  │  Auto HTTPS │                     │  │
                               │   │  └──┬──────┬───┘                     │  │
                               │   │     │      │                          │  │
                               │   │  ┌──┘   ┌──┘                         │  │
                               │   │  ▼      ▼                             │  │
                               │   │ ┌────┐ ┌──────┐ ┌───┐               │  │
                               │   │ │Next│ │FastAPI│ │n8n│               │  │
                               │   │ │.js │ │:8000  │ │:5678│             │  │
                               │   │ └────┘ └──┬───┘ └───┘               │  │
                               │   │          │                            │  │
                               │   │  ┌───────┴────────────────┐          │  │
                               │   │  │  Internal Docker net    │          │  │
                               │   │  │  (172.30.0.0/16)        │          │  │
                               │   │  │  ┌──────────┐ ┌───────┐ │          │  │
                               │   │  │  │PostgreSQL│ │ChromaDB│ │          │  │
                               │   │  │  │ :5432    │ │ :8000  │ │          │  │
                               │   │  │  └──────────┘ └───────┘ │          │  │
                               │   │  └────────────────────────┘          │  │
                               │   └───────────────────────────────────────┘  │
                               │                                             │
                               │   ┌─────────────────────────────────────┐   │
                               │   │  Google Cloud Services               │   │
                               │   │  ┌──────────────┐ ┌───────────────┐ │   │
                               │   │  │ Cloud Storage│ │Secret Manager │ │   │
                               │   │  │  (documents) │ │   (secrets)   │ │   │
                               │   │  └──────────────┘ └───────────────┘ │   │
                               │   └─────────────────────────────────────┘   │
                               └─────────────────────────────────────────────┘
```

**Security Design:**
- PostgreSQL and ChromaDB are **never exposed publicly** — internal Docker network only
- PostgreSQL binds to `127.0.0.1:5432` only for host-level maintenance
- All secrets stored in **Google Secret Manager**, never in environment files or git
- Service account uses **least-privilege** IAM roles scoped to required buckets only
- n8n protected behind Caddy with HTTP Basic Auth
- TLS certificates issued automatically by Let's Encrypt via Caddy

---

## 2. Prerequisites

| Requirement | Minimum Spec |
|---|---|
| GCE Instance Type | `e2-standard-4` (4 vCPU, 16 GB RAM) |
| Boot Disk | 50 GB SSD Persistent Disk |
| OS | Ubuntu 24.04 LTS |
| Region | Your closest region (e.g. `us-central1`) |
| DNS | A records for `app`, `api`, `n8n` subdomains pointing to static IP |

**GCP APIs Required:**
- Compute Engine API
- Cloud Storage API
- Secret Manager API
- IAM API

---

## 3. Step 1 — Reserve a Static IP Address

```bash
# Reserve a regional static IP
gcloud compute addresses create supportpilot-ip \
  --region=us-central1 \
  --project=YOUR_PROJECT_ID

# Get the reserved IP
gcloud compute addresses describe supportpilot-ip \
  --region=us-central1 \
  --format="get(address)"
```

Configure DNS **A records** at your registrar:
- `app.yourdomain.com` → `<STATIC_IP>`
- `api.yourdomain.com` → `<STATIC_IP>`
- `n8n.yourdomain.com` → `<STATIC_IP>`

---

## 4. Step 2 — Provision GCP Infrastructure (Run Locally / Cloud Shell)

This script creates the GCS buckets, service account, IAM bindings, and Secret Manager secrets:

```bash
# Clone the repo locally (or open Cloud Shell)
git clone https://github.com/Subhranshu-sekhar-Patra/SupportPilot-AI.git
cd SupportPilot-AI

# Run infrastructure provisioning
chmod +x scripts/gcp_setup_infra.sh

GCP_PROJECT_ID=YOUR_PROJECT_ID \
GCP_REGION=us-central1 \
GCS_BUCKET_NAME=YOUR_PROJECT-supportpilot-documents \
GCS_BACKUP_BUCKET=YOUR_PROJECT-supportpilot-backups \
  ./scripts/gcp_setup_infra.sh
```

**What this script does:**
1. Enables required GCP APIs
2. Creates GCS document and backup buckets with lifecycle rules
3. Creates `supportpilot-sa` service account
4. Grants `storage.objectAdmin` (bucket-scoped) + `secretmanager.secretAccessor` roles
5. Creates service account JSON key → `./secrets/gcp-sa-key.json`
6. Creates all required Secret Manager secrets with auto-generated values

**After running, update the Gemini API key:**
```bash
echo -n "AIzaSy_YOUR_GEMINI_KEY" | gcloud secrets versions add supportpilot-gemini-api-key \
  --data-file=- --project=YOUR_PROJECT_ID
```

---

## 5. Step 3 — Create the Compute Engine VM

```bash
gcloud compute instances create supportpilot-vm \
  --project=YOUR_PROJECT_ID \
  --zone=us-central1-a \
  --machine-type=e2-standard-4 \
  --boot-disk-size=50GB \
  --boot-disk-type=pd-ssd \
  --image-family=ubuntu-2404-lts \
  --image-project=ubuntu-os-cloud \
  --address=supportpilot-ip \
  --tags=http-server,https-server \
  --service-account=supportpilot-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com \
  --scopes=storage-rw,secret-manager

# Allow HTTP/HTTPS traffic
gcloud compute firewall-rules create allow-http-https \
  --project=YOUR_PROJECT_ID \
  --allow tcp:80,tcp:443 \
  --target-tags=http-server,https-server
```

---

## 6. Step 4 — Copy Service Account Key to VM

```bash
# Copy SA key (created in Step 2) to the VM
gcloud compute scp ./secrets/gcp-sa-key.json \
  supportpilot-vm:/tmp/gcp-sa-key.json \
  --zone=us-central1-a \
  --project=YOUR_PROJECT_ID
```

---

## 7. Step 5 — Deploy on the VM

SSH into the VM and run the deployment script:

```bash
# SSH into VM
gcloud compute ssh supportpilot-vm \
  --zone=us-central1-a \
  --project=YOUR_PROJECT_ID

# On the VM — place SA key
sudo mkdir -p /opt/supportpilot/secrets
sudo mv /tmp/gcp-sa-key.json /opt/supportpilot/secrets/gcp-sa-key.json
sudo chmod 600 /opt/supportpilot/secrets/gcp-sa-key.json

# Run deployment script
sudo GCP_PROJECT_ID=YOUR_PROJECT_ID \
     GCS_BUCKET_NAME=YOUR_PROJECT-supportpilot-documents \
     GCP_SA_EMAIL=supportpilot-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com \
     DOMAIN_APP=app.yourdomain.com \
     DOMAIN_API=api.yourdomain.com \
     DOMAIN_N8N=n8n.yourdomain.com \
     ACME_EMAIL=admin@yourdomain.com \
     SUPERADMIN_EMAIL=admin@yourdomain.com \
     SUPERADMIN_PASSWORD=YourStrongPassword123! \
     bash /opt/supportpilot/scripts/deploy_gcp.sh
```

**What `deploy_gcp.sh` does:**
1. Installs Docker Engine and Docker Compose V2
2. Installs Google Cloud SDK
3. Clones / updates the repository
4. Fetches all secrets from Secret Manager → `.env.gcp`
5. Builds and starts all 6 Docker containers
6. Runs Alembic database migrations
7. Creates initial Super Admin account
8. Configures daily backup cron job to GCS

---

## 8. Step 6 — Verify Deployment

```bash
# Check all containers are healthy
docker compose -f /opt/supportpilot/docker-compose.gcp.yml ps

# Backend health check
curl -f https://api.yourdomain.com/health

# Frontend
curl -I https://app.yourdomain.com

# Widget JavaScript loader
curl -I https://api.yourdomain.com/api/v1/widget/loader.js

# View live logs
docker compose -f /opt/supportpilot/docker-compose.gcp.yml logs -f
```

Expected container statuses:
```
NAME                         STATUS
supportpilot_caddy_gcp       Up (healthy)
supportpilot_postgres_gcp    Up (healthy)
supportpilot_chromadb_gcp    Up (healthy)
supportpilot_backend_gcp     Up (healthy)
supportpilot_frontend_gcp    Up (healthy)
supportpilot_n8n_gcp         Up (healthy)
```

---

## 9. Cloud Storage Configuration

Document uploads are stored in Google Cloud Storage when `STORAGE_BACKEND=gcs`.

The pluggable storage service (`backend/app/services/storage_service.py`) handles:
- **Local mode** (`STORAGE_BACKEND=local`): stores to `/app/uploads/{org_id}/` (dev/fallback)
- **GCS mode** (`STORAGE_BACKEND=gcs`): stores to `gs://{GCS_BUCKET_NAME}/uploads/{org_id}/{filename}`

**Bucket structure:**
```
gs://YOUR_PROJECT-supportpilot-documents/
├── uploads/
│   ├── {org_uuid_1}/document.pdf
│   └── {org_uuid_2}/policy.docx

gs://YOUR_PROJECT-supportpilot-backups/
├── postgres-backups/
│   └── supportpilot_postgres_20261124_020000.sql.gz
└── chromadb-backups/
    └── supportpilot_chromadb_20261124_020000.tar.gz
```

---

## 10. Secret Manager Secrets Reference

| Secret Name | Environment Variable | Description |
|---|---|---|
| `supportpilot-secret-key` | `SECRET_KEY` | JWT signing key (hex 32) |
| `supportpilot-db-password` | `POSTGRES_PASSWORD` | PostgreSQL password |
| `supportpilot-gemini-api-key` | `GEMINI_API_KEY` | Google Gemini API key |
| `supportpilot-n8n-api-key` | `N8N_API_KEY` | n8n webhook HMAC key |
| `supportpilot-n8n-encryption-key` | `N8N_ENCRYPTION_KEY` | n8n credentials encryption |
| `supportpilot-n8n-basic-auth-pw` | `N8N_BASIC_AUTH_PASSWORD` | n8n admin password |
| `supportpilot-postgres-db` | `POSTGRES_DB` | Database name |
| `supportpilot-postgres-user` | `POSTGRES_USER` | Database username |

**Update a secret:**
```bash
echo -n "NEW_VALUE" | gcloud secrets versions add supportpilot-secret-key \
  --data-file=- --project=YOUR_PROJECT_ID
```

---

## 11. Database Backup & Restore

### On-Demand Backup to GCS

```bash
GCS_BUCKET_NAME=YOUR_PROJECT-supportpilot-backups \
GCP_PROJECT_ID=YOUR_PROJECT_ID \
  /opt/supportpilot/scripts/backup_gcs.sh
```

### List Available Backups

```bash
gcloud storage ls gs://YOUR_PROJECT-supportpilot-backups/postgres-backups/
```

### Restore from Backup

```bash
# Download backup
gcloud storage cp \
  gs://YOUR_PROJECT-supportpilot-backups/postgres-backups/supportpilot_postgres_20261124_020000.sql.gz \
  /tmp/restore.sql.gz

# Stop application
docker compose -f /opt/supportpilot/docker-compose.gcp.yml stop frontend backend

# Restore
gunzip -c /tmp/restore.sql.gz | docker exec -i supportpilot_postgres_gcp \
  psql -U supportpilot_admin -d supportpilot_prod

# Apply migrations
docker compose -f /opt/supportpilot/docker-compose.gcp.yml exec backend \
  python -m alembic upgrade head

# Restart
docker compose -f /opt/supportpilot/docker-compose.gcp.yml start backend frontend
```

---

## 12. Rolling Updates (Zero Downtime)

```bash
cd /opt/supportpilot

# 1. Pull latest code
git pull origin main

# 2. Rebuild and restart only changed services
docker compose -f docker-compose.gcp.yml build backend frontend
docker compose -f docker-compose.gcp.yml up -d --no-deps backend frontend

# 3. Run any new migrations
docker compose -f docker-compose.gcp.yml exec backend python -m alembic upgrade head
```

---

## 13. Restart Individual Services

```bash
cd /opt/supportpilot

# Restart backend only
docker compose -f docker-compose.gcp.yml restart backend

# Restart all services
docker compose -f docker-compose.gcp.yml restart

# Full stop and start
docker compose -f docker-compose.gcp.yml down
docker compose -f docker-compose.gcp.yml up -d
```

---

## 14. Troubleshooting Commands

```bash
# View logs for a specific service
docker compose -f /opt/supportpilot/docker-compose.gcp.yml logs -f backend
docker compose -f /opt/supportpilot/docker-compose.gcp.yml logs -f caddy
docker compose -f /opt/supportpilot/docker-compose.gcp.yml logs -f postgres

# Enter a running container
docker exec -it supportpilot_backend_gcp bash
docker exec -it supportpilot_postgres_gcp psql -U supportpilot_admin -d supportpilot_prod

# Check container resource usage
docker stats

# Check Caddy TLS certificate status
docker exec supportpilot_caddy_gcp caddy list-modules

# Check database connectivity
docker compose -f /opt/supportpilot/docker-compose.gcp.yml exec backend \
  python -c "from app.db.session import engine; print('DB OK')"

# Check GCS access from backend container
docker exec supportpilot_backend_gcp \
  python -c "from google.cloud import storage; c=storage.Client(); print('GCS OK')"
```

---

## 15. Security Checklist

- [ ] `.env.gcp` and `secrets/gcp-sa-key.json` added to `.gitignore`
- [ ] PostgreSQL not publicly reachable (only `127.0.0.1:5432`)
- [ ] ChromaDB not publicly reachable (internal Docker network only)
- [ ] All secrets stored in Secret Manager (not `.env.gcp`)
- [ ] Service account has only `storage.objectAdmin` (bucket-scoped) + `secretmanager.secretAccessor`
- [ ] n8n protected with HTTP Basic Auth via `N8N_BASIC_AUTH_*` variables
- [ ] UFW firewall: only ports 22, 80, 443 open
- [ ] `GEMINI_API_KEY` set via Secret Manager, not committed
- [ ] Daily backup cron job active (`crontab -l` to verify)
- [ ] Let's Encrypt TLS certificate active (check `https://app.yourdomain.com` padlock)
