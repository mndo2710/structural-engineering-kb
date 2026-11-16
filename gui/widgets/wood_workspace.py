"""PySide6 Wood Connections & Lateral Interactive 4-Panel Workspace (Day 14 Vertical Slice).

Conforms to SAD v1.0 Sections 8.2.B, 8.3, 8.4 & Master Rules 2, 5, 6, 8.
Supports all 5 V1 Wood Connections & Lateral workflows:
  1. Bolt / Dowel Lateral & Group Tear-Out (NDS 2024 Ch. 12 & App. E)
  2. Nail / Wood Screw / Lag Screw / Simpson SDS (NDS 2024 Ch. 12 & ESR-2236)
  3. Wood-Frame Shear Wall & Holdown Anchorage (SDPWS 2021 Sec. 4.3 & Simpson HDU)
  4. Wood Structural Panel Diaphragm, Chord & Collector (SDPWS 2021 Sec. 4.2 & Straps)
  5. Simpson Joist Hanger & Hurricane Tie Multi-Axis Check (Simpson C-C-2026)
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

from app.services.calculation_service import CalculationService
from app.services.knowledge_base_service import KnowledgeBaseService
from app.services.project_service import ProjectService
from app.services.report_service import ReportService
from core.common.calculation_result import CalculationResult, DesignMethod
from gui.widgets.base_workspace import BaseCalculationWorkspace, DiagramWidget


class WoodDiagramWidget(DiagramWidget):
    """Dynamic 2D schematic structural diagram for all 5 Wood Connections & Lateral modules."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.module_id = "wood_bolt_lateral"
        self.params: Dict[str, Any] = {}
        self.summary_note = "e_end,m = 3.0 in < 7D = 4.375 in -> C_Delta = 0.69"

    def update_wood_diagram(
        self,
        module_id: str,
        params: Dict[str, Any],
        summary_note: str = "",
    ) -> None:
        self.module_id = module_id
        self.params = dict(params)
        if summary_note:
            self.summary_note = summary_note

        # Keep base class attributes synced for wood_bolt_lateral
        self.p_demand_lb = float(params.get("P_demand_lbs", params.get("p_demand", 340.0)))
        self.t_m_in = float(params.get("t_m_in", 1.5))
        self.t_s_in = float(params.get("t_s_in", 1.5))
        self.e_end_m_in = float(params.get("e_end_m_in", 3.0))
        self.bolt_dia_in = float(params.get("D_in", 0.625))
        self.c_delta = float(params.get("C_Delta", 0.69))
        self.update()

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
            # Draw wood shear wall panel with boundary posts and HDU holdowns
            painter.setPen(struct_pen)
            painter.setBrush(QBrush(QColor("#fde6cf")))
            sw_w = 110
            sw_h = int(h * 0.56)
            sw_x = int(cx - sw_w * 0.5)
            sw_y = int(cy - sw_h * 0.5)
            painter.drawRect(sw_x, sw_y, sw_w, sw_h)
            # Holdown brackets at bottom corners
            painter.setBrush(QBrush(QColor("#007bff")))
            painter.drawRect(sw_x + 4, sw_y + sw_h - 24, 12, 24)
            painter.drawRect(sw_x + sw_w - 16, sw_y + sw_h - 24, 12, 24)
            # Top lateral shear arrow V
            painter.setPen(force_pen)
            painter.drawLine(sw_x - 50, sw_y + 4, sw_x - 4, sw_y + 4)
            painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
            v_dem = self.params.get("V_asd_lbs", 2240.0)
            t_hd = self.params.get("T_holdown_demand_lbs", 5300.0)
            painter.drawText(QRectF(sw_x - 125, sw_y - 6, 120, 20), Qt.AlignLeft, f"V = {v_dem:.0f} lbs")
            painter.drawText(QRectF(sw_x - 125, sw_y + sw_h - 20, 120, 20), Qt.AlignLeft, f"T_HD = {t_hd:.0f} lbs")

        elif "diaphragm" in self.module_id:
            # Plan view of blocked diaphragm with chords and collector drag strut
            painter.setPen(struct_pen)
            painter.setBrush(QBrush(QColor("#f8f9fa")))
            dw = 180
            dh = 80
            dx = int(cx - dw * 0.5)
            dy = int(cy - dh * 0.5)
            painter.drawRect(dx, dy, dw, dh)
            v_u = self.params.get("v_unit_demand_plf", 378.0)
            t_ch = self.params.get("T_chord_max_lbs", 6804.0)
            painter.setPen(force_pen)
            painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
            painter.drawText(QRectF(dx, dy - 20, 180, 18), Qt.AlignCenter, f"T_chord = {t_ch:.0f} lbs | v = {v_u:.1f} plf")

        else:
            # Fastener or Simpson Hanger / Hurricane Tie schematic
            painter.setPen(struct_pen)
            painter.setBrush(QBrush(QColor("#fde6cf")))
            painter.drawRect(int(cx - 75), int(cy - 28), 55, 65)
            painter.drawRect(int(cx - 20), int(cy - 20), 110, 48)
            painter.setBrush(QBrush(QColor("#adb5bd")))
            painter.drawRect(int(cx - 26), int(cy - 16), 14, 44)

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

    MODULE_CONFIGS: Dict[str, Dict[str, Any]] = {
        "wood_bolt_lateral": {
            "label": "Bolt / Dowel Lateral & Group Tear-Out (NDS Ch. 12 & App. E)",
            "code": "NDS 2024",
            "fields": [
                ("D_in", "Bolt Diameter D (in.)", "0.625"),
                ("shear_planes", "Shear Planes (Single Shear / Double Shear)", "Single Shear"),
                ("F_yb_psi", "Bolt Bending Yield F_yb (psi)", "45000.0"),
                ("main_species", "Main Member Species", "Douglas Fir-Larch"),
                ("side_material", "Side Member (Wood / Steel / Concrete)", "Wood"),
                ("t_m_in", "Main Thickness t_m (in.)", "1.5"),
                ("t_s_in", "Side Thickness t_s (in.)", "1.5"),
                ("e_end_m_in", "Loaded End Distance e_end,m (in.)", "3.0"),
                ("n_rows", "Number of Bolt Rows n_rows", "1"),
                ("n_bolts_per_row", "Bolts per Row n_b", "1"),
                ("C_D", "Load Duration Factor C_D", "1.00"),
                ("P_demand_lbs", "Applied Tension Demand P (lbs)", "340.0"),
            ],
        },
        "wood_fastener_nds": {
            "label": "Nail / Wood Screw / Lag Screw / Simpson SDS (NDS Ch. 12)",
            "code": "NDS 2024 / ICC-ES ESR-2236",
            "fields": [
                ("fastener_type", "Type (Lag_Screw / Simpson_SDS / Wood_Screw / Common_Nail)", "Lag_Screw"),
                ("species", "Wood Species", "Douglas Fir-Larch"),
                ("side_member_type", "Side Member (Wood / Steel)", "Wood"),
                ("D_in", "Fastener Diameter D (in.)", "0.375"),
                ("L_in", "Fastener Length L (in.)", "4.0"),
                ("t_s_in", "Side Thickness t_s (in.)", "1.5"),
                ("n_fasteners", "Total Fasteners N", "4"),
                ("C_D", "Load Duration Factor C_D", "1.00"),
                ("V_demand_lbs", "Lateral Shear Demand V (lbs)", "650.0"),
                ("T_demand_lbs", "Axial Withdrawal Demand T (lbs)", "320.0"),
            ],
        },
        "wood_shear_wall_sdpws": {
            "label": "Wood-Frame Shear Wall & Holdown (SDPWS 2021 Sec. 4.3)",
            "code": "SDPWS 2021 / NDS 2024",
            "fields": [
                ("h_ft", "Wall Clear Height h (ft)", "10.0"),
                ("bs_ft", "Wall Segment Width b_s (ft)", "4.0"),
                ("V_asd_lbs", "ASD Seismic Shear V_ASD (lbs)", "2240.0"),
                ("V_lrfd_lbs", "LRFD Seismic Shear V_LRFD (lbs)", "3200.0"),
                ("w_DL_plf", "Tributary Dead Load w_DL (plf)", "250.0"),
                ("sheathing_category", "Sheathing Category (Structural I / Sheathing)", "Structural I"),
                ("panel_thickness", "Panel Thickness (15/32 / 7/16 / 3/8)", "15/32"),
                ("nail_size", "Common Nail Size (10d / 8d / 6d)", "10d"),
                ("edge_spacing_in", "Edge Nail Spacing (6 / 4 / 3 / 2 in.)", "3"),
                ("holdown_model", "Simpson Holdown Model", "HDU5-SDS2.5"),
            ],
        },
        "wood_diaphragm_sdpws": {
            "label": "Wood Diaphragm, Chord & Collector (SDPWS 2021 Sec. 4.2)",
            "code": "SDPWS 2021 / NDS 2024",
            "fields": [
                ("L_span_ft", "Diaphragm Span L (ft)", "72.0"),
                ("W_depth_ft", "Diaphragm Depth W (ft)", "30.0"),
                ("w_asd_plf", "ASD Uniform Load w_ASD (plf)", "315.0"),
                ("w_lrfd_plf", "LRFD Uniform Load w_LRFD (plf)", "450.0"),
                ("sheathing_grade", "Grade (Sheathing and Single-Floor / Structural I)", "Sheathing and Single-Floor"),
                ("nail_size", "Common Nail Size (10d / 8d)", "10d"),
                ("panel_thickness", "Panel Thickness (15/32 / 7/16 / 3/8)", "15/32"),
                ("boundary_spacing_in", "Boundary Nail Spacing (6 / 4 / 2.5 / 2 in.)", "4.0"),
                ("unsupported_drag_ft", "Unsupported Collector Length (ft)", "15.0"),
                ("strap_model", "Simpson Collector Strap Model", "MSTC66"),
            ],
        },
        "wood_simpson_hanger_tie": {
            "label": "Simpson Joist Hanger & Hurricane Tie (C-C-2026)",
            "code": "Simpson C-C-2026 / NDS 2024",
            "fields": [
                ("hanger_model", "Simpson Hanger Model", "HUS210-2"),
                ("hanger_species", "Hanger Wood Species (DF/SP / SPF/HF)", "DF/SP"),
                ("H_joist_in", "Carried Member Depth H (in.)", "9.25"),
                ("R_floor_lbs", "Floor Download R_floor (lbs, CD=1.00)", "2600.0"),
                ("R_roof_lbs", "Roof Download R_roof (lbs, CD=1.25)", "3150.0"),
                ("U_hanger_lbs", "Hanger Wind Uplift U (lbs, CD=1.60)", "1450.0"),
                ("tie_model", "Hurricane Tie Model", "H10A (Nails)"),
                ("tie_species", "Hurricane Tie Species (SPF/HF / DF/SP)", "SPF/HF"),
                ("U_tie_lbs", "Rafter Wind Uplift U_tie (lbs)", "520.0"),
                ("F1_tie_lbs", "In-Plane Shear F1 (lbs)", "320.0"),
                ("F2_tie_lbs", "Out-of-Plane Reaction F2 (lbs)", "95.0"),
            ],
        },
    }

    def __init__(
        self,
        calc_service: Optional[CalculationService] = None,
        project_service: Optional[ProjectService] = None,
        report_service: Optional[ReportService] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        self.kb_service = calc_service.kb_service if calc_service else KnowledgeBaseService()
        self.project_service = project_service or ProjectService()
        self.calc_service = calc_service or CalculationService(
            kb_service=self.kb_service,
            project_service=self.project_service,
        )
        self.report_service = report_service or ReportService(
            kb_service=self.kb_service,
            project_service=self.project_service,
        )
        self._active_module_id = "wood_bolt_lateral"
        self._input_edits: Dict[str, QLineEdit] = {}

        super().__init__(
            module_title="Wood Connections & Lateral",
            default_code="NDS 2024 / SDPWS 2021",
            parent=parent,
        )

        # Replace generic diagram with WoodDiagramWidget
        parent_card_layout = self.diagram_widget.parentWidget().layout()
        old_diag = self.diagram_widget
        self.diagram_widget = WoodDiagramWidget(self)
        parent_card_layout.replaceWidget(old_diag, self.diagram_widget)
        old_diag.deleteLater()

        self.calculateRequested.connect(self._execute_active_calculation)
        self.run_active_module()

    def _populate_sample_inputs(self) -> None:
        while self.form_layout.rowCount() > 0:
            self.form_layout.removeRow(0)
        self._input_edits.clear()

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

        cfg = self.MODULE_CONFIGS[self._active_module_id]
        for key, label_str, default_val in cfg["fields"]:
            lbl = QLabel(label_str)
            lbl.setStyleSheet("font-size: 11px; color: #495057;")
            edit = QLineEdit(str(default_val))
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
            self._input_edits[key] = edit
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

    def select_submodule(self, module_id: str) -> None:
        if module_id in self.MODULE_CONFIGS:
            self._active_module_id = module_id
            self._populate_sample_inputs()
            self.run_active_module()

    def _on_submodule_changed(self, index: int) -> None:
        mod_id = self.combo_module.itemData(index)
        if mod_id and mod_id != self._active_module_id:
            self._active_module_id = mod_id
            self._populate_sample_inputs()
            self.run_active_module()

    def get_form_inputs(self) -> Dict[str, Any]:
        parsed: Dict[str, Any] = {}
        for k, edit in self._input_edits.items():
            raw = edit.text().strip()
            try:
                parsed[k] = float(raw)
            except ValueError:
                parsed[k] = raw
        return parsed

    def set_design_method(self, method: DesignMethod) -> None:
        super().set_design_method(method)
        self.run_active_module()

    def run_active_module(self) -> CalculationResult:
        inputs = self.get_form_inputs()
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
        if isinstance(self.diagram_widget, WoodDiagramWidget):
            diag_params = dict(result.input_parameters)
            diag_params.update(result.intermediate_results)
            note = f"{result.code_edition} ({result.design_method.value}) · DCR = {result.dcr:.2f} ({result.status.value})"
            self.diagram_widget.update_wood_diagram(
                module_id=result.module_id,
                params=diag_params,
                summary_note=note,
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
        out_path = Path("storage/projects") / f"{self._current_result.module_id}_{self._current_result.design_method.value}.xlsx"
        saved = self.export_current_to_excel(out_path)
        self.exportExcelRequested.emit(str(saved))

    def _on_export_pdf_clicked(self) -> None:
        if self._current_result is None:
            self.run_active_module()
        out_path = Path("storage/projects") / f"{self._current_result.module_id}_{self._current_result.design_method.value}.pdf"
        saved = self.export_current_to_pdf(out_path)
        self.exportPdfRequested.emit(str(saved))
