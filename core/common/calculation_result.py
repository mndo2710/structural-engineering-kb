"""Standardized CalculationResult and structured CalcStep trace data models.

Conforms to SAD v1.1 (Sections 6.3 & 6.4), Consolidated Proposal Section 5.3,
and Master Rule 5 (4-Stage Load-Path Verification Sequence).
"""

from dataclasses import dataclass, field
from enum import Enum, IntEnum
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple, Union

from core.common.math_markup import validate_math_markup


ALLOWED_REF_KINDS = frozenset({
    "section",
    "equation",
    "table",
    "figure",
    "procedure",
    "catalog",
})

ALLOWED_ACCEPTANCE_COMPARISONS = frozenset({
    "<=",
    ">=",
    "<",
    ">",
    "==",
    "!=",
    "in_range",
    "info",
})


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


class LoadPathStage(IntEnum):
    """Mandatory Rule 5 4-Stage Load-Path Verification Sequence."""
    STAGE_1_GEOMETRY_AND_LIMITS = 1
    STAGE_2_PRIMARY_FORCE_TRANSFER = 2
    STAGE_3_CONNECTING_ELEMENT_AND_BASE_METAL = 3
    STAGE_4_SUPPORTING_MEMBER_AND_GLOBAL = 4


def _normalize_status(value: Union[CalculationStatus, str]) -> CalculationStatus:
    """Normalize a CalculationStatus enum or string value into CalculationStatus."""
    if isinstance(value, CalculationStatus):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        for member in CalculationStatus:
            if stripped == member.value or stripped.upper() == member.value or stripped.upper() == member.name:
                return member
    raise ValueError(f"Unsupported calculation status: '{value}'.")


def _normalize_design_method(value: Union[DesignMethod, str]) -> DesignMethod:
    """Normalize a DesignMethod enum or string value into DesignMethod."""
    if isinstance(value, DesignMethod):
        return value
    if isinstance(value, str):
        normalized = value.strip().upper()
        if normalized in ("ASD", "ALLOWABLE_STRESS_DESIGN"):
            return DesignMethod.ASD
        if normalized in ("LRFD", "STRENGTH_DESIGN"):
            return DesignMethod.LRFD
    raise ValueError(f"Unsupported design method: '{value}'.")


def _serialize_json_value(value: Any) -> Any:
    """Convert domain values deterministically into JSON-safe primitives."""
    if isinstance(value, Quantity):
        return value.to_dict()
    if isinstance(value, AcceptanceCriterion):
        return value.to_dict()
    if isinstance(value, RefSpec):
        return value.to_dict()
    if isinstance(value, CalcStep):
        return value.to_dict()
    if isinstance(value, LimitStateResult):
        return value.to_dict()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(k): _serialize_json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize_json_value(item) for item in value]
    return value


def _deserialize_variable_value(value: Any) -> Any:
    """Reconstruct typed Quantity instances inside CalcStep.variables when serialized."""
    if isinstance(value, Quantity):
        return value
    if isinstance(value, Mapping):
        keys = set(value.keys())
        if {"symbol", "value"}.issubset(keys) and keys.issubset({"symbol", "value", "unit", "label"}):
            return Quantity.from_dict(value)
        return {str(k): _deserialize_variable_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_deserialize_variable_value(item) for item in value]
    return value


@dataclass(frozen=True)
class Quantity:
    """Typed engineering quantity with symbolic identifier, value, and US Customary unit."""
    symbol: str
    value: Union[float, int, str]
    unit: str = ""
    label: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.symbol, str) or not self.symbol.strip():
            raise ValueError("Quantity.symbol must be a non-empty string.")
        object.__setattr__(self, "symbol", self.symbol.strip())

        if isinstance(self.value, bool) or not isinstance(self.value, (int, float, str)):
            raise ValueError(f"Quantity.value must be int, float, or str, got {type(self.value).__name__}.")
        if isinstance(self.value, float) and not math.isfinite(self.value):
            raise ValueError("Quantity.value cannot be NaN or infinite.")

        if not isinstance(self.unit, str):
            raise ValueError("Quantity.unit must be a string.")
        if not isinstance(self.label, str):
            raise ValueError("Quantity.label must be a string.")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize Quantity to a plain JSON-compatible dictionary."""
        return {
            "symbol": self.symbol,
            "value": self.value,
            "unit": self.unit,
            "label": self.label,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Quantity":
        """Deserialize Quantity from a dictionary."""
        return cls(
            symbol=str(data["symbol"]),
            value=data["value"],
            unit=str(data.get("unit", "")),
            label=str(data.get("label", "")),
        )


@dataclass(frozen=True)
class AcceptanceCriterion:
    """Typed acceptance criterion supporting both DCR and non-DCR checks."""
    comparison: str
    limit_value: Optional[Union[float, str]] = None
    limit_unit: str = ""
    description: str = ""
    is_dcr_check: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.comparison, str) or self.comparison.strip() not in ALLOWED_ACCEPTANCE_COMPARISONS:
            raise ValueError(
                f"AcceptanceCriterion.comparison must be one of {sorted(ALLOWED_ACCEPTANCE_COMPARISONS)}, "
                f"got '{self.comparison}'."
            )
        object.__setattr__(self, "comparison", self.comparison.strip())
        if isinstance(self.limit_value, bool) or (
            self.limit_value is not None and not isinstance(self.limit_value, (int, float, str))
        ):
            raise ValueError("AcceptanceCriterion.limit_value must be float, int, str, or None.")
        if not isinstance(self.limit_unit, str):
            raise ValueError("AcceptanceCriterion.limit_unit must be a string.")
        if not isinstance(self.description, str):
            raise ValueError("AcceptanceCriterion.description must be a string.")
        object.__setattr__(self, "is_dcr_check", bool(self.is_dcr_check))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize AcceptanceCriterion to a plain JSON-compatible dictionary."""
        return {
            "comparison": self.comparison,
            "limit_value": self.limit_value,
            "limit_unit": self.limit_unit,
            "description": self.description,
            "is_dcr_check": self.is_dcr_check,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AcceptanceCriterion":
        """Deserialize AcceptanceCriterion from a dictionary."""
        return cls(
            comparison=str(data["comparison"]),
            limit_value=data.get("limit_value"),
            limit_unit=str(data.get("limit_unit", "")),
            description=str(data.get("description", "")),
            is_dcr_check=bool(data.get("is_dcr_check", True)),
        )


@dataclass(frozen=True)
class RefSpec:
    """Grounded code, standard, procedure, or catalog reference specification."""
    code: str
    edition: str
    kind: str
    locator: str
    kb_reference_id: Optional[str] = None
    source_path: Optional[str] = None
    sha256: Optional[str] = None

    def __post_init__(self) -> None:
        for field_name in ("code", "edition", "kind", "locator"):
            val = getattr(self, field_name)
            if not isinstance(val, str) or not val.strip():
                raise ValueError(f"RefSpec.{field_name} must be a non-empty string.")
            object.__setattr__(self, field_name, val.strip())

        normalized_kind = self.kind.lower()
        if normalized_kind not in ALLOWED_REF_KINDS:
            raise ValueError(
                f"RefSpec.kind must be one of {sorted(ALLOWED_REF_KINDS)}, got '{self.kind}'."
            )
        object.__setattr__(self, "kind", normalized_kind)

        for opt_field in ("kb_reference_id", "source_path", "sha256"):
            opt_val = getattr(self, opt_field)
            if opt_val is not None:
                if not isinstance(opt_val, str):
                    raise ValueError(f"RefSpec.{opt_field} must be a string or None.")
                stripped = opt_val.strip()
                object.__setattr__(self, opt_field, stripped if stripped else None)

    @property
    def display_label(self) -> str:
        """Human-readable inline code reference label for Panel 3 and reports."""
        edition_already_present = (
            self.edition in self.code
            or (len(self.edition) == 4 and self.edition.isdigit() and self.code.endswith(self.edition[-2:]))
        )
        if edition_already_present:
            return f"{self.code} {self.locator}"
        return f"{self.code}-{self.edition} {self.locator}"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize RefSpec to a plain JSON-compatible dictionary."""
        return {
            "code": self.code,
            "edition": self.edition,
            "kind": self.kind,
            "locator": self.locator,
            "kb_reference_id": self.kb_reference_id,
            "source_path": self.source_path,
            "sha256": self.sha256,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "RefSpec":
        """Deserialize RefSpec from a dictionary."""
        return cls(
            code=str(data["code"]),
            edition=str(data["edition"]),
            kind=str(data["kind"]),
            locator=str(data["locator"]),
            kb_reference_id=data.get("kb_reference_id"),
            source_path=data.get("source_path"),
            sha256=data.get("sha256"),
        )


CodeReference = RefSpec


@dataclass(frozen=True)
class CalcStep:
    """Single structured calculation trace step shared across GUI, PDF, and XLSX."""
    step_id: str
    stage: int
    title: str
    symbolic: str = ""
    substituted: str = ""
    variables: Dict[str, Any] = field(default_factory=dict)
    result_value: Optional[Union[float, str]] = None
    result_unit: Optional[str] = None
    acceptance: Optional[Union[AcceptanceCriterion, str, Dict[str, Any]]] = None
    dcr: Optional[float] = None
    status: Union[CalculationStatus, str] = CalculationStatus.PASS
    refs: Tuple[RefSpec, ...] = ()
    note: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.step_id, str) or not self.step_id.strip():
            raise ValueError("CalcStep.step_id must be a non-empty string.")
        object.__setattr__(self, "step_id", self.step_id.strip())

        if isinstance(self.stage, bool) or not isinstance(self.stage, int):
            raise ValueError(f"CalcStep.stage must be an integer (1..4), got {type(self.stage).__name__}.")
        stage_int = int(self.stage)
        if stage_int not in (1, 2, 3, 4):
            raise ValueError(f"CalcStep.stage must be between 1 and 4 per Rule 5, got {stage_int}.")
        object.__setattr__(self, "stage", stage_int)

        if not isinstance(self.title, str) or not self.title.strip():
            raise ValueError("CalcStep.title must be a non-empty string.")
        object.__setattr__(self, "title", self.title.strip())

        if not isinstance(self.symbolic, str):
            raise ValueError("CalcStep.symbolic must be a string.")
        if self.symbolic != "":
            object.__setattr__(self, "symbolic", validate_math_markup(self.symbolic))

        if not isinstance(self.substituted, str):
            raise ValueError("CalcStep.substituted must be a string.")
        if self.substituted != "":
            object.__setattr__(self, "substituted", validate_math_markup(self.substituted))

        if self.variables is None:
            object.__setattr__(self, "variables", {})
        elif isinstance(self.variables, Mapping):
            object.__setattr__(self, "variables", dict(self.variables))
        else:
            raise ValueError("CalcStep.variables must be a mapping.")

        if isinstance(self.result_value, bool) or (
            self.result_value is not None and not isinstance(self.result_value, (int, float, str))
        ):
            raise ValueError("CalcStep.result_value must be float, int, str, or None.")
        if isinstance(self.result_value, float) and not math.isfinite(self.result_value):
            raise ValueError("CalcStep.result_value cannot be NaN or infinite.")

        if self.result_unit is not None and not isinstance(self.result_unit, str):
            raise ValueError("CalcStep.result_unit must be a string or None.")

        if self.acceptance is not None and not isinstance(self.acceptance, (AcceptanceCriterion, str, Mapping)):
            raise ValueError("CalcStep.acceptance must be AcceptanceCriterion, str, dict, or None.")
        if isinstance(self.acceptance, Mapping) and not isinstance(self.acceptance, dict):
            object.__setattr__(self, "acceptance", dict(self.acceptance))

        if self.dcr is not None:
            if isinstance(self.dcr, bool) or not isinstance(self.dcr, (int, float)):
                raise ValueError("CalcStep.dcr must be a numeric float or None.")
            dcr_val = float(self.dcr)
            if not math.isfinite(dcr_val):
                raise ValueError("CalcStep.dcr cannot be NaN or infinite.")
            object.__setattr__(self, "dcr", dcr_val)

        object.__setattr__(self, "status", _normalize_status(self.status))

        if self.refs is None:
            object.__setattr__(self, "refs", ())
        else:
            if isinstance(self.refs, (str, bytes)) or not isinstance(self.refs, Iterable):
                raise ValueError("CalcStep.refs must be a tuple or list of RefSpec instances.")
            normalized_refs: List[RefSpec] = []
            for item in self.refs:
                if isinstance(item, RefSpec):
                    normalized_refs.append(item)
                elif isinstance(item, Mapping):
                    normalized_refs.append(RefSpec.from_dict(item))
                else:
                    raise ValueError(f"Each item in CalcStep.refs must be a RefSpec, got {type(item).__name__}.")
            object.__setattr__(self, "refs", tuple(normalized_refs))

        if not isinstance(self.note, str):
            raise ValueError("CalcStep.note must be a string.")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize CalcStep to a deterministic JSON-compatible dictionary."""
        if isinstance(self.acceptance, AcceptanceCriterion):
            acc_payload: Any = self.acceptance.to_dict()
        elif isinstance(self.acceptance, Mapping):
            acc_payload = _serialize_json_value(self.acceptance)
        else:
            acc_payload = self.acceptance

        status_val = self.status.value if isinstance(self.status, CalculationStatus) else str(self.status)

        return {
            "step_id": self.step_id,
            "stage": int(self.stage),
            "title": self.title,
            "symbolic": self.symbolic,
            "substituted": self.substituted,
            "variables": {str(k): _serialize_json_value(v) for k, v in self.variables.items()},
            "result_value": self.result_value,
            "result_unit": self.result_unit,
            "acceptance": acc_payload,
            "dcr": self.dcr,
            "status": status_val,
            "refs": [ref.to_dict() for ref in self.refs],
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CalcStep":
        """Deserialize CalcStep from a dictionary."""
        raw_vars = data.get("variables") or {}
        variables = {str(k): _deserialize_variable_value(v) for k, v in raw_vars.items()}

        raw_acc = data.get("acceptance")
        if isinstance(raw_acc, AcceptanceCriterion):
            acceptance: Optional[Union[AcceptanceCriterion, str, Dict[str, Any]]] = raw_acc
        elif isinstance(raw_acc, Mapping):
            if "comparison" in raw_acc:
                acceptance = AcceptanceCriterion.from_dict(raw_acc)
            else:
                acceptance = dict(raw_acc)
        else:
            acceptance = raw_acc

        raw_refs = data.get("refs") or ()
        refs = tuple(r if isinstance(r, RefSpec) else RefSpec.from_dict(r) for r in raw_refs)

        return cls(
            step_id=str(data["step_id"]),
            stage=int(data["stage"]),
            title=str(data["title"]),
            symbolic=str(data.get("symbolic", "")),
            substituted=str(data.get("substituted", "")),
            variables=variables,
            result_value=data.get("result_value"),
            result_unit=data.get("result_unit"),
            acceptance=acceptance,
            dcr=data.get("dcr"),
            status=data.get("status", CalculationStatus.PASS),
            refs=refs,
            note=str(data.get("note", "")),
        )


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

    def to_dict(self) -> Dict[str, Any]:
        """Serialize LimitStateResult to a deterministic JSON-compatible dictionary."""
        status_val = self.status.value if isinstance(self.status, CalculationStatus) else str(self.status)
        return {
            "step_id": self.step_id,
            "name": self.name,
            "code_clause": self.code_clause,
            "equation_latex": self.equation_latex,
            "substitution_str": self.substitution_str,
            "demand": float(self.demand),
            "capacity": float(self.capacity),
            "units": self.units,
            "dcr": float(self.dcr),
            "status": status_val,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "LimitStateResult":
        """Deserialize LimitStateResult from a dictionary."""
        return cls(
            step_id=str(data["step_id"]),
            name=str(data["name"]),
            code_clause=str(data["code_clause"]),
            equation_latex=str(data["equation_latex"]),
            substitution_str=str(data["substitution_str"]),
            demand=float(data["demand"]),
            capacity=float(data["capacity"]),
            units=str(data["units"]),
            dcr=float(data["dcr"]),
            status=_normalize_status(data["status"]),
            notes=str(data.get("notes", "")),
        )


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
    trace: Tuple[CalcStep, ...] = field(default_factory=tuple)
    is_stale: bool = False
    incomplete_reasons: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.design_method = _normalize_design_method(self.design_method)
        self.status = _normalize_status(self.status)
        self.is_stale = bool(self.is_stale)

        if self.incomplete_reasons is None:
            self.incomplete_reasons = []
        else:
            self.incomplete_reasons = [str(r) for r in self.incomplete_reasons]

        if self.trace is None:
            self.trace = ()
        else:
            if isinstance(self.trace, (str, bytes)) or not isinstance(self.trace, Iterable):
                raise ValueError("CalculationResult.trace must be a tuple or list of CalcStep instances.")
            normalized_steps: List[CalcStep] = []
            for step in self.trace:
                if isinstance(step, CalcStep):
                    normalized_steps.append(step)
                elif isinstance(step, Mapping):
                    normalized_steps.append(CalcStep.from_dict(step))
                else:
                    raise ValueError(
                        f"Each item in CalculationResult.trace must be a CalcStep, got {type(step).__name__}."
                    )
            self.trace = tuple(normalized_steps)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize CalculationResult (including structured trace) to a JSON-compatible dictionary."""
        return {
            "calculation_id": self.calculation_id,
            "module_id": self.module_id,
            "code_edition": self.code_edition,
            "design_method": self.design_method.value,
            "input_parameters": _serialize_json_value(self.input_parameters),
            "assumptions": list(self.assumptions),
            "intermediate_results": _serialize_json_value(self.intermediate_results),
            "limit_states": [ls.to_dict() for ls in self.limit_states],
            "governing_limit_state": (
                self.governing_limit_state.to_dict() if self.governing_limit_state is not None else None
            ),
            "demand": float(self.demand),
            "capacity": float(self.capacity),
            "dcr": float(self.dcr),
            "status": self.status.value,
            "reference_files": list(self.reference_files),
            "software_version": self.software_version,
            "warnings": list(self.warnings),
            "trace": [step.to_dict() for step in self.trace],
            "is_stale": bool(self.is_stale),
            "incomplete_reasons": list(self.incomplete_reasons),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CalculationResult":
        """Deserialize CalculationResult from a dictionary (supports both v1 and v2 payloads)."""
        limit_states = [
            ls if isinstance(ls, LimitStateResult) else LimitStateResult.from_dict(ls)
            for ls in (data.get("limit_states") or [])
        ]

        raw_gov = data.get("governing_limit_state")
        governing_ls: Optional[LimitStateResult]
        if isinstance(raw_gov, LimitStateResult):
            governing_ls = raw_gov
        elif isinstance(raw_gov, Mapping):
            governing_ls = LimitStateResult.from_dict(raw_gov)
        elif isinstance(raw_gov, str) and raw_gov:
            governing_ls = next((ls for ls in limit_states if ls.name == raw_gov or ls.step_id == raw_gov), None)
        else:
            governing_ls = None

        raw_trace = data.get("trace") or ()
        trace = tuple(
            step if isinstance(step, CalcStep) else CalcStep.from_dict(step)
            for step in raw_trace
        )

        return cls(
            calculation_id=str(data["calculation_id"]),
            module_id=str(data["module_id"]),
            code_edition=str(data["code_edition"]),
            design_method=_normalize_design_method(data["design_method"]),
            input_parameters=dict(data.get("input_parameters") or {}),
            assumptions=[str(a) for a in (data.get("assumptions") or [])],
            intermediate_results=dict(data.get("intermediate_results") or {}),
            limit_states=limit_states,
            governing_limit_state=governing_ls,
            demand=float(data.get("demand", 0.0)),
            capacity=float(data.get("capacity", 0.0)),
            dcr=float(data.get("dcr", 0.0)),
            status=_normalize_status(data.get("status", CalculationStatus.INCOMPLETE)),
            reference_files=[str(rf) for rf in (data.get("reference_files") or [])],
            software_version=str(data.get("software_version", "1.0.0")),
            warnings=[str(w) for w in (data.get("warnings") or [])],
            trace=trace,
            is_stale=bool(data.get("is_stale", False)),
            incomplete_reasons=[str(r) for r in (data.get("incomplete_reasons") or [])],
        )
