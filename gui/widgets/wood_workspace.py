"""PySide6 Wood Connections & Lateral Interactive 4-Panel Workspace (Day 14 Vertical Slice).

Conforms to SAD v1.1 Sections 6.1, 8.1 & Master Rules 2, 5, 6, 8.
Supports all V1 Wood Connections & Lateral workflows via ModuleRegistry:
  1. Bolt / Dowel Lateral & Group Tear-Out (NDS 2024 Ch. 12 & App. E)
  2. Nail / Wood Screw / Lag Screw / Simpson SDS (NDS 2024 Ch. 12 & ESR-2236)
  3. Wood-Frame Shear Wall & Holdown Anchorage (SDPWS 2021 Sec. 4.3 & Simpson HDU)
  4. Wood Structural Panel Diaphragm, Chord & Collector (SDPWS 2021 Sec. 4.2 & Straps)
  5. Simpson Joist Hanger & Hurricane Tie Multi-Axis Check (Simpson C-C-2026)
"""

from pathlib import Path
from typing import Any, Dict, Optional

from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QBrush
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
from gui.widgets.base_workspace import BaseCalculationWorkspace, DiagramWidget


_FASTENER_TEMPLATE_IDS = {
    "wood_nail_lateral",
    "wood_screw_withdrawal",
    "wood_combined_lateral_withdrawal",
}


def _build_wood_module_configs(registry: ModuleRegistry) -> Dict[str, Dict[str, Any]]:
    configs: Dict[str, Dict[str, Any]] = {}
    for spec in registry.list_modules(category="Wood (NDS)", canonical_only=True):
        configs[spec.module_id] = {
            "label": f"{spec.title} ({registry.resolve_code_display(spec.module_id)})",
            "code": registry.resolve_code_display(spec.module_id),
            "fields": [(f.key, f.label, f.benchmark_value) for f in spec.fields],
        }
    return configs


class WoodDiagramWidget(DiagramWidget):
    """Dynamic 2D schematic structural diagram for all Wood Connections & Lateral modules."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.module_id = "wood_bolt_lateral"
        self.params: Dict[str, Any] = {}
        self.summary_note = ""

    def update_wood_diagram(
        self,
        module_id: str,
        params: Dict[str, Any],
        summary_note: str = "",
        has_result: bool = True,
    ) -> None:
        self.module_id = module_id
        self.params = dict(params)
        self.summary_note = summary_note
        self.has_result = has_result

        self.p_demand_lb = (
            float(params["P_demand_lbs"])
            if "P_demand_lbs" in params and params["P_demand_lbs"] is not None
            else (float(params["p_demand"]) if "p_demand" in params and params["p_demand"] is not None else None)
        )
        self.t_m_in = float(params["t_m_in"]) if params.get("t_m_in") is not None else None
        self.t_s_in = float(params["t_s_in"]) if params.get("t_s_in") is not None else None
        self.e_end_m_in = float(params["e_end_m_in"]) if params.get("e_end_m_in") is not None else None
        self.e_end_s_in = float(params["e_end_s_in"]) if params.get("e_end_s_in") is not None else None
        self.bolt_dia_in = float(params["D_in"]) if params.get("D_in") is not None else None
        self.c_delta = float(params["C_Delta"]) if params.get("C_Delta") is not None else None
        self.update()

    def clear_diagram(self, module_id: Optional[str] = None) -> None:
        if module_id:
            self.module_id = module_id
        self.params = {}
        self.summary_note = ""
        self.has_result = False
        self.p_demand_lb = None
        self.c_delta = None
        self.t_m_in = None
        self.t_s_in = None
        self.e_end_m_in = None
        self.e_end_s_in = None
        self.bolt_dia_in = None
        self.update()

    def apply_diagram_spec(self, spec: DiagramSpec) -> None:
        """Apply Qt-independent DiagramSpec directly to Panel 2 canvas (WP-8)."""
        merged: Dict[str, Any] = dict(spec.geometry_params)
        if spec.has_engine_result:
            merged.update(spec.derived_params)
        self.update_wood_diagram(
            module_id=spec.module_id,
            params=merged,
            summary_note=spec.summary_badge if spec.has_engine_result else "",
            has_result=spec.has_engine_result,
        )

    def paintEvent(self, event) -> None:
        if "bolt" in self.module_id:
            super().paintEvent(event)
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        h = self.height()
        painter.fillRect(0, 0, w, h, QColor("#ffffff"))

        cx = w * 0.46
        cy = h * 0.52

        struct_pen = QPen(QColor("#343a40"), 2.0)
        force_pen = QPen(QColor("#d96818"), 2.0)

        if "shear_wall" in self.module_id:
            painter.setPen(struct_pen)
            painter.setBrush(QBrush(QColor("#fde6cf")))
            sw_w = 110
            sw_h = int(h * 0.56)
            sw_x = int(cx - sw_w * 0.5)
            sw_y = int(cy - sw_h * 0.5)
            painter.drawRect(sw_x, sw_y, sw_w, sw_h)
            painter.setBrush(QBrush(QColor("#007bff")))
            painter.drawRect(sw_x + 4, sw_y + sw_h - 24, 12, 24)
            painter.drawRect(sw_x + sw_w - 16, sw_y + sw_h - 24, 12, 24)
            painter.setPen(force_pen)
            painter.drawLine(sw_x - 50, sw_y + 4, sw_x - 4, sw_y + 4)
            painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
            v_dem = self.params.get("V_asd_lbs") if self.has_result else None
            t_hd = self.params.get("T_holdown_demand_lbs") if self.has_result else None
            v_txt = f"V = {v_dem:.0f} lbs" if isinstance(v_dem, (int, float)) else "V = —"
            t_txt = f"T_HD = {t_hd:.0f} lbs" if isinstance(t_hd, (int, float)) else "T_HD = —"
            painter.drawText(QRectF(sw_x - 125, sw_y - 6, 120, 20), Qt.AlignLeft, v_txt)
            painter.drawText(QRectF(sw_x - 125, sw_y + sw_h - 20, 120, 20), Qt.AlignLeft, t_txt)

        elif "diaphragm" in self.module_id:
            painter.setPen(struct_pen)
            painter.setBrush(QBrush(QColor("#f8f9fa")))
            dw = 180
            dh = 80
            dx = int(cx - dw * 0.5)
            dy = int(cy - dh * 0.5)
            painter.drawRect(dx, dy, dw, dh)
            v_u = self.params.get("v_unit_demand_plf") if self.has_result else None
            t_ch = self.params.get("T_chord_max_lbs") if self.has_result else None
            t_txt = f"T_chord = {t_ch:.0f} lbs" if isinstance(t_ch, (int, float)) else "T_chord = —"
            v_txt = f"v = {v_u:.1f} plf" if isinstance(v_u, (int, float)) else "v = —"
            painter.setPen(force_pen)
            painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
            painter.drawText(QRectF(dx, dy - 20, 190, 18), Qt.AlignCenter, f"{t_txt} | {v_txt}")

        else:
            painter.setPen(struct_pen)
            painter.setBrush(QBrush(QColor("#fde6cf")))
            painter.drawRect(int(cx - 75), int(cy - 28), 55, 65)
            painter.drawRect(int(cx - 20), int(cy - 20), 110, 48)
            painter.setBrush(QBrush(QColor("#adb5bd")))
            painter.drawRect(int(cx - 26), int(cy - 16), 14, 44)

        if self.has_result and self.summary_note:
            note_w = 275.0
            note_h = 24.0
            note_rect = QRectF(w - note_w - 12, 10, note_w, note_h)
            painter.setPen(QPen(QColor("#ffeeba"), 1))
            painter.setBrush(QBrush(QColor("#fff3cd")))
            painter.drawRoundedRect(note_rect, 4, 4)
            painter.setPen(QPen(QColor("#856404"), 1))
            painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
            painter.drawText(note_rect, Qt.AlignCenter, self.summary_note)


class WoodCalculationWorkspace(BaseCalculationWorkspace):
    """
    Interactive 4-Panel Wood Connections & Lateral Workspace wired to CalculationService,
    ProjectService, and ReportService for the Day 14 End-to-End Vertical Slice.
    """

    exportExcelRequested = Signal(str)
    exportPdfRequested = Signal(str)

    MODULE_CONFIGS: Dict[str, Dict[str, Any]] = _build_wood_module_configs(get_module_registry())

    def __init__(
        self,
        calc_service: Optional[CalculationService] = None,
        project_service: Optional[ProjectService] = None,
        report_service: Optional[ReportService] = None,
        start_blank: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        self.registry = calc_service.registry if calc_service else get_module_registry()
        self.MODULE_CONFIGS = _build_wood_module_configs(self.registry)
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
        self._active_module_id = "wood_bolt_lateral"
        self._active_template_id = "wood_bolt_lateral"
        self._wood_start_blank = start_blank

        super().__init__(
            module_title="Wood Connections & Lateral",
            default_code=self.registry.resolve_code_display(self._active_module_id),
            start_blank=True,
            parent=parent,
        )

        # Replace generic diagram cleanly to prevent double-diagram ghosting (UI-01)
        parent_card_layout = self.diagram_widget.parentWidget().layout()
        old_diag = self.diagram_widget
        self.diagram_widget = WoodDiagramWidget(self)
        parent_card_layout.replaceWidget(old_diag, self.diagram_widget)
        old_diag.hide()
        old_diag.setParent(None)
        old_diag.deleteLater()

        self.calculateRequested.connect(self._execute_active_calculation)
        self.reset_inputs(blank=self._wood_start_blank)
        if not self._wood_start_blank:
            self.run_active_module()

    def _build_input_form(self, blank: bool) -> None:
        while self.form_layout.rowCount() > 0:
            self.form_layout.removeRow(0)
        self._input_edits.clear()

        spec = self.registry.resolve(self._active_template_id)
        self._active_field_specs = spec.fields
        self.default_code = self.registry.resolve_code_display(spec.module_id)

        lbl_mod = QLabel("Wood Sub-Module")
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
        if isinstance(self.diagram_widget, WoodDiagramWidget):
            self.diagram_widget.clear_diagram(self._active_module_id)

    def show_invalid_input(self, message: str) -> None:
        super().show_invalid_input(message)
        if isinstance(self.diagram_widget, WoodDiagramWidget):
            self.diagram_widget.clear_diagram(self._active_module_id)

    def select_submodule(self, module_id: str, start_blank: bool = False) -> None:
        """Switch active Wood module or specialized template (resolving aliases cleanly)."""
        spec = self.registry.get(module_id)
        resolved_id = spec.module_id if spec is not None else module_id

        if resolved_id in _FASTENER_TEMPLATE_IDS:
            self._active_template_id = resolved_id
            self._active_module_id = "wood_fastener_nds"
        elif resolved_id in self.MODULE_CONFIGS:
            self._active_template_id = resolved_id
            self._active_module_id = resolved_id
        else:
            return

        self.reset_inputs(blank=start_blank)
        if not start_blank:
            self.run_active_module()

    def _on_submodule_changed(self, index: int) -> None:
        mod_id = self.combo_module.itemData(index)
        if mod_id and mod_id != self._active_module_id:
            self._active_module_id = mod_id
            self._active_template_id = mod_id
            self.reset_inputs(blank=self._wood_start_blank)
            if not self._wood_start_blank:
                self.run_active_module()

    def get_form_inputs(self) -> Dict[str, Any]:
        spec = self.registry.get(self._active_template_id)
        parsed: Dict[str, Any] = dict(spec.preset_inputs) if spec else {}
        for k, edit in self._input_edits.items():
            raw = edit.text().strip()
            if raw == "":
                continue
            try:
                parsed[k] = float(raw)
            except ValueError:
                parsed[k] = raw
        return parsed

    def validate_and_get_inputs(self):
        parsed, err_status, err_msg = super().validate_and_get_inputs()
        if err_status is not None:
            return parsed, err_status, err_msg
        spec = self.registry.get(self._active_template_id)
        if spec and spec.preset_inputs:
            merged = dict(spec.preset_inputs)
            merged.update(parsed)
            return merged, None, ""
        return parsed, None, ""

    def set_design_method(self, method: DesignMethod) -> None:
        super().set_design_method(method)
        _, err_status, _ = self.validate_and_get_inputs()
        if err_status is None:
            self.run_active_module()

    def run_active_module(self) -> Optional[CalculationResult]:
        inputs, err_status, err_msg = self.validate_and_get_inputs()
        if err_status == CalculationStatus.INCOMPLETE:
            self.clear_to_incomplete(err_msg)
            return None
        if err_status == CalculationStatus.INVALID_INPUT:
            self.show_invalid_input(err_msg)
            return None

        method = self.get_selected_design_method()
        result = self.calc_service.run_calculation(
            module_id=self._active_template_id,
            inputs=inputs,
            design_method=method,
        )
        self.display_results(result)
        return result

    def _execute_active_calculation(self, inputs: Dict[str, Any], method: DesignMethod) -> None:
        result = self.calc_service.run_calculation(
            module_id=self._active_template_id,
            inputs=inputs,
            design_method=method,
        )
        self.display_results(result)

    def display_results(self, result: CalculationResult) -> None:
        super().display_results(result)
        if isinstance(self.diagram_widget, WoodDiagramWidget):
            diag_params = dict(result.input_parameters)
            diag_params.update(result.intermediate_results)
            note = f"{result.code_edition} ({result.design_method.value}) · DCR = {result.dcr:.2f} ({result.status.value})"
            self.diagram_widget.update_wood_diagram(
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
