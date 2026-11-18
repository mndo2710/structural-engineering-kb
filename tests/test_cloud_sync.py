"""Unit, integrity, conflict, and offline tests for Day 17 cloud synchronization (cloud/)."""

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import pytest

from app.services.knowledge_base_service import KnowledgeBaseService
from cloud.credential_store import (
    DEFAULT_SERVICE_NAME,
    CredentialStore,
    InMemoryCredentialBackend,
    redact_sensitive,
)
from cloud.drive_sync_service import (
    RAW_UPLOAD_MIME_TYPE,
    CloudSyncPolicyError,
    CloudSyncService,
    RemoteFileMetadata,
    SyncConnectionStatus,
)
from cloud.local_cache_manager import LocalCacheManager
from core.asce7.wind.parapet import calculate_parapet_wind
from core.common.calculation_result import CalculationStatus, DesignMethod
from storage.repositories.project_repository import ProjectRepository


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class MockDriveClient:
    """In-memory mock Google Drive transport for deterministic sync testing."""

    def __init__(
        self,
        connected: Any = True,
        remote_files: Optional[List[RemoteFileMetadata]] = None,
        payloads: Optional[Dict[str, bytes]] = None,
        fail_download_ids: Optional[Dict[str, Exception]] = None,
    ) -> None:
        self.connected = connected
        self.remote_files = list(remote_files or [])
        self.payloads = dict(payloads or {})
        self.fail_download_ids = dict(fail_download_ids or {})
        self.upload_calls: List[Dict[str, Any]] = []

    def is_connected(self):
        if isinstance(self.connected, Exception):
            raise self.connected
        return self.connected

    def list_reference_files(self, folder_id: Optional[str] = None) -> Sequence[RemoteFileMetadata]:
        if isinstance(self.connected, Exception):
            raise self.connected
        return list(self.remote_files)

    def download_raw_file(self, file_id: str) -> bytes:
        if file_id in self.fail_download_ids:
            raise self.fail_download_ids[file_id]
        if file_id not in self.payloads:
            raise FileNotFoundError(f"Mock remote file not found: {file_id}")
        return self.payloads[file_id]

    def upload_raw_file(
        self,
        relative_path: str,
        file_id: Optional[str],
        content: bytes,
        mime_type: str = RAW_UPLOAD_MIME_TYPE,
        convert: bool = False,
    ) -> RemoteFileMetadata:
        self.upload_calls.append({
            "relative_path": relative_path,
            "file_id": file_id,
            "content": content,
            "mime_type": mime_type,
            "convert": convert,
        })
        new_id = file_id or f"drv-up-{len(self.upload_calls)}"
        meta = RemoteFileMetadata(
            file_id=new_id,
            name=Path(relative_path).name,
            relative_path=relative_path,
            mime_type=mime_type,
            sha256=_sha256(content),
            modified_time="2026-11-18T09:00:00Z",
            size_bytes=len(content),
        )
        self.payloads[new_id] = content
        self.remote_files.append(meta)
        return meta


def _build_temp_kb_workspace(tmp_path: Path, files: Dict[str, bytes]) -> Dict[str, Any]:
    """Create a minimal workspace with config/reference_manifest.json and optional files."""
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    app_settings = {
        "CLOUD_SYNC": {
            "PROVIDER": "Google_Drive_API_v3",
            "RAW_UPLOAD_MIME_TYPE": "application/octet-stream",
            "SYNC_PROJECT_SQLITE_TO_CLOUD": False,
            "CONFLICT_POLICY": "preserve_both_require_explicit_resolution",
        }
    }
    (tmp_path / "config" / "app_settings.json").write_text(json.dumps(app_settings), encoding="utf-8")

    references = []
    for idx, (rel_path, content) in enumerate(files.items(), start=1):
        references.append({
            "reference_id": f"REF-{idx:02d}",
            "file_name": Path(rel_path).name,
            "drive_file_id": f"drv-{idx:02d}",
            "relative_path": rel_path,
            "sha256": _sha256(content),
        })

    manifest = {
        "manifest_version": "1.0.0",
        "references": references,
    }
    (tmp_path / "config" / "reference_manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )
    return manifest


class TestCredentialStoreAndRedaction:
    def test_save_load_delete_and_service_name(self):
        backend = InMemoryCredentialBackend()
        store = CredentialStore(backend=backend)

        assert store.service_name == DEFAULT_SERVICE_NAME == "structural-engineering-kb"
        assert store.has_credentials() is False
        assert store.load_credentials() is None

        payload = {
            "access_token": "ya29.test_access_token_value_123",
            "refresh_token": "1//0gTestRefreshTokenXYZ",
            "client_id": "test-client-id.apps.googleusercontent.com",
            "client_secret": "GOCSPX-TestSecret9999",
        }
        store.save_credentials(payload)

        assert store.has_credentials() is True
        loaded = store.load_credentials()
        assert loaded == payload
        assert backend.get_password("structural-engineering-kb", store.account_name) is not None

        assert store.delete_credentials() is True
        assert store.has_credentials() is False
        assert store.delete_credentials() is False

    def test_keyring_error_falls_back_gracefully_and_redacts_secrets(self, monkeypatch):
        import cloud.credential_store as cred_mod

        class FakeKeyringError(Exception):
            pass

        class FailingKeyring:
            @staticmethod
            def get_keyring():
                return object()

            @staticmethod
            def get_password(service_name, username):
                raise FakeKeyringError("Simulated locked keyring")

            @staticmethod
            def set_password(service_name, username, password):
                raise FakeKeyringError("Simulated locked keyring")

            @staticmethod
            def delete_password(service_name, username):
                raise FakeKeyringError("Simulated locked keyring")

        monkeypatch.setattr(cred_mod, "_os_keyring", FailingKeyring)
        monkeypatch.setattr(cred_mod, "_KeyringError", FakeKeyringError)

        store = CredentialStore(allow_memory_fallback=True)
        # get_keyring() succeeded above so _backend_type starts as "keyring";
        # calling save_credentials triggers FakeKeyringError and switches to memory_fallback.
        assert store.backend_type == "keyring"
        store.save_credentials({"refresh_token": "refresh-secret-abc"})
        assert store.backend_type == "memory_fallback"
        assert store.has_credentials() is True
        assert store.load_credentials() == {"refresh_token": "refresh-secret-abc"}

        raw_log = (
            "Auth failed with Bearer abc123.xyz+99= "
            "access_token=ya29.SuperSecretTokenValue "
            'client_secret="GOCSPX-MySecretClientKey" '
            '{"refresh_token": "1//0gMyRefreshSecret"}'
        )
        scrubbed = redact_sensitive(raw_log, extra_secrets=["1//0gMyRefreshSecret"])
        assert "abc123.xyz+99=" not in scrubbed
        assert "ya29.SuperSecretTokenValue" not in scrubbed
        assert "GOCSPX-MySecretClientKey" not in scrubbed
        assert "1//0gMyRefreshSecret" not in scrubbed
        assert "[REDACTED" in scrubbed


class TestLocalCacheManager:
    def test_real_repository_offline_status_92_of_92_verified(self):
        repo_root = Path(__file__).resolve().parent.parent
        cache_mgr = LocalCacheManager(root_dir=repo_root)
        status = cache_mgr.get_offline_status()

        assert status["manifest_present"] is True
        assert status["total_registered"] == 92
        assert status["verified_count"] == 92
        assert status["missing_files"] == []
        assert status["mismatched_files"] == []
        assert status["is_offline_ready"] is True

    def test_stage_conflict_copy_backup_and_explicit_resolution(self, tmp_path):
        rel = "database/asce_7/v7_22/test_table.csv"
        local_bytes = b"\xef\xbb\xbfcol_a,col_b\n1,2\n"
        remote_bytes = b"\xef\xbb\xbfcol_a,col_b\n1,99\n"

        local_file = tmp_path / rel
        local_file.parent.mkdir(parents=True, exist_ok=True)
        local_file.write_bytes(local_bytes)

        cache_mgr = LocalCacheManager(root_dir=tmp_path)
        conflict_path = cache_mgr.stage_conflict_copy(
            relative_path=rel,
            remote_bytes=remote_bytes,
            remote_modified_time="2026-11-18T08:00:00Z",
        )

        # Active local file must remain untouched; remote copy preserved in conflicts/
        assert local_file.read_bytes() == local_bytes
        assert conflict_path.exists()
        assert conflict_path.parent == tmp_path / "storage" / "local_cache" / "conflicts"
        assert conflict_path.read_bytes() == remote_bytes

        pending = cache_mgr.list_pending_conflicts()
        assert len(pending) == 1
        assert pending[0]["relative_path"] == rel

        # Explicit resolution 'accept_remote' backs up superseded local file first
        resolved = cache_mgr.resolve_conflict(pending[0]["conflict_id"], "accept_remote")
        assert resolved["resolution_status"] == "resolved:accept_remote"
        assert local_file.read_bytes() == remote_bytes
        backup_file = Path(resolved["backup_path"])
        assert backup_file.exists()
        assert backup_file.parent == tmp_path / "backup"
        assert "_backup" in backup_file.name
        assert backup_file.read_bytes() == local_bytes
        assert cache_mgr.list_pending_conflicts() == []

        # Second backup_before_replace preserves first backup instead of overwriting
        second_backup = cache_mgr.backup_before_replace(rel)
        assert second_backup is not None
        assert second_backup != backup_file
        assert backup_file.exists() and second_backup.exists()

    def test_path_traversal_blocked(self, tmp_path):
        cache_mgr = LocalCacheManager(root_dir=tmp_path)
        with pytest.raises(ValueError, match="Path traversal"):
            cache_mgr.normalize_relative_path("../../outside.csv")


class TestCloudSyncService:
    def test_offline_and_unauthenticated_fallback_never_blocks_calculations(self, tmp_path):
        repo_root = Path(__file__).resolve().parent.parent

        # 1. Default unauthenticated GoogleDriveApiClient -> AUTH_REQUIRED, non-blocking
        cred_store = CredentialStore(backend=InMemoryCredentialBackend())
        sync_unauth = CloudSyncService(
            root_dir=repo_root,
            credential_store=cred_store,
            log_path=tmp_path / "logs" / "cloud_sync.log",
        )
        assert sync_unauth.check_connection() == SyncConnectionStatus.AUTH_REQUIRED
        res_unauth = sync_unauth.sync_knowledge_base(direction="pull")
        assert res_unauth.connection_status == SyncConnectionStatus.AUTH_REQUIRED
        assert res_unauth.status == "AUTH_REQUIRED"
        assert res_unauth.offline_ready is True

        # 2. Disconnected network error -> OFFLINE, non-blocking
        mock_offline = MockDriveClient(connected=ConnectionError("Network unreachable; Bearer ya29.secret_tok_999"))
        sync_offline = CloudSyncService(
            root_dir=repo_root,
            credential_store=cred_store,
            drive_client=mock_offline,
            log_path=tmp_path / "logs" / "cloud_sync.log",
        )
        assert sync_offline.check_connection() == SyncConnectionStatus.OFFLINE
        res_offline = sync_offline.sync_knowledge_base(direction="pull")
        assert res_offline.connection_status == SyncConnectionStatus.OFFLINE
        assert res_offline.status == "OFFLINE"
        assert res_offline.offline_ready is True

        # Log file contains no leaked Bearer token
        log_text = (tmp_path / "logs" / "cloud_sync.log").read_text(encoding="utf-8")
        assert "ya29.secret_tok_999" not in log_text

        # Deterministic local calculation runs 100% unblocked offline
        kb = KnowledgeBaseService(root_dir=repo_root)
        calc_res = calculate_parapet_wind(
            inputs={"V_mph": 115.0, "h_roof_ft": 25.0, "h_par_ft": 3.5},
            kb=kb,
            design_method=DesignMethod.ASD,
            calculation_id="offline-parapet-01",
        )
        assert calc_res.status == CalculationStatus.PASS

    def test_download_missing_raw_files_with_sha256_verification(self, tmp_path):
        csv_rel = "database/asce_7/v7_22/sample_wind.csv"
        md_rel = "procedures/01_loads_and_seismic/sample_proc.md"
        csv_bytes = b"\xef\xbb\xbfzone,p_psf\nZ1,25.0\n"
        md_bytes = b"# Procedure\nSection 1\n"

        _build_temp_kb_workspace(tmp_path, {csv_rel: csv_bytes, md_rel: md_bytes})

        remote_files = [
            RemoteFileMetadata(
                file_id="drv-01",
                name="sample_wind.csv",
                relative_path=csv_rel,
                mime_type=RAW_UPLOAD_MIME_TYPE,
                sha256=_sha256(csv_bytes),
            ),
            RemoteFileMetadata(
                file_id="drv-02",
                name="sample_proc.md",
                relative_path=md_rel,
                mime_type=RAW_UPLOAD_MIME_TYPE,
                sha256=_sha256(md_bytes),
            ),
        ]
        mock_drive = MockDriveClient(
            connected=True,
            remote_files=remote_files,
            payloads={"drv-01": csv_bytes, "drv-02": md_bytes},
        )

        sync = CloudSyncService(root_dir=tmp_path, drive_client=mock_drive)
        plan = sync.plan_sync()
        assert len(plan.to_download) == 2

        result = sync.sync_knowledge_base(direction="pull")
        assert result.status == "SUCCESS"
        assert result.files_synced == 2
        assert set(result.downloaded) == {csv_rel, md_rel}
        assert result.offline_ready is True
        assert (tmp_path / csv_rel).read_bytes() == csv_bytes
        assert (tmp_path / md_rel).read_bytes() == md_bytes

    def test_quarantine_corrupted_download_on_sha256_mismatch(self, tmp_path):
        csv_rel = "database/asce_7/v7_22/corrupt_table.csv"
        valid_bytes = b"\xef\xbb\xbfid,val\n1,100\n"
        corrupted_bytes = b"\xef\xbb\xbfid,val\n1,999_TAMPERED\n"

        _build_temp_kb_workspace(tmp_path, {csv_rel: valid_bytes})
        mock_drive = MockDriveClient(
            connected=True,
            remote_files=[
                RemoteFileMetadata(
                    file_id="drv-01",
                    name="corrupt_table.csv",
                    relative_path=csv_rel,
                    mime_type=RAW_UPLOAD_MIME_TYPE,
                    sha256=_sha256(corrupted_bytes),
                )
            ],
            payloads={"drv-01": corrupted_bytes},
        )

        sync = CloudSyncService(root_dir=tmp_path, drive_client=mock_drive)
        result = sync.sync_knowledge_base(direction="pull")

        assert result.status == "INTEGRITY_ERROR"
        assert result.offline_ready is False
        assert len(result.quarantined) == 1
        assert not (tmp_path / csv_rel).exists()

        q_path = Path(result.quarantined[0]["quarantine_path"])
        assert q_path.exists()
        assert q_path.parent == tmp_path / "storage" / "local_cache" / "quarantine"
        assert q_path.read_bytes() == corrupted_bytes

        # Also verify strict mode raises CloudSyncPolicyError
        with pytest.raises(CloudSyncPolicyError, match="SHA-256 mismatch"):
            sync.sync_knowledge_base(direction="pull", raise_on_integrity_error=True)

    def test_conflict_preserves_both_copies_without_overwriting_local(self, tmp_path):
        md_rel = "procedures/02_wood_design/wood_bolt_workflow.md"
        manifest_bytes = b"# Baseline Procedure\n"
        local_edited_bytes = b"# Locally Edited Procedure\nlocal edit\n"
        remote_edited_bytes = b"# Remotely Edited Procedure\nremote edit\n"

        _build_temp_kb_workspace(tmp_path, {md_rel: manifest_bytes})
        local_path = tmp_path / md_rel
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(local_edited_bytes)

        mock_drive = MockDriveClient(
            connected=True,
            remote_files=[
                RemoteFileMetadata(
                    file_id="drv-01",
                    name="wood_bolt_workflow.md",
                    relative_path=md_rel,
                    mime_type=RAW_UPLOAD_MIME_TYPE,
                    sha256=_sha256(remote_edited_bytes),
                    modified_time="2026-11-18T08:30:00Z",
                )
            ],
            payloads={"drv-01": remote_edited_bytes},
        )

        sync = CloudSyncService(root_dir=tmp_path, drive_client=mock_drive)
        plan = sync.plan_sync()
        assert len(plan.conflicts) == 1

        result = sync.sync_knowledge_base(direction="pull")
        assert result.status == "PARTIAL_WITH_CONFLICTS"
        assert len(result.conflicts) == 1
        assert local_path.read_bytes() == local_edited_bytes

        staged_copy = Path(result.conflicts[0]["conflict_copy_path"])
        assert staged_copy.exists()
        assert staged_copy.parent == tmp_path / "storage" / "local_cache" / "conflicts"
        assert staged_copy.read_bytes() == remote_edited_bytes
        assert len(sync.cache_manager.list_pending_conflicts()) == 1

    def test_raw_octet_stream_enforced_and_google_docs_sheets_rejected(self, tmp_path):
        csv_rel = "database/nds_wood/v2024/bolts.csv"
        md_rel = "procedures/02_wood_design/bolts.md"
        gdoc_rel = "procedures/03_steel_design/steel_sheet.md"

        csv_bytes = b"\xef\xbb\xbfdia,Z\n0.5,500\n"
        md_bytes = b"# Bolts\n"
        gdoc_bytes = b"# Steel\n"

        _build_temp_kb_workspace(tmp_path, {csv_rel: csv_bytes, md_rel: md_bytes, gdoc_rel: gdoc_bytes})
        for rel, content in [(csv_rel, csv_bytes), (md_rel, md_bytes)]:
            p = tmp_path / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(content)

        # Remote contains a converted Google Doc for gdoc_rel and nothing for csv_rel / md_rel
        mock_drive = MockDriveClient(
            connected=True,
            remote_files=[
                RemoteFileMetadata(
                    file_id="drv-03",
                    name="steel_sheet.md",
                    relative_path=gdoc_rel,
                    mime_type="application/vnd.google-apps.document",
                )
            ],
        )

        sync = CloudSyncService(root_dir=tmp_path, drive_client=mock_drive)

        # Direct upload attempts violating Rule 3 must be rejected
        with pytest.raises(CloudSyncPolicyError):
            sync.upload_raw_file(csv_rel, mime_type="application/vnd.google-apps.spreadsheet")
        with pytest.raises(CloudSyncPolicyError):
            sync.upload_raw_file(md_rel, mime_type="application/vnd.google-apps.document")
        with pytest.raises(CloudSyncPolicyError):
            sync.upload_raw_file(csv_rel, convert=True)

        # Bidirectional sync rejects converted remote file and pushes raw local files as octet-stream
        result = sync.sync_knowledge_base(direction="bidirectional")
        assert len(result.rejected_conversions) == 1
        assert result.rejected_conversions[0]["relative_path"] == gdoc_rel
        assert set(result.uploaded) == {csv_rel, md_rel}
        assert len(mock_drive.upload_calls) == 2
        assert all(c["mime_type"] == "application/octet-stream" and c["convert"] is False for c in mock_drive.upload_calls)
        assert not (tmp_path / gdoc_rel).exists()

    def test_refuses_to_sync_sqlite_project_databases_decision_d7(self, tmp_path):
        csv_rel = "database/aisc_360/v16th_ed/welds.csv"
        csv_bytes = b"\xef\xbb\xbfsize,cap\n0.25,5.56\n"
        _build_temp_kb_workspace(tmp_path, {csv_rel: csv_bytes})
        (tmp_path / csv_rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / csv_rel).write_bytes(csv_bytes)

        db_path = tmp_path / "storage" / "projects" / "structural_app.sqlite3"
        repo = ProjectRepository(db_path=db_path, backup_dir=tmp_path / "storage" / "backups")

        mock_drive = MockDriveClient(
            connected=True,
            remote_files=[
                RemoteFileMetadata(
                    file_id="drv-01",
                    name="welds.csv",
                    relative_path=csv_rel,
                    mime_type=RAW_UPLOAD_MIME_TYPE,
                    sha256=_sha256(csv_bytes),
                ),
                RemoteFileMetadata(
                    file_id="drv-sql",
                    name="structural_app.sqlite3",
                    relative_path="storage/projects/structural_app.sqlite3",
                    mime_type=RAW_UPLOAD_MIME_TYPE,
                ),
            ],
            payloads={"drv-01": csv_bytes, "drv-sql": b"corrupt-remote-db"},
        )

        sync = CloudSyncService(root_dir=tmp_path, drive_client=mock_drive, repository=repo)

        with pytest.raises(CloudSyncPolicyError, match="Decision D-7"):
            sync.upload_raw_file("storage/projects/structural_app.sqlite3")

        plan = sync.plan_sync()
        assert "storage/projects/structural_app.sqlite3" in plan.skipped_sqlite
        assert all(not item["relative_path"].endswith(".sqlite3") for item in plan.to_upload)
        assert all(not item["relative_path"].endswith(".sqlite3") for item in plan.to_download)

        result = sync.sync_knowledge_base(direction="bidirectional")
        assert "storage/projects/structural_app.sqlite3" in result.skipped_sqlite
        assert mock_drive.upload_calls == []
        # Local SQLite database remains intact and queryable
        assert repo.get_schema_version() == 2

    def test_records_sync_history_and_handles_mid_sync_disconnect(self, tmp_path):
        csv1 = "database/asce_7/v7_22/f1.csv"
        csv2 = "database/asce_7/v7_22/f2.csv"
        b1 = b"\xef\xbb\xbfa,b\n1,2\n"
        b2 = b"\xef\xbb\xbfc,d\n3,4\n"

        _build_temp_kb_workspace(tmp_path, {csv1: b1, csv2: b2})
        db_path = tmp_path / "storage" / "projects" / "sync_audit.sqlite3"
        repo = ProjectRepository(db_path=db_path, backup_dir=tmp_path / "storage" / "backups")

        cred_store = CredentialStore(backend=InMemoryCredentialBackend())
        cred_store.save_credentials({"access_token": "ya29.TopSecretRuntimeToken12345"})

        mock_drive = MockDriveClient(
            connected=True,
            remote_files=[
                RemoteFileMetadata(file_id="drv-01", name="f1.csv", relative_path=csv1, sha256=_sha256(b1)),
                RemoteFileMetadata(file_id="drv-02", name="f2.csv", relative_path=csv2, sha256=_sha256(b2)),
            ],
            payloads={"drv-01": b1},
            fail_download_ids={
                "drv-02": ConnectionError("Socket reset; token=ya29.TopSecretRuntimeToken12345")
            },
        )

        log_file = tmp_path / "logs" / "cloud_sync.log"
        sync = CloudSyncService(
            root_dir=tmp_path,
            credential_store=cred_store,
            drive_client=mock_drive,
            repository=repo,
            log_path=log_file,
        )

        # Mid-sync disconnect should not crash; f1 stays downloaded, f2 error redacted, audit persisted
        result = sync.sync_knowledge_base(direction="pull")
        assert result.connection_status == SyncConnectionStatus.OFFLINE
        assert result.status == "OFFLINE"
        assert result.downloaded == [csv1]
        assert (tmp_path / csv1).read_bytes() == b1
        assert not (tmp_path / csv2).exists()
        assert "ya29.TopSecretRuntimeToken12345" not in " ".join(result.errors)
        assert "ya29.TopSecretRuntimeToken12345" not in log_file.read_text(encoding="utf-8")

        conn = sqlite3.connect(str(db_path))
        try:
            rows = conn.execute(
                "SELECT sync_id, direction, files_synced, conflicts, status, details_json FROM sync_history;"
            ).fetchall()
            assert len(rows) == 1
            assert rows[0][0] == result.sync_id
            assert rows[0][1] == "pull"
            assert rows[0][2] == 1
            assert rows[0][3] == 0
            assert rows[0][4] == "OFFLINE"
            details = json.loads(rows[0][5])
            assert details["downloaded"] == [csv1]
        finally:
            conn.close()
