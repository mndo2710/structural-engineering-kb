"""PySide6 Components & Cladding (C&C) Interactive 4-Panel Workspace (Day 13 Vertical Slice).

Conforms to SAD v1.1 Sections 6.1, 8.1 & Master Rules 2, 5, 6, 8.
Supports all 5 V1 C&C workflows via ModuleRegistry:
  1. Parapet Wind Pressure (ASCE 7-22 Sec. 27.3.4 & 30.9)
  2. Roof Overhang Wind Uplift (ASCE 7-22 Sec. 30.7)
  3. Attached Awning & Canopy Wind/Seismic (ASCE 7-22 Sec. 30.11 & Ch. 13)
  4. Open-Frame Trellis & Pergola Wind/Seismic (ASCE 7-22 Sec. 29.4 & Ch. 13/15)
  5. Guardrail & Handrail Live/Wind Loads (2024 IBC Sec. 1607.9 / ASCE 7-22 Sec. 4.5.1)
"""

from pathlib import Path
from typing import Any, Dict, Optional

from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QPolygonF
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

from app.models import CalculationResult, CalculationStatus, DesignMethod, DiagramSpec
from app.registry import ModuleRegistry, get_module_registry
from app.services.calculation_service import CalculationService
from app.services.knowledge_base_service import KnowledgeBaseService
from app.services.project_service import ProjectService
from app.services.report_service import ReportService
from gui.widgets.base_workspace import BaseCalculationWorkspace


def _build_cc_module_configs(registry: ModuleRegistry) -> Dict[str, Dict[str, Any]]:
    configs: Dict[str, Dict[str, Any]] = {}
    for spec in registry.list_modules(category="Loads (ASCE 7)"):
        configs[spec.module_id] = {
            "label": f"{spec.title} ({registry.resolve_code_display(spec.module_id)})",
            "code": registry.resolve_code_display(spec.module_id),
            "fields": [(f.key, f.label, f.benchmark_value) for f in spec.fields],
        }
    return configs


class CCDiagramWidget(QWidget):
    """Dynamic 2D schematic structural diagram for all 5 C&C sub-assemblies."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(180)
        self.setStyleSheet("background-color: #ffffff;")
        self.module_id = "asce7_parapet_wind"
        self.params: Dict[str, Any] = {}
        self.has_result: bool = False
        self.summary_note: str = ""

    def update_cc_diagram(
        self,
        module_id: str,
        params: Dict[str, Any],
        summary_note: str = "",
        has_result: bool = True,
    ) -> None:
        self.module_id = module_id
        self.params = dict(params)
        self.has_result = has_result
        self.summary_note = summary_note
        self.update()

    def clear_diagram(self, module_id: Optional[str] = None) -> None:
        if module_id:
            self.module_id = module_id
        self.params = {}
        self.has_result = False
        self.summary_note = ""
        self.update()

    def apply_diagram_spec(self, spec: DiagramSpec) -> None:
        """Apply Qt-independent DiagramSpec directly to Panel 2 canvas (WP-8)."""
        merged: Dict[str, Any] = dict(spec.geometry_params)
        if spec.has_engine_result:
            merged.update(spec.derived_params)
        self.module_id = spec.module_id
        self.params = merged
        self.has_result = spec.has_engine_result
        self.summary_note = spec.summary_badge if spec.has_engine_result else ""
        self.update()

    def update_parameters(self, **kwargs: Any) -> None:
        """Compatibility hook for BaseCalculationWorkspace."""
        if "has_result" in kwargs:
            self.has_result = bool(kwargs.pop("has_result"))
        self.params.update(kwargs)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        painter.fillRect(0, 0, w, h, QColor("#ffffff"))

        cx = w * 0.45
        cy = h * 0.55

        struct_pen = QPen(QColor("#343a40"), 2.0)
        force_pen = QPen(QColor("#007bff"), 2.0)
        dim_pen = QPen(QColor("#d96818"), 1.3)

        if "parapet" in self.module_id:
            painter.setPen(struct_pen)
            painter.setBrush(QBrush(QColor("#e9ecef")))
            painter.drawRect(int(cx), int(cy), int(w * 0.35), 14)
            painter.drawRect(int(cx - 14), int(cy), 14, int(h * 0.32))
            painter.setBrush(QBrush(QColor("#fde6cf")))
            par_h_px = int(h * 0.36)
            painter.drawRect(int(cx - 14), int(cy - par_h_px), 14, par_h_px)

            painter.setPen(force_pen)
            for frac in (0.2, 0.5, 0.8):
                ay = int(cy - par_h_px * frac)
                painter.drawLine(int(cx - 75), ay, int(cx - 18), ay)
                painter.drawLine(int(cx - 24), ay - 4, int(cx - 18), ay)
                painter.drawLine(int(cx - 24), ay + 4, int(cx - 18), ay)

            h_par = self.params.get("h_par_ft")
            p_gov = self.params.get("p_gov_psf") if self.has_result else None
            p_txt = f"p_gov = {p_gov:.1f} psf" if isinstance(p_gov, (int, float)) else "p_gov = —"
            h_txt = f"h_par = {h_par:.1f} ft" if isinstance(h_par, (int, float)) else "h_par = —"
            painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
            painter.drawText(QRectF(cx - 135, cy - par_h_px * 0.65, 110, 20), Qt.AlignLeft, p_txt)
            painter.setPen(dim_pen)
            painter.drawText(QRectF(cx + 8, cy - par_h_px * 0.6, 110, 20), Qt.AlignLeft, h_txt)

        elif "overhang" in self.module_id:
            painter.setPen(struct_pen)
            painter.setBrush(QBrush(QColor("#e9ecef")))
            painter.drawRect(int(cx - 8), int(cy - 10), 16, int(h * 0.36))

            painter.setBrush(QBrush(QColor("#fde6cf")))
            rafter_poly = QPolygonF([
                QPointF(cx - 95, cy + 12),
                QPointF(cx + 120, cy - 32),
                QPointF(cx + 120, cy - 16),
                QPointF(cx - 95, cy + 28),
            ])
            painter.drawPolygon(rafter_poly)

            painter.setPen(force_pen)
            for ax in (int(cx - 75), int(cx - 45)):
                painter.drawLine(ax, int(cy + 40), ax, int(cy - 18))
                painter.drawLine(ax - 4, int(cy - 12), ax, int(cy - 18))
                painter.drawLine(ax + 4, int(cy - 12), ax, int(cy - 18))

            l_oh = self.params.get("L_oh_ft")
            r_up = self.params.get("R_uplift_lbs") if self.has_result else None
            l_txt = f"L_oh = {l_oh:.1f} ft" if isinstance(l_oh, (int, float)) else "L_oh = —"
            r_txt = f"R_tie = {r_up:.0f} lbs uplift" if isinstance(r_up, (int, float)) else "R_tie = —"
            painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
            painter.drawText(QRectF(cx - 130, cy - 38, 120, 20), Qt.AlignLeft, l_txt)
            painter.setPen(dim_pen)
            painter.drawText(QRectF(cx + 14, cy + 8, 150, 20), Qt.AlignLeft, r_txt)

        elif "awning" in self.module_id:
            painter.setPen(struct_pen)
            painter.setBrush(QBrush(QColor("#e9ecef")))
            painter.drawRect(int(cx - 60), int(h * 0.16), 16, int(h * 0.68))

            painter.setBrush(QBrush(QColor("#ced4da")))
            painter.drawRect(int(cx - 44), int(cy), 120, 12)

            painter.setPen(QPen(QColor("#c86816"), 2.0))
            painter.drawLine(int(cx - 44), int(cy - 45), int(cx + 55), int(cy))

            bc = self.params.get("Bc_ft")
            m_w = self.params.get("M_wall_lb_ft") if self.has_result else None
            bc_txt = f"B_c = {bc:.1f} ft" if isinstance(bc, (int, float)) else "B_c = —"
            m_txt = f"M = {m_w:.0f} lb-ft" if isinstance(m_w, (int, float)) else "M = —"
            painter.setPen(force_pen)
            painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
            painter.drawText(QRectF(cx - 30, cy + 18, 170, 20), Qt.AlignLeft, f"{bc_txt} | {m_txt}")

        elif "trellis" in self.module_id:
            painter.setPen(struct_pen)
            painter.setBrush(QBrush(QColor("#fde6cf")))
            left_x = int(cx - 70)
            right_x = int(cx + 70)
            top_y = int(h * 0.28)
            bot_y = int(h * 0.78)
            painter.drawRect(left_x, top_y, 12, bot_y - top_y)
            painter.drawRect(right_x, top_y, 12, bot_y - top_y)
            painter.drawRect(left_x - 10, top_y - 10, right_x - left_x + 32, 10)

            painter.setPen(force_pen)
            painter.drawLine(left_x - 55, top_y - 5, left_x - 14, top_y - 5)
            painter.drawLine(left_x - 20, top_y - 9, left_x - 14, top_y - 5)
            painter.drawLine(left_x - 20, top_y - 1, left_x - 14, top_y - 5)

            v_post = self.params.get("V_post_lbs") if self.has_result else None
            v_txt = f"V_post = {v_post:.1f} lbs" if isinstance(v_post, (int, float)) else "V_post = —"
            painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
            painter.drawText(QRectF(left_x - 85, top_y + 12, 120, 20), Qt.AlignLeft, v_txt)

        else:
            painter.setPen(struct_pen)
            painter.setBrush(QBrush(QColor("#e9ecef")))
            painter.drawRect(int(cx - 70), int(cy + 20), 140, 16)
            painter.setBrush(QBrush(QColor("#adb5bd")))
            painter.drawRect(int(cx - 18), int(cy + 14), 36, 6)
            painter.drawRect(int(cx - 6), int(cy - 55), 12, 69)

            painter.setPen(force_pen)
            painter.drawLine(int(cx - 65), int(cy - 50), int(cx - 10), int(cy - 50))
            painter.drawLine(int(cx - 16), int(cy - 54), int(cx - 10), int(cy - 50))
            painter.drawLine(int(cx - 16), int(cy - 46), int(cx - 10), int(cy - 50))
            painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
            p_txt = "P = 200 lbs (IBC 1607.9)" if self.has_result else "P = — (IBC 1607.9)"
            painter.drawText(QRectF(cx - 95, cy - 70, 140, 18), Qt.AlignLeft, p_txt)

        # Top-right summary pill badge (only when calculated)
        if self.has_result and self.summary_note:
            note_w = 275.0
            note_h = 24.0
            note_rect = QRectF(w - note_w - 12, 10, note_w, note_h)
            painter.setPen(QPen(QColor("#b8daff"), 1))
            painter.setBrush(QBrush(QColor("#e7f1ff")))
            painter.drawRoundedRect(note_rect, 4, 4)
            painter.setPen(QPen(QColor("#004085"), 1))
            painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
            painter.drawText(note_rect, Qt.AlignCenter, self.summary_note)


class CCCalculationWorkspace(BaseCalculationWorkspace):
    """
    Interactive 4-Panel C&C Workspace wired to CalculationService, ProjectService,
    and ReportService for the Day 13 End-to-End Vertical Slice.
    """

    exportExcelRequested = Signal(str)
    exportPdfRequested = Signal(str)

    MODULE_CONFIGS: Dict[str, Dict[str, Any]] = _build_cc_module_configs(get_module_registry())

    def __init__(
        self,
        calc_service: Optional[CalculationService] = None,
        project_service: Optional[ProjectService] = None,
        report_service: Optional[ReportService] = None,
        start_blank: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        self.registry = calc_service.registry if calc_service else get_module_registry()
        self.MODULE_CONFIGS = _build_cc_module_configs(self.registry)
        self.kb_service = calc_service.kb_service if calc_service else KnowledgeBaseService()
        self.project_service = project_service or ProjectService()
        self.calc_service = calc_service or CalculationService(
            kb_service=self.kb_service,
            project_service=self.project_service,
            registry=self.registry,
        )
        self.report_service = report_service or ReportService(
            kb_service=self.kb_service,
            project_service=self.project_service,
        )
        self._active_module_id = "asce7_parapet_wind"
        self._cc_start_blank = start_blank

        super().__init__(
            module_title="Components & Cladding Loads",
            default_code=self.registry.resolve_code_display(self._active_module_id),
            start_blank=True,
            parent=parent,
        )

        # Replace base diagram widget cleanly to prevent double-diagram ghosting (UI-01)
        parent_card_layout = self.diagram_widget.parentWidget().layout()
        old_diag = self.diagram_widget
        self.diagram_widget = CCDiagramWidget(self)
        parent_card_layout.replaceWidget(old_diag, self.diagram_widget)
        old_diag.hide()
        old_diag.setParent(None)
        old_diag.deleteLater()

        # Connect calculate signal to deterministic execution
        self.calculateRequested.connect(self._execute_active_calculation)

        self.reset_inputs(blank=self._cc_start_blank)
        if not self._cc_start_blank:
            self.run_active_module()

    def _build_input_form(self, blank: bool) -> None:
        """Build sub-assembly selector and editable parameter fields."""
        while self.form_layout.rowCount() > 0:
            self.form_layout.removeRow(0)
        self._input_edits.clear()

        spec = self.registry.resolve(self._active_module_id)
        self._active_field_specs = spec.fields
        self.default_code = self.registry.resolve_code_display(spec.module_id)

        lbl_mod = QLabel("C&C Sub-Assembly")
        lbl_mod.setStyleSheet("font-size: 11px; font-weight: bold; color: #007bff;")
        self.combo_module = QComboBox()
        for mod_id, cfg in self.MODULE_CONFIGS.items():
            self.combo_module.addItem(cfg["label"], mod_id)
        idx = self.combo_module.findData(self._active_module_id)
        if idx >= 0:
            self.combo_module.setCurrentIndex(idx)
        self.combo_module.currentIndexChanged.connect(self._on_submodule_changed)
        self.form_layout.addRow(lbl_mod)
        self.form_layout.addRow(self.combo_module)

        for fld in spec.fields:
            lbl = QLabel(fld.label)
            lbl.setStyleSheet("font-size: 11px; color: #495057;")
            init_val = "" if blank else ("" if fld.benchmark_value is None else str(fld.benchmark_value))
            edit = QLineEdit(init_val)
            edit.setAlignment(Qt.AlignRight)
            edit.setFixedHeight(26)
            edit.setStyleSheet("""
                QLineEdit {
                    background-color: #ffffff;
                    border: 1px solid #ced4da;
                    border-radius: 4px;
                    padding: 2px 6px;
                    font-size: 12px;
                    font-weight: bold;
                    color: #0000ff;
                }
            """)
            self._input_edits[fld.key] = edit
            self.form_layout.addRow(lbl, edit)

        export_row = QHBoxLayout()
        export_row.setSpacing(6)
        self.btn_export_xlsx = QPushButton("Export XLSX (17-Col)")
        self.btn_export_xlsx.setFixedHeight(28)
        self.btn_export_xlsx.setStyleSheet("font-size: 11px; font-weight: bold; color: #1F4E78;")
        self.btn_export_xlsx.clicked.connect(self._on_export_xlsx_clicked)

        self.btn_export_pdf = QPushButton("Export PDF (12-Sec)")
        self.btn_export_pdf.setFixedHeight(28)
        self.btn_export_pdf.setStyleSheet("font-size: 11px; font-weight: bold; color: #1F4E78;")
        self.btn_export_pdf.clicked.connect(self._on_export_pdf_clicked)

        export_row.addWidget(self.btn_export_xlsx)
        export_row.addWidget(self.btn_export_pdf)
        self.form_layout.addRow(export_row)

    def _populate_blank_inputs(self) -> None:
        # Built after _active_module_id is set via reset_inputs()
        pass

    def _populate_sample_inputs(self) -> None:
        self._build_input_form(blank=False)

    def reset_inputs(self, blank: bool = True) -> None:
        """Reset panel inputs to blank (live-safe) or benchmark defaults."""
        if blank:
            self.clear_inputs_to_blank()
        else:
            self.load_benchmark_defaults()

    def clear_inputs_to_blank(self) -> None:
        """Clear all input controls to blank and reset output panels to INCOMPLETE."""
        self._build_input_form(blank=True)
        self.clear_to_incomplete()

    def load_benchmark_defaults(self) -> None:
        """Populate controlled benchmark defaults for explicit demos and regression tests."""
        self._build_input_form(blank=False)

    def clear_to_incomplete(self, reason: str = "Enter required inputs and click Run Calculation.") -> None:
        super().clear_to_incomplete(reason)
        if isinstance(self.diagram_widget, CCDiagramWidget):
            self.diagram_widget.clear_diagram(self._active_module_id)

    def show_invalid_input(self, message: str) -> None:
        super().show_invalid_input(message)
        if isinstance(self.diagram_widget, CCDiagramWidget):
            self.diagram_widget.clear_diagram(self._active_module_id)

    def select_submodule(self, module_id: str, start_blank: bool = False) -> None:
        """Programmatically switch active C&C workflow template (resolving aliases)."""
        spec = self.registry.get(module_id)
        canonical_id = spec.module_id if spec is not None else module_id
        if canonical_id in self.MODULE_CONFIGS:
            self._active_module_id = canonical_id
            self.reset_inputs(blank=start_blank)
            if not start_blank:
                self.run_active_module()

    def _on_submodule_changed(self, index: int) -> None:
        mod_id = self.combo_module.itemData(index)
        if mod_id and mod_id != self._active_module_id:
            self._active_module_id = mod_id
            self.reset_inputs(blank=self._cc_start_blank)
            if not self._cc_start_blank:
                self.run_active_module()

    def get_form_inputs(self) -> Dict[str, Any]:
        """Parse typed inputs from QLineEdit controls."""
        parsed: Dict[str, Any] = {}
        for k, edit in self._input_edits.items():
            raw = edit.text().strip()
            if raw == "":
                continue
            try:
                parsed[k] = float(raw)
            except ValueError:
                parsed[k] = raw
        return parsed

    def set_design_method(self, method: DesignMethod) -> None:
        super().set_design_method(method)
        _, err_status, _ = self.validate_and_get_inputs()
        if err_status is None:
            self.run_active_module()

    def run_active_module(self) -> Optional[CalculationResult]:
        """Execute active C&C module and update all 4 workspace panels."""
        inputs, err_status, err_msg = self.validate_and_get_inputs()
        if err_status == CalculationStatus.INCOMPLETE:
            self.clear_to_incomplete(err_msg)
            return None
        if err_status == CalculationStatus.INVALID_INPUT:
            self.show_invalid_input(err_msg)
            return None

        method = self.get_selected_design_method()
        result = self.calc_service.run_calculation(
            module_id=self._active_module_id,
            inputs=inputs,
            design_method=method,
        )
        self.display_results(result)
        return result

    def _execute_active_calculation(self, inputs: Dict[str, Any], method: DesignMethod) -> None:
        result = self.calc_service.run_calculation(
            module_id=self._active_module_id,
            inputs=inputs,
            design_method=method,
        )
        self.display_results(result)

    def display_results(self, result: CalculationResult) -> None:
        super().display_results(result)
        if isinstance(self.diagram_widget, CCDiagramWidget):
            diag_params = dict(result.input_parameters)
            diag_params.update(result.intermediate_results)
            if "p_gov_unfactored_psf" in result.intermediate_results:
                diag_params["p_gov_psf"] = result.intermediate_results["p_gov_unfactored_psf"]
            if "M_down_wall_lb_ft" in result.intermediate_results:
                diag_params["M_wall_lb_ft"] = max(
                    result.intermediate_results.get("M_down_wall_lb_ft", 0.0),
                    result.intermediate_results.get("M_up_wall_lb_ft", 0.0),
                )
            note = f"{result.code_edition} ({result.design_method.value}) · DCR = {result.dcr:.2f} ({result.status.value})"
            self.diagram_widget.update_cc_diagram(
                module_id=result.module_id,
                params=diag_params,
                summary_note=note,
                has_result=True,
            )

    def export_current_to_excel(self, output_path: Path) -> Path:
        if self._current_result is None:
            self.run_active_module()
        return self.report_service.export_excel(self._current_result, output_path)

    def export_current_to_pdf(self, output_path: Path) -> Path:
        if self._current_result is None:
            self.run_active_module()
        return self.report_service.export_pdf(self._current_result, output_path)

    def _on_export_xlsx_clicked(self) -> None:
        if self._current_result is None:
            self.run_active_module()
        if self._current_result is None:
            return
        out_path = Path("storage/projects") / f"{self._current_result.module_id}_{self._current_result.design_method.value}.xlsx"
        saved = self.export_current_to_excel(out_path)
        self.exportExcelRequested.emit(str(saved))

    def _on_export_pdf_clicked(self) -> None:
        if self._current_result is None:
            self.run_active_module()
        if self._current_result is None:
            return
        out_path = Path("storage/projects") / f"{self._current_result.module_id}_{self._current_result.design_method.value}.pdf"
        saved = self.export_current_to_pdf(out_path)
        self.exportPdfRequested.emit(str(saved))
