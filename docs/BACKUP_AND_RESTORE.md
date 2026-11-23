# SupportPilot AI — Database Backup & Disaster Recovery Guide

This runbook covers operational backup procedures, scheduled cron jobs, verification tests, and disaster recovery processes for PostgreSQL in SupportPilot AI.

---

## 1. Backup Strategy Overview

| Tier | Frequency | Tool / Method | Retention Window | Destination |
| :--- | :--- | :--- | :--- | :--- |
| **Full Snapshot** | Daily at 02:00 UTC | `pg_dump` compressed (`.sql.gz`) | 30 Days | Cloud Object Storage (S3/GCS) |
| **Hot Backup** | Every 6 hours | Docker exec automated script | 14 Days | Dedicated backup volume / off-site |
| **Vector Store** | Weekly snapshot | Directory tarball of `/app/chroma_data` | 14 Days | Cloud Object Storage |

---

## 2. On-Demand Backup

### Linux / Docker Host (Bash)
```bash
# Execute automated backup script
chmod +x ./scripts/backup_db.sh
./scripts/backup_db.sh ./backups/postgres
```

### Windows Host (PowerShell)
```powershell
.\scripts\backup_db.ps1 -BackupDir ".\backups\postgres"
```

### Direct Docker Command
```bash
docker exec -t supportpilot_postgres_prod pg_dump \
  -U supportpilot_admin \
  -d supportpilot_prod \
  --clean --if-exists --no-owner --no-privileges | gzip -9 > ./backups/manual_backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

---

## 3. Automated Backup Automation (Cron)

To schedule automatic nightly backups at 02:00 AM on Linux production hosts:

```bash
# Open crontab editor
crontab -e

# Add nightly execution with stdout/stderr logged
0 2 * * * /opt/supportpilot/scripts/backup_db.sh /var/backups/supportpilot >> /var/log/supportpilot_backup.log 2>&1
```

### Cloud Replication (S3 / GCS Example)
Append off-site sync to your backup script or cron pipeline:
```bash
# Sync local backup directory to AWS S3 bucket with server-side encryption
aws s3 sync /var/backups/supportpilot s3://my-enterprise-backups/supportpilot/postgres/ --sse AES256

# Or Google Cloud Storage
gcloud storage rsync /var/backups/supportpilot gs://my-enterprise-backups/supportpilot/postgres/
```

---

## 4. Disaster Recovery & Database Restoration

> [!WARNING]
> Restoring a database snapshot drops and replaces existing tables in the target database. Run this operation only during scheduled maintenance or recovery events.

### Step 1: Put Application into Maintenance Mode
```bash
docker compose -f docker-compose.prod.yml stop frontend backend
```

### Step 2: Execute Restore Script
```bash
chmod +x ./scripts/restore_db.sh
./scripts/restore_db.sh ./backups/postgres/supportpilot_backup_20261123_120000.sql.gz
```

### Step 3: Run Alembic Migrations to Ensure Schema Parity
```bash
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head
```

### Step 4: Restart Services & Verify Health
```bash
docker compose -f docker-compose.prod.yml start backend frontend
curl -f http://localhost:8000/health
```

---

## 5. ChromaDB Vector Store Backup

Vector embeddings stored in ChromaDB should also be archived periodically:

```bash
# Archive ChromaDB persistent volume
docker compose -f docker-compose.prod.yml run --rm backend \
  tar -czf /app/uploads/chroma_backup_$(date +%Y%m%d).tar.gz -C /app chroma_data
```
