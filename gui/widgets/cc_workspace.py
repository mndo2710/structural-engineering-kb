"""PySide6 Components & Cladding (C&C) Interactive 4-Panel Workspace (Day 13 Vertical Slice).

Conforms to SAD v1.0 Sections 8.2.A, 8.3, 8.4 & Master Rules 2, 5, 6, 8.
Supports all 5 V1 C&C workflows:
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

from app.services.calculation_service import CalculationService
from app.services.knowledge_base_service import KnowledgeBaseService
from app.services.project_service import ProjectService
from app.services.report_service import ReportService
from core.common.calculation_result import CalculationResult, DesignMethod
from gui.widgets.base_workspace import BaseCalculationWorkspace


class CCDiagramWidget(QWidget):
    """Dynamic 2D schematic structural diagram for all 5 C&C sub-assemblies."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(180)
        self.setStyleSheet("background-color: #ffffff;")
        self.module_id = "asce7_parapet_wind"
        self.params: Dict[str, Any] = {}
        self.summary_note = "ASCE 7-22 Sec. 30.9 · C&C Net Pressure"

    def update_cc_diagram(
        self,
        module_id: str,
        params: Dict[str, Any],
        summary_note: str = "",
    ) -> None:
        self.module_id = module_id
        self.params = dict(params)
        if summary_note:
            self.summary_note = summary_note
        self.update()

    def update_parameters(self, **kwargs: Any) -> None:
        """Compatibility hook for BaseCalculationWorkspace."""
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
            # Draw roof diaphragm + vertical cantilever parapet stud
            painter.setPen(struct_pen)
            painter.setBrush(QBrush(QColor("#e9ecef")))
            # Roof deck
            painter.drawRect(int(cx), int(cy), int(w * 0.35), 14)
            # Wall below roof
            painter.drawRect(int(cx - 14), int(cy), 14, int(h * 0.32))
            # Parapet stud above roof
            painter.setBrush(QBrush(QColor("#fde6cf")))
            par_h_px = int(h * 0.36)
            painter.drawRect(int(cx - 14), int(cy - par_h_px), 14, par_h_px)

            # Wind arrows pushing on parapet
            painter.setPen(force_pen)
            for frac in (0.2, 0.5, 0.8):
                ay = int(cy - par_h_px * frac)
                painter.drawLine(int(cx - 75), ay, int(cx - 18), ay)
                painter.drawLine(int(cx - 24), ay - 4, int(cx - 18), ay)
                painter.drawLine(int(cx - 24), ay + 4, int(cx - 18), ay)

            h_par = self.params.get("h_par_ft", 3.5)
            p_gov = self.params.get("p_gov_psf", 52.0)
            painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
            painter.drawText(QRectF(cx - 135, cy - par_h_px * 0.65, 110, 20), Qt.AlignLeft, f"p_gov = {p_gov:.1f} psf")

            painter.setPen(dim_pen)
            painter.drawText(QRectF(cx + 8, cy - par_h_px * 0.6, 110, 20), Qt.AlignLeft, f"h_par = {h_par:.1f} ft")

        elif "overhang" in self.module_id:
            # Draw exterior wall + sloped rafter with overhang cantilever
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

            # Upward wind suction arrows on overhang
            painter.setPen(force_pen)
            for ax in (int(cx - 75), int(cx - 45)):
                painter.drawLine(ax, int(cy + 40), ax, int(cy - 18))
                painter.drawLine(ax - 4, int(cy - 12), ax, int(cy - 18))
                painter.drawLine(ax + 4, int(cy - 12), ax, int(cy - 18))

            l_oh = self.params.get("L_oh_ft", 2.5)
            r_up = self.params.get("R_uplift_lbs", 420.0)
            painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
            painter.drawText(QRectF(cx - 130, cy - 38, 120, 20), Qt.AlignLeft, f"L_oh = {l_oh:.1f} ft")
            painter.setPen(dim_pen)
            painter.drawText(QRectF(cx + 14, cy + 8, 150, 20), Qt.AlignLeft, f"R_tie = {r_up:.0f} lbs uplift")

        elif "awning" in self.module_id:
            # Wall + cantilevered canopy with tie-back rod
            painter.setPen(struct_pen)
            painter.setBrush(QBrush(QColor("#e9ecef")))
            painter.drawRect(int(cx - 60), int(h * 0.16), 16, int(h * 0.68))

            painter.setBrush(QBrush(QColor("#ced4da")))
            painter.drawRect(int(cx - 44), int(cy), 120, 12)

            # Diagonal tie-back rod
            painter.setPen(QPen(QColor("#c86816"), 2.0))
            painter.drawLine(int(cx - 44), int(cy - 45), int(cx + 55), int(cy))

            bc = self.params.get("Bc_ft", 5.0)
            m_w = self.params.get("M_wall_lb_ft", 1185.0)
            painter.setPen(force_pen)
            painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
            painter.drawText(QRectF(cx - 30, cy + 18, 150, 20), Qt.AlignLeft, f"B_c = {bc:.1f} ft | M = {m_w:.0f} lb-ft")

        elif "trellis" in self.module_id:
            # Open pergola portal frame with top slats
            painter.setPen(struct_pen)
            painter.setBrush(QBrush(QColor("#fde6cf")))
            left_x = int(cx - 70)
            right_x = int(cx + 70)
            top_y = int(h * 0.28)
            bot_y = int(h * 0.78)
            painter.drawRect(left_x, top_y, 12, bot_y - top_y)
            painter.drawRect(right_x, top_y, 12, bot_y - top_y)
            painter.drawRect(left_x - 10, top_y - 10, right_x - left_x + 32, 10)

            # Wind arrow on open trellis
            painter.setPen(force_pen)
            painter.drawLine(left_x - 55, top_y - 5, left_x - 14, top_y - 5)
            painter.drawLine(left_x - 20, top_y - 9, left_x - 14, top_y - 5)
            painter.drawLine(left_x - 20, top_y - 1, left_x - 14, top_y - 5)

            v_post = self.params.get("V_post_lbs", 157.2)
            painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
            painter.drawText(QRectF(left_x - 85, top_y + 12, 110, 20), Qt.AlignLeft, f"V_post = {v_post:.1f} lbs")

        else:
            # Guardrail post on deck with 200 lb concentrated top-rail load
            painter.setPen(struct_pen)
            painter.setBrush(QBrush(QColor("#e9ecef")))
            painter.drawRect(int(cx - 70), int(cy + 20), 140, 16)
            # Base plate & post
            painter.setBrush(QBrush(QColor("#adb5bd")))
            painter.drawRect(int(cx - 18), int(cy + 14), 36, 6)
            painter.drawRect(int(cx - 6), int(cy - 55), 12, 69)

            # 200 lb horizontal arrow at top of guard post
            painter.setPen(force_pen)
            painter.drawLine(int(cx - 65), int(cy - 50), int(cx - 10), int(cy - 50))
            painter.drawLine(int(cx - 16), int(cy - 54), int(cx - 10), int(cy - 50))
            painter.drawLine(int(cx - 16), int(cy - 46), int(cx - 10), int(cy - 50))
            painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
            painter.drawText(QRectF(cx - 95, cy - 70, 110, 18), Qt.AlignLeft, "P = 200 lbs (IBC 1607.9)")

        # Top-right summary pill badge
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

    MODULE_CONFIGS: Dict[str, Dict[str, Any]] = {
        "asce7_parapet_wind": {
            "label": "Parapet Wind Pressure (ASCE 7-22 Sec. 30.9)",
            "code": "ASCE 7-22",
            "fields": [
                ("V_mph", "Basic Wind Speed V (mph)", "115.0"),
                ("exposure", "Exposure Category (B/C/D)", "C"),
                ("h_roof_ft", "Mean Roof Height h (ft)", "25.0"),
                ("h_par_ft", "Parapet Height h_par (ft)", "3.5"),
                ("spacing_ft", "Stud Spacing s (ft)", "1.333"),
                ("roof_slope_deg", "Roof Slope θ (deg)", "5.0"),
                ("wall_zone", "Wall Zone (Zone 4 / Zone 5)", "Zone 5"),
                ("roof_zone", "Roof Zone (Zone 2 / Zone 3)", "Zone 3"),
                ("backspan_ft", "Stud Backspan L_back (ft)", "10.0"),
                ("M_cap_asd_lb_ft", "Stud Bending Cap M_cap (lb-ft)", "650.0"),
                ("V_cap_asd_lbs", "Base Shear Cap V_cap (lbs)", "450.0"),
                ("R_cap_asd_lbs", "Roof Diaphragm Cap R_cap (lbs)", "600.0"),
            ],
        },
        "asce7_roof_overhang": {
            "label": "Roof Overhang Wind Uplift (ASCE 7-22 Sec. 30.7)",
            "code": "ASCE 7-22",
            "fields": [
                ("V_mph", "Basic Wind Speed V (mph)", "115.0"),
                ("exposure", "Exposure Category (B/C/D)", "C"),
                ("h_roof_ft", "Mean Roof Height h (ft)", "20.0"),
                ("L_oh_ft", "Overhang Projection L_oh (ft)", "2.5"),
                ("L_back_ft", "Rafter Backspan L_back (ft)", "14.0"),
                ("spacing_ft", "Rafter Spacing s (ft)", "2.0"),
                ("roof_slope_deg", "Roof Slope θ (deg)", "15.0"),
                ("roof_zone", "Roof Zone (Zone 2 / Zone 3)", "Zone 2"),
                ("dead_load_psf", "Roof Dead Load D (psf)", "12.0"),
                ("R_tie_cap_asd_lbs", "Hurricane Tie Cap R_cap (lbs)", "685.0"),
                ("M_cap_asd_lb_ft", "Rafter Bending Cap M_cap (lb-ft)", "950.0"),
            ],
        },
        "asce7_awning_canopy": {
            "label": "Attached Awning & Canopy (ASCE 7-22 Sec. 30.11)",
            "code": "ASCE 7-22",
            "fields": [
                ("V_mph", "Basic Wind Speed V (mph)", "115.0"),
                ("exposure", "Exposure Category (B/C/D)", "C"),
                ("h_roof_ft", "Main Roof Height h (ft)", "20.0"),
                ("he_ft", "Eave Height h_e (ft)", "20.0"),
                ("hc_ft", "Canopy Height h_c (ft)", "10.0"),
                ("Bc_ft", "Canopy Projection B_c (ft)", "5.0"),
                ("Sb_ft", "Bracket Spacing S_b (ft)", "6.0"),
                ("w_D_psf", "Canopy Dead Load w_D (psf)", "12.0"),
                ("w_Lr_psf", "Canopy Live Load w_Lr (psf)", "20.0"),
                ("SDS_g", "Seismic Parameter S_DS (g)", "1.0"),
                ("support_type", "Support (Cantilever_Bracket / TieBack_Hanger)", "Cantilever_Bracket"),
                ("M_wall_cap_asd_lb_ft", "Wall Moment Cap M_cap (lb-ft)", "1600.0"),
            ],
        },
        "asce7_trellis_loads": {
            "label": "Open-Frame Trellis Wind/Seismic (ASCE 7-22 Sec. 29.4)",
            "code": "ASCE 7-22",
            "fields": [
                ("V_mph", "Basic Wind Speed V (mph)", "115.0"),
                ("exposure", "Exposure Category (B/C/D)", "C"),
                ("z_top_ft", "Trellis Top Height z (ft)", "10.0"),
                ("Hp_ft", "Post Clear Height H_p (ft)", "10.0"),
                ("Lt_ft", "Plan Length L_t (ft)", "16.0"),
                ("Bt_ft", "Plan Width B_t (ft)", "12.0"),
                ("Af_eff_ft2", "Projected Solid Area A_f,eff (ft^2)", "28.0"),
                ("epsilon_elev", "Solidity Ratio ε (As/Ag)", "0.18"),
                ("num_posts", "Number of Posts N_p", "4"),
                ("w_D_psf", "Trellis Dead Load w_D (psf)", "8.0"),
                ("SDS_g", "Seismic Parameter S_DS (g)", "1.0"),
                ("M_post_cap_asd_lb_ft", "Post Base Moment Cap (lb-ft)", "2000.0"),
            ],
        },
        "ibc_guardrail_loads": {
            "label": "Guardrail & Handrail Loads (2024 IBC Sec. 1607.9)",
            "code": "2024 IBC / ASCE 7-22",
            "fields": [
                ("occupancy", "Occupancy (R-3_Residential / Commercial_Standard)", "R-3_Residential"),
                ("H_guard_in", "Guard Height H_guard (in.)", "42.0"),
                ("S_post_ft", "Post Spacing S_post (ft)", "5.0"),
                ("e_fas_in", "Fascia Offset e_fas (in.)", "0.0"),
                ("p_W_psf", "Exterior Wind Pressure p_W (psf)", "20.0"),
                ("epsilon_guard", "Guard Solidity Ratio ε", "0.30"),
                ("N_t_bolts", "Tension Row Bolts N_t", "2"),
                ("d_bolt_in", "Bolt Lever Arm d_bolt (in.)", "4.25"),
                ("T_bolt_cap_asd_lbs", "Bolt Tension Cap T_cap (lbs)", "1250.0"),
                ("M_post_cap_asd_lb_ft", "Post Flexural Cap M_cap (lb-ft)", "950.0"),
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
        self._active_module_id = "asce7_parapet_wind"
        self._input_edits: Dict[str, QLineEdit] = {}

        super().__init__(
            module_title="Components & Cladding Loads",
            default_code="ASCE 7-22",
            parent=parent,
        )

        # Replace generic wood bolt diagram with C&C schematic diagram widget
        parent_card_layout = self.diagram_widget.parentWidget().layout()
        old_diag = self.diagram_widget
        self.diagram_widget = CCDiagramWidget(self)
        parent_card_layout.replaceWidget(old_diag, self.diagram_widget)
        old_diag.deleteLater()

        # Connect calculate signal to deterministic execution
        self.calculateRequested.connect(self._execute_active_calculation)

        # Run initial default calculation so all 4 panels show live verified C&C results
        self.run_active_module()

    def _populate_sample_inputs(self) -> None:
        """Build interactive module selector and editable parameter fields."""
        # Clear existing rows
        while self.form_layout.rowCount() > 0:
            self.form_layout.removeRow(0)
        self._input_edits.clear()

        # Sub-module selector combo box
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

        # Quick Export buttons row inside input panel
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
        """Programmatically switch active C&C workflow template."""
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
        """Parse typed inputs from QLineEdit controls."""
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
        """Execute active C&C module and update all 4 workspace panels."""
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
