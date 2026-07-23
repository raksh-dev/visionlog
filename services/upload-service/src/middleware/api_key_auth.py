"""API key authentication middleware.

The expected key is fetched once from Secret Manager and cached in memory for
the lifetime of the instance (the spec forbids calling Secret Manager on every
request). Locally we use a hardcoded dev key and never touch Secret Manager.

/health is excluded so Cloud Run health checks don't need a key.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from ..config import get_settings
from ..logging_config import get_logger, log_event

logger = get_logger()

# Paths that never require an API key.
PUBLIC_PATHS = {"/health", "/docs", "/redoc", "/openapi.json"}

_cached_api_key: str | None = None


def _load_api_key() -> str:
    """Resolve the expected API key, caching it in memory."""
    global _cached_api_key
    if _cached_api_key is not None:
        return _cached_api_key

    settings = get_settings()
    if settings.is_local:
        _cached_api_key = settings.local_api_key
        return _cached_api_key

    from google.cloud import secretmanager

    client = secretmanager.SecretManagerServiceClient()
    name = (
        f"projects/{settings.gcp_project_id}/secrets/"
        f"{settings.api_key_secret_name}/versions/latest"
    )
    response = client.access_secret_version(request={"name": name})
    _cached_api_key = response.payload.data.decode("utf-8").strip()
    return _cached_api_key


def reset_api_key_cache() -> None:
    """Test helper to clear the cached key between tests."""
    global _cached_api_key
    _cached_api_key = None


class ApiKeyAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        provided = request.headers.get("X-API-Key")
        if not provided:
            log_event(logger, "Missing API key", severity="WARNING", path=request.url.path)
            return JSONResponse(status_code=401, content={"detail": "Missing X-API-Key header."})

        if provided != _load_api_key():
            log_event(logger, "Invalid API key", severity="WARNING", path=request.url.path)
            return JSONResponse(status_code=401, content={"detail": "Invalid API key."})

        return await call_next(request)
