# SupportPilot AI — Ubuntu VPS Production Deployment Guide

This guide provides end-to-end instructions for deploying SupportPilot AI to a single Ubuntu 22.04 LTS or 24.04 LTS VPS with high availability, automated TLS encryption (via Caddy), multi-tenant isolation, and automated database backups.

---

## 1. Architecture Overview

```
                                  [ Internet / Clients ]
                                             │
                                   Port 80 / 443 (TLS)
                                             ▼
                        ┌────────────────────────────────────────┐
                        │      Caddy 2 Reverse Proxy             │
                        │    (Automatic HTTPS & Cert Renewal)    │
                        └───────┬────────────┬───────────┬───────┘
                                │            │           │
                 ┌──────────────┘            │           └──────────────┐
                 ▼                           ▼                          ▼
    ┌─────────────────────────┐  ┌────────────────────────┐  ┌────────────────────────┐
    │  Next.js 14 Frontend    │  │   FastAPI Backend      │  │  n8n Automation Engine │
    │  app.yourdomain.com     │  │   api.yourdomain.com   │  │  n8n.yourdomain.com    │
    │  (Port 3000 internal)   │  │   (Port 8000 internal) │  │  (Port 5678 internal)  │
    └─────────────────────────┘  └───────────┬────────────┘  └────────────────────────┘
                                             │
                     ┌───────────────────────┴───────────────────────┐
                     ▼                                               ▼
      ┌─────────────────────────────┐                 ┌─────────────────────────────┐
      │   PostgreSQL 16 Database    │                 │   ChromaDB Vector Store     │
      │   (Isolated Docker Network) │                 │   (Isolated Docker Network) │
      │   127.0.0.1:5432 (local)    │                 │   chromadb:8000 (no host)   │
      └─────────────────────────────┘                 └─────────────────────────────┘
```

---

## 2. Server Specifications & Prerequisites

### Minimum Hardware
- **CPU:** 4 vCPUs (x86_64 or ARM64)
- **RAM:** 8 GB RAM (or 4 GB RAM with 4 GB swap space)
- **Storage:** 50 GB NVMe / SSD
- **OS:** Ubuntu 22.04 LTS or 24.04 LTS

### Required DNS Records
Configure A records at your DNS registrar pointing to your VPS public IPv4:
- `app.yourdomain.com` ➔ `<VPS_IP>`
- `api.yourdomain.com` ➔ `<VPS_IP>`
- `n8n.yourdomain.com` ➔ `<VPS_IP>`

---

## 3. Server Preparation & Hardening

SSH into your VPS as `root` (or a user with `sudo` privileges):

```bash
# 1. Update packages
sudo apt update && sudo apt upgrade -y

# 2. Install baseline dependencies
sudo apt install -y curl wget git ufw ca-certificates gnupg lsb-release

# 3. Configure Swap Space (Recommended if RAM is <= 8GB)
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# 4. Configure UFW Firewall (Deny all incoming except SSH, HTTP, HTTPS)
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
sudo ufw status
```

---

## 4. Install Docker & Docker Compose V2

```bash
# Add Docker official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Set up repository
echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker packages
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Enable Docker on startup
sudo systemctl enable docker
sudo systemctl start docker

# Verify installation
docker --version
docker compose version
```

---

## 5. Clone Repository & Setup Directory

```bash
# Clone to /opt/supportpilot
sudo git clone https://github.com/Subhranshu-sekhar-Patra/SupportPilot-AI.git /opt/supportpilot
cd /opt/supportpilot

# Set permissions for current user
sudo chown -R $USER:$USER /opt/supportpilot
```

---

## 6. Configure Production Environment Variables

1. Copy the production environment template:
```bash
cp .env.production.example .env.production
chmod 600 .env.production
```

2. Edit `.env.production`:
```bash
nano .env.production
```

Configure values:
```dotenv
# Domains
DOMAIN_APP=app.yourdomain.com
DOMAIN_API=api.yourdomain.com
DOMAIN_N8N=n8n.yourdomain.com
ACME_EMAIL=admin@yourdomain.com
NEXT_PUBLIC_API_URL=https://api.yourdomain.com

# PostgreSQL Secrets
POSTGRES_USER=supportpilot_prod_admin
POSTGRES_PASSWORD=YourStrongDatabasePasswordHere_12345!
POSTGRES_DB=supportpilot_production

# Application Secrets (Generate with `openssl rand -hex 32`)
SECRET_KEY=generate_with_openssl_rand_hex_32
N8N_API_KEY=generate_with_openssl_rand_hex_24
N8N_ENCRYPTION_KEY=generate_with_openssl_rand_hex_24

# AI Credentials
GEMINI_API_KEY=AIzaSy...YourGoogleGeminiApiKey...
```

---

## 7. Build and Deploy Stack

```bash
# 1. Pull base images and build containers
docker compose -f docker-compose.prod.yml build

# 2. Launch all services in detached mode
docker compose -f docker-compose.prod.yml up -d

# 3. Check health status of all 6 containers
docker compose -f docker-compose.prod.yml ps
```

All 6 containers should show `Up (healthy)`:
- `supportpilot_caddy_prod`
- `supportpilot_frontend_prod`
- `supportpilot_backend_prod`
- `supportpilot_postgres_prod`
- `supportpilot_chromadb_prod`
- `supportpilot_n8n_prod`

---

## 8. Run Database Migrations

Apply database migrations:
```bash
docker compose -f docker-compose.prod.yml exec backend python -m alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade  -> 001_initial_schema
INFO  [alembic.runtime.migration] Running upgrade 001_initial_schema -> 002_customer_feedback
INFO  [alembic.runtime.migration] Running upgrade 002_customer_feedback -> 003_superadmin_usage_widget
```

---

## 9. Create Initial Super Admin Account

Run the interactive superadmin creation utility:
```bash
docker compose -f docker-compose.prod.yml exec backend python -m app.scripts.create_superadmin \
  --email "superadmin@yourdomain.com" \
  --password "SuperSecretAdminPassword123!" \
  --name "Platform Superadmin"
```

---

## 10. Verify Deployment & Endpoints

1. **Frontend App:** Visit `https://app.yourdomain.com` in your browser. Verify the green padlock (Let's Encrypt SSL) and log in with your superadmin credentials.
2. **Backend API Health:**
   ```bash
   curl -f https://api.yourdomain.com/health
   ```
   Returns: `{"status":"healthy","version":"1.0.0","env":"production","service":"supportpilot-backend"}`
3. **Embeddable Chatbot Script:**
   ```bash
   curl -I https://api.yourdomain.com/api/v1/widget/loader.js
   ```
   Returns: `HTTP/2 200 OK` with `content-type: application/javascript`.
4. **n8n Automation Console:** Visit `https://n8n.yourdomain.com` and complete initial owner setup.

---

## 11. Embed the Chat Widget on External Websites

Add this script tag right before `</body>` on any customer-facing website:

```html
<script 
  src="https://api.yourdomain.com/api/v1/widget/loader.js" 
  data-org-slug="your-org-slug" 
  data-primary-color="#2563eb"
  defer>
</script>
```

---

## 12. Automated Backups & Maintenance

1. Configure nightly PostgreSQL backup cron job:
```bash
sudo crontab -e
```
Add the following line:
```cron
0 2 * * * /opt/supportpilot/scripts/backup_db.sh /var/backups/supportpilot >> /var/log/supportpilot_backup.log 2>&1
```

2. Manual backup command:
```bash
chmod +x /opt/supportpilot/scripts/backup_db.sh
/opt/supportpilot/scripts/backup_db.sh ./backups
```

3. Database restoration:
```bash
chmod +x /opt/supportpilot/scripts/restore_db.sh
./scripts/restore_db.sh ./backups/supportpilot_backup_YYYYMMDD_HHMMSS.sql.gz
```

---

## 13. Zero-Downtime Updates & Troubleshooting

### Pull Latest Changes & Rolling Update
```bash
cd /opt/supportpilot
git pull origin main
docker compose -f docker-compose.prod.yml build backend frontend
docker compose -f docker-compose.prod.yml up -d --no-deps backend frontend
docker compose -f docker-compose.prod.yml exec backend python -m alembic upgrade head
```

### Inspect Container Logs
```bash
# View combined logs
docker compose -f docker-compose.prod.yml logs -f

# View backend logs only
docker compose -f docker-compose.prod.yml logs -f backend

# View Caddy reverse proxy logs
docker compose -f docker-compose.prod.yml logs -f caddy
```
