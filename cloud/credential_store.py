"""Secure OAuth 2.0 credential storage via OS keyring and log redaction helpers.

Conforms to SAD v1.1 Section 14, ADR-06, and Master Rule 3:
- Uses OS credential manager (`keyring`) when available.
- Supports an injectable backend or in-memory fallback for headless CI/tests.
- Never writes tokens or secrets to config/, logs/, or source files.
"""

import json
import re
from typing import Any, Dict, Iterable, Optional, Protocol

try:
    import keyring as _os_keyring
    from keyring.errors import KeyringError as _KeyringError
except Exception:  # pragma: no cover - keyring optional in minimal environments
    _os_keyring = None
    _KeyringError = Exception


DEFAULT_SERVICE_NAME = "structural-engineering-kb"
DEFAULT_ACCOUNT_NAME = "google_drive_oauth2"

_SENSITIVE_KEY_PATTERN = re.compile(
    r'(?i)(["\']?(?:access_token|refresh_token|client_secret|id_token|token|password|authorization|secret|api_key)["\']?\s*[:=]\s*)(["\']?)([^"\'\s,}]+)(\2)'
)
_BEARER_PATTERN = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9\-._~+/]+=*")
_GOOGLE_ACCESS_TOKEN_PATTERN = re.compile(r"\bya29\.[A-Za-z0-9\-._]+")
_GOOGLE_SECRET_PATTERN = re.compile(r"\b(?:GOCSPX-[A-Za-z0-9\-_]+|AIza[0-9A-Za-z\-_]{20,})")


class CredentialBackendProtocol(Protocol):
    """Minimal keyring-compatible backend interface."""

    def get_password(self, service_name: str, username: str) -> Optional[str]:
        ...

    def set_password(self, service_name: str, username: str, password: str) -> None:
        ...

    def delete_password(self, service_name: str, username: str) -> None:
        ...


class InMemoryCredentialBackend:
    """Ephemeral in-memory credential store for headless tests and locked CI runners."""

    def __init__(self) -> None:
        self._store: Dict[tuple[str, str], str] = {}

    def get_password(self, service_name: str, username: str) -> Optional[str]:
        return self._store.get((service_name, username))

    def set_password(self, service_name: str, username: str, password: str) -> None:
        self._store[(service_name, username)] = password

    def delete_password(self, service_name: str, username: str) -> None:
        key = (service_name, username)
        if key not in self._store:
            raise KeyError(f"No credentials stored for {service_name}/{username}")
        del self._store[key]


def redact_sensitive(text: str, extra_secrets: Optional[Iterable[str]] = None) -> str:
    """Sanitize tokens, Bearer headers, and OAuth secrets before writing logs."""
    if not text:
        return ""

    sanitized = str(text)
    if extra_secrets:
        for secret in extra_secrets:
            if secret and len(secret) >= 4:
                sanitized = sanitized.replace(secret, "[REDACTED]")

    sanitized = _BEARER_PATTERN.sub("Bearer [REDACTED]", sanitized)
    sanitized = _GOOGLE_ACCESS_TOKEN_PATTERN.sub("[REDACTED_TOKEN]", sanitized)
    sanitized = _GOOGLE_SECRET_PATTERN.sub("[REDACTED_SECRET]", sanitized)
    sanitized = _SENSITIVE_KEY_PATTERN.sub(r"\1\2[REDACTED]\4", sanitized)
    return sanitized


def _is_usable_os_keyring(kr_module: Any) -> bool:
    if kr_module is None:
        return False
    try:
        kr = kr_module.get_keyring()
        cls_name = f"{type(kr).__module__}.{type(kr).__name__}".lower()
        if "fail.keyring" in cls_name or "null" in cls_name:
            return False
        return True
    except Exception:
        return False


class CredentialStore:
    """Stores, retrieves, and deletes OAuth 2.0 credential payloads via OS keyring."""

    def __init__(
        self,
        service_name: str = DEFAULT_SERVICE_NAME,
        account_name: str = DEFAULT_ACCOUNT_NAME,
        backend: Optional[CredentialBackendProtocol] = None,
        allow_memory_fallback: bool = True,
    ) -> None:
        self.service_name = service_name
        self.account_name = account_name
        self.allow_memory_fallback = allow_memory_fallback

        if backend is not None:
            self._backend: CredentialBackendProtocol = backend
            self._backend_type = "custom"
        elif _is_usable_os_keyring(_os_keyring):
            self._backend = _os_keyring
            self._backend_type = "keyring"
        elif allow_memory_fallback:
            self._backend = InMemoryCredentialBackend()
            self._backend_type = "memory_fallback"
        else:
            raise RuntimeError("OS keyring backend is unavailable and memory fallback is disabled.")

    @property
    def backend_type(self) -> str:
        return self._backend_type

    def _switch_to_memory_fallback(self) -> None:
        if not self.allow_memory_fallback:
            raise RuntimeError("OS keyring operation failed and memory fallback is disabled.")
        self._backend = InMemoryCredentialBackend()
        self._backend_type = "memory_fallback"

    def save_credentials(
        self,
        token_payload: Dict[str, Any],
        account_name: Optional[str] = None,
    ) -> None:
        """Persist OAuth 2.0 token dictionary securely in the configured credential store."""
        if not isinstance(token_payload, dict) or not token_payload:
            raise ValueError("token_payload must be a non-empty dictionary.")

        acct = account_name or self.account_name
        serialized = json.dumps(token_payload, sort_keys=True)

        try:
            self._backend.set_password(self.service_name, acct, serialized)
        except _KeyringError:
            self._switch_to_memory_fallback()
            self._backend.set_password(self.service_name, acct, serialized)

    def load_credentials(self, account_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieve OAuth 2.0 token dictionary from the credential store, or None if absent."""
        acct = account_name or self.account_name
        try:
            raw = self._backend.get_password(self.service_name, acct)
        except _KeyringError:
            self._switch_to_memory_fallback()
            raw = self._backend.get_password(self.service_name, acct)

        if not raw:
            return None

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    def delete_credentials(self, account_name: Optional[str] = None) -> bool:
        """Remove stored credentials for the account. Returns True if deleted, False if absent."""
        acct = account_name or self.account_name
        try:
            existing = self._backend.get_password(self.service_name, acct)
            if existing is None:
                return False
            self._backend.delete_password(self.service_name, acct)
            return True
        except KeyError:
            return False
        except _KeyringError as exc:
            # Handle PasswordDeleteError cleanly if item didn't exist or keyring locked
            if "not found" in str(exc).lower() or "delete" in type(exc).__name__.lower():
                return False
            if self.allow_memory_fallback:
                self._switch_to_memory_fallback()
                return False
            raise

    def has_credentials(self, account_name: Optional[str] = None) -> bool:
        """Return True if a stored credential payload exists for the account."""
        payload = self.load_credentials(account_name=account_name)
        if not payload:
            return False
        return bool(
            payload.get("refresh_token")
            or payload.get("access_token")
            or payload.get("token")
        )

    def extract_secret_values(self, account_name: Optional[str] = None) -> list[str]:
        """Collect sensitive string values currently stored so logs can scrub them explicitly."""
        payload = self.load_credentials(account_name=account_name)
        if not payload:
            return []
        secrets: list[str] = []
        for key in ("access_token", "refresh_token", "token", "client_secret", "id_token"):
            val = payload.get(key)
            if isinstance(val, str) and val:
                secrets.append(val)
        return secrets
