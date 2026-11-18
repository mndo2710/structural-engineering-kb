"""Report orchestration service for single calculations and ordered multi-item projects."""

from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from app.models import DiagramSpec
from app.rendering.diagram_builders import build_diagram_spec
from app.services.history_service import HistoryService
from app.services.knowledge_base_service import KnowledgeBaseService
from app.services.project_service import ProjectService
from core.common.calculation_result import CalculationResult, CalculationStatus
from exporters.excel_builder import export_calculation_to_excel, export_project_to_excel
from exporters.pdf_builder import export_calculation_to_pdf, export_project_to_pdf


class ReportService:
    """Orchestrates deterministic Excel & PDF reports using verified KB sources."""

    def __init__(
        self,
        kb_service: Optional[KnowledgeBaseService] = None,
        project_service: Optional[ProjectService] = None,
    ) -> None:
        self.kb_service = kb_service or KnowledgeBaseService()
        self.project_service = project_service

    def _resolve_project_metadata(
        self,
        project_info: Optional[Dict[str, Any]] = None,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        resolved: Dict[str, Any] = {
            "project_name": "Default Structural Project",
            "project_code": "PRJ-001",
            "engineer": "Structural Engineer",
            "date": date.today().isoformat(),
        }
        if self.project_service is not None:
            proj = (
                self.project_service.get_project(project_id)
                if project_id
                else self.project_service.get_active_project()
            )
            if proj:
                resolved["project_name"] = proj.get("name", resolved["project_name"])
                resolved["project_code"] = proj.get("code", resolved["project_code"])
                resolved["engineer"] = proj.get("engineer", resolved["engineer"])
        if project_info:
            resolved.update(project_info)
        return resolved

    def _collect_ordered_project_items(
        self,
        project_id: Optional[str] = None,
        item_ids: Optional[Sequence[str]] = None,
        controller: Any = None,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Collect project items in exact sidebar tree order with latest result or disclosure."""
        if self.project_service is None:
            raise ValueError("ReportService requires project_service for multi-item project reports.")

        p_id = project_id or self.project_service.active_project_id
        if not p_id:
            raise ValueError("No active project available for report export.")

        ordered_rows = self.project_service.list_items(project_id=p_id, include_deleted=False)
        if item_ids is not None:
            allowed = set(item_ids)
            ordered_rows = [
                row
                for row in ordered_rows
                if row.get("calculation_id") in allowed or row.get("display_code") in allowed
            ]

        history_svc = HistoryService(repository=self.project_service.repository)
        items_payload: List[Dict[str, Any]] = []

        for idx, row in enumerate(ordered_rows, start=1):
            calc_id = str(row["calculation_id"])
            display_code = str(row.get("display_code") or f"C-{int(row.get('item_number') or idx):02d}")
            title = str(row.get("title") or row.get("module_id") or display_code)
            group_name = str(row.get("group_name") or "Ungrouped")
            rev_num = int(row.get("current_revision") or 0)

            diagram_spec: Optional[DiagramSpec] = None
            calc_result: Optional[CalculationResult] = None

            if controller is not None:
                vm = controller.load(calc_id)
                diagram_spec = vm.diagram_spec
                if vm.last_result is not None:
                    res_dict = vm.last_result.to_dict()
                    res_dict["is_stale"] = bool(vm.is_stale)
                    calc_result = CalculationResult.from_dict(res_dict)
                else:
                    calc_result = CalculationResult(
                        calculation_id=calc_id,
                        module_id=vm.module_id,
                        code_edition=vm.code_edition,
                        design_method=vm.design_method,
                        input_parameters=dict(vm.draft_inputs),
                        status=vm.status,
                        is_stale=bool(vm.is_stale),
                        incomplete_reasons=list(vm.incomplete_reasons or ()),
                    )
            else:
                draft_inputs = dict(row.get("draft_inputs") or {})
                row_status = str(row.get("status") or CalculationStatus.INCOMPLETE.value)
                is_stale = bool(row.get("is_stale", False))

                if rev_num > 0:
                    hist_res = history_svc.reconstruct_calculation_result(calc_id, rev_num)
                    if hist_res is not None:
                        if not is_stale and draft_inputs and draft_inputs != hist_res.input_parameters:
                            is_stale = True
                        res_dict = hist_res.to_dict()
                        res_dict["is_stale"] = is_stale
                        calc_result = CalculationResult.from_dict(res_dict)

                if calc_result is None:
                    reasons = (
                        ["Calculation has not been saved or run with complete inputs."]
                        if row_status == CalculationStatus.INCOMPLETE.value
                        else []
                    )
                    calc_result = CalculationResult(
                        calculation_id=calc_id,
                        module_id=str(row.get("module_id", "")),
                        code_edition=str(row.get("code_edition", "")),
                        design_method=row.get("design_method", "ASD"),
                        input_parameters=draft_inputs,
                        status=row_status,
                        is_stale=is_stale,
                        incomplete_reasons=reasons,
                    )

                diagram_spec = build_diagram_spec(
                    calc_result.module_id,
                    calc_result.input_parameters or {},
                    result=(
                        calc_result
                        if calc_result.status
                        not in (CalculationStatus.INCOMPLETE, CalculationStatus.INVALID_INPUT)
                        else None
                    ),
                    is_stale=bool(calc_result.is_stale),
                )

            items_payload.append(
                {
                    "calculation_id": calc_id,
                    "display_code": display_code,
                    "title": title,
                    "group_name": group_name,
                    "revision_number": rev_num,
                    "calc_result": calc_result,
                    "diagram_spec": diagram_spec,
                }
            )

        return p_id, items_payload

    def export_excel(
        self,
        calc_result: CalculationResult,
        output_path: Union[str, Path],
        project_info: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """Generate a 3-tab Excel calculation workbook (Rule 6)."""
        meta = self._resolve_project_metadata(project_info)
        return export_calculation_to_excel(
            calc_result=calc_result,
            output_path=output_path,
            project_info=meta,
            kb=self.kb_service,
        )

    def export_pdf(
        self,
        calc_result: CalculationResult,
        output_path: Union[str, Path],
        project_info: Optional[Dict[str, Any]] = None,
        diagram_spec: Optional[DiagramSpec] = None,
    ) -> Path:
        """Generate a structured Plan-Check PDF calculation report."""
        meta = self._resolve_project_metadata(project_info)
        return export_calculation_to_pdf(
            calc_result=calc_result,
            output_path=output_path,
            project_info=meta,
            kb=self.kb_service,
            diagram_spec=diagram_spec,
        )

    def export_project_excel(
        self,
        output_path: Union[str, Path],
        project_id: Optional[str] = None,
        item_ids: Optional[Sequence[str]] = None,
        project_info: Optional[Dict[str, Any]] = None,
        controller: Any = None,
    ) -> Path:
        """Generate an ordered multi-item Excel package preserving sidebar tree order."""
        p_id, items = self._collect_ordered_project_items(
            project_id=project_id,
            item_ids=item_ids,
            controller=controller,
        )
        meta = self._resolve_project_metadata(project_info, project_id=p_id)
        return export_project_to_excel(
            items=items,
            output_path=output_path,
            project_info=meta,
            kb=self.kb_service,
        )

    def export_project_pdf(
        self,
        output_path: Union[str, Path],
        project_id: Optional[str] = None,
        item_ids: Optional[Sequence[str]] = None,
        project_info: Optional[Dict[str, Any]] = None,
        controller: Any = None,
    ) -> Path:
        """Generate an ordered multi-item PDF package preserving sidebar tree order."""
        p_id, items = self._collect_ordered_project_items(
            project_id=project_id,
            item_ids=item_ids,
            controller=controller,
        )
        meta = self._resolve_project_metadata(project_info, project_id=p_id)
        return export_project_to_pdf(
            items=items,
            output_path=output_path,
            project_info=meta,
            kb=self.kb_service,
        )
