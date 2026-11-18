"""CalculationService: Central Application Service for Executing Engineering Modules.

Conforms to SAD v1.1 Section 6.1 & Master Rule 8.
Dispatches deterministic calculation requests through the canonical ModuleRegistry
without embedding engineering equations inside the GUI.
"""

from typing import Any, Callable, Dict, List, Optional, Union

from app.models import CalculationResult, DesignMethod
from app.registry import ModuleMaturity, ModuleRegistry, get_module_registry
from app.services.knowledge_base_service import KnowledgeBaseService
from app.services.project_service import ProjectService
from core.common.exceptions import StructuralEngineeringError
from core.common.validation import validate_design_method


class CalculationService:
    """Dispatches calculation requests to verified deterministic core modules via ModuleRegistry."""

    def __init__(
        self,
        kb_service: Optional[KnowledgeBaseService] = None,
        project_service: Optional[ProjectService] = None,
        registry: Optional[ModuleRegistry] = None,
    ) -> None:
        self.kb_service = kb_service or KnowledgeBaseService()
        self.project_service = project_service
        self.registry = registry or get_module_registry()

        # Backward-compatible mapping of all verified module IDs and aliases -> callable
        self._registry: Dict[str, Callable[..., CalculationResult]] = {}
        for spec in self.registry.list_modules(maturity=ModuleMaturity.VERIFIED):
            if spec.calculation_callable is not None:
                self._registry[spec.module_id] = spec.calculation_callable
                for alias in spec.aliases:
                    self._registry[alias] = spec.calculation_callable

    def list_supported_modules(self) -> List[str]:
        """Return list of canonical verified module identifiers from ModuleRegistry."""
        return self.registry.list_canonical_verified_ids()

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
        try:
            spec = self.registry.resolve(mod_key)
        except KeyError:
            raise StructuralEngineeringError(
                f"Calculation module '{mod_key}' is not registered. Supported: {self.list_supported_modules()}"
            )

        if spec.maturity != ModuleMaturity.VERIFIED or spec.calculation_callable is None:
            raise StructuralEngineeringError(
                f"Calculation module '{mod_key}' is {spec.maturity.value} and not yet available for execution."
            )

        method = validate_design_method(design_method)
        effective_inputs = dict(spec.preset_inputs)
        effective_inputs.update(inputs)

        result = spec.calculation_callable(
            inputs=effective_inputs,
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
