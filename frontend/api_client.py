"""HTTP client for the CVForge API.

The UI layer never touches ``requests`` directly. Configuration, authentication,
connection pooling, retries and error shaping all live here so that every call
site gets identical, predictable behaviour.
"""

from __future__ import annotations

import os
from typing import Any, Mapping, Optional

import requests
import streamlit as st
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

CONNECT_TIMEOUT = 10
FAST_TIMEOUT = 30
GENERATION_TIMEOUT = 180
USER_AGENT = "CVForge-UI/1.0"


def _resolve_base_url() -> str:
    """Resolve the API base URL from Streamlit secrets, then env, then default."""
    url = ""
    try:
        url = st.secrets.get("CVFORGE_API_URL", "") or ""
    except Exception:
        # No secrets file / running outside a Streamlit runtime.
        url = ""
    url = url or os.getenv("CVFORGE_API_URL", "") or "http://localhost:8000"
    return url.rstrip("/")


API_URL = _resolve_base_url()


# --------------------------------------------------------------------------- #
# Errors
# --------------------------------------------------------------------------- #

class APIError(Exception):
    """Raised for transport failures and non-2xx API responses."""

    def __init__(
        self,
        message: str,
        *,
        status: Optional[int] = None,
        detail: Optional[str] = None,
        path: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.detail = detail or message
        self.path = path

    @property
    def is_auth_error(self) -> bool:
        return self.status in (401, 403)

    @property
    def is_validation_error(self) -> bool:
        return self.status == 422

    @property
    def is_service_unavailable(self) -> bool:
        return self.status == 503


# --------------------------------------------------------------------------- #
# Session
# --------------------------------------------------------------------------- #

@st.cache_resource(show_spinner=False)
def _session() -> requests.Session:
    """A pooled, retrying session shared across reruns.

    Only idempotent verbs are retried — generation endpoints are never
    replayed silently.
    """
    session = requests.Session()
    retry = Retry(
        total=3,
        connect=3,
        read=2,
        backoff_factor=0.4,
        status_forcelist=(429, 502, 503, 504),
        allowed_methods=frozenset({"GET", "HEAD", "PUT", "DELETE", "OPTIONS"}),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=16, pool_maxsize=16)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
    return session


# --------------------------------------------------------------------------- #
# Response helpers
# --------------------------------------------------------------------------- #

def _extract_detail(response: requests.Response) -> str:
    """Turn any error body into a single readable sentence."""
    try:
        payload = response.json()
    except ValueError:
        text = (response.text or "").strip()
        return text[:500] if text else (response.reason or "Request failed")

    if not isinstance(payload, Mapping):
        return str(payload)[:500]

    detail: Any = payload.get("detail", payload)

    # FastAPI validation errors arrive as a list of {loc, msg, type}.
    if isinstance(detail, list):
        parts = []
        for item in detail:
            if isinstance(item, Mapping):
                loc = ".".join(
                    str(x) for x in item.get("loc", []) if x not in ("body", "query", "path")
                )
                msg = str(item.get("msg", "")).strip()
                parts.append(f"{loc}: {msg}" if loc else msg)
            else:
                parts.append(str(item))
        joined = "; ".join(p for p in parts if p)
        return joined or "Validation failed"

    if isinstance(detail, Mapping):
        return str(detail.get("message") or detail.get("error") or detail)

    return str(detail)


def _decode(response: requests.Response) -> Any:
    if response.status_code == 204 or not response.content:
        return None
    try:
        return response.json()
    except ValueError as exc:
        raise APIError(
            "The API returned a malformed JSON response.",
            status=response.status_code,
            path=str(response.url),
        ) from exc


# --------------------------------------------------------------------------- #
# Core request
# --------------------------------------------------------------------------- #

def request(
    method: str,
    path: str,
    token: Optional[str] = None,
    *,
    timeout: int = GENERATION_TIMEOUT,
    **kwargs: Any,
) -> requests.Response:
    """Perform an API request and return the raw ``requests.Response``."""
    headers = dict(kwargs.pop("headers", {}) or {})
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = path if path.startswith(("http://", "https://")) else f"{API_URL}{path}"

    try:
        response = _session().request(
            method,
            url,
            headers=headers,
            timeout=(CONNECT_TIMEOUT, timeout),
            **kwargs,
        )
    except requests.Timeout as exc:
        raise APIError(
            f"The request to {path} timed out. The job may be large — try again.",
            path=path,
        ) from exc
    except requests.RequestException as exc:
        raise APIError(f"Cannot reach the CVForge API at {API_URL}: {exc}", path=path) from exc

    if not response.ok:
        detail = _extract_detail(response)
        raise APIError(
            f"{response.status_code}: {detail}",
            status=response.status_code,
            detail=detail,
            path=path,
        )

    return response


# --------------------------------------------------------------------------- #
# Convenience wrappers
# --------------------------------------------------------------------------- #

def auth(path: str, payload: Mapping[str, Any]) -> Any:
    """Unauthenticated POST used for login and registration."""
    return _decode(
        request("POST", path, json=dict(payload), timeout=FAST_TIMEOUT)
    )


def get(path: str, token: Optional[str], **kwargs: Any) -> Any:
    kwargs.setdefault("timeout", FAST_TIMEOUT)
    return _decode(request("GET", path, token=token, **kwargs))


def post(path: str, token: Optional[str], **kwargs: Any) -> Any:
    kwargs.setdefault("timeout", GENERATION_TIMEOUT)
    return _decode(request("POST", path, token=token, **kwargs))


def put(path: str, token: Optional[str], **kwargs: Any) -> Any:
    return _decode(request("PUT", path, token=token, **kwargs))


def download(path: str, token: Optional[str], **kwargs: Any) -> bytes:
    """Fetch a binary artefact (PDF / DOCX export)."""
    return request("GET", path, token=token, **kwargs).content


def health() -> bool:
    """Best-effort reachability probe — never raises."""
    try:
        request("GET", "/health", timeout=5)
        return True
    except APIError:
        try:
            request("GET", "/", timeout=5)
            return True
        except APIError:
            return False