"""HistoryService: Calculation Revision Tracking and Audit Service.

Conforms to SAD v1.0 Section 7.2 & 9.4.
Enforces immutable calculation history and change detection across revisions.
"""

from typing import Any, Dict, List, Optional
from storage.repositories.project_repository import ProjectRepository


class HistoryService:
    """Provides calculation revision history, audit trails, and input/output diffing."""

    def __init__(self, repository: Optional[ProjectRepository] = None) -> None:
        self.repository = repository or ProjectRepository()

    def get_history(self, calculation_id: str) -> List[Dict[str, Any]]:
        """Retrieve revision summary list for a calculation."""
        return self.repository.get_calculation_revisions(calculation_id)

    def get_revision(self, calculation_id: str, revision_number: int) -> Optional[Dict[str, Any]]:
        """Retrieve full details of a specific revision."""
        return self.repository.get_revision_detail(calculation_id, revision_number)

    def compare_revisions(
        self,
        calculation_id: str,
        from_revision: int,
        to_revision: int
    ) -> Dict[str, Any]:
        """
        Compare inputs and results between two calculation revisions.
        Returns detailed parameter deltas and result changes.
        """
        r1 = self.get_revision(calculation_id, from_revision)
        r2 = self.get_revision(calculation_id, to_revision)

        if not r1:
            raise ValueError(f"Revision {from_revision} not found for calculation '{calculation_id}'.")
        if not r2:
            raise ValueError(f"Revision {to_revision} not found for calculation '{calculation_id}'.")

        inputs1 = r1.get("inputs", {})
        inputs2 = r2.get("inputs", {})

        # Compute input diffs
        all_keys = set(inputs1.keys()).union(set(inputs2.keys()))
        input_diffs: Dict[str, Dict[str, Any]] = {}
        for k in sorted(all_keys):
            v1 = inputs1.get(k)
            v2 = inputs2.get(k)
            if v1 != v2:
                input_diffs[k] = {
                    "previous": v1,
                    "current": v2,
                    "changed": True
                }

        # Result differences
        dcr_change = r2.get("dcr", 0.0) - r1.get("dcr", 0.0)

        return {
            "calculation_id": calculation_id,
            "from_revision": from_revision,
            "to_revision": to_revision,
            "from_date": r1.get("created_at"),
            "to_date": r2.get("created_at"),
            "change_notes": r2.get("change_notes", ""),
            "author": r2.get("created_by", ""),
            "input_diffs": input_diffs,
            "result_diffs": {
                "previous_status": r1.get("status"),
                "current_status": r2.get("status"),
                "previous_dcr": r1.get("dcr"),
                "current_dcr": r2.get("dcr"),
                "dcr_delta": round(dcr_change, 4),
                "previous_governing": r1.get("governing_limit_state"),
                "current_governing": r2.get("governing_limit_state"),
            }
        }
