"""ReportService: Application Service for Generating XLSX and PDF Calculation Deliverables.

Conforms to SAD v1.0 Sections 7.2 & 11.
Coordinates CalculationResult, ProjectService, and KnowledgeBaseService with
exporters/excel_builder.py and exporters/pdf_builder.py.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Union

from app.services.knowledge_base_service import KnowledgeBaseService
from app.services.project_service import ProjectService
from core.common.calculation_result import CalculationResult
from exporters.excel_builder import export_calculation_to_excel
from exporters.pdf_builder import export_calculation_to_pdf


class ReportService:
    """Coordinates generating Excel (.xlsx) and PDF (.pdf) reports from calculation results."""

    def __init__(
        self,
        kb_service: Optional[KnowledgeBaseService] = None,
        project_service: Optional[ProjectService] = None,
    ) -> None:
        self.kb_service = kb_service or KnowledgeBaseService()
        self.project_service = project_service

    def _resolve_project_metadata(self, project_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if project_info:
            return project_info
        if self.project_service and self.project_service.active_project_id:
            active_prj = self.project_service.get_active_project()
            if active_prj:
                return active_prj
        return {
            "name": "Smith Residence",
            "code": "PRJ-2026-001",
            "engineer": "Senior Structural Engineer, PE",
        }

    def export_excel(
        self,
        calc_result: CalculationResult,
        output_path: Union[str, Path],
        project_info: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """Export CalculationResult to a 17-column Arial 10pt 3-tab Excel (.xlsx) workbook."""
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
    ) -> Path:
        """Export CalculationResult to a 12-section ReportLab PDF calculation report."""
        meta = self._resolve_project_metadata(project_info)
        return export_calculation_to_pdf(
            calc_result=calc_result,
            output_path=output_path,
            project_info=meta,
            kb=self.kb_service,
        )
