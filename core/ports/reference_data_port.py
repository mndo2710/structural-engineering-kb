"""Domain-owned ReferenceDataPort protocol (Clean Architecture Dependency Inversion boundary).

Resolves F-07 by allowing `core/` calculation modules to depend strictly on an abstract
port owned by `core/ports/` rather than concrete `app.services.knowledge_base_service`
or any `gui/` / `storage/` modules.
"""

from pathlib import Path
from typing import Any, Dict, List, Protocol, Union, runtime_checkable


@runtime_checkable
class ReferenceDataPort(Protocol):
    """Protocol defining reference lookup, procedure loading, and integrity access for `core/`."""

    def resolve_reference(self, identifier: str) -> Dict[str, Any]:
        """Resolve a table or procedure identifier to its manifest metadata entry."""
        ...

    def get_file_path(self, identifier: str) -> Path:
        """Resolve the filesystem path for a reference identifier or relative path."""
        ...

    def get_table(self, identifier: str) -> Any:
        """Load a CSV lookup table (typically returning a pandas DataFrame)."""
        ...

    def get_table_as_dicts(self, identifier: str) -> List[Dict[str, Any]]:
        """Load a CSV lookup table as a list of row dictionaries."""
        ...

    def get_procedure(self, identifier: str) -> str:
        """Load a Markdown calculation procedure document as text."""
        ...

    def lookup_value(
        self,
        identifier: str,
        match_col: str,
        match_val: Any,
        target_col: str,
    ) -> Any:
        """Look up a single target column value where match_col matches match_val."""
        ...

    def filter_rows(self, identifier: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Filter table rows matching all key-value conditions in filters."""
        ...

    @staticmethod
    def compute_sha256(file_path: Union[str, Path]) -> str:
        """Compute the lowercase hexadecimal SHA-256 checksum for a file."""
        ...

    def verify_integrity(self) -> Dict[str, Any]:
        """Verify manifest reference files exist on disk and match expected SHA-256 hashes."""
        ...
