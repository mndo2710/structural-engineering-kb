"""Standardized CalculationResult data model per SAD v1.0 (Sections 6.4 & 8.4)."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class DesignMethod(str, Enum):
    """Supported structural design philosophies."""
    ASD = "ASD"
    LRFD = "LRFD"


class CalculationStatus(str, Enum):
    """Explicit calculation status codes per SAD Section 8.4."""
    PASS = "PASS"
    FAIL = "FAIL"
    REQUIRES_REVIEW = "REQUIRES REVIEW"
    INCOMPLETE = "INCOMPLETE"
    INVALID_INPUT = "INVALID INPUT"


@dataclass(frozen=True)
class LimitStateResult:
    """Individual limit-state evaluation record with full equation traceability."""
    step_id: str
    name: str
    code_clause: str
    equation_latex: str
    substitution_str: str
    demand: float
    capacity: float
    units: str
    dcr: float
    status: CalculationStatus
    notes: str = ""


@dataclass
class CalculationResult:
    """Common calculation result object returned by all core calculation modules (SAD Sec. 6.4)."""
    calculation_id: str
    module_id: str
    code_edition: str
    design_method: DesignMethod
    input_parameters: Dict[str, Any]
    assumptions: List[str] = field(default_factory=list)
    intermediate_results: Dict[str, Any] = field(default_factory=dict)
    limit_states: List[LimitStateResult] = field(default_factory=list)
    governing_limit_state: Optional[LimitStateResult] = None
    demand: float = 0.0
    capacity: float = 0.0
    dcr: float = 0.0
    status: CalculationStatus = CalculationStatus.INCOMPLETE
    reference_files: List[str] = field(default_factory=list)
    software_version: str = "1.0.0"
    warnings: List[str] = field(default_factory=list)
