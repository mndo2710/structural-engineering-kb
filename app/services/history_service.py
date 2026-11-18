"""HistoryService: Calculation Revision Tracking, Audit, and Reconstruction Service.

Conforms to SAD v1.1 Section 7.2 & 9.4.
Enforces immutable calculation history and change detection across revisions.
"""

import json
from typing import Any, Dict, List, Optional

from app.models import CalculationResult
from storage.repositories.project_repository import ProjectRepository


class HistoryService:
    """Provides calculation revision history, audit trails, diffing, and result reconstruction."""

    def __init__(self, repository: Optional[ProjectRepository] = None) -> None:
        self.repository = repository or ProjectRepository()

    def get_history(self, calculation_id: str) -> List[Dict[str, Any]]:
        """Retrieve revision summary list for a calculation."""
        return self.repository.get_calculation_revisions(calculation_id)

    def get_revision(self, calculation_id: str, revision_number: int) -> Optional[Dict[str, Any]]:
        """Retrieve full details of a specific revision."""
        return self.repository.get_revision_detail(calculation_id, revision_number)

    def reconstruct_calculation_result(
        self,
        calculation_id: str,
        revision_number: int,
    ) -> Optional[CalculationResult]:
        """
        Reconstruct a full CalculationResult (including limit_states and structured trace)
        from an immutable SQLite revision snapshot. Falls back gracefully on legacy payloads.
        """
        rev = self.get_revision(calculation_id, revision_number)
        if not rev:
            return None

        raw_results = rev.get("results")
        if raw_results is None and rev.get("results_json"):
            try:
                raw_results = json.loads(rev["results_json"])
            except (TypeError, json.JSONDecodeError):
                return None

        if not isinstance(raw_results, dict):
            return None

        payload: Dict[str, Any] = dict(raw_results)
        payload.setdefault("calculation_id", calculation_id)

        if "input_parameters" not in payload:
            raw_inputs = rev.get("inputs")
            if raw_inputs is None and rev.get("inputs_json"):
                try:
                    raw_inputs = json.loads(rev["inputs_json"])
                except (TypeError, json.JSONDecodeError):
                    raw_inputs = {}
            payload["input_parameters"] = dict(raw_inputs) if isinstance(raw_inputs, dict) else {}

        if not payload.get("governing_limit_state") and rev.get("governing_limit_state"):
            payload["governing_limit_state"] = rev["governing_limit_state"]

        if not payload.get("code_edition") and rev.get("code_edition"):
            payload["code_edition"] = rev["code_edition"]

        try:
            return CalculationResult.from_dict(payload)
        except Exception:
            # Graceful fallback for partial legacy revision rows without structured trace/limit_states
            try:
                return CalculationResult(
                    calculation_id=str(payload.get("calculation_id", calculation_id)),
                    module_id=str(payload.get("module_id", "")),
                    code_edition=str(payload.get("code_edition", "")),
                    design_method=payload.get("design_method", "ASD"),
                    input_parameters=dict(payload.get("input_parameters") or {}),
                    assumptions=[str(a) for a in (payload.get("assumptions") or [])],
                    intermediate_results=dict(payload.get("intermediate_results") or {}),
                    demand=float(payload.get("demand", 0.0)),
                    capacity=float(payload.get("capacity", 0.0)),
                    dcr=float(payload.get("dcr", 0.0)),
                    status=payload.get("status", "INCOMPLETE"),
                    reference_files=[str(rf) for rf in (payload.get("reference_files") or [])],
                    software_version=str(payload.get("software_version", "1.0.0")),
                    warnings=[str(w) for w in (payload.get("warnings") or [])],
                )
            except Exception:
                return None

    def compare_revisions(
        self,
        calculation_id: str,
        from_revision: int,
        to_revision: int,
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

        all_keys = set(inputs1.keys()).union(set(inputs2.keys()))
        input_diffs: Dict[str, Dict[str, Any]] = {}
        for k in sorted(all_keys):
            v1 = inputs1.get(k)
            v2 = inputs2.get(k)
            if v1 != v2:
                input_diffs[k] = {
                    "previous": v1,
                    "current": v2,
                    "changed": True,
                }

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
            },
        }
