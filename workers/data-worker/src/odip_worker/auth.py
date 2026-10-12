"""Application credentials are obtained from the platform's project-wide binding."""
import os
import time
from urllib.parse import urlsplit
import requests

_cached_token = None
_expires_at = 0.0

class DependencyError(RuntimeError):
    pass

def headers():
    global _cached_token, _expires_at
    mode = os.environ.get("ODIP_IDENTITY_MODE", "platform")
    if mode == "development":
        return {
            "X-Platform-Principal-Id": os.getenv("ODIP_API_PRINCIPAL_ID", "odip-ingestion-worker"),
            "X-Platform-Principal-Kind": "service",
            "X-Platform-Principal-Issuer": os.getenv("ODIP_API_PRINCIPAL_ISSUER", "https://odip.internal"),
            "X-Platform-Principal-Subject": os.getenv("ODIP_API_PRINCIPAL_SUBJECT", "odip-ingestion-worker"),
            "X-Platform-Principal-Group-Ids": os.getenv("ODIP_API_PRINCIPAL_GROUP_IDS", ""),
            "X-Platform-Principal-Client-Id": "development-worker",
        }
    if mode != "platform":
        raise ValueError("Unsupported identity mode")
    if _cached_token is None or time.monotonic() >= _expires_at:
        prefix = os.environ["ODIP_WORKER_BINDING_PREFIX"]
        token_url = os.environ[prefix + "_TOKEN_URL"]
        parsed = urlsplit(token_url)
        if parsed.scheme != "https" or parsed.username or parsed.password or parsed.fragment:
            raise ValueError("Managed token endpoint must use HTTPS")
        response = requests.post(token_url, data={
            "grant_type": "client_credentials",
            "client_id": os.environ[prefix + "_CLIENT_ID"],
            "client_secret": os.environ[prefix + "_CLIENT_SECRET"],
        }, timeout=(10, 20), allow_redirects=False)
        if response.status_code != 200:
            raise DependencyError("Service token acquisition failed")
        document = response.json()
        expires = min(int(document["expires_in"]), 300)
        if expires <= 30 or document.get("token_type", "").lower() != "bearer":
            raise DependencyError("Invalid token response")
        _cached_token = document["access_token"]
        _expires_at = time.monotonic() + expires - 30
    return {"Authorization": "Bearer " + _cached_token}

def api_url(value):
    parsed = urlsplit(value)
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Invalid API origin")
    if os.environ.get("ODIP_IDENTITY_MODE", "platform") == "platform" and parsed.scheme != "https":
        raise ValueError("Deployed API access requires HTTPS")
    return value.rstrip("/")

def call(method, url, **kwargs):
    response = getattr(requests, method)(url, headers=headers(), timeout=(10, 60), allow_redirects=False, **kwargs)
    if 300 <= response.status_code < 400:
        raise DependencyError("API redirects are prohibited")
    return response
