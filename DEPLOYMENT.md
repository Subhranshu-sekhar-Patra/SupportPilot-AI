# SupportPilot AI — Production Deployment Guide

This guide provides end-to-end instructions for deploying SupportPilot AI to production using Docker Compose, reverse proxies with SSL termination, automated database migrations, and operational observability.

---

## Architecture Overview

```
                      ┌─────────────────────────────────────────┐
                      │          Nginx Reverse Proxy            │
                      │     (HTTPS 443 with Let's Encrypt)      │
                      └─────────────┬───────────────────────────┘
                                    │
              ┌─────────────────────┴─────────────────────┐
              │                                           │
              ▼                                           ▼
┌───────────────────────────┐               ┌───────────────────────────┐
│     Next.js Frontend      │               │      FastAPI Backend      │
│      (Port 3000)          │               │  Gunicorn / Uvicorn Workers│
│   (Standalone Next 14)    │               │        (Port 8000)        │
└───────────────────────────┘               └─────────────┬─────────────┘
                                                          │
                             ┌────────────────────────────┼───────────────────────────┐
                             │                            │                           │
                             ▼                            ▼                           ▼
              ┌───────────────────────────┐┌───────────────────────────┐┌───────────────────────────┐
              │    PostgreSQL 16 DB       ││    ChromaDB Vector Store  ││   n8n Automation Engine   │
              │  (Port 5432 - Isolated)   ││    (Multi-tenant Embeddings││ (Port 5678 - Authenticated)│
              └───────────────────────────┘└───────────────────────────┘└───────────────────────────┘
```

---

## 1. Prerequisites

- **Host Operating System:** Ubuntu 22.04 LTS, Debian 12, or RHEL 9 (Windows Server with Docker Desktop also supported).
- **Docker:** Engine v25.0+ and Docker Compose v2.24+.
- **Hardware Minimum:** 4 vCPU, 8 GB RAM, 50 GB SSD.
- **DNS Records:**
  - `app.yourdomain.com` → A record pointing to host public IP.
  - `api.yourdomain.com` → A record pointing to host public IP.
  - `n8n.yourdomain.com` (optional for workflow admin UI) → A record.

---

## 2. Production Environment Configuration

1. Clone the repository onto the production server:
   ```bash
   git clone https://github.com/Subhranshu-sekhar-Patra/SupportPilot-AI.git /opt/supportpilot
   cd /opt/supportpilot
   ```

2. Copy the production environment template:
   ```bash
   cp .env.production.example .env.production
   chmod 600 .env.production
   ```

3. Populate the required secrets in `.env.production`:
   ```bash
   # Generate cryptographic keys
   openssl rand -hex 32  # Use for SECRET_KEY
   openssl rand -hex 24  # Use for N8N_API_KEY
   openssl rand -hex 24  # Use for N8N_ENCRYPTION_KEY
   openssl rand -base64 24 # Use for POSTGRES_PASSWORD
   ```

   Ensure `GEMINI_API_KEY` is set to an active Google Gemini API key with access to `gemini-2.0-flash` and `models/text-embedding-004`.

---

## 3. Launching Services with Docker Compose

1. Build and start all services in detached mode:
   ```bash
   docker compose -f docker-compose.prod.yml up -d --build
   ```

2. Verify all container health checks report `healthy`:
   ```bash
   docker compose -f docker-compose.prod.yml ps
   ```

   Expected status:
   ```
   NAME                           IMAGE                                STATUS
   supportpilot_postgres_prod     postgres:16-alpine                   Up (healthy)
   supportpilot_backend_prod      supportpilot-backend:latest          Up (healthy)
   supportpilot_frontend_prod     supportpilot-frontend:latest         Up (healthy)
   supportpilot_n8n_prod          docker.n8n.io/n8nio/n8n:latest       Up (healthy)
   ```

3. Execute database schema migrations:
   ```bash
   docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
   ```

---

## 4. Reverse Proxy Setup (Nginx + Let's Encrypt)

Create an Nginx server block at `/etc/nginx/sites-available/supportpilot`:

```nginx
# API Backend
server {
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 50M;
    }
}

# Frontend Dashboard
server {
    server_name app.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable SSL certificates using Certbot:
```bash
sudo certbot --nginx -d app.yourdomain.com -d api.yourdomain.com
```

---

## 5. Post-Deployment Verification Checklist

- [ ] **Health Endpoint:** `curl -f https://api.yourdomain.com/health` returns `{"status":"healthy","service":"supportpilot-backend"}`.
- [ ] **OpenAPI Documentation:** Access `https://api.yourdomain.com/docs` to verify all route schemas.
- [ ] **Frontend Accessibility:** Load `https://app.yourdomain.com` and verify the login screen renders.
- [ ] **Registration & Auth Flow:** Register a test owner account and verify JWT issuance.
- [ ] **Ticket State Machine:** Create a ticket, assign to an agent, add internal note, resolve, and view audit trail.
- [ ] **RAG Document Ingestion:** Upload a sample policy document (PDF/DOCX/TXT) and test semantic retrieval.
- [ ] **Structured Logging:** Check container logs: `docker compose -f docker-compose.prod.yml logs -f backend | jq .` to verify JSON logs.
- [ ] **Rate Limiting:** Issue rapid requests to `/api/v1/auth/login` to confirm HTTP 429 is returned after 10 requests.

---

## 6. Maintenance & Updates

### Zero-Downtime Rolling Update
```bash
# Pull latest code
git pull origin main

# Rebuild and restart services gracefully
docker compose -f docker-compose.prod.yml up -d --build --no-deps backend
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
docker compose -f docker-compose.prod.yml up -d --build --no-deps frontend
```

### Viewing Production Logs
```bash
# Stream backend logs formatted
docker compose -f docker-compose.prod.yml logs -f --tail=100 backend

# Filter for errors
docker compose -f docker-compose.prod.yml logs backend | grep '"level":"ERROR"'
```
