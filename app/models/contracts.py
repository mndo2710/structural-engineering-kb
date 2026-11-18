"""Application-facing data contracts, ViewModels, and DTO re-exports.

Enforces Clean Architecture dependency direction (SAD v1.1 Section 3.2):
`gui/` imports calculation status, design method, result DTOs, and pure-Python
ViewModels exclusively from `app.models` rather than reaching into `core/`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

from app.models.diagram_spec import (
    DiagramCalloutPill,
    DiagramDimension,
    DiagramForceVector,
    DiagramShape,
    DiagramSpec,
)
from core.common.calculation_result import (
    CalcStep,
    CalculationResult,
    CalculationStatus,
    DesignMethod,
    LimitStateResult,
    LoadPathStage,
    Quantity,
    RefSpec,
)

if TYPE_CHECKING:
    from app.registry.module_spec import FieldSpec, ModuleSpec


@dataclass(frozen=True)
class FieldViewModel:
    """Presentation-ready state for a single schema-driven input field."""

    spec: FieldSpec
    raw_value: str
    parsed_value: Any
    is_valid: bool
    error_message: str = ""
    is_visible: bool = True


@dataclass(frozen=True)
class SummaryRowViewModel:
    """Single row in Panel 4's 7-column Limit State Summary table."""

    step_id: str
    check_name: str
    clause: str
    demand_str: str
    capacity_str: str
    dcr_str: str
    dcr: Optional[float]
    status: CalculationStatus
    is_dcr_check: bool = True


@dataclass(frozen=True)
class SummaryViewModel:
    """Presentation-ready summary state for Panel 4 (status pill, DCR gauge, table)."""

    status: CalculationStatus
    is_stale: bool
    governing_check: str
    governing_clause: str
    dcr: Optional[float]
    dcr_percent: int
    dcr_text: str
    rows: Tuple[SummaryRowViewModel, ...]
    warnings: Tuple[str, ...] = ()
    incomplete_reasons: Tuple[str, ...] = ()


@dataclass(frozen=True)
class WorkspaceViewModel:
    """Complete pure-Python state projection for a selected calculation item."""

    item_id: str
    project_id: str
    item_number: int
    display_code: str
    title: str
    group_id: Optional[str]
    group_name: str
    module_id: str
    module_spec: ModuleSpec
    design_method: DesignMethod
    code_edition: str
    current_revision: int
    fields: Tuple[FieldViewModel, ...]
    draft_inputs: Dict[str, Any]
    status: CalculationStatus
    is_dirty: bool
    is_stale: bool
    last_result: Optional[CalculationResult]
    summary: SummaryViewModel
    input_hash: str
    last_run_input_hash: Optional[str]
    diagram_spec: Optional[DiagramSpec] = None
    warnings: Tuple[str, ...] = ()
    incomplete_reasons: Tuple[str, ...] = ()


__all__ = [
    "CalcStep",
    "CalculationResult",
    "CalculationStatus",
    "DesignMethod",
    "DiagramCalloutPill",
    "DiagramDimension",
    "DiagramForceVector",
    "DiagramShape",
    "DiagramSpec",
    "FieldViewModel",
    "LimitStateResult",
    "LoadPathStage",
    "Quantity",
    "RefSpec",
    "SummaryRowViewModel",
    "SummaryViewModel",
    "WorkspaceViewModel",
]
