"""Schema-driven WorkspaceHost binding Panel 1–4 directly to WorkspaceController (WP-6).

Preserves the exact Frozen 4-Panel UI layout from BaseCalculationWorkspace while
dynamically rendering FieldSpec forms, Qt-independent DiagramSpec canvases,
offline Calculation Sheet math traces, and SummaryViewModel state per item_id.
"""

import html
from pathlib import Path
from typing import Dict, Optional

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidgetItem,
    QWidget,
)

from app.controllers import WorkspaceController
from app.models import (
    CalculationResult,
    CalculationStatus,
    DesignMethod,
    DiagramSpec,
    FieldViewModel,
    WorkspaceViewModel,
)
from app.rendering import render_calculation_sheet_html
from app.services.report_service import ReportService
from gui.widgets.base_workspace import BaseCalculationWorkspace
from gui.widgets.cc_workspace import CCDiagramWidget
from gui.widgets.wood_workspace import WoodDiagramWidget


class DiagramSpecCanvasWidget(QWidget):
    """Qt vector canvas rendering any Qt-independent DiagramSpec (Steel, Concrete/CMU, etc.)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(180)
        self.setStyleSheet("background-color: #ffffff;")
        self._spec: Optional[DiagramSpec] = None
        self.has_result = False

    def apply_diagram_spec(self, spec: DiagramSpec) -> None:
        self._spec = spec
        self.has_result = bool(spec.has_engine_result)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w = float(self.width())
        h = float(self.height())
        painter.fillRect(0, 0, int(w), int(h), QColor("#ffffff"))

        spec = self._spec
        if spec is None or spec.is_empty_state:
            msg = spec.empty_message if spec else "Schematic diagram unavailable."
            painter.setPen(QColor("#6c757d"))
            painter.setFont(QFont("Segoe UI", 10))
            painter.drawText(self.rect().adjusted(16, 16, -16, -16), Qt.AlignCenter | Qt.TextWordWrap, msg)
            return

        # Compute bounds across shapes, dimensions, forces
        xs: list[float] = []
        ys: list[float] = []
        for shp in spec.shapes:
            if shp.kind == "rect" and len(shp.coords) >= 4:
                x, y, sw, sh = shp.coords[:4]
                xs.extend([x, x + sw])
                ys.extend([y, y + sh])
            elif shp.kind == "line" and len(shp.coords) >= 4:
                xs.extend([shp.coords[0], shp.coords[2]])
                ys.extend([shp.coords[1], shp.coords[3]])
            elif shp.kind == "circle" and len(shp.coords) >= 3:
                cx, cy, r = shp.coords[:3]
                xs.extend([cx - r, cx + r])
                ys.extend([cy - r, cy + r])
            elif shp.kind == "polygon" and len(shp.coords) >= 6:
                xs.extend(shp.coords[0::2])
                ys.extend(shp.coords[1::2])
        for dim in spec.dimensions:
            xs.extend([dim.p1[0], dim.p2[0]])
            ys.extend([dim.p1[1], dim.p2[1]])
        for frc in spec.forces:
            xs.extend([frc.origin[0], frc.origin[0] + frc.direction[0] * 36.0])
            ys.extend([frc.origin[1], frc.origin[1] + frc.direction[1] * 36.0])

        min_x = min(xs) if xs else 0.0
        max_x = max(xs) if xs else 380.0
        min_y = min(ys) if ys else 0.0
        max_y = max(ys) if ys else 200.0
        span_x = max(max_x - min_x, 40.0)
        span_y = max(max_y - min_y, 30.0)

        pad_x, pad_top, pad_bot = 30.0, 26.0, 24.0
        scale = min(max(w - 2 * pad_x, 60.0) / span_x, max(h - pad_top - pad_bot, 50.0) / span_y)
        off_x = (w - span_x * scale) / 2.0 - min_x * scale
        off_y = pad_top + (max(h - pad_top - pad_bot, 50.0) - span_y * scale) / 2.0 - min_y * scale

        def _tx(val: float) -> float:
            return val * scale + off_x

        def _ty(val: float) -> float:
            return val * scale + off_y

        # Title
        painter.setPen(QColor("#1b365d"))
        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
        painter.drawText(10, 17, spec.title)

        # Shapes
        for shp in spec.shapes:
            stroke = QColor(shp.stroke_color or "#343a40")
            fill = QColor(shp.fill_color or "#dee2e6")
            painter.setPen(QPen(stroke, max(1.0, shp.stroke_width)))
            painter.setBrush(QBrush(fill))
            if shp.kind == "rect" and len(shp.coords) >= 4:
                x, y, sw, sh = shp.coords[:4]
                painter.drawRect(int(_tx(x)), int(_ty(y)), int(max(sw * scale, 2.0)), int(max(sh * scale, 2.0)))
                if shp.label:
                    painter.setPen(QColor("#212529"))
                    painter.setFont(QFont("Segoe UI", 8))
                    painter.drawText(
                        int(_tx(x)), int(_ty(y)), int(max(sw * scale, 2.0)), int(max(sh * scale, 2.0)),
                        Qt.AlignCenter, shp.label,
                    )
            elif shp.kind == "line" and len(shp.coords) >= 4:
                painter.drawLine(int(_tx(shp.coords[0])), int(_ty(shp.coords[1])), int(_tx(shp.coords[2])), int(_ty(shp.coords[3])))
            elif shp.kind == "circle" and len(shp.coords) >= 3:
                cx, cy, r = shp.coords[:3]
                rr = max(r * scale, 2.0)
                painter.drawEllipse(QPointF(_tx(cx), _ty(cy)), rr, rr)
            elif shp.kind == "polygon" and len(shp.coords) >= 6:
                poly = QPolygonF(
                    [QPointF(_tx(shp.coords[i]), _ty(shp.coords[i + 1])) for i in range(0, len(shp.coords) - 1, 2)]
                )
                painter.drawPolygon(poly)

        # Dimensions
        painter.setFont(QFont("Segoe UI", 8))
        for dim in spec.dimensions:
            c = QColor(dim.color or "#007bff")
            painter.setPen(QPen(c, 1.1, Qt.DashLine))
            x1, y1 = _tx(dim.p1[0]), _ty(dim.p1[1])
            x2, y2 = _tx(dim.p2[0]), _ty(dim.p2[1])
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
            painter.setPen(c)
            painter.drawText(int((x1 + x2) / 2.0) - 24, int((y1 + y2) / 2.0) - 4, dim.label)

        # Engine-derived force vectors
        painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
        for frc in spec.forces:
            c = QColor("#b45309" if frc.is_stale else (frc.color or "#d96818"))
            ox, oy = _tx(frc.origin[0]), _ty(frc.origin[1])
            ex = ox + frc.direction[0] * 32.0 * scale
            ey = oy + frc.direction[1] * 32.0 * scale
            painter.setPen(QPen(c, 2.0))
            painter.drawLine(int(ox), int(oy), int(ex), int(ey))
            painter.setBrush(QBrush(c))
            painter.drawEllipse(QPointF(ex, ey), 3.0, 3.0)
            lbl = frc.label if (not frc.is_stale or "STALE" in frc.label.upper()) else f"{frc.label} [STALE]"
            painter.drawText(int(ex) + 5, int(ey) + 4, lbl)

        # Callout pills & summary badge
        pill_y = 8
        for pill in spec.callouts[:2]:
            bg = QColor("#fff3cd" if pill.severity == "warning" else ("#d1e7dd" if pill.severity == "pass" else "#f8d7da"))
            fg = QColor("#7c2d12" if pill.severity == "warning" else ("#0f5132" if pill.severity == "pass" else "#842029"))
            txt = pill.text[:48]
            pill_w = min(220, max(90, len(txt) * 6 + 14))
            painter.setPen(QPen(fg, 1.0))
            painter.setBrush(QBrush(bg))
            painter.drawRoundedRect(int(w - pill_w - 10), pill_y, int(pill_w), 18, 4, 4)
            painter.setPen(fg)
            painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
            painter.drawText(int(w - pill_w - 6), pill_y, int(pill_w - 8), 18, Qt.AlignCenter, txt)
            pill_y += 22

        if spec.summary_badge:
            painter.setPen(QColor("#b45309" if spec.is_stale else "#1b365d"))
            painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
            painter.drawText(10, int(h - 7), spec.summary_badge)


class EmptyDiagramWidget(QWidget):
    """Clean empty-state Panel 2 canvas for modules without an active schematic."""

    def __init__(self, message: str = "Schematic diagram unavailable until calculation module is active.", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(180)
        self.setStyleSheet("background-color: #ffffff;")
        self.message = message
        self.has_result = False
        self.c_delta = None

    def apply_diagram_spec(self, spec: DiagramSpec) -> None:
        self.message = spec.empty_message or "Schematic diagram unavailable until calculation module is active."
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(0, 0, self.width(), self.height(), QColor("#ffffff"))
        painter.setPen(QColor("#6c757d"))
        painter.setFont(QFont("Segoe UI", 10))
        painter.drawText(self.rect().adjusted(16, 16, -16, -16), Qt.AlignCenter | Qt.TextWordWrap, self.message)


class WorkspaceHost(BaseCalculationWorkspace):
    """Schema-driven 4-panel workspace host synchronized with pure-Python WorkspaceController."""

    itemStateChanged = Signal(str, object)
    revisionSaved = Signal(str, int)
    statusMessageRequested = Signal(str)
    exportExcelRequested = Signal(str)
    exportPdfRequested = Signal(str)

    def __init__(
        self,
        controller: WorkspaceController,
        module_title: str = "Structural Calculation",
        default_code: str = "ASCE 7-22 / NDS 2024",
        report_service: Optional[ReportService] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        self.controller = controller
        self.report_service = report_service or ReportService(
            kb_service=controller.kb_service,
            project_service=controller.project_service,
        )
        self.export_dir: Optional[Path] = None
        self._active_item_id: Optional[str] = None
        self._active_viewmodel: Optional[WorkspaceViewModel] = None
        self._field_widgets: Dict[str, QWidget] = {}
        self._is_binding = False
        self._diagram_kind = "empty"
        self.btn_export_xlsx: Optional[QPushButton] = None
        self.btn_export_pdf: Optional[QPushButton] = None

        super().__init__(
            module_title=module_title,
            default_code=default_code,
            start_blank=True,
            parent=parent,
        )
        self._append_export_row()

    @property
    def active_item_id(self) -> Optional[str]:
        return self._active_item_id

    @property
    def active_viewmodel(self) -> Optional[WorkspaceViewModel]:
        return self._active_viewmodel

    def bind_item(self, item_id: str) -> WorkspaceViewModel:
        """Bind a calculation item from WorkspaceController and render all 4 panels."""
        vm = self.controller.load(item_id)
        self._active_item_id = item_id
        self._active_viewmodel = vm
        self.module_title = vm.module_spec.title
        self.default_code = vm.code_edition

        self._rebuild_form_from_viewmodel(vm)
        self.refresh_from_viewmodel(vm)
        return vm

    def _rebuild_form_from_viewmodel(self, vm: WorkspaceViewModel) -> None:
        """Build Panel 1 schema-driven form grouped by FieldSpec.section without clipping."""
        self._is_binding = True
        try:
            while self.form_layout.rowCount() > 0:
                self.form_layout.removeRow(0)
            self._input_edits.clear()
            self._field_widgets.clear()

            if not vm.fields:
                info = QLabel(
                    f"{vm.module_spec.title}\n"
                    f"Module maturity: {vm.module_spec.maturity.value.upper()}. "
                    "Input schema will be activated once engine verification completes."
                )
                info.setWordWrap(True)
                info.setStyleSheet("font-size: 12px; color: #6c757d;")
                self.form_layout.addRow(info)
                return

            last_section: Optional[str] = None
            for fvm in vm.fields:
                if not fvm.is_visible:
                    continue
                fld = fvm.spec
                if fld.section != last_section:
                    sec_lbl = QLabel(fld.section.upper())
                    sec_lbl.setStyleSheet(
                        "font-size: 10px; font-weight: bold; color: #6c757d; margin-top: 6px; letter-spacing: 0.4px;"
                    )
                    self.form_layout.addRow(sec_lbl)
                    last_section = fld.section

                label_text = fld.label
                if fld.unit and f"({fld.unit})" not in label_text and fld.unit not in label_text:
                    label_text = f"{label_text} ({fld.unit})"

                lbl = QLabel(label_text)
                lbl.setWordWrap(True)
                lbl.setMinimumWidth(115)
                lbl.setStyleSheet("font-size: 11px; color: #495057;")

                tip_parts = []
                if fld.symbol:
                    tip_parts.append(f"Symbol: {fld.symbol}")
                if fld.default_reference:
                    tip_parts.append(f"Ref: {fld.default_reference}")
                if tip_parts:
                    lbl.setToolTip(" · ".join(tip_parts))

                if fld.value_type == "bool":
                    combo = QComboBox()
                    combo.setFixedHeight(26)
                    combo.setMinimumWidth(110)
                    combo.addItem("— Select —", "")
                    combo.addItem("Yes (True)", "true")
                    combo.addItem("No (False)", "false")
                    norm_bool = str(fvm.raw_value).strip().lower()
                    if norm_bool in ("true", "1", "yes"):
                        combo.setCurrentIndex(1)
                    elif norm_bool in ("false", "0", "no"):
                        combo.setCurrentIndex(2)
                    else:
                        combo.setCurrentIndex(0)
                    combo.setStyleSheet("""
                        QComboBox {
                            background-color: #ffffff;
                            border: 1px solid #ced4da;
                            border-radius: 4px;
                            padding: 2px 6px;
                            font-size: 11px;
                            font-weight: bold;
                            color: #0000ff;
                        }
                    """)
                    combo.currentIndexChanged.connect(
                        lambda _i, k=fld.key, c=combo: self._on_combo_edited(k, c)
                    )
                    self._field_widgets[fld.key] = combo
                    self.form_layout.addRow(lbl, combo)
                elif fld.value_type == "enum" and fld.enum_options:
                    combo = QComboBox()
                    combo.setFixedHeight(26)
                    combo.setMinimumWidth(110)
                    combo.addItem("— Select —", "")
                    for opt in fld.enum_options:
                        combo.addItem(opt, opt)
                    idx = combo.findData(fvm.raw_value)
                    if idx >= 0:
                        combo.setCurrentIndex(idx)
                    else:
                        combo.setCurrentIndex(0)
                    combo.setStyleSheet("""
                        QComboBox {
                            background-color: #ffffff;
                            border: 1px solid #ced4da;
                            border-radius: 4px;
                            padding: 2px 6px;
                            font-size: 11px;
                            font-weight: bold;
                            color: #0000ff;
                        }
                    """)
                    combo.currentIndexChanged.connect(
                        lambda _i, k=fld.key, c=combo: self._on_combo_edited(k, c)
                    )
                    self._field_widgets[fld.key] = combo
                    self.form_layout.addRow(lbl, combo)
                else:
                    edit = QLineEdit(fvm.raw_value)
                    edit.setAlignment(Qt.AlignRight)
                    edit.setFixedHeight(26)
                    edit.setMinimumWidth(90)
                    self._apply_edit_style(edit, valid=(fvm.raw_value == "" or fvm.is_valid))
                    edit.textEdited.connect(
                        lambda text, k=fld.key, e=edit: self._on_line_edited(k, text, e)
                    )
                    self._input_edits[fld.key] = edit
                    self._field_widgets[fld.key] = edit
                    self.form_layout.addRow(lbl, edit)

            self._append_export_row()
        finally:
            self._is_binding = False

    def _append_export_row(self) -> None:
        """Append compact Panel 1 single-item export buttons matching legacy workspaces."""
        export_row = QHBoxLayout()
        export_row.setSpacing(6)
        self.btn_export_xlsx = QPushButton("Export XLSX (17-Col)")
        self.btn_export_xlsx.setFixedHeight(28)
        self.btn_export_xlsx.setCursor(Qt.PointingHandCursor)
        self.btn_export_xlsx.setStyleSheet("font-size: 11px; font-weight: bold; color: #1F4E78;")
        self.btn_export_xlsx.clicked.connect(self._on_export_xlsx_clicked)

        self.btn_export_pdf = QPushButton("Export PDF (12-Sec)")
        self.btn_export_pdf.setFixedHeight(28)
        self.btn_export_pdf.setCursor(Qt.PointingHandCursor)
        self.btn_export_pdf.setStyleSheet("font-size: 11px; font-weight: bold; color: #1F4E78;")
        self.btn_export_pdf.clicked.connect(self._on_export_pdf_clicked)

        export_row.addWidget(self.btn_export_xlsx)
        export_row.addWidget(self.btn_export_pdf)
        self.form_layout.addRow(export_row)

    @staticmethod
    def _apply_edit_style(edit: QLineEdit, valid: bool) -> None:
        border = "#ced4da" if valid else "#dc3545"
        text_color = "#0000ff" if valid else "#dc3545"
        edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: #ffffff;
                border: 1px solid {border};
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 12px;
                font-weight: bold;
                color: {text_color};
            }}
        """)

    def _on_line_edited(self, key: str, raw_text: str, edit: QLineEdit) -> None:
        if self._is_binding or not self._active_item_id:
            return
        vm = self.controller.edit_field(self._active_item_id, key, raw_text)
        fvm = next((f for f in vm.fields if f.spec.key == key), None)
        if fvm is not None:
            self._apply_edit_style(edit, valid=(fvm.raw_value == "" or fvm.is_valid))
        self.refresh_from_viewmodel(vm)
        self.itemStateChanged.emit(self._active_item_id, vm)

    def _on_combo_edited(self, key: str, combo: QComboBox) -> None:
        if self._is_binding or not self._active_item_id:
            return
        val = combo.currentData()
        vm = self.controller.edit_field(self._active_item_id, key, "" if val is None else str(val))
        self.refresh_from_viewmodel(vm)
        self.itemStateChanged.emit(self._active_item_id, vm)

    def _ensure_diagram_canvas(self, spec: Optional[DiagramSpec], category: str) -> None:
        if spec is None or spec.is_empty_state:
            desired = "empty"
        elif category == "Loads (ASCE 7)":
            desired = "cc"
        elif category == "Wood (NDS)":
            desired = "wood"
        else:
            desired = "generic_spec"

        if desired == self._diagram_kind:
            return

        parent_layout = self.diagram_widget.parentWidget().layout()
        old_diag = self.diagram_widget
        if desired == "cc":
            new_diag: QWidget = CCDiagramWidget(self)
        elif desired == "wood":
            new_diag = WoodDiagramWidget(self)
        elif desired == "generic_spec":
            new_diag = DiagramSpecCanvasWidget(self)
        else:
            msg = spec.empty_message if spec else "Schematic diagram unavailable until calculation module is active."
            new_diag = EmptyDiagramWidget(message=msg, parent=self)

        self.diagram_widget = new_diag
        parent_layout.replaceWidget(old_diag, self.diagram_widget)
        old_diag.hide()
        old_diag.setParent(None)
        old_diag.deleteLater()
        self._diagram_kind = desired

    def refresh_from_viewmodel(self, vm: WorkspaceViewModel) -> None:
        """Synchronize Panels 2, 3, and 4 from WorkspaceViewModel."""
        self._active_viewmodel = vm
        self._current_result = vm.last_result
        self.default_code = vm.code_edition

        self._is_binding = True
        try:
            super().set_design_method(vm.design_method)
        finally:
            self._is_binding = False

        # Panel 2: DiagramSpec
        self._ensure_diagram_canvas(vm.diagram_spec, vm.module_spec.category)
        if vm.diagram_spec is not None and hasattr(self.diagram_widget, "apply_diagram_spec"):
            self.diagram_widget.apply_diagram_spec(vm.diagram_spec)

        # Panel 3: Code Basis Banner & Calculation Sheet
        stale_tag = " · STALE (inputs changed)" if vm.is_stale else ""
        rev_tag = f" · Rev {vm.current_revision}" if vm.current_revision > 0 else " · Unsaved Draft"
        self.lbl_code_basis.setText(
            f"Code basis: {vm.code_edition} · {vm.design_method.value}{rev_tag}{stale_tag} · Knowledge Base verified (SHA-256)"
        )
        self.calc_text.setHtml(
            render_calculation_sheet_html(
                result=vm.last_result,
                code_edition=vm.code_edition,
                design_method=vm.design_method.value,
                is_stale=vm.is_stale,
                incomplete_reasons=vm.incomplete_reasons,
            )
        )

        if vm.last_result is not None:
            ref_lines = [
                f"<b>Code Edition:</b> {html.escape(vm.last_result.code_edition)} ({vm.last_result.design_method.value})",
                f"<b>Reference Files:</b> {', '.join(vm.last_result.reference_files) if vm.last_result.reference_files else 'None'}",
            ]
            for a in vm.last_result.assumptions:
                ref_lines.append(f" • {html.escape(str(a))}")
            self.ref_text.setHtml("<br>".join(ref_lines))
        else:
            self.ref_text.setHtml("")

        # Panel 4: SummaryViewModel
        summary = vm.summary
        self.status_badge.update_status(summary.status)
        self.dcr_bar.setValue(summary.dcr_percent)
        dcr_suffix = " (STALE)" if vm.is_stale and summary.dcr is not None else ""
        self.lbl_dcr_val.setText(f"{summary.dcr_text}{dcr_suffix}")

        if vm.is_stale and summary.dcr is not None:
            chunk_color = "#fd7e14"
        elif summary.dcr is not None and summary.dcr > 1.0:
            chunk_color = "#dc3545"
        else:
            chunk_color = "#28a745"
        self.dcr_bar.setStyleSheet(f"""
            QProgressBar {{ background-color: #e9ecef; border-radius: 4px; }}
            QProgressBar::chunk {{ background-color: {chunk_color}; border-radius: 4px; }}
        """)

        clause_part = f" ({summary.governing_clause})" if summary.governing_clause else ""
        stale_prefix = "[STALE] " if vm.is_stale else ""
        self.lbl_governing.setText(f"Governing limit state: {stale_prefix}{summary.governing_check}{clause_part}")

        self.table_limit_states.setRowCount(len(summary.rows))
        for r_idx, row in enumerate(summary.rows):
            self.table_limit_states.setItem(r_idx, 0, QTableWidgetItem(row.step_id))
            self.table_limit_states.setItem(r_idx, 1, QTableWidgetItem(row.check_name))
            self.table_limit_states.setItem(r_idx, 2, QTableWidgetItem(row.clause))
            self.table_limit_states.setItem(r_idx, 3, QTableWidgetItem(row.demand_str))
            self.table_limit_states.setItem(r_idx, 4, QTableWidgetItem(row.capacity_str))
            self.table_limit_states.setItem(r_idx, 5, QTableWidgetItem(row.dcr_str))

            st_item = QTableWidgetItem(row.status.value)
            if row.status == CalculationStatus.PASS:
                st_item.setForeground(QColor("#28a745"))
                st_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
            elif row.status == CalculationStatus.FAIL:
                st_item.setForeground(QColor("#dc3545"))
                st_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
            self.table_limit_states.setItem(r_idx, 6, st_item)

    def set_design_method(self, method: DesignMethod) -> None:
        super().set_design_method(method)
        if self._is_binding or not self._active_item_id:
            return
        vm = self.controller.set_design_method(self._active_item_id, method)
        self._rebuild_form_from_viewmodel(vm)
        self.refresh_from_viewmodel(vm)
        self.itemStateChanged.emit(self._active_item_id, vm)

    def _on_calculate_clicked(self) -> None:
        if not self._active_item_id:
            super()._on_calculate_clicked()
            return
        vm = self.controller.run(self._active_item_id)
        self.refresh_from_viewmodel(vm)
        self.itemStateChanged.emit(self._active_item_id, vm)
        if vm.last_result is not None:
            self.statusMessageRequested.emit(
                f"Calculated {vm.display_code} ({vm.design_method.value}): {vm.status.value}, DCR = {vm.summary.dcr_text}"
            )

    def _on_save_revision_clicked(self) -> None:
        if not self._active_item_id:
            super()._on_save_revision_clicked()
            return
        try:
            vm = self.controller.save_revision(self._active_item_id, change_notes="Saved from desktop workspace")
        except ValueError as exc:
            self.statusMessageRequested.emit(str(exc))
            return
        self.refresh_from_viewmodel(vm)
        self.revisionSaved.emit(self._active_item_id, vm.current_revision)
        self.itemStateChanged.emit(self._active_item_id, vm)
        self.statusMessageRequested.emit(f"Saved {vm.display_code} Revision {vm.current_revision} (immutable SQLite snapshot)")

    def _resolve_export_result(self) -> Optional[tuple[WorkspaceViewModel, CalculationResult]]:
        if not self._active_item_id:
            return None
        vm = self.controller.load(self._active_item_id)
        if vm.last_result is None and vm.status not in (
            CalculationStatus.INCOMPLETE,
            CalculationStatus.INVALID_INPUT,
        ):
            vm = self.controller.run(self._active_item_id)
            self.refresh_from_viewmodel(vm)

        if vm.last_result is not None:
            data = vm.last_result.to_dict()
            data["is_stale"] = bool(vm.is_stale)
            calc_res = CalculationResult.from_dict(data)
        else:
            calc_res = CalculationResult(
                calculation_id=vm.item_id,
                module_id=vm.module_id,
                code_edition=vm.code_edition,
                design_method=vm.design_method,
                input_parameters=dict(vm.draft_inputs),
                status=vm.status,
                is_stale=bool(vm.is_stale),
                incomplete_reasons=list(vm.incomplete_reasons or ()),
            )
        return vm, calc_res

    def export_current_to_excel(self, output_path: Optional[Path] = None) -> Optional[Path]:
        resolved = self._resolve_export_result()
        if resolved is None:
            return None
        vm, calc_res = resolved
        base_dir = self.export_dir or Path("storage/exports")
        target = Path(output_path) if output_path else (
            base_dir / f"{vm.display_code}_{vm.module_id}_{vm.design_method.value}.xlsx"
        )
        saved = self.report_service.export_excel(calc_res, target)
        self.statusMessageRequested.emit(f"Exported XLSX: {saved}")
        self.exportExcelRequested.emit(str(saved))
        return saved

    def export_current_to_pdf(self, output_path: Optional[Path] = None) -> Optional[Path]:
        resolved = self._resolve_export_result()
        if resolved is None:
            return None
        vm, calc_res = resolved
        base_dir = self.export_dir or Path("storage/exports")
        target = Path(output_path) if output_path else (
            base_dir / f"{vm.display_code}_{vm.module_id}_{vm.design_method.value}.pdf"
        )
        saved = self.report_service.export_pdf(calc_res, target, diagram_spec=vm.diagram_spec)
        self.statusMessageRequested.emit(f"Exported PDF: {saved}")
        self.exportPdfRequested.emit(str(saved))
        return saved

    def _on_export_xlsx_clicked(self) -> None:
        self.export_current_to_excel()

    def _on_export_pdf_clicked(self) -> None:
        self.export_current_to_pdf()
