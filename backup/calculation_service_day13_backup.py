"""CalculationService: Central Application Service for Executing Engineering Modules.

Conforms to SAD v1.0 Section 7.2 & Master Rule 8.
Connects the PySide6 GUI to deterministic Python calculation modules in core/
and KnowledgeBaseService without embedding engineering equations inside the GUI.
"""

from typing import Any, Callable, Dict, List, Optional, Union

from app.services.knowledge_base_service import KnowledgeBaseService
from app.services.project_service import ProjectService
from core.asce7.wind.awning import calculate_awning_canopy_loads
from core.asce7.wind.guardrail import calculate_guardrail_loads
from core.asce7.wind.parapet import calculate_parapet_wind
from core.asce7.wind.roof_overhang import calculate_roof_overhang_wind
from core.asce7.wind.trellis import calculate_trellis_loads
from core.common.calculation_result import CalculationResult, DesignMethod
from core.common.exceptions import StructuralEngineeringError
from core.common.validation import validate_design_method


class CalculationService:
    """Dispatches calculation requests to verified deterministic core modules."""

    def __init__(
        self,
        kb_service: Optional[KnowledgeBaseService] = None,
        project_service: Optional[ProjectService] = None,
    ) -> None:
        self.kb_service = kb_service or KnowledgeBaseService()
        self.project_service = project_service

        self._registry: Dict[str, Callable[..., CalculationResult]] = {
            "asce7_parapet_wind": calculate_parapet_wind,
            "cc_parapet": calculate_parapet_wind,
            "asce7_roof_overhang": calculate_roof_overhang_wind,
            "cc_overhang": calculate_roof_overhang_wind,
            "asce7_awning_canopy": calculate_awning_canopy_loads,
            "cc_awning": calculate_awning_canopy_loads,
            "asce7_trellis_loads": calculate_trellis_loads,
            "cc_trellis": calculate_trellis_loads,
            "ibc_guardrail_loads": calculate_guardrail_loads,
            "cc_guardrail": calculate_guardrail_loads,
        }

    def list_supported_modules(self) -> List[str]:
        """Return list of registered canonical module identifiers."""
        return [
            "asce7_parapet_wind",
            "asce7_roof_overhang",
            "asce7_awning_canopy",
            "asce7_trellis_loads",
            "ibc_guardrail_loads",
        ]

    def run_calculation(
        self,
        module_id: str,
        inputs: Dict[str, Any],
        design_method: Union[str, DesignMethod] = DesignMethod.ASD,
        calculation_id: Optional[str] = None,
        auto_save_revision: bool = False,
        change_notes: str = "",
    ) -> CalculationResult:
        """
        Execute a registered deterministic calculation module and optionally persist
        a new immutable revision in SQLite via ProjectService.
        """
        mod_key = module_id.strip()
        if mod_key not in self._registry:
            raise StructuralEngineeringError(
                f"Calculation module '{mod_key}' is not registered. Supported: {self.list_supported_modules()}"
            )

        method = validate_design_method(design_method)
        calc_fn = self._registry[mod_key]

        result = calc_fn(
            inputs=inputs,
            kb=self.kb_service,
            design_method=method,
            calculation_id=calculation_id,
        )

        if auto_save_revision and self.project_service is not None and calculation_id:
            self.project_service.save_calculation_run(
                calculation_id=calculation_id,
                calc_result=result,
                change_notes=change_notes or f"Executed {mod_key} ({method.value})",
            )

        return result
