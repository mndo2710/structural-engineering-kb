"""WorkspaceController: Pure-Python Application Controller for Calculation Items (WP-4).

Conforms to SAD v1.1 Section 7.1 & Clean Architecture Rules:
- Zero PySide6 / Qt imports.
- Manages per-item independent draft inputs, field validation, canonical hash
  stale tracking, in-memory Run Execution, immutable Save Revision, and
  historical revision loading.
"""

from datetime import datetime, timezone
import hashlib
import json
import math
from typing import Any, Dict, List, Optional, Tuple, Union

from app.models import (
    CalculationResult,
    CalculationStatus,
    DesignMethod,
    FieldViewModel,
    SummaryRowViewModel,
    SummaryViewModel,
    WorkspaceViewModel,
)
from app.registry import FieldSpec, ModuleRegistry, ModuleSpec, get_module_registry
from app.rendering import build_diagram_spec
from app.services.calculation_service import CalculationService
from app.services.history_service import HistoryService
from app.services.knowledge_base_service import KnowledgeBaseService
from app.services.project_service import ProjectService


# Reverse-mapping for core modules whose CalculationResult.input_parameters
# rename an input capacity key (e.g. roof_overhang stores R_tie_cap_lbs).
_CORE_INPUT_KEY_ALIASES: Dict[str, Tuple[str, ...]] = {
    "R_tie_cap_asd_lbs": ("R_tie_cap_lbs",),
    "M_cap_asd_lb_ft": ("M_cap_lb_ft",),
    "V_cap_asd_lbs": ("V_cap_lbs",),
    "R_cap_asd_lbs": ("R_cap_lbs",),
    "M_wall_cap_asd_lb_ft": ("M_wall_cap_lb_ft",),
    "M_post_cap_asd_lb_ft": ("M_post_cap_lb_ft",),
    "T_bolt_cap_asd_lbs": ("T_bolt_cap_lbs",),
}


def _normalize_design_method(method: Union[str, DesignMethod]) -> DesignMethod:
    if isinstance(method, DesignMethod):
        return method
    raw = str(method).strip().upper()
    if raw == "ASD":
        return DesignMethod.ASD
    if raw == "LRFD":
        return DesignMethod.LRFD
    raise ValueError(f"Unsupported design method '{method}'. Expected 'ASD' or 'LRFD'.")


def _normalize_json_value(val: Any) -> Any:
    """Normalize numeric and string values so equivalent representations hash identically."""
    if isinstance(val, bool):
        return val
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        if val.is_integer():
            return int(val)
        return round(val, 10)
    if isinstance(val, str):
        return val.strip()
    if isinstance(val, dict):
        return {str(k): _normalize_json_value(v) for k, v in sorted(val.items())}
    if isinstance(val, (list, tuple)):
        return [_normalize_json_value(v) for v in val]
    return val


def _evaluate_visible_if(expr: Optional[str], draft_inputs: Dict[str, Any]) -> bool:
    """Evaluate simple FieldSpec.visible_if expressions ('key == value' / 'key != value')."""
    if not expr or not expr.strip():
        return True
    text = expr.strip()
    if "==" in text:
        lhs, rhs = [part.strip() for part in text.split("==", 1)]
        rhs_clean = rhs.strip("'\"")
        return str(draft_inputs.get(lhs, "")).strip() == rhs_clean
    if "!=" in text:
        lhs, rhs = [part.strip() for part in text.split("!=", 1)]
        rhs_clean = rhs.strip("'\"")
        return str(draft_inputs.get(lhs, "")).strip() != rhs_clean
    return True


class WorkspaceController:
    """Pure-Python controller orchestrating calculation item lifecycle and ViewModel projection."""

    def __init__(
        self,
        project_service: ProjectService,
        calculation_service: Optional[CalculationService] = None,
        history_service: Optional[HistoryService] = None,
        knowledge_base_service: Optional[KnowledgeBaseService] = None,
        registry: Optional[ModuleRegistry] = None,
        software_version: str = "1.0.0",
    ) -> None:
        self.project_service = project_service
        self.registry = registry or project_service.registry or get_module_registry()
        self.kb_service = knowledge_base_service or (
            calculation_service.kb_service if calculation_service else KnowledgeBaseService()
        )
        self.calculation_service = calculation_service or CalculationService(
            kb_service=self.kb_service,
            project_service=self.project_service,
            registry=self.registry,
        )
        self.history_service = history_service or HistoryService(repository=self.project_service.repository)
        self.software_version = software_version

        # Per-item independent state maps (keyed by calculation_id)
        self._draft_inputs: Dict[str, Dict[str, Any]] = {}
        self._design_methods: Dict[str, DesignMethod] = {}
        self._last_results: Dict[str, CalculationResult] = {}
        self._last_run_hashes: Dict[str, str] = {}
        self._dirty_flags: Dict[str, bool] = {}

        self._manifest_hash_cache: Optional[str] = None

    def _get_manifest_hash(self) -> str:
        if self._manifest_hash_cache is not None:
            return self._manifest_hash_cache
        manifest_path = getattr(self.kb_service, "manifest_path", None)
        if manifest_path and manifest_path.exists():
            self._manifest_hash_cache = self.kb_service.compute_sha256(manifest_path)
        else:
            self._manifest_hash_cache = ""
        return self._manifest_hash_cache

    @staticmethod
    def compute_canonical_input_hash(
        module_id: str,
        normalized_inputs: Dict[str, Any],
        design_method: Union[str, DesignMethod],
        code_edition: str,
        manifest_hash: str = "",
        software_version: str = "1.0.0",
    ) -> str:
        """Compute deterministic SHA-256 hash over normalized inputs and engineering context."""
        method_str = _normalize_design_method(design_method).value
        payload = {
            "module_id": module_id.strip(),
            "inputs": _normalize_json_value(normalized_inputs),
            "design_method": method_str,
            "code_edition": code_edition.strip(),
            "software_version": software_version.strip(),
            "manifest_hash": manifest_hash.strip(),
        }
        canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    def _get_item_record(self, item_id: str) -> Dict[str, Any]:
        item = self.project_service.get_calculation(item_id)
        if item is None or item.get("is_deleted"):
            raise ValueError(f"Calculation item '{item_id}' not found.")
        return item

    def _ensure_loaded(self, item_id: str) -> Dict[str, Any]:
        item = self._get_item_record(item_id)
        if item_id not in self._draft_inputs:
            self.load(item_id)
        return item

    @staticmethod
    def _validate_single_field(
        fld: FieldSpec,
        raw_val: Any,
        is_visible: bool,
    ) -> FieldViewModel:
        if raw_val is None:
            raw_str = ""
        elif isinstance(raw_val, bool):
            raw_str = "true" if raw_val else "false"
        else:
            raw_str = str(raw_val).strip()

        if raw_str == "" and fld.default_value is not None:
            raw_str = str(fld.default_value).strip()

        if raw_str == "":
            if not is_visible or not fld.required:
                return FieldViewModel(
                    spec=fld,
                    raw_value="",
                    parsed_value=fld.default_value,
                    is_valid=True,
                    error_message="",
                    is_visible=is_visible,
                )
            return FieldViewModel(
                spec=fld,
                raw_value="",
                parsed_value=None,
                is_valid=False,
                error_message=f"{fld.label} ({fld.key}) is required.",
                is_visible=is_visible,
            )

        parsed: Any = raw_str
        vtype = fld.value_type

        if vtype == "float":
            try:
                val_f = float(raw_str)
            except ValueError:
                return FieldViewModel(
                    spec=fld,
                    raw_value=raw_str,
                    parsed_value=None,
                    is_valid=False,
                    error_message=f"Invalid numeric value for {fld.label} ({fld.key}): '{raw_str}'.",
                    is_visible=is_visible,
                )
            if not math.isfinite(val_f):
                return FieldViewModel(
                    spec=fld,
                    raw_value=raw_str,
                    parsed_value=None,
                    is_valid=False,
                    error_message=f"{fld.label} ({fld.key}) must be finite.",
                    is_visible=is_visible,
                )
            parsed = val_f
        elif vtype == "int":
            try:
                if isinstance(raw_val, int) and not isinstance(raw_val, bool):
                    val_i = raw_val
                else:
                    val_i = int(raw_str)
            except ValueError:
                return FieldViewModel(
                    spec=fld,
                    raw_value=raw_str,
                    parsed_value=None,
                    is_valid=False,
                    error_message=f"Invalid integer value for {fld.label} ({fld.key}): '{raw_str}'.",
                    is_visible=is_visible,
                )
            parsed = val_i
        elif vtype == "bool":
            low = raw_str.lower()
            if low in ("true", "1", "yes"):
                parsed = True
            elif low in ("false", "0", "no"):
                parsed = False
            else:
                return FieldViewModel(
                    spec=fld,
                    raw_value=raw_str,
                    parsed_value=None,
                    is_valid=False,
                    error_message=f"Invalid boolean value for {fld.label} ({fld.key}): '{raw_str}'.",
                    is_visible=is_visible,
                )
        elif vtype == "enum" and fld.enum_options:
            if raw_str not in fld.enum_options:
                match = next((opt for opt in fld.enum_options if opt.lower() == raw_str.lower()), None)
                if match is None:
                    return FieldViewModel(
                        spec=fld,
                        raw_value=raw_str,
                        parsed_value=None,
                        is_valid=False,
                        error_message=(
                            f"Invalid option '{raw_str}' for {fld.label} ({fld.key}). "
                            f"Expected one of: {', '.join(fld.enum_options)}."
                        ),
                        is_visible=is_visible,
                    )
                parsed = match

        # Numeric range checks
        if fld.validation and isinstance(parsed, (int, float)) and not isinstance(parsed, bool):
            num_val = float(parsed)
            bounds = fld.validation
            if "gt" in bounds and not (num_val > float(bounds["gt"])):
                return FieldViewModel(
                    spec=fld,
                    raw_value=raw_str,
                    parsed_value=parsed,
                    is_valid=False,
                    error_message=f"{fld.label} ({fld.key}) must be > {bounds['gt']}.",
                    is_visible=is_visible,
                )
            if "ge" in bounds and not (num_val >= float(bounds["ge"])):
                return FieldViewModel(
                    spec=fld,
                    raw_value=raw_str,
                    parsed_value=parsed,
                    is_valid=False,
                    error_message=f"{fld.label} ({fld.key}) must be >= {bounds['ge']}.",
                    is_visible=is_visible,
                )
            if "lt" in bounds and not (num_val < float(bounds["lt"])):
                return FieldViewModel(
                    spec=fld,
                    raw_value=raw_str,
                    parsed_value=parsed,
                    is_valid=False,
                    error_message=f"{fld.label} ({fld.key}) must be < {bounds['lt']}.",
                    is_visible=is_visible,
                )
            if "le" in bounds and not (num_val <= float(bounds["le"])):
                return FieldViewModel(
                    spec=fld,
                    raw_value=raw_str,
                    parsed_value=parsed,
                    is_valid=False,
                    error_message=f"{fld.label} ({fld.key}) must be <= {bounds['le']}.",
                    is_visible=is_visible,
                )

        return FieldViewModel(
            spec=fld,
            raw_value=raw_str,
            parsed_value=parsed,
            is_valid=True,
            error_message="",
            is_visible=is_visible,
        )

    def _evaluate_fields(
        self,
        spec: ModuleSpec,
        draft_inputs: Dict[str, Any],
        design_method: Optional[DesignMethod] = None,
    ) -> Tuple[Tuple[FieldViewModel, ...], Dict[str, Any], Optional[CalculationStatus], Tuple[str, ...]]:
        field_vms: List[FieldViewModel] = []
        parsed_inputs: Dict[str, Any] = dict(spec.preset_inputs)
        missing_reasons: List[str] = []
        invalid_reasons: List[str] = []
        visible_ctx = dict(draft_inputs)
        if design_method is not None:
            visible_ctx["design_method"] = design_method.value

        for fld in spec.fields:
            is_visible = _evaluate_visible_if(fld.visible_if, visible_ctx)
            raw_val = draft_inputs.get(fld.key)
            fvm = self._validate_single_field(fld, raw_val, is_visible)
            field_vms.append(fvm)

            if is_visible:
                if fvm.raw_value == "" and fld.required:
                    missing_reasons.append(f"Missing required input: {fld.label} ({fld.key})")
                elif not fvm.is_valid:
                    invalid_reasons.append(fvm.error_message)
                elif fvm.parsed_value is not None:
                    parsed_inputs[fld.key] = fvm.parsed_value

        if invalid_reasons:
            return tuple(field_vms), parsed_inputs, CalculationStatus.INVALID_INPUT, tuple(invalid_reasons)
        if missing_reasons:
            return tuple(field_vms), parsed_inputs, CalculationStatus.INCOMPLETE, tuple(missing_reasons)
        return tuple(field_vms), parsed_inputs, None, ()

    def _compute_item_hash(
        self,
        spec: ModuleSpec,
        draft_inputs: Dict[str, Any],
        parsed_inputs: Dict[str, Any],
        validation_status: Optional[CalculationStatus],
        design_method: DesignMethod,
        code_edition: str,
    ) -> str:
        # Build canonical schema-key map so equivalent edits / revision reloads match deterministically
        hash_payload: Dict[str, Any] = dict(spec.preset_inputs)
        for fld in spec.fields:
            if validation_status is None and fld.key in parsed_inputs:
                hash_payload[fld.key] = parsed_inputs[fld.key]
            elif fld.key in draft_inputs:
                hash_payload[fld.key] = draft_inputs[fld.key]
            elif fld.default_value is not None:
                hash_payload[fld.key] = fld.default_value
            else:
                hash_payload[fld.key] = ""

        return self.compute_canonical_input_hash(
            module_id=spec.module_id,
            normalized_inputs=hash_payload,
            design_method=design_method,
            code_edition=code_edition,
            manifest_hash=self._get_manifest_hash(),
            software_version=self.software_version,
        )

    @staticmethod
    def _build_summary_view_model(
        status: CalculationStatus,
        is_stale: bool,
        last_result: Optional[CalculationResult],
        reasons: Tuple[str, ...],
        cached_last_dcr: Optional[float] = None,
    ) -> SummaryViewModel:
        if status == CalculationStatus.INVALID_INPUT:
            msg = reasons[0] if reasons else "Invalid calculation input."
            return SummaryViewModel(
                status=CalculationStatus.INVALID_INPUT,
                is_stale=is_stale,
                governing_check=msg,
                governing_clause="",
                dcr=None,
                dcr_percent=0,
                dcr_text="—",
                rows=(),
                warnings=(),
                incomplete_reasons=reasons,
            )

        if status == CalculationStatus.INCOMPLETE and last_result is None:
            return SummaryViewModel(
                status=CalculationStatus.INCOMPLETE,
                is_stale=is_stale,
                governing_check="Not calculated (INCOMPLETE)",
                governing_clause="",
                dcr=None,
                dcr_percent=0,
                dcr_text="—",
                rows=(),
                warnings=(),
                incomplete_reasons=reasons,
            )

        if last_result is None:
            if cached_last_dcr is not None:
                pct = int(min(float(cached_last_dcr) * 100.0, 150.0))
                return SummaryViewModel(
                    status=status,
                    is_stale=is_stale,
                    governing_check="Cached run summary (re-run for full trace)" if is_stale else "Cached run summary",
                    governing_clause="",
                    dcr=float(cached_last_dcr),
                    dcr_percent=pct,
                    dcr_text=f"{pct}% ({float(cached_last_dcr):.2f})",
                    rows=(),
                    warnings=(),
                    incomplete_reasons=reasons,
                )
            return SummaryViewModel(
                status=CalculationStatus.INCOMPLETE,
                is_stale=is_stale,
                governing_check="Not calculated (INCOMPLETE)",
                governing_clause="",
                dcr=None,
                dcr_percent=0,
                dcr_text="—",
                rows=(),
                warnings=(),
                incomplete_reasons=reasons,
            )

        rows: List[SummaryRowViewModel] = []
        for ls in last_result.limit_states:
            rows.append(
                SummaryRowViewModel(
                    step_id=ls.step_id,
                    check_name=ls.name,
                    clause=ls.code_clause,
                    demand_str=f"{ls.demand:.2f} {ls.units}".strip(),
                    capacity_str=f"{ls.capacity:.2f} {ls.units}".strip(),
                    dcr_str=f"{ls.dcr:.2f}",
                    dcr=float(ls.dcr),
                    status=ls.status,
                    is_dcr_check=True,
                )
            )

        gov_name = last_result.governing_limit_state.name if last_result.governing_limit_state else "None"
        gov_clause = last_result.governing_limit_state.code_clause if last_result.governing_limit_state else ""
        dcr_val = float(last_result.dcr)
        dcr_pct = int(min(dcr_val * 100.0, 150.0))
        return SummaryViewModel(
            status=status,
            is_stale=is_stale,
            governing_check=gov_name,
            governing_clause=gov_clause,
            dcr=dcr_val,
            dcr_percent=dcr_pct,
            dcr_text=f"{dcr_pct}% ({dcr_val:.2f})",
            rows=tuple(rows),
            warnings=tuple(last_result.warnings),
            incomplete_reasons=reasons,
        )

    def _build_view_model(self, item_id: str, item_record: Optional[Dict[str, Any]] = None) -> WorkspaceViewModel:
        item = item_record or self._get_item_record(item_id)
        spec = self.registry.resolve(item["module_id"])
        draft_inputs = dict(self._draft_inputs.get(item_id, {}))
        design_method = self._design_methods.get(item_id) or _normalize_design_method(item.get("design_method", "ASD"))
        code_edition = item.get("code_edition") or self.registry.resolve_code_display(spec.module_id)

        field_vms, parsed_inputs, validation_status, reasons = self._evaluate_fields(
            spec, draft_inputs, design_method=design_method
        )
        current_hash = self._compute_item_hash(
            spec=spec,
            draft_inputs=draft_inputs,
            parsed_inputs=parsed_inputs,
            validation_status=validation_status,
            design_method=design_method,
            code_edition=code_edition,
        )

        last_result = self._last_results.get(item_id)
        last_run_hash = self._last_run_hashes.get(item_id)
        if last_run_hash is None:
            last_run_hash = item.get("last_input_hash")

        has_prior_run = (last_result is not None) or (last_run_hash is not None)
        is_stale = bool(has_prior_run and last_run_hash is not None and current_hash != last_run_hash)

        if validation_status == CalculationStatus.INVALID_INPUT:
            effective_status = CalculationStatus.INVALID_INPUT
        elif validation_status == CalculationStatus.INCOMPLETE:
            effective_status = CalculationStatus.INCOMPLETE
        elif last_result is not None:
            effective_status = last_result.status
        elif item.get("last_input_hash") == current_hash and item.get("last_dcr") is not None:
            effective_status = CalculationStatus(item.get("status", CalculationStatus.INCOMPLETE.value))
        else:
            effective_status = CalculationStatus.INCOMPLETE

        summary = self._build_summary_view_model(
            status=effective_status,
            is_stale=is_stale,
            last_result=last_result,
            reasons=reasons,
            cached_last_dcr=item.get("last_dcr"),
        )

        item_num = int(item.get("item_number") or 0)
        display_code = item.get("display_code") or (f"C-{item_num:02d}" if item_num > 0 else "C-00")
        diagram_spec = build_diagram_spec(
            module_id=spec.module_id,
            draft_inputs=draft_inputs,
            result=last_result,
            is_stale=is_stale,
        )

        return WorkspaceViewModel(
            item_id=item_id,
            project_id=item["project_id"],
            item_number=item_num,
            display_code=display_code,
            title=item["title"],
            group_id=item.get("group_id"),
            group_name=item.get("group_name") or "Ungrouped",
            module_id=spec.module_id,
            module_spec=spec,
            design_method=design_method,
            code_edition=code_edition,
            current_revision=int(item.get("current_revision") or 0),
            fields=field_vms,
            draft_inputs=draft_inputs,
            status=effective_status,
            is_dirty=self._dirty_flags.get(item_id, False),
            is_stale=is_stale,
            last_result=last_result,
            summary=summary,
            input_hash=current_hash,
            last_run_input_hash=last_run_hash,
            diagram_spec=diagram_spec,
            warnings=tuple(last_result.warnings) if last_result else (),
            incomplete_reasons=reasons,
        )

    @staticmethod
    def _extract_schema_inputs_from_revision(spec: ModuleSpec, rev_inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Map stored revision inputs onto schema field keys (handling known core key aliases)."""
        mapped: Dict[str, Any] = {}
        field_keys = {f.key for f in spec.fields}
        for k, v in rev_inputs.items():
            if k in field_keys or k in spec.preset_inputs:
                mapped[k] = v

        for fld in spec.fields:
            if fld.key not in mapped:
                for alias_key in _CORE_INPUT_KEY_ALIASES.get(fld.key, ()):
                    if alias_key in rev_inputs:
                        mapped[fld.key] = rev_inputs[alias_key]
                        break
        return mapped

    # --------------------------------------------------------------------------
    # Public Controller API
    # --------------------------------------------------------------------------
    def load(self, item_id: str) -> WorkspaceViewModel:
        """Load or activate a calculation item and project its full WorkspaceViewModel."""
        item = self._get_item_record(item_id)
        spec = self.registry.resolve(item["module_id"])
        design_method = _normalize_design_method(item.get("design_method", "ASD"))
        code_edition = item.get("code_edition") or self.registry.resolve_code_display(spec.module_id)

        if item_id not in self._draft_inputs:
            draft = dict(item.get("draft_inputs") or {})
            rev_num = int(item.get("current_revision") or 0)

            if rev_num > 0:
                rev_result = self.history_service.reconstruct_calculation_result(item_id, rev_num)
                if rev_result is not None:
                    self._last_results[item_id] = rev_result

                rev_detail = self.history_service.get_revision(item_id, rev_num)
                if rev_detail and isinstance(rev_detail.get("inputs"), dict):
                    rev_schema_inputs = self._extract_schema_inputs_from_revision(spec, rev_detail["inputs"])
                    if not draft:
                        draft = rev_schema_inputs

                    # Populate baseline hash if database row lacked last_input_hash (e.g. migrated v1 item)
                    if not item.get("last_input_hash"):
                        rev_method = rev_result.design_method if rev_result else design_method
                        _, rev_parsed, rev_val_status, _ = self._evaluate_fields(
                            spec, rev_schema_inputs, design_method=rev_method
                        )
                        rev_code = rev_detail.get("code_edition") or code_edition
                        self._last_run_hashes[item_id] = self._compute_item_hash(
                            spec=spec,
                            draft_inputs=rev_schema_inputs,
                            parsed_inputs=rev_parsed,
                            validation_status=rev_val_status,
                            design_method=rev_method,
                            code_edition=rev_code,
                        )

            self._draft_inputs[item_id] = draft
            self._design_methods[item_id] = design_method
            if item.get("last_input_hash"):
                self._last_run_hashes[item_id] = item["last_input_hash"]
            self._dirty_flags.setdefault(item_id, False)

        return self._build_view_model(item_id, item_record=item)

    def edit_field(
        self,
        item_id: str,
        key: str,
        raw_value: Any,
        autosave: bool = True,
    ) -> WorkspaceViewModel:
        """Update a single input field in draft state, autosave, and flag stale if prior result exists."""
        item = self._ensure_loaded(item_id)
        spec = self.registry.resolve(item["module_id"])

        draft = self._draft_inputs[item_id]
        draft[key] = raw_value
        self._dirty_flags[item_id] = True
        design_method = self._design_methods.get(item_id) or _normalize_design_method(item.get("design_method", "ASD"))

        _, _, validation_status, _ = self._evaluate_fields(spec, draft, design_method=design_method)
        if autosave:
            if validation_status in (CalculationStatus.INCOMPLETE, CalculationStatus.INVALID_INPUT):
                save_status: Optional[CalculationStatus] = validation_status
            elif item_id in self._last_results:
                save_status = self._last_results[item_id].status
            else:
                save_status = CalculationStatus.INCOMPLETE
            item = self.project_service.save_draft(
                item_id=item_id,
                draft_inputs=draft,
                status=save_status,
            )

        return self._build_view_model(item_id, item_record=item)

    def set_design_method(
        self,
        item_id: str,
        method: Union[str, DesignMethod],
        autosave: bool = True,
    ) -> WorkspaceViewModel:
        """Switch design method (ASD | LRFD) for an item, updating stale state without auto-saving a revision."""
        item = self._ensure_loaded(item_id)
        normalized_method = _normalize_design_method(method)
        self._design_methods[item_id] = normalized_method
        self._dirty_flags[item_id] = True

        if autosave:
            item = self.project_service.save_draft(
                item_id=item_id,
                draft_inputs=self._draft_inputs[item_id],
                design_method=normalized_method,
            )

        return self._build_view_model(item_id, item_record=item)

    def validate(self, item_id: str) -> WorkspaceViewModel:
        """Validate all visible fields for an item without running the calculation engine."""
        item = self._ensure_loaded(item_id)
        return self._build_view_model(item_id, item_record=item)

    def run(self, item_id: str) -> WorkspaceViewModel:
        """
        Validate and execute deterministic calculation in memory, updating cached last_dcr
        on the calculation row WITHOUT creating an immutable revision.
        """
        item = self._ensure_loaded(item_id)
        spec = self.registry.resolve(item["module_id"])
        draft = self._draft_inputs[item_id]
        design_method = self._design_methods[item_id]
        code_edition = item.get("code_edition") or self.registry.resolve_code_display(spec.module_id)

        _, parsed_inputs, validation_status, _ = self._evaluate_fields(
            spec, draft, design_method=design_method
        )
        if validation_status in (CalculationStatus.INCOMPLETE, CalculationStatus.INVALID_INPUT):
            self._last_results.pop(item_id, None)
            self._last_run_hashes.pop(item_id, None)
            updated = self.project_service.update_item_run_state(
                item_id=item_id,
                last_dcr=None,
                status=validation_status,
                last_input_hash=None,
            )
            return self._build_view_model(item_id, item_record=updated)

        result = self.calculation_service.run_calculation(
            module_id=spec.module_id,
            inputs=parsed_inputs,
            design_method=design_method,
            calculation_id=item_id,
            auto_save_revision=False,
        )

        run_hash = self._compute_item_hash(
            spec=spec,
            draft_inputs=draft,
            parsed_inputs=parsed_inputs,
            validation_status=None,
            design_method=design_method,
            code_edition=code_edition,
        )

        self._last_results[item_id] = result
        self._last_run_hashes[item_id] = run_hash
        self._dirty_flags[item_id] = False

        updated = self.project_service.update_item_run_state(
            item_id=item_id,
            last_dcr=result.dcr,
            status=result.status,
            last_input_hash=run_hash,
        )
        return self._build_view_model(item_id, item_record=updated)

    def _build_reference_snapshot(self, result: CalculationResult) -> Tuple[Optional[str], Dict[str, Any]]:
        manifest_sha = self._get_manifest_hash() or None
        file_hashes: Dict[str, Optional[str]] = {}
        for ref_id in result.reference_files:
            try:
                fpath = self.kb_service.get_file_path(ref_id)
                file_hashes[ref_id] = self.kb_service.compute_sha256(fpath)
            except Exception:
                file_hashes[ref_id] = None

        snapshot = {
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "reference_files": file_hashes,
        }
        return manifest_sha, snapshot

    def save_revision(self, item_id: str, change_notes: str = "") -> WorkspaceViewModel:
        """
        Persist an immutable SQLite revision snapshot (inputs, results, trace, code edition,
        software version, and KB SHA-256 provenance).
        """
        vm = self.load(item_id)
        if vm.last_result is None or vm.is_stale or vm.status in (
            CalculationStatus.INCOMPLETE,
            CalculationStatus.INVALID_INPUT,
        ):
            vm = self.run(item_id)

        if vm.status in (CalculationStatus.INCOMPLETE, CalculationStatus.INVALID_INPUT) or vm.last_result is None:
            raise ValueError(
                f"Cannot save revision for item '{item_id}' in status '{vm.status.value}'."
            )

        manifest_sha, ref_snapshot = self._build_reference_snapshot(vm.last_result)
        self.project_service.save_calculation_run(
            calculation_id=item_id,
            calc_result=vm.last_result,
            change_notes=change_notes or f"Saved revision ({vm.design_method.value})",
            reference_manifest_sha256=manifest_sha,
            reference_snapshot=ref_snapshot,
            input_hash=vm.input_hash,
        )

        # Keep draft synced with saved revision snapshot
        self.project_service.save_draft(
            item_id=item_id,
            draft_inputs=self._draft_inputs[item_id],
            design_method=vm.design_method,
            code_edition=vm.code_edition,
            status=vm.last_result.status,
        )
        self._last_run_hashes[item_id] = vm.input_hash
        self._dirty_flags[item_id] = False
        return self._build_view_model(item_id)

    def load_revision(self, item_id: str, revision_number: int) -> WorkspaceViewModel:
        """Restore a historical immutable revision into the active item workspace."""
        item = self._get_item_record(item_id)
        spec = self.registry.resolve(item["module_id"])

        rev_detail = self.history_service.get_revision(item_id, revision_number)
        if not rev_detail:
            raise ValueError(f"Revision {revision_number} not found for item '{item_id}'.")

        rev_result = self.history_service.reconstruct_calculation_result(item_id, revision_number)
        raw_rev_inputs = rev_detail.get("inputs") or {}
        restored_draft = self._extract_schema_inputs_from_revision(spec, raw_rev_inputs)

        if rev_result is not None:
            restored_method = rev_result.design_method
            restored_code = rev_result.code_edition
            restored_status = rev_result.status
            restored_dcr: Optional[float] = rev_result.dcr
        else:
            raw_res = rev_detail.get("results") or {}
            restored_method = _normalize_design_method(raw_res.get("design_method", item.get("design_method", "ASD")))
            restored_code = rev_detail.get("code_edition") or item.get("code_edition") or ""
            restored_status = CalculationStatus(raw_res.get("status", CalculationStatus.INCOMPLETE.value))
            restored_dcr = raw_res.get("dcr")

        _, parsed_inputs, val_status, _ = self._evaluate_fields(
            spec, restored_draft, design_method=restored_method
        )
        restored_hash = self._compute_item_hash(
            spec=spec,
            draft_inputs=restored_draft,
            parsed_inputs=parsed_inputs,
            validation_status=val_status,
            design_method=restored_method,
            code_edition=restored_code,
        )

        self._draft_inputs[item_id] = restored_draft
        self._design_methods[item_id] = restored_method
        if rev_result is not None:
            self._last_results[item_id] = rev_result
        else:
            self._last_results.pop(item_id, None)
        self._last_run_hashes[item_id] = restored_hash
        self._dirty_flags[item_id] = False

        self.project_service.save_draft(
            item_id=item_id,
            draft_inputs=restored_draft,
            design_method=restored_method,
            code_edition=restored_code,
            status=restored_status,
        )
        updated = self.project_service.update_item_run_state(
            item_id=item_id,
            last_dcr=restored_dcr,
            status=restored_status,
            last_input_hash=restored_hash,
        )
        return self._build_view_model(item_id, item_record=updated)
