"""
SupportPilot AI — Google Secret Manager Integration
Loads production secrets at startup when running on GCP.

Usage:
    Set GCP_SECRET_MANAGER_ENABLED=true and GCP_PROJECT_ID=<your-project-id>.
    Secret names must follow the naming convention below.

Secrets resolved:
    supportpilot-secret-key        → SECRET_KEY
    supportpilot-db-password       → POSTGRES_PASSWORD
    supportpilot-gemini-api-key    → GEMINI_API_KEY
    supportpilot-n8n-api-key       → N8N_API_KEY
    supportpilot-n8n-encryption-key→ N8N_ENCRYPTION_KEY
    supportpilot-n8n-basic-auth-pw → N8N_BASIC_AUTH_PASSWORD
"""

import os
from typing import Optional

from app.core.logger import get_logger

logger = get_logger(__name__)

_ENABLED = os.getenv("GCP_SECRET_MANAGER_ENABLED", "false").lower() == "true"
_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "")

# Map: Secret Manager name → environment variable name
SECRET_MAP = {
    "supportpilot-secret-key": "SECRET_KEY",
    "supportpilot-db-password": "POSTGRES_PASSWORD",
    "supportpilot-gemini-api-key": "GEMINI_API_KEY",
    "supportpilot-n8n-api-key": "N8N_API_KEY",
    "supportpilot-n8n-encryption-key": "N8N_ENCRYPTION_KEY",
    "supportpilot-n8n-basic-auth-pw": "N8N_BASIC_AUTH_PASSWORD",
    "supportpilot-postgres-db": "POSTGRES_DB",
    "supportpilot-postgres-user": "POSTGRES_USER",
}


def _access_secret(client, project_id: str, secret_name: str, version: str = "latest") -> Optional[str]:
    """Fetch the latest version of a secret from Secret Manager."""
    name = f"projects/{project_id}/secrets/{secret_name}/versions/{version}"
    try:
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("utf-8").strip()
    except Exception as exc:
        logger.warning("secret_manager_fetch_failed", secret=secret_name, error=str(exc))
        return None


def load_secrets_from_manager() -> int:
    """
    Pull all defined secrets from Google Secret Manager and inject them
    as environment variables. Called once at application startup.

    Returns the number of secrets successfully loaded.
    """
    if not _ENABLED:
        logger.info("secret_manager_disabled")
        return 0

    if not _PROJECT_ID:
        logger.warning("secret_manager_no_project_id", msg="GCP_PROJECT_ID not set; skipping Secret Manager")
        return 0

    try:
        from google.cloud import secretmanager  # noqa: PLC0415
    except ImportError:
        logger.error("secret_manager_sdk_missing", msg="google-cloud-secret-manager not installed")
        return 0

    client = secretmanager.SecretManagerServiceClient()
    loaded = 0

    for secret_name, env_var in SECRET_MAP.items():
        # Only override if the env var is not already set (allows local override)
        if os.environ.get(env_var):
            logger.debug("secret_manager_skip_existing", env_var=env_var)
            continue

        value = _access_secret(client, _PROJECT_ID, secret_name)
        if value is not None:
            os.environ[env_var] = value
            loaded += 1
            logger.info("secret_manager_loaded", secret=secret_name, env_var=env_var)

    logger.info("secret_manager_complete", loaded=loaded, total=len(SECRET_MAP))
    return loaded
