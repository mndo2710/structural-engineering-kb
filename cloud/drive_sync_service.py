"""Google Drive Raw Knowledge Base Synchronization & Offline Mode Service (Day 17).

Conforms to SAD v1.1 Section 10, ADR-06, ADR-07, ADR-18 (Decision D-7), and Master Rule 3:
- Synchronizes raw .csv, .md, .py, .json, and .txt files using application/octet-stream.
- Prohibits converting Knowledge Base files to Google Docs or Google Sheets.
- Refuses to upload or overwrite local SQLite project databases (SYNC_PROJECT_SQLITE_TO_CLOUD = False).
- Preserves both copies on conflict for explicit user resolution.
- Quarantines corrupted downloads that fail SHA-256 manifest verification.
- Guarantees non-blocking offline calculation mode when disconnected or unauthenticated.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import io
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Sequence, Union
import uuid

from cloud.credential_store import CredentialStore, redact_sensitive
from cloud.local_cache_manager import LocalCacheManager
from core.common.exceptions import StructuralEngineeringError


RAW_UPLOAD_MIME_TYPE = "application/octet-stream"
RAW_ALLOWED_EXTENSIONS = frozenset({".csv", ".md", ".py", ".json", ".txt"})
FORBIDDEN_GOOGLE_APPS_MIMES = frozenset({
    "application/vnd.google-apps.document",
    "application/vnd.google-apps.spreadsheet",
    "application/vnd.google-apps.presentation",
    "application/vnd.google-apps.drawing",
    "application/vnd.google-apps.script",
})
FORBIDDEN_SQLITE_EXTENSIONS = frozenset({".sqlite", ".sqlite3", ".db"})
DEFAULT_DRIVE_SCOPES = ("https://www.googleapis.com/auth/drive",)

_LOGGER = logging.getLogger("structural_app.cloud_sync")


class CloudSyncPolicyError(StructuralEngineeringError, ValueError):
    """Raised when an operation violates raw-file MIME rules or Decision D-7 SQLite boundaries."""


class SyncConnectionStatus(str, Enum):
    """Explicit cloud connection / authentication states."""

    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    ERROR = "ERROR"


@dataclass(frozen=True)
class RemoteFileMetadata:
    """Normalized metadata for a raw file stored on Google Drive."""

    file_id: str
    name: str
    relative_path: str
    mime_type: str = RAW_UPLOAD_MIME_TYPE
    sha256: Optional[str] = None
    md5_checksum: Optional[str] = None
    modified_time: str = ""
    size_bytes: Optional[int] = None


@dataclass
class SyncPlan:
    """Dry-run / pre-execution plan comparing local KB state against Google Drive."""

    connection_status: SyncConnectionStatus
    to_download: List[Dict[str, Any]] = field(default_factory=list)
    to_upload: List[Dict[str, Any]] = field(default_factory=list)
    up_to_date: List[str] = field(default_factory=list)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    skipped_sqlite: List[str] = field(default_factory=list)
    rejected_mime_types: List[Dict[str, Any]] = field(default_factory=list)
    offline_status: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


@dataclass
class SyncResult:
    """Outcome record for a knowledge base sync attempt."""

    sync_id: str
    timestamp: str
    direction: str
    dry_run: bool
    connection_status: SyncConnectionStatus
    status: str
    files_synced: int = 0
    downloaded: List[str] = field(default_factory=list)
    uploaded: List[str] = field(default_factory=list)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    quarantined: List[Dict[str, Any]] = field(default_factory=list)
    skipped_sqlite: List[str] = field(default_factory=list)
    rejected_conversions: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    offline_ready: bool = False
    details: Dict[str, Any] = field(default_factory=dict)


class DriveClientProtocol(Protocol):
    """Transport abstraction enabling Google Drive API v3 in production and mocks in tests."""

    def is_connected(self) -> Union[bool, SyncConnectionStatus]:
        ...

    def list_reference_files(
        self, folder_id: Optional[str] = None
    ) -> Sequence[Union[RemoteFileMetadata, Dict[str, Any]]]:
        ...

    def download_raw_file(self, file_id: str) -> bytes:
        ...

    def upload_raw_file(
        self,
        relative_path: str,
        file_id: Optional[str],
        content: bytes,
        mime_type: str = RAW_UPLOAD_MIME_TYPE,
        convert: bool = False,
    ) -> Union[RemoteFileMetadata, Dict[str, Any]]:
        ...


def is_sqlite_project_path(path_str: str) -> bool:
    """Return True if path_str points to a SQLite database file excluded by Decision D-7."""
    norm = str(path_str).replace("\\", "/").lower().strip()
    suffix = Path(norm).suffix
    return (
        suffix in FORBIDDEN_SQLITE_EXTENSIONS
        or norm.endswith("structural_app.sqlite3")
        or (
            "/storage/projects/" in f"/{norm}"
            and suffix != ""
            and "local_cache" not in norm
        )
    )


def is_forbidden_google_mime(mime_type: str) -> bool:
    """Return True if mime_type represents a converted Google Docs/Sheets workspace artifact."""
    norm = (mime_type or "").strip().lower()
    return norm in FORBIDDEN_GOOGLE_APPS_MIMES or norm.startswith("application/vnd.google-apps.")


class GoogleDriveApiClient:
    """
    Production Google Drive API v3 transport adapter using OAuth 2.0 credentials
    stored in OS keyring via CredentialStore.
    Lazily imports Google API client libraries so offline environments without
    cloud packages never fail at import or calculation startup time.
    """

    def __init__(
        self,
        credential_store: CredentialStore,
        root_folder_id: str = "",
        scopes: Sequence[str] = DEFAULT_DRIVE_SCOPES,
    ) -> None:
        self.credential_store = credential_store
        self.root_folder_id = root_folder_id
        self.scopes = tuple(scopes)
        self._service: Any = None

    def _load_google_modules(self) -> Dict[str, Any]:
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaInMemoryUpload, MediaIoBaseDownload
        except ImportError as exc:
            raise ConnectionError(f"Google Drive API dependencies unavailable: {exc}") from exc

        return {
            "Request": Request,
            "Credentials": Credentials,
            "InstalledAppFlow": InstalledAppFlow,
            "build": build,
            "MediaInMemoryUpload": MediaInMemoryUpload,
            "MediaIoBaseDownload": MediaIoBaseDownload,
        }

    def authenticate_oauth2(self, client_secrets_path: Union[str, Path]) -> Dict[str, Any]:
        """Run interactive OAuth 2.0 desktop flow and persist tokens in CredentialStore."""
        mods = self._load_google_modules()
        flow = mods["InstalledAppFlow"].from_client_secrets_file(
            str(client_secrets_path),
            scopes=list(self.scopes),
        )
        creds = flow.run_local_server(port=0)
        token_payload = json.loads(creds.to_json())
        self.credential_store.save_credentials(token_payload)
        self._service = None
        return {"authenticated": True, "backend": self.credential_store.backend_type}

    def _get_service(self) -> Any:
        if self._service is not None:
            return self._service

        token_payload = self.credential_store.load_credentials()
        if not token_payload:
            raise PermissionError("OAuth 2.0 credentials not found in CredentialStore.")

        mods = self._load_google_modules()
        creds = mods["Credentials"].from_authorized_user_info(token_payload, scopes=list(self.scopes))
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(mods["Request"]())
            self.credential_store.save_credentials(json.loads(creds.to_json()))

        if not creds or not creds.valid:
            raise PermissionError("OAuth 2.0 credentials are invalid or expired without refresh token.")

        self._service = mods["build"]("drive", "v3", credentials=creds, cache_discovery=False)
        return self._service

    def is_connected(self) -> SyncConnectionStatus:
        if not self.credential_store.has_credentials():
            return SyncConnectionStatus.AUTH_REQUIRED
        try:
            service = self._get_service()
            service.about().get(fields="user").execute()
            return SyncConnectionStatus.ONLINE
        except PermissionError:
            return SyncConnectionStatus.AUTH_REQUIRED
        except Exception:
            return SyncConnectionStatus.OFFLINE

    def list_reference_files(self, folder_id: Optional[str] = None) -> List[RemoteFileMetadata]:
        service = self._get_service()
        target_folder = folder_id or self.root_folder_id
        query = "trashed = false"
        if target_folder:
            query = f"'{target_folder}' in parents and trashed = false"

        results: List[RemoteFileMetadata] = []
        page_token: Optional[str] = None
        while True:
            resp = (
                service.files()
                .list(
                    q=query,
                    spaces="drive",
                    fields="nextPageToken, files(id, name, mimeType, md5Checksum, modifiedTime, size, appProperties)",
                    pageToken=page_token,
                )
                .execute()
            )
            for item in resp.get("files", []):
                app_props = item.get("appProperties") or {}
                results.append(
                    RemoteFileMetadata(
                        file_id=item["id"],
                        name=item["name"],
                        relative_path=app_props.get("relative_path", item["name"]),
                        mime_type=item.get("mimeType", RAW_UPLOAD_MIME_TYPE),
                        sha256=app_props.get("sha256"),
                        md5_checksum=item.get("md5Checksum"),
                        modified_time=item.get("modifiedTime", ""),
                        size_bytes=int(item["size"]) if item.get("size") is not None else None,
                    )
                )
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        return results

    def download_raw_file(self, file_id: str) -> bytes:
        service = self._get_service()
        meta = service.files().get(fileId=file_id, fields="id, name, mimeType").execute()
        mime_type = meta.get("mimeType", "")
        if is_forbidden_google_mime(mime_type):
            raise CloudSyncPolicyError(
                f"Refusing to export Google Docs/Sheets file '{meta.get('name', file_id)}' ({mime_type}); "
                "raw binary files are mandatory."
            )

        mods = self._load_google_modules()
        request = service.files().get_media(fileId=file_id)
        buffer = io.BytesIO()
        downloader = mods["MediaIoBaseDownload"](buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return buffer.getvalue()

    def upload_raw_file(
        self,
        relative_path: str,
        file_id: Optional[str],
        content: bytes,
        mime_type: str = RAW_UPLOAD_MIME_TYPE,
        convert: bool = False,
    ) -> RemoteFileMetadata:
        if convert or is_forbidden_google_mime(mime_type) or mime_type != RAW_UPLOAD_MIME_TYPE:
            raise CloudSyncPolicyError(
                f"Raw upload requires mime_type='{RAW_UPLOAD_MIME_TYPE}' with convert=False."
            )
        if is_sqlite_project_path(relative_path):
            raise CloudSyncPolicyError(
                f"Refusing to upload SQLite project database '{relative_path}' (Decision D-7)."
            )

        service = self._get_service()
        mods = self._load_google_modules()
        media = mods["MediaInMemoryUpload"](content, mimetype=RAW_UPLOAD_MIME_TYPE, resumable=False)
        sha256 = LocalCacheManager.compute_bytes_sha256(content)
        file_name = Path(relative_path).name
        body: Dict[str, Any] = {
            "name": file_name,
            "mimeType": RAW_UPLOAD_MIME_TYPE,
            "appProperties": {
                "relative_path": relative_path.replace("\\", "/"),
                "sha256": sha256,
            },
        }
        if file_id:
            updated = (
                service.files()
                .update(
                    fileId=file_id,
                    body=body,
                    media_body=media,
                    fields="id, name, mimeType, md5Checksum, modifiedTime, size, appProperties",
                )
                .execute()
            )
        else:
            if self.root_folder_id:
                body["parents"] = [self.root_folder_id]
            updated = (
                service.files()
                .create(
                    body=body,
                    media_body=media,
                    fields="id, name, mimeType, md5Checksum, modifiedTime, size, appProperties",
                )
                .execute()
            )

        return RemoteFileMetadata(
            file_id=updated["id"],
            name=updated["name"],
            relative_path=relative_path.replace("\\", "/"),
            mime_type=updated.get("mimeType", RAW_UPLOAD_MIME_TYPE),
            sha256=sha256,
            md5_checksum=updated.get("md5Checksum"),
            modified_time=updated.get("modifiedTime", ""),
            size_bytes=len(content),
        )


class CloudSyncService:
    """
    Coordinates raw Knowledge Base synchronization with Google Drive, local SHA-256
    integrity checks, conflict preservation, and non-blocking offline calculation readiness.
    """

    def __init__(
        self,
        root_dir: Optional[Union[str, Path]] = None,
        credential_store: Optional[CredentialStore] = None,
        cache_manager: Optional[LocalCacheManager] = None,
        drive_client: Optional[DriveClientProtocol] = None,
        repository: Optional[Any] = None,
        log_path: Optional[Union[str, Path]] = None,
    ) -> None:
        self.root_dir = (
            Path(root_dir).resolve()
            if root_dir is not None
            else Path(__file__).resolve().parent.parent
        )
        self.credential_store = credential_store or CredentialStore()
        self.cache_manager = cache_manager or LocalCacheManager(root_dir=self.root_dir)
        self.repository = repository
        self.log_path = Path(log_path).resolve() if log_path is not None else None

        self._cloud_config = self._load_cloud_config()
        self.root_folder_id: str = str(self._cloud_config.get("ROOT_FOLDER_ID", ""))
        self.raw_upload_mime_type: str = str(
            self._cloud_config.get("RAW_UPLOAD_MIME_TYPE", RAW_UPLOAD_MIME_TYPE)
        )
        # Decision D-7: local project SQLite DB is never synced automatically
        self.sync_project_sqlite_to_cloud: bool = bool(
            self._cloud_config.get("SYNC_PROJECT_SQLITE_TO_CLOUD", False)
        )
        self.conflict_policy: str = str(
            self._cloud_config.get("CONFLICT_POLICY", "preserve_both_require_explicit_resolution")
        )

        self.drive_client: DriveClientProtocol = drive_client or GoogleDriveApiClient(
            credential_store=self.credential_store,
            root_folder_id=self.root_folder_id,
        )

    def _load_cloud_config(self) -> Dict[str, Any]:
        settings_path = self.root_dir / "config" / "app_settings.json"
        if not settings_path.exists():
            return {}
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            cloud_cfg = data.get("CLOUD_SYNC", {})
            return cloud_cfg if isinstance(cloud_cfg, dict) else {}
        except Exception:
            return {}

    @staticmethod
    def _utc_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _log_event(self, level: int, message: str, event_sink: Optional[List[str]] = None) -> str:
        secrets = self.credential_store.extract_secret_values()
        safe_msg = redact_sensitive(message, extra_secrets=secrets)
        _LOGGER.log(level, safe_msg)
        if event_sink is not None:
            event_sink.append(safe_msg)
        if self.log_path is not None:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            ts = self._utc_iso()
            level_name = logging.getLevelName(level)
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(f"{ts} [{level_name}] {safe_msg}\n")
        return safe_msg

    def validate_transfer_policy(
        self,
        relative_path: str,
        mime_type: str = RAW_UPLOAD_MIME_TYPE,
        convert: bool = False,
    ) -> str:
        """
        Enforce Rule 3 (raw application/octet-stream, zero Google Docs/Sheets conversion)
        and Decision D-7 (no SQLite project database synchronization).
        """
        rel_norm = str(relative_path).replace("\\", "/").lstrip("/")
        if is_sqlite_project_path(rel_norm) and not self.sync_project_sqlite_to_cloud:
            raise CloudSyncPolicyError(
                f"Sync blocked by Decision D-7: SQLite project database '{rel_norm}' cannot be synced to Google Drive."
            )

        if convert:
            raise CloudSyncPolicyError(
                f"Conversion to Google Workspace format is prohibited for '{rel_norm}' (Rule 3)."
            )

        if is_forbidden_google_mime(mime_type):
            raise CloudSyncPolicyError(
                f"Forbidden Google Docs/Sheets MIME type '{mime_type}' for '{rel_norm}'; "
                f"must remain '{RAW_UPLOAD_MIME_TYPE}'."
            )

        suffix = Path(rel_norm).suffix.lower()
        if suffix in RAW_ALLOWED_EXTENSIONS and mime_type != self.raw_upload_mime_type:
            raise CloudSyncPolicyError(
                f"Raw file '{rel_norm}' must use mime_type='{self.raw_upload_mime_type}', got '{mime_type}'."
            )

        return self.cache_manager.normalize_relative_path(rel_norm)

    def upload_raw_file(
        self,
        relative_path: str,
        file_id: Optional[str] = None,
        mime_type: str = RAW_UPLOAD_MIME_TYPE,
        convert: bool = False,
    ) -> RemoteFileMetadata:
        """
        Explicitly validate raw transfer policy and upload a single Knowledge Base file
        using application/octet-stream without converting to Google Docs/Sheets.
        """
        rel_norm = self.validate_transfer_policy(
            relative_path=relative_path,
            mime_type=mime_type,
            convert=convert,
        )
        local_path = self.cache_manager.resolve_path(rel_norm)
        if not local_path.exists():
            raise FileNotFoundError(f"Local file does not exist for upload: '{rel_norm}'")
        payload = local_path.read_bytes()
        raw_result = self.drive_client.upload_raw_file(
            relative_path=rel_norm,
            file_id=file_id,
            content=payload,
            mime_type=self.raw_upload_mime_type,
            convert=False,
        )
        return self._normalize_remote_item(raw_result)

    def check_connection(self) -> SyncConnectionStatus:
        """Non-blocking cloud connectivity and credential check."""
        try:
            status = self.drive_client.is_connected()
            if isinstance(status, SyncConnectionStatus):
                return status
            return SyncConnectionStatus.ONLINE if bool(status) else SyncConnectionStatus.OFFLINE
        except PermissionError as exc:
            self._log_event(logging.WARNING, f"Cloud auth required: {exc}")
            return SyncConnectionStatus.AUTH_REQUIRED
        except (ConnectionError, TimeoutError, OSError) as exc:
            self._log_event(logging.INFO, f"Cloud offline: {exc}")
            return SyncConnectionStatus.OFFLINE
        except Exception as exc:
            self._log_event(logging.WARNING, f"Cloud connectivity check error: {exc}")
            return SyncConnectionStatus.ERROR

    @staticmethod
    def _normalize_remote_item(item: Union[RemoteFileMetadata, Dict[str, Any]]) -> RemoteFileMetadata:
        if isinstance(item, RemoteFileMetadata):
            return RemoteFileMetadata(
                file_id=item.file_id,
                name=item.name,
                relative_path=item.relative_path.replace("\\", "/").lstrip("/"),
                mime_type=item.mime_type or RAW_UPLOAD_MIME_TYPE,
                sha256=item.sha256,
                md5_checksum=item.md5_checksum,
                modified_time=item.modified_time,
                size_bytes=item.size_bytes,
            )

        rel_path = str(item.get("relative_path") or item.get("name") or "").replace("\\", "/").lstrip("/")
        return RemoteFileMetadata(
            file_id=str(item.get("file_id") or item.get("id") or ""),
            name=str(item.get("name") or Path(rel_path).name),
            relative_path=rel_path,
            mime_type=str(item.get("mime_type") or item.get("mimeType") or RAW_UPLOAD_MIME_TYPE),
            sha256=item.get("sha256"),
            md5_checksum=item.get("md5_checksum") or item.get("md5Checksum"),
            modified_time=str(item.get("modified_time") or item.get("modifiedTime") or ""),
            size_bytes=item.get("size_bytes") or item.get("size"),
        )

    def _remote_differs_from_local(
        self,
        local_path: Path,
        local_sha256: str,
        remote: RemoteFileMetadata,
    ) -> Optional[bool]:
        """Compare local file against remote metadata hashes. Returns None if remote provides no hash."""
        if remote.sha256:
            return local_sha256 != remote.sha256
        if remote.md5_checksum:
            local_md5 = self.cache_manager.compute_md5(local_path)
            return local_md5.lower() != remote.md5_checksum.lower()
        return None

    def plan_sync(self, extra_local_paths: Optional[Sequence[str]] = None) -> SyncPlan:
        """
        Compare local Knowledge Base manifest/disk checksums against Google Drive metadata
        without modifying any local or remote files.
        """
        offline_status = self.cache_manager.get_offline_status()
        conn_status = self.check_connection()
        plan = SyncPlan(
            connection_status=conn_status,
            offline_status=offline_status,
        )

        # Explicitly inspect SQLite boundary candidates (Decision D-7)
        sqlite_candidates: List[str] = []
        projects_dir = self.root_dir / "storage" / "projects"
        if projects_dir.exists():
            for db_file in sorted(projects_dir.glob("*")):
                if db_file.is_file() and db_file.suffix.lower() in FORBIDDEN_SQLITE_EXTENSIONS:
                    sqlite_candidates.append(db_file.relative_to(self.root_dir).as_posix())
        if extra_local_paths:
            for p in extra_local_paths:
                norm_p = str(p).replace("\\", "/").lstrip("/")
                if is_sqlite_project_path(norm_p) and norm_p not in sqlite_candidates:
                    sqlite_candidates.append(norm_p)

        for sql_rel in sqlite_candidates:
            if not self.sync_project_sqlite_to_cloud:
                plan.skipped_sqlite.append(sql_rel)

        if conn_status != SyncConnectionStatus.ONLINE:
            plan.warnings.append(
                f"Cloud status is {conn_status.value}; local deterministic KB calculations remain unblocked."
            )
            return plan

        try:
            raw_remote = self.drive_client.list_reference_files(folder_id=self.root_folder_id or None)
        except Exception as exc:
            self._log_event(logging.WARNING, f"Failed to list remote reference files: {exc}")
            plan.connection_status = SyncConnectionStatus.OFFLINE
            plan.warnings.append("Remote listing failed; operating in offline mode.")
            return plan

        remote_by_id: Dict[str, RemoteFileMetadata] = {}
        remote_by_path: Dict[str, RemoteFileMetadata] = {}
        for item in raw_remote:
            meta = self._normalize_remote_item(item)
            if is_sqlite_project_path(meta.relative_path) or is_sqlite_project_path(meta.name):
                if not self.sync_project_sqlite_to_cloud:
                    if meta.relative_path not in plan.skipped_sqlite:
                        plan.skipped_sqlite.append(meta.relative_path)
                continue
            if is_forbidden_google_mime(meta.mime_type):
                plan.rejected_mime_types.append({
                    "relative_path": meta.relative_path,
                    "file_id": meta.file_id,
                    "mime_type": meta.mime_type,
                    "reason": "Google Docs/Sheets conversion prohibited; raw binary required.",
                })
                continue
            if meta.file_id:
                remote_by_id[meta.file_id] = meta
            if meta.relative_path:
                remote_by_path[meta.relative_path] = meta

        rejected_paths = {r["relative_path"] for r in plan.rejected_mime_types}
        rejected_ids = {r["file_id"] for r in plan.rejected_mime_types if r.get("file_id")}
        entries = self.cache_manager.get_manifest_entries() if offline_status.get("manifest_present") else []

        for entry in entries:
            rel_path = self.cache_manager.normalize_relative_path(entry.get("relative_path", ""))
            if is_sqlite_project_path(rel_path):
                if rel_path not in plan.skipped_sqlite:
                    plan.skipped_sqlite.append(rel_path)
                continue
            drive_id = str(entry.get("drive_file_id", ""))
            if rel_path in rejected_paths or (drive_id and drive_id in rejected_ids):
                continue

            manifest_sha = str(entry.get("sha256", ""))
            ref_id = str(entry.get("reference_id", ""))
            local_path = self.root_dir / rel_path
            remote = remote_by_id.get(drive_id) or remote_by_path.get(rel_path)

            if not local_path.exists():
                if remote is not None:
                    plan.to_download.append({
                        "reference_id": ref_id,
                        "relative_path": rel_path,
                        "drive_file_id": remote.file_id or drive_id,
                        "expected_sha256": manifest_sha,
                        "remote_sha256": remote.sha256,
                        "remote_modified_time": remote.modified_time,
                        "reason": "missing_locally",
                    })
                else:
                    plan.warnings.append(f"Missing both locally and remotely: {rel_path}")
                continue

            local_sha = self.cache_manager.compute_sha256(local_path)
            if remote is None:
                plan.to_upload.append({
                    "reference_id": ref_id,
                    "relative_path": rel_path,
                    "drive_file_id": drive_id or None,
                    "local_sha256": local_sha,
                    "mime_type": self.raw_upload_mime_type,
                    "reason": "missing_on_drive",
                })
                continue

            differs = self._remote_differs_from_local(local_path, local_sha, remote)
            if differs is True:
                plan.conflicts.append({
                    "reference_id": ref_id,
                    "relative_path": rel_path,
                    "drive_file_id": remote.file_id or drive_id,
                    "local_sha256": local_sha,
                    "remote_sha256": remote.sha256,
                    "manifest_sha256": manifest_sha,
                    "remote_modified_time": remote.modified_time,
                    "reason": "local_and_remote_differ",
                })
            elif manifest_sha and local_sha != manifest_sha:
                plan.conflicts.append({
                    "reference_id": ref_id,
                    "relative_path": rel_path,
                    "drive_file_id": remote.file_id or drive_id,
                    "local_sha256": local_sha,
                    "remote_sha256": remote.sha256,
                    "manifest_sha256": manifest_sha,
                    "remote_modified_time": remote.modified_time,
                    "reason": "local_manifest_mismatch",
                })
            else:
                plan.up_to_date.append(rel_path)

        return plan

    def _record_sync_history(self, result: SyncResult) -> None:
        if self.repository is None or result.dry_run:
            return
        details = {
            "connection_status": result.connection_status.value,
            "downloaded": result.downloaded,
            "uploaded": result.uploaded,
            "conflicts": result.conflicts,
            "quarantined": result.quarantined,
            "skipped_sqlite": result.skipped_sqlite,
            "rejected_conversions": result.rejected_conversions,
            "errors": result.errors,
            "warnings": result.warnings,
            "offline_ready": result.offline_ready,
        }
        try:
            with self.repository._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO sync_history (
                        sync_id, timestamp, direction, files_synced, conflicts, status, details_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        result.sync_id,
                        result.timestamp,
                        result.direction,
                        result.files_synced,
                        len(result.conflicts),
                        result.status,
                        json.dumps(details),
                    ),
                )
                conn.commit()
        except Exception as exc:
            self._log_event(logging.WARNING, f"Failed to write sync_history audit record: {exc}")

    def sync_knowledge_base(
        self,
        direction: str = "pull",
        dry_run: bool = False,
        extra_local_paths: Optional[Sequence[str]] = None,
        raise_on_integrity_error: bool = False,
    ) -> SyncResult:
        """
        Synchronize raw Knowledge Base files without blocking local calculations when offline.

        - direction='pull': downloads missing manifest files, verifies SHA-256, quarantines corrupt
          downloads, and preserves conflicting modified local files via stage_conflict_copy().
        - direction='push': uploads missing raw files with application/octet-stream while refusing
          SQLite project DBs and Google Docs/Sheets conversions.
        - direction='bidirectional': executes pull/conflict-staging followed by missing raw uploads.
        """
        norm_dir = direction.strip().lower()
        if norm_dir not in {"pull", "push", "bidirectional"}:
            raise ValueError(f"Unsupported sync direction '{direction}'. Expected 'pull', 'push', or 'bidirectional'.")

        sync_id = str(uuid.uuid4())
        ts = self._utc_iso()
        log_events: List[str] = []

        plan = self.plan_sync(extra_local_paths=extra_local_paths)
        result = SyncResult(
            sync_id=sync_id,
            timestamp=ts,
            direction=norm_dir,
            dry_run=dry_run,
            connection_status=plan.connection_status,
            status=plan.connection_status.value,
            skipped_sqlite=list(plan.skipped_sqlite),
            rejected_conversions=list(plan.rejected_mime_types),
            warnings=list(plan.warnings),
            offline_ready=bool(plan.offline_status.get("is_offline_ready", False)),
        )

        for sql_path in plan.skipped_sqlite:
            self._log_event(
                logging.INFO,
                f"Decision D-7 boundary enforced: skipped SQLite file '{sql_path}'.",
                log_events,
            )

        for rej in plan.rejected_mime_types:
            msg = f"Rejected forbidden Google Workspace conversion for '{rej['relative_path']}' ({rej['mime_type']})."
            self._log_event(logging.ERROR, msg, log_events)
            result.errors.append(msg)

        if plan.connection_status != SyncConnectionStatus.ONLINE:
            self._log_event(
                logging.INFO,
                f"Sync skipped ({plan.connection_status.value}); offline_ready={result.offline_ready}.",
                log_events,
            )
            result.details = {"log_events": log_events, "offline_status": plan.offline_status}
            self._record_sync_history(result)
            return result

        if dry_run:
            result.status = "DRY_RUN"
            result.details = {
                "plan": asdict(plan),
                "log_events": log_events,
            }
            return result

        try:
            # 1. Pull missing files and stage conflicts (without overwriting local edits)
            if norm_dir in {"pull", "bidirectional"}:
                for item in plan.to_download:
                    rel_path = item["relative_path"]
                    file_id = item["drive_file_id"]
                    expected_sha = item.get("expected_sha256") or ""

                    self.validate_transfer_policy(rel_path, mime_type=self.raw_upload_mime_type, convert=False)
                    payload = self.drive_client.download_raw_file(file_id)
                    actual_sha = self.cache_manager.compute_bytes_sha256(payload)

                    if expected_sha and actual_sha != expected_sha:
                        q_path = self.cache_manager.quarantine_corrupted_file(
                            relative_path=rel_path,
                            payload=payload,
                            expected_sha256=expected_sha,
                            actual_sha256=actual_sha,
                        )
                        err_msg = (
                            f"SHA-256 mismatch downloading '{rel_path}': expected {expected_sha}, "
                            f"got {actual_sha}. Quarantined at '{q_path}'."
                        )
                        self._log_event(logging.ERROR, err_msg, log_events)
                        result.quarantined.append({
                            "relative_path": rel_path,
                            "expected_sha256": expected_sha,
                            "actual_sha256": actual_sha,
                            "quarantine_path": str(q_path),
                        })
                        result.errors.append(err_msg)
                        if raise_on_integrity_error:
                            raise CloudSyncPolicyError(err_msg)
                        continue

                    self.cache_manager.write_verified_file(
                        relative_path=rel_path,
                        payload=payload,
                        expected_sha256=expected_sha or None,
                    )
                    result.downloaded.append(rel_path)
                    self._log_event(logging.INFO, f"Downloaded and verified raw file '{rel_path}'.", log_events)

                for conflict in plan.conflicts:
                    rel_path = conflict["relative_path"]
                    file_id = conflict["drive_file_id"]
                    remote_bytes = self.drive_client.download_raw_file(file_id)
                    conflict_copy = self.cache_manager.stage_conflict_copy(
                        relative_path=rel_path,
                        remote_bytes=remote_bytes,
                        remote_modified_time=conflict.get("remote_modified_time", ""),
                    )
                    conflict_entry = {
                        **conflict,
                        "conflict_copy_path": str(conflict_copy),
                        "policy": self.conflict_policy,
                    }
                    result.conflicts.append(conflict_entry)
                    self._log_event(
                        logging.WARNING,
                        f"Conflict preserved for '{rel_path}': remote copy staged at '{conflict_copy}'.",
                        log_events,
                    )

            # 2. Push missing raw files (with strict raw MIME & SQLite exclusion)
            if norm_dir in {"push", "bidirectional"}:
                for item in plan.to_upload:
                    rel_path = item["relative_path"]
                    self.validate_transfer_policy(rel_path, mime_type=self.raw_upload_mime_type, convert=False)
                    local_path = self.cache_manager.resolve_path(rel_path)
                    payload = local_path.read_bytes()
                    self.drive_client.upload_raw_file(
                        relative_path=rel_path,
                        file_id=item.get("drive_file_id"),
                        content=payload,
                        mime_type=self.raw_upload_mime_type,
                        convert=False,
                    )
                    result.uploaded.append(rel_path)
                    self._log_event(logging.INFO, f"Uploaded raw file '{rel_path}' as {self.raw_upload_mime_type}.", log_events)

        except CloudSyncPolicyError:
            raise
        except PermissionError as exc:
            msg = self._log_event(logging.WARNING, f"Sync interrupted due to auth error: {exc}", log_events)
            result.connection_status = SyncConnectionStatus.AUTH_REQUIRED
            result.status = SyncConnectionStatus.AUTH_REQUIRED.value
            result.errors.append(msg)
        except (ConnectionError, TimeoutError, OSError) as exc:
            msg = self._log_event(logging.WARNING, f"Sync interrupted (falling back offline): {exc}", log_events)
            result.connection_status = SyncConnectionStatus.OFFLINE
            result.status = SyncConnectionStatus.OFFLINE.value
            result.errors.append(msg)
        except Exception as exc:
            msg = self._log_event(logging.ERROR, f"Unexpected sync failure: {exc}", log_events)
            result.connection_status = SyncConnectionStatus.ERROR
            result.status = SyncConnectionStatus.ERROR.value
            result.errors.append(msg)
        else:
            if result.quarantined:
                result.status = "INTEGRITY_ERROR"
            elif result.conflicts or result.rejected_conversions or result.errors:
                result.status = "PARTIAL_WITH_CONFLICTS"
            else:
                result.status = "SUCCESS"

        result.files_synced = len(result.downloaded) + len(result.uploaded)
        post_offline = self.cache_manager.get_offline_status()
        result.offline_ready = bool(post_offline.get("is_offline_ready", False))
        result.details = {"log_events": log_events, "offline_status": post_offline}
        self._record_sync_history(result)
        return result
