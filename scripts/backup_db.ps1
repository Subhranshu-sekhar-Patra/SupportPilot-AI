# ============================================================
# SupportPilot AI — Windows PowerShell PostgreSQL Backup Script
# Usage: .\scripts\backup_db.ps1 [-BackupDir ".\backups\postgres"]
# ============================================================
param (
    [string]$BackupDir = ".\backups\postgres",
    [string]$ContainerName = "supportpilot_postgres_prod",
    [string]$DbUser = "supportpilot_admin",
    [string]$DbName = "supportpilot_prod",
    [int]$RetentionDays = 14
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
}

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupFile = Join-Path $BackupDir "supportpilot_backup_$Timestamp.sql"

Write-Host "==> Starting SupportPilot PostgreSQL backup..." -ForegroundColor Cyan
Write-Host "    Container: $ContainerName"
Write-Host "    Database:  $DbName"
Write-Host "    Target:    $BackupFile"

docker exec $ContainerName pg_dump -U $DbUser -d $DbName --clean --if-exists --no-owner --no-privileges > $BackupFile

if (Test-Path $BackupFile) {
    $Size = (Get-Item $BackupFile).Length / 1MB
    Write-Host ("==> Backup succeeded ({0:N2} MB): {1}" -f $Size, $BackupFile) -ForegroundColor Green
} else {
    Write-Error "Backup file was not created."
}

# Cleanup older files
$Cutoff = (Get-Date).AddDays(-$RetentionDays)
Get-ChildItem -Path $BackupDir -Filter "supportpilot_backup_*.sql" | Where-Object { $_.LastWriteTime -lt $Cutoff } | Remove-Item -Force
Write-Host "==> Backup procedure finished." -ForegroundColor Cyan
