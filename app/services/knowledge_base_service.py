"""KnowledgeBaseService: CSV Table & Markdown Procedure Access and Integrity Service.

Conforms to SAD v1.0 Section 5.3 & Master Rules 1, 2, 4.
Loads reference data strictly from database/ and procedures/ with utf-8-sig encoding.
Provides caching and SHA-256 integrity verification.
"""

import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import pandas as pd

from core.common.exceptions import (
    ReferenceDataNotFoundError,
    ReferenceIntegrityError,
)


class KnowledgeBaseService:
    """Central service for loading, caching, and verifying engineering reference content."""

    def __init__(self, root_dir: Optional[Union[str, Path]] = None, manifest_path: Optional[Union[str, Path]] = None) -> None:
        if root_dir is None:
            # Default to repo root (two levels up from app/services/)
            self.root_dir = Path(__file__).resolve().parent.parent.parent
        else:
            self.root_dir = Path(root_dir).resolve()

        if manifest_path is None:
            self.manifest_path = self.root_dir / "config" / "reference_manifest.json"
        else:
            self.manifest_path = Path(manifest_path).resolve()

        self.database_dir = self.root_dir / "database"
        self.procedures_dir = self.root_dir / "procedures"

        # Manifest data
        self.manifest_data: Dict[str, Any] = {}
        self._references_by_id: Dict[str, Dict[str, Any]] = {}
        self._references_by_filename: Dict[str, Dict[str, Any]] = {}
        self._references_by_path: Dict[str, Dict[str, Any]] = {}

        # In-memory caches to prevent repeated disk I/O
        self._table_cache: Dict[str, pd.DataFrame] = {}
        self._table_dicts_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._procedure_cache: Dict[str, str] = {}

        self.reload_manifest()

    def reload_manifest(self) -> None:
        """Load or reload reference_manifest.json and re-index references."""
        if not self.manifest_path.exists():
            raise ReferenceDataNotFoundError(f"Reference manifest not found at: {self.manifest_path}")

        with open(self.manifest_path, "r", encoding="utf-8") as f:
            self.manifest_data = json.load(f)

        self._references_by_id.clear()
        self._references_by_filename.clear()
        self._references_by_path.clear()

        for ref in self.manifest_data.get("references", []):
            ref_id = ref.get("reference_id")
            file_name = ref.get("file_name")
            rel_path = ref.get("relative_path")

            if ref_id:
                self._references_by_id[ref_id] = ref
            if file_name:
                self._references_by_filename[file_name] = ref
            if rel_path:
                normalized_path = str(Path(rel_path)).replace("\\", "/")
                self._references_by_path[normalized_path] = ref

    def resolve_reference(self, identifier: str) -> Dict[str, Any]:
        """Resolve a table or procedure identifier to its manifest entry."""
        # 1. Lookup by reference_id
        if identifier in self._references_by_id:
            return self._references_by_id[identifier]

        # 2. Lookup by file_name
        if identifier in self._references_by_filename:
            return self._references_by_filename[identifier]

        # 3. Lookup by normalized relative path
        norm = str(Path(identifier)).replace("\\", "/")
        if norm in self._references_by_path:
            return self._references_by_path[norm]

        raise ReferenceDataNotFoundError(f"Reference not registered in manifest: '{identifier}'")

    def get_file_path(self, identifier: str) -> Path:
        """Resolve full filesystem Path for a given reference identifier or relative path."""
        try:
            ref = self.resolve_reference(identifier)
            rel_path = ref.get("relative_path", "")
            full_path = self.root_dir / rel_path
            if full_path.exists():
                return full_path
        except ReferenceDataNotFoundError:
            pass

        # Fallback: check direct paths under root_dir, database_dir, or procedures_dir
        for base_dir in (self.root_dir, self.database_dir, self.procedures_dir):
            direct = base_dir / identifier
            if direct.is_file():
                return direct

        # Fallback: search by filename in database/ or procedures/
        leaf_name = Path(identifier).name
        for candidate in self.database_dir.rglob(leaf_name):
            if candidate.is_file() and candidate.as_posix().endswith(identifier.replace("\\", "/")):
                return candidate
        for candidate in self.procedures_dir.rglob(leaf_name):
            if candidate.is_file() and candidate.as_posix().endswith(identifier.replace("\\", "/")):
                return candidate

        raise ReferenceDataNotFoundError(f"Reference file not found on disk: '{identifier}'")

    def get_table_raw_rows(self, identifier: str) -> List[List[str]]:
        """Read all non-empty raw CSV rows using utf-8-sig encoding."""
        file_path = self.get_file_path(identifier)
        try:
            with open(file_path, mode="r", encoding="utf-8-sig", newline="") as f:
                return [row for row in csv.reader(f) if any(str(cell).strip() != "" for cell in row)]
        except Exception as e:
            raise ReferenceIntegrityError(f"Failed to read raw CSV rows '{file_path}': {e}") from e

    @staticmethod
    def _make_unique_headers(raw_headers: List[str], max_cols: int) -> List[str]:
        seen: Dict[str, int] = {}
        headers: List[str] = []
        for idx in range(max_cols):
            base = str(raw_headers[idx]).strip() if idx < len(raw_headers) else ""
            if not base:
                base = f"Column_{idx + 1}"
            count = seen.get(base, 0) + 1
            seen[base] = count
            headers.append(base if count == 1 else f"{base}_{count}")
        return headers

    def get_table(self, identifier: str) -> pd.DataFrame:
        """
        Load CSV lookup table as pandas DataFrame with utf-8-sig encoding per Master Rule 4.
        Supports both standard uniform CSVs and ragged multi-header / banner / footnote CSVs.
        Caches DataFrame in memory for subsequent zero-overhead access.
        """
        file_path = self.get_file_path(identifier)
        cache_key = str(file_path.resolve())

        if cache_key in self._table_cache:
            return self._table_cache[cache_key].copy()

        try:
            raw_rows = self.get_table_raw_rows(identifier)
            if not raw_rows:
                df = pd.DataFrame()
                self._table_cache[cache_key] = df
                return df.copy()

            max_cols = max(len(r) for r in raw_rows)
            row_lens = {len(r) for r in raw_rows}

            # Use fast pd.read_csv only when header width matches max_cols and > 1
            if len(row_lens) == 1 and max_cols > 1:
                df = pd.read_csv(file_path, encoding="utf-8-sig")
            elif len(raw_rows[0]) == max_cols and max_cols > 1:
                try:
                    df = pd.read_csv(file_path, encoding="utf-8-sig")
                    if len(df.columns) != max_cols:
                        raise ValueError("Column count mismatch")
                except Exception:
                    df = self._parse_ragged_csv_to_dataframe(raw_rows, max_cols)
            else:
                df = self._parse_ragged_csv_to_dataframe(raw_rows, max_cols)

            self._table_cache[cache_key] = df
            return df.copy()
        except ReferenceIntegrityError:
            raise
        except Exception as e:
            raise ReferenceIntegrityError(f"Failed to read CSV table '{file_path}': {e}") from e

    def _parse_ragged_csv_to_dataframe(self, raw_rows: List[List[str]], max_cols: int) -> pd.DataFrame:
        """Parse ragged multi-header/banner/footnote CSV rows into a uniform DataFrame."""
        header_idx = next((i for i, r in enumerate(raw_rows) if len(r) == max_cols), 0)
        headers = self._make_unique_headers(raw_rows[header_idx], max_cols)
        data_rows: List[List[str]] = []
        for r in raw_rows[header_idx + 1 :]:
            padded = [str(c) for c in r] + [""] * max(0, max_cols - len(r))
            data_rows.append(padded[:max_cols])
        return pd.DataFrame(data_rows, columns=headers)

    def get_table_as_dicts(self, identifier: str) -> List[Dict[str, Any]]:
        """Return CSV table as list of row dictionaries."""
        file_path = self.get_file_path(identifier)
        cache_key = str(file_path.resolve())

        if cache_key in self._table_dicts_cache:
            return [dict(row) for row in self._table_dicts_cache[cache_key]]

        try:
            with open(file_path, mode="r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            self._table_dicts_cache[cache_key] = rows
            return [dict(row) for row in rows]
        except Exception as e:
            raise ReferenceIntegrityError(f"Failed to parse CSV dicts '{file_path}': {e}") from e

    def get_procedure(self, identifier: str) -> str:
        """
        Load Markdown calculation procedure as text string.
        Caches content in memory for rapid repeated access.
        """
        file_path = self.get_file_path(identifier)
        cache_key = str(file_path.resolve())

        if cache_key in self._procedure_cache:
            return self._procedure_cache[cache_key]

        try:
            with open(file_path, mode="r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            self._procedure_cache[cache_key] = content
            return content
        except Exception as e:
            raise ReferenceIntegrityError(f"Failed to read procedure '{file_path}': {e}") from e

    def lookup_value(
        self,
        identifier: str,
        match_col: str,
        match_val: Any,
        target_col: str
    ) -> Any:
        """
        Lookup a single target value from a CSV table where match_col == match_val.
        Deterministic lookup matching SAD v1.0 Section 5.3.
        """
        df = self.get_table(identifier)
        if match_col not in df.columns:
            raise ReferenceDataNotFoundError(f"Column '{match_col}' not in table '{identifier}'.")
        if target_col not in df.columns:
            raise ReferenceDataNotFoundError(f"Column '{target_col}' not in table '{identifier}'.")

        # Convert both to string for robust comparison, stripping whitespace
        s_val = str(match_val).strip()
        matched = df[df[match_col].astype(str).str.strip() == s_val]

        if matched.empty:
            raise ReferenceDataNotFoundError(
                f"No row found in '{identifier}' where '{match_col}' == '{match_val}'."
            )
        return matched.iloc[0][target_col]

    def filter_rows(self, identifier: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Filter table rows matching all key-value conditions in filters dict."""
        rows = self.get_table_as_dicts(identifier)
        result: List[Dict[str, Any]] = []
        for row in rows:
            matches = True
            for k, v in filters.items():
                if k not in row or str(row[k]).strip() != str(v).strip():
                    matches = False
                    break
            if matches:
                result.append(row)
        return result

    @staticmethod
    def compute_sha256(file_path: Union[str, Path]) -> str:
        """Compute SHA-256 hash of a file."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    def verify_integrity(self) -> Dict[str, Any]:
        """
        Verify all registered reference files in reference_manifest.json exist on disk
        and calculate their SHA-256 checksums.
        """
        missing: List[str] = []
        verified: List[Dict[str, Any]] = []
        checksum_mismatches: List[str] = []

        for ref in self.manifest_data.get("references", []):
            ref_id = ref.get("reference_id", "unknown")
            rel_path = ref.get("relative_path", "")
            full_path = self.root_dir / rel_path

            if not full_path.exists():
                missing.append(f"{ref_id} ({rel_path})")
                continue

            # Compute current checksum
            sha256 = self.compute_sha256(full_path)
            expected_sha = ref.get("sha256")

            if expected_sha and expected_sha != sha256:
                checksum_mismatches.append(f"{ref_id}: expected {expected_sha}, got {sha256}")
            else:
                verified.append({
                    "reference_id": ref_id,
                    "relative_path": rel_path,
                    "sha256": sha256,
                    "size_bytes": full_path.stat().st_size
                })

        return {
            "total_registered": len(self.manifest_data.get("references", [])),
            "verified_count": len(verified),
            "missing_count": len(missing),
            "missing_files": missing,
            "mismatch_count": len(checksum_mismatches),
            "mismatches": checksum_mismatches,
            "verified_details": verified
        }

    def sync_manifest_checksums(self) -> int:
        """
        Compute SHA-256 for all reference files in the manifest and save back to
        config/reference_manifest.json. Returns count of references updated.
        """
        updated_count = 0
        for ref in self.manifest_data.get("references", []):
            rel_path = ref.get("relative_path", "")
            full_path = self.root_dir / rel_path
            if full_path.exists():
                ref["sha256"] = self.compute_sha256(full_path)
                updated_count += 1

        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(self.manifest_data, f, indent=2, ensure_ascii=False)

        self.reload_manifest()
        return updated_count

    def clear_cache(self) -> None:
        """Clear all in-memory table and procedure caches."""
        self._table_cache.clear()
        self._table_dicts_cache.clear()
        self._procedure_cache.clear()
