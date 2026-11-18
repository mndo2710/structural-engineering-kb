"""Local Knowledge Base offline cache, SHA-256 verification, and conflict staging.

Conforms to SAD v1.1 Section 10, ADR-07, and Master Rule 3:
- Inspects database/, procedures/, and config/reference_manifest.json (92 references).
- Verifies SHA-256 checksums for deterministic offline readiness.
- Preserves conflicting remote copies under storage/local_cache/conflicts/ without
  ever overwriting modified local files silently.
- Quarantines corrupted downloads under storage/local_cache/quarantine/.
- Archives superseded local files to backup/ with a _backup suffix before replacement.
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional, Union
import uuid


class LocalCacheManager:
    """Manages local KB SHA-256 verification, offline readiness, backups, and conflict staging."""

    def __init__(
        self,
        root_dir: Optional[Union[str, Path]] = None,
        manifest_path: Optional[Union[str, Path]] = None,
        local_cache_dir: Optional[Union[str, Path]] = None,
        backup_dir: Optional[Union[str, Path]] = None,
    ) -> None:
        if root_dir is None:
            self.root_dir = Path(__file__).resolve().parent.parent
        else:
            self.root_dir = Path(root_dir).resolve()

        self.manifest_path = (
            Path(manifest_path).resolve()
            if manifest_path is not None
            else self.root_dir / "config" / "reference_manifest.json"
        )
        self.local_cache_dir = (
            Path(local_cache_dir).resolve()
            if local_cache_dir is not None
            else self.root_dir / "storage" / "local_cache"
        )
        self.backup_dir = (
            Path(backup_dir).resolve()
            if backup_dir is not None
            else self.root_dir / "backup"
        )
        self.conflicts_dir = self.local_cache_dir / "conflicts"
        self.quarantine_dir = self.local_cache_dir / "quarantine"

    @staticmethod
    def _utc_compact() -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")

    @staticmethod
    def _utc_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def compute_bytes_sha256(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def compute_sha256(file_path: Union[str, Path]) -> str:
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def compute_md5(file_path: Union[str, Path]) -> str:
        hasher = hashlib.md5()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    def normalize_relative_path(self, relative_path: str) -> str:
        """Normalize and validate that a relative path resolves safely inside root_dir."""
        rel_norm = str(relative_path).replace("\\", "/").lstrip("/")
        if not rel_norm:
            raise ValueError("relative_path must not be empty.")
        candidate = (self.root_dir / rel_norm).resolve()
        root_resolved = self.root_dir.resolve()
        if candidate != root_resolved and root_resolved not in candidate.parents:
            raise ValueError(f"Path traversal outside workspace root is prohibited: '{relative_path}'")
        return rel_norm

    def resolve_path(self, relative_path: str) -> Path:
        rel_norm = self.normalize_relative_path(relative_path)
        return (self.root_dir / rel_norm).resolve()

    def load_manifest(self) -> Dict[str, Any]:
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Reference manifest not found: {self.manifest_path}")
        with open(self.manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_manifest_entries(self) -> List[Dict[str, Any]]:
        data = self.load_manifest()
        refs = data.get("references", [])
        return [dict(r) for r in refs] if isinstance(refs, list) else []

    def get_offline_status(self) -> Dict[str, Any]:
        """
        Inspect local KB files against config/reference_manifest.json and report
        deterministic offline calculation readiness.
        """
        checked_at = self._utc_iso()
        if not self.manifest_path.exists():
            return {
                "is_offline_ready": False,
                "manifest_present": False,
                "manifest_path": str(self.manifest_path),
                "manifest_sha256": None,
                "verified_count": 0,
                "total_registered": 0,
                "missing_files": [str(self.manifest_path)],
                "mismatched_files": [],
                "pending_conflicts": len(self.list_pending_conflicts()),
                "checked_at": checked_at,
            }

        manifest_sha = self.compute_sha256(self.manifest_path)
        entries = self.get_manifest_entries()
        total_registered = len(entries)
        verified_count = 0
        missing_files: List[str] = []
        mismatched_files: List[str] = []

        for entry in entries:
            rel_path = self.normalize_relative_path(entry.get("relative_path", ""))
            expected_sha = entry.get("sha256", "")
            full_path = self.root_dir / rel_path

            if not full_path.exists():
                missing_files.append(rel_path)
                continue

            actual_sha = self.compute_sha256(full_path)
            if expected_sha and actual_sha != expected_sha:
                mismatched_files.append(rel_path)
            else:
                verified_count += 1

        is_ready = total_registered > 0 and not missing_files and not mismatched_files
        return {
            "is_offline_ready": is_ready,
            "manifest_present": True,
            "manifest_path": str(self.manifest_path),
            "manifest_sha256": manifest_sha,
            "verified_count": verified_count,
            "total_registered": total_registered,
            "missing_files": missing_files,
            "mismatched_files": mismatched_files,
            "pending_conflicts": len(self.list_pending_conflicts()),
            "checked_at": checked_at,
        }

    def _conflicts_index_path(self) -> Path:
        return self.conflicts_dir / "conflicts_index.json"

    def _load_conflicts_index(self) -> List[Dict[str, Any]]:
        idx_path = self._conflicts_index_path()
        if not idx_path.exists():
            return []
        try:
            with open(idx_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save_conflicts_index(self, records: List[Dict[str, Any]]) -> None:
        self.conflicts_dir.mkdir(parents=True, exist_ok=True)
        with open(self._conflicts_index_path(), "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)

    def list_pending_conflicts(self) -> List[Dict[str, Any]]:
        """Return conflict records awaiting explicit user resolution."""
        return [
            rec
            for rec in self._load_conflicts_index()
            if rec.get("resolution_status") == "pending_explicit_resolution"
        ]

    def stage_conflict_copy(
        self,
        relative_path: str,
        remote_bytes: bytes,
        remote_modified_time: str = "",
    ) -> Path:
        """
        Preserve both local and remote copies on sync conflict per Rule 3 and
        CONFLICT_POLICY = 'preserve_both_require_explicit_resolution'.
        Never overwrites the active local file.
        """
        rel_norm = self.normalize_relative_path(relative_path)
        local_path = self.resolve_path(rel_norm)
        local_sha = self.compute_sha256(local_path) if local_path.exists() else None
        remote_sha = self.compute_bytes_sha256(remote_bytes)

        self.conflicts_dir.mkdir(parents=True, exist_ok=True)
        ts = self._utc_compact()
        orig = Path(rel_norm)
        conflict_path = self.conflicts_dir / f"{orig.stem}_conflict_{ts}{orig.suffix}"
        counter = 1
        while conflict_path.exists():
            conflict_path = self.conflicts_dir / f"{orig.stem}_conflict_{ts}_{counter}{orig.suffix}"
            counter += 1

        conflict_path.write_bytes(remote_bytes)

        records = self._load_conflicts_index()
        records.append({
            "conflict_id": str(uuid.uuid4()),
            "relative_path": rel_norm,
            "local_path": str(local_path),
            "conflict_copy_path": str(conflict_path),
            "local_sha256": local_sha,
            "remote_sha256": remote_sha,
            "remote_modified_time": remote_modified_time,
            "detected_at": self._utc_iso(),
            "resolution_status": "pending_explicit_resolution",
        })
        self._save_conflicts_index(records)
        return conflict_path

    def resolve_conflict(self, conflict_id: str, choice: str) -> Dict[str, Any]:
        """
        Explicitly resolve a staged conflict ('keep_local', 'accept_remote', or 'keep_both').
        When 'accept_remote' is chosen, the superseded local file is backed up first.
        """
        valid_choices = {"keep_local", "accept_remote", "keep_both"}
        if choice not in valid_choices:
            raise ValueError(f"Unsupported conflict resolution choice '{choice}'. Expected one of {sorted(valid_choices)}.")

        records = self._load_conflicts_index()
        target: Optional[Dict[str, Any]] = None
        for rec in records:
            if rec.get("conflict_id") == conflict_id:
                target = rec
                break

        if target is None:
            raise ValueError(f"Conflict '{conflict_id}' not found.")

        rel_norm = target["relative_path"]
        local_path = self.resolve_path(rel_norm)
        conflict_copy = Path(target["conflict_copy_path"])

        backup_path: Optional[Path] = None
        if choice == "accept_remote":
            if not conflict_copy.exists():
                raise FileNotFoundError(f"Staged conflict copy missing: {conflict_copy}")
            backup_path = self.backup_before_replace(rel_norm)
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(conflict_copy.read_bytes())

        target["resolution_status"] = f"resolved:{choice}"
        target["resolved_at"] = self._utc_iso()
        if backup_path is not None:
            target["backup_path"] = str(backup_path)
        self._save_conflicts_index(records)
        return dict(target)

    def quarantine_corrupted_file(
        self,
        relative_path: str,
        payload: bytes,
        expected_sha256: str,
        actual_sha256: str,
    ) -> Path:
        """Isolate a download whose SHA-256 failed manifest verification without touching active KB."""
        rel_norm = self.normalize_relative_path(relative_path)
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)
        ts = self._utc_compact()
        orig = Path(rel_norm)
        quarantine_path = self.quarantine_dir / f"{orig.stem}_corrupted_{ts}{orig.suffix}"
        counter = 1
        while quarantine_path.exists():
            quarantine_path = self.quarantine_dir / f"{orig.stem}_corrupted_{ts}_{counter}{orig.suffix}"
            counter += 1

        quarantine_path.write_bytes(payload)

        meta_path = quarantine_path.with_suffix(f"{quarantine_path.suffix}.meta.json")
        meta = {
            "relative_path": rel_norm,
            "expected_sha256": expected_sha256,
            "actual_sha256": actual_sha256,
            "quarantined_at": self._utc_iso(),
            "quarantine_path": str(quarantine_path),
        }
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
        return quarantine_path

    def backup_before_replace(self, relative_path: str) -> Optional[Path]:
        """
        Copy an active local file into backup/ with a _backup suffix before replacing it
        per Master Rule 3. Returns backup Path, or None if the local file does not exist.
        """
        rel_norm = self.normalize_relative_path(relative_path)
        src = self.resolve_path(rel_norm)
        if not src.exists():
            return None

        self.backup_dir.mkdir(parents=True, exist_ok=True)
        candidate = self.backup_dir / f"{src.stem}_backup{src.suffix}"
        if candidate.exists():
            ts = self._utc_compact()
            candidate = self.backup_dir / f"{src.stem}_backup_{ts}{src.suffix}"
            counter = 1
            while candidate.exists():
                candidate = self.backup_dir / f"{src.stem}_backup_{ts}_{counter}{src.suffix}"
                counter += 1

        shutil.copy2(src, candidate)
        return candidate

    def write_verified_file(
        self,
        relative_path: str,
        payload: bytes,
        expected_sha256: Optional[str] = None,
    ) -> Path:
        """
        Verify SHA-256 (if expected_sha256 provided) and atomically write a KB file.
        On checksum mismatch, quarantines payload and raises ValueError.
        """
        rel_norm = self.normalize_relative_path(relative_path)
        actual_sha = self.compute_bytes_sha256(payload)
        if expected_sha256 and actual_sha != expected_sha256:
            q_path = self.quarantine_corrupted_file(
                relative_path=rel_norm,
                payload=payload,
                expected_sha256=expected_sha256,
                actual_sha256=actual_sha,
            )
            raise ValueError(
                f"SHA-256 verification failed for '{rel_norm}': expected {expected_sha256}, "
                f"got {actual_sha}. Quarantined at '{q_path}'."
            )

        target_path = self.resolve_path(rel_norm)
        if target_path.exists():
            existing_sha = self.compute_sha256(target_path)
            if existing_sha != actual_sha:
                self.backup_before_replace(rel_norm)

        target_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = target_path.with_name(f".{target_path.name}.{uuid.uuid4().hex}.tmp")
        try:
            tmp_path.write_bytes(payload)
            tmp_path.replace(target_path)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

        return target_path
