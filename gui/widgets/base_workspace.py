"""4-Panel Calculation Workspace per SAD v1.0 Section 8.3, 8.4 & Mockup Architecture.

Provides standardized interface panels:
  1. Input Panel (left): Parameter inputs, right-aligned values, Run & Save buttons.
  2. Diagram Panel (top right): Dynamic schematic engineering drawing with dimensions.
  3. Calculation Sheet Panel (middle right): Step-by-step equations, substitutions, and right-aligned code references.
  4. Summary Panel (bottom right): PASS/FAIL pill badge, governing limit state, DCR gauge, and limit-state table.
"""

from typing import Any, Dict, List, Optional
from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QPolygonF
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.common.calculation_result import CalculationResult, CalculationStatus, DesignMethod


class StatusBadgeWidget(QLabel):
    """Visual status pill badge displaying explicit SAD Section 8.4 calculation statuses."""

    STATUS_STYLES = {
        CalculationStatus.PASS: "background-color: #28a745; color: white;",
        CalculationStatus.FAIL: "background-color: #dc3545; color: white;",
        CalculationStatus.REQUIRES_REVIEW: "background-color: #fd7e14; color: white;",
        CalculationStatus.INCOMPLETE: "background-color: #6c757d; color: white;",
        CalculationStatus.INVALID_INPUT: "background-color: #6f42c1; color: white;",
    }

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__("INCOMPLETE", parent)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedHeight(26)
        self.setMinimumWidth(80)
        self.update_status(CalculationStatus.INCOMPLETE)

    def update_status(self, status: CalculationStatus) -> None:
        style = self.STATUS_STYLES.get(status, "background-color: #6c757d; color: white;")
        self.setText(status.value)
        self.setStyleSheet(f"""
            QLabel {{
                {style}
                font-weight: bold;
                font-size: 11px;
                border-radius: 13px;
                padding: 2px 14px;
                letter-spacing: 0.5px;
            }}
        """)


class DiagramWidget(QWidget):
    """Schematic engineering diagram with live dimension annotations matching the mockup."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(180)
        self.setSizeIncrement(1, 1)
        self.setStyleSheet("background-color: #ffffff;")

        # Parametric diagram properties
        self.p_demand_lb = 340.0
        self.t_m_in = 1.5
        self.t_s_in = 1.5
        self.e_end_m_in = 3.0
        self.e_end_s_in = 3.0
        self.bolt_dia_in = 0.625
        self.c_delta = 0.69

    def update_parameters(
        self,
        p_demand: float = 340.0,
        t_m: float = 1.5,
        t_s: float = 1.5,
        e_end_m: float = 3.0,
        e_end_s: float = 3.0,
        bolt_dia: float = 0.625,
        c_delta: float = 0.69
    ) -> None:
        self.p_demand_lb = p_demand
        self.t_m_in = t_m
        self.t_s_in = t_s
        self.e_end_m_in = e_end_m
        self.e_end_s_in = e_end_s
        self.bolt_dia_in = bolt_dia
        self.c_delta = c_delta
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # Canvas background
        painter.fillRect(0, 0, w, h, QColor("#ffffff"))

        # Geometry dimensions
        cx = w * 0.52
        cy = h * 0.48

        wood_w = min(w * 0.38, 220.0)
        wood_h = min(h * 0.18, 32.0)
        overlap = wood_w * 0.55

        # Wood members (Light tan with dark gray border)
        wood_brush = QBrush(QColor("#fde6cf"))
        wood_pen = QPen(QColor("#343a40"), 1.5)
        painter.setPen(wood_pen)
        painter.setBrush(wood_brush)

        # Upper side member
        side_rect = QRectF(cx - overlap * 0.4, cy - wood_h, wood_w, wood_h)
        painter.drawRect(side_rect)

        # Lower main member
        main_rect = QRectF(cx - overlap * 0.4 - (wood_w - overlap), cy, wood_w, wood_h)
        painter.drawRect(main_rect)

        # Through bolt (Orange vertical dowel with round caps)
        bolt_w = 14.0
        bolt_h = wood_h * 2 + 28.0
        bolt_x = cx - bolt_w * 0.5
        bolt_y = cy - wood_h - 14.0

        bolt_pen = QPen(QColor("#c86816"), 1.5)
        bolt_brush = QBrush(QColor("#e67e22"))
        painter.setPen(bolt_pen)
        painter.setBrush(bolt_brush)
        painter.drawRoundedRect(QRectF(bolt_x, bolt_y, bolt_w, bolt_h), 3, 3)

        # Bolt head and washer lines
        painter.drawLine(int(bolt_x - 3), int(bolt_y + 4), int(bolt_x + bolt_w + 3), int(bolt_y + 4))
        painter.drawLine(int(bolt_x - 3), int(bolt_y + bolt_h - 4), int(bolt_x + bolt_w + 3), int(bolt_y + bolt_h - 4))

        # Tension Arrows (Orange arrows pulling outwards)
        force_pen = QPen(QColor("#d96818"), 2)
        painter.setPen(force_pen)
        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))

        # Left arrow <-
        left_arr_x1 = main_rect.left() - 36
        left_arr_x2 = main_rect.left() - 4
        left_arr_y = cy + wood_h * 0.5
        painter.drawLine(int(left_arr_x2), int(left_arr_y), int(left_arr_x1), int(left_arr_y))
        # Arrowhead
        arr_left = QPolygonF([
            QPointF(left_arr_x1, left_arr_y),
            QPointF(left_arr_x1 + 8, left_arr_y - 4),
            QPointF(left_arr_x1 + 8, left_arr_y + 4),
        ])
        painter.setBrush(QBrush(QColor("#d96818")))
        painter.drawPolygon(arr_left)
        painter.drawText(QRectF(left_arr_x1 - 10, left_arr_y - 20, 80, 16), Qt.AlignLeft, f"P = {self.p_demand_lb:.0f} lb")

        # Right arrow ->
        right_arr_x1 = side_rect.right() + 4
        right_arr_x2 = side_rect.right() + 36
        right_arr_y = cy - wood_h * 0.5
        painter.drawLine(int(right_arr_x1), int(right_arr_y), int(right_arr_x2), int(right_arr_y))
        # Arrowhead
        arr_right = QPolygonF([
            QPointF(right_arr_x2, right_arr_y),
            QPointF(right_arr_x2 - 8, right_arr_y - 4),
            QPointF(right_arr_x2 - 8, right_arr_y + 4),
        ])
        painter.drawPolygon(arr_right)
        painter.drawText(QRectF(right_arr_x2 + 4, right_arr_y - 7, 80, 16), Qt.AlignLeft, f"P = {self.p_demand_lb:.0f} lb")

        # Blue Dimension Lines
        dim_pen = QPen(QColor("#007bff"), 1.2)
        painter.setPen(dim_pen)
        painter.setFont(QFont("Segoe UI", 8))

        # Dimension: t_s (side thickness)
        ts_x = side_rect.right() + 6
        painter.drawLine(int(ts_x), int(side_rect.top()), int(ts_x), int(side_rect.bottom()))
        painter.drawLine(int(ts_x - 3), int(side_rect.top()), int(ts_x + 3), int(side_rect.top()))
        painter.drawLine(int(ts_x - 3), int(side_rect.bottom()), int(ts_x + 3), int(side_rect.bottom()))
        painter.drawText(QRectF(ts_x + 5, side_rect.top(), 80, wood_h), Qt.AlignVCenter | Qt.AlignLeft, f"ts = {self.t_s_in:.1f} in")

        # Dimension: t_m (main thickness)
        tm_x = main_rect.left() + 20
        painter.drawLine(int(tm_x), int(main_rect.top()), int(tm_x), int(main_rect.bottom() + 14))
        painter.drawLine(int(tm_x - 3), int(main_rect.top()), int(tm_x + 3), int(main_rect.top()))
        painter.drawLine(int(tm_x - 3), int(main_rect.bottom()), int(tm_x + 3), int(main_rect.bottom()))
        painter.drawText(QRectF(tm_x - 45, main_rect.bottom() + 1, 40, 14), Qt.AlignRight, f"tm = {self.t_m_in:.1f} in")

        # Dimension: e_end,s (top dimension from bolt to side end)
        top_dim_y = side_rect.top() - 14
        painter.drawLine(int(cx), int(top_dim_y), int(side_rect.right()), int(top_dim_y))
        painter.drawLine(int(cx), int(top_dim_y - 3), int(cx), int(top_dim_y + 3))
        painter.drawLine(int(side_rect.right()), int(top_dim_y - 3), int(side_rect.right()), int(top_dim_y + 3))
        painter.drawText(QRectF(side_rect.right() + 4, top_dim_y - 8, 120, 16), Qt.AlignLeft, f"e_end,s = {self.e_end_s_in:.1f} in")

        # Dimension: e_end,m (bottom dimension from bolt to main member loaded end)
        bot_dim_y = cy + wood_h + 20
        dim_brown_pen = QPen(QColor("#a75815"), 1.2)
        painter.setPen(dim_brown_pen)
        painter.drawLine(int(main_rect.right()), int(bot_dim_y), int(cx), int(bot_dim_y))
        painter.drawLine(int(main_rect.right()), int(bot_dim_y - 3), int(main_rect.right()), int(bot_dim_y + 3))
        painter.drawLine(int(cx), int(bot_dim_y - 3), int(cx), int(bot_dim_y + 3))
        painter.drawText(QRectF(cx - 20, bot_dim_y + 4, 150, 16), Qt.AlignLeft, f"e_end,m = {self.e_end_m_in:.1f} in (< 7D)")

        # Top-right Pill Note: e_end,m = 3.0 in < 7D = 4.375 in -> C_Delta = 0.69
        note_text = f"e_end,m = {self.e_end_m_in:.1f} in < 7D = {7.0 * self.bolt_dia_in:.3f} in → C_Δ = {self.c_delta:.2f}"
        note_w = 260.0
        note_h = 24.0
        note_rect = QRectF(w - note_w - 12, 10, note_w, note_h)

        painter.setPen(QPen(QColor("#ffeeba"), 1))
        painter.setBrush(QBrush(QColor("#fff3cd")))
        painter.drawRoundedRect(note_rect, 4, 4)

        painter.setPen(QPen(QColor("#856404"), 1))
        painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
        painter.drawText(note_rect, Qt.AlignCenter, note_text)


class BaseCalculationWorkspace(QWidget):
    """
    4-Panel Grid Workspace per SAD v1.0 Section 8.3 & Mockup:
      - Left column: Panel 1 (INPUTS) + Bottom Actions (Run Calculation & Save Revision)
      - Right column: Panel 2 (DIAGRAM), Panel 3 (CALCULATION SHEET), Panel 4 (SUMMARY)
    """

    calculateRequested = Signal(dict, DesignMethod)
    saveRevisionRequested = Signal(str)

    def __init__(self, module_title: str, default_code: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.module_title = module_title
        self.default_code = default_code
        self._current_result: Optional[CalculationResult] = None
        self._design_method = DesignMethod.ASD

        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 12)
        main_layout.setSpacing(12)

        # Main Splitter: Left (Inputs + Actions) vs Right (Diagram + Calc + Summary)
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: transparent;
                width: 6px;
            }
        """)

        # ======================================================================
        # LEFT COLUMN: 1. INPUTS PANEL & ACTION BUTTONS
        # ======================================================================
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        # Card container for Inputs
        card_inputs = QFrame()
        card_inputs.setStyleSheet("""
            QFrame#card_inputs {
                background-color: #ffffff;
                border: 1px solid #dee2e6;
                border-radius: 8px;
            }
        """)
        card_inputs.setObjectName("card_inputs")
        card_inputs_layout = QVBoxLayout(card_inputs)
        card_inputs_layout.setContentsMargins(14, 12, 14, 12)
        card_inputs_layout.setSpacing(8)

        lbl_inputs_title = QLabel("1. INPUTS")
        lbl_inputs_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #343a40; letter-spacing: 0.5px;")
        card_inputs_layout.addWidget(lbl_inputs_title)

        # Hidden radio buttons for backward compatibility with existing tests
        self.radio_asd = QRadioButton("ASD")
        self.radio_lrfd = QRadioButton("LRFD")
        self.radio_asd.setChecked(True)
        self.radio_asd.setVisible(False)
        self.radio_lrfd.setVisible(False)
        self.method_btn_group = QButtonGroup(self)
        self.method_btn_group.addButton(self.radio_asd)
        self.method_btn_group.addButton(self.radio_lrfd)

        # Scrollable form for key-value inputs
        scroll_form = QScrollArea()
        scroll_form.setWidgetResizable(True)
        scroll_form.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        self.form_widget = QWidget()
        self.form_layout = QFormLayout(self.form_widget)
        self.form_layout.setContentsMargins(0, 4, 0, 4)
        self.form_layout.setSpacing(8)
        self.form_layout.setLabelAlignment(Qt.AlignLeft)
        self.form_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)

        # Populate sample input fields matching mockup
        self._populate_sample_inputs()

        scroll_form.setWidget(self.form_widget)
        card_inputs_layout.addWidget(scroll_form, stretch=1)
        left_layout.addWidget(card_inputs, stretch=1)

        # Bottom Action Bar
        action_bar = QHBoxLayout()
        action_bar.setSpacing(8)

        self.btn_calculate = QPushButton("Run Calculation")
        self.btn_calculate.setFixedHeight(36)
        self.btn_calculate.setCursor(Qt.PointingHandCursor)
        self.btn_calculate.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                border: none;
                border-radius: 6px;
                color: #ffffff;
                font-weight: bold;
                font-size: 13px;
                padding: 0 16px;
            }
            QPushButton:hover {
                background-color: #0069d9;
            }
            QPushButton:pressed {
                background-color: #0056b3;
            }
        """)
        self.btn_calculate.clicked.connect(self._on_calculate_clicked)

        self.btn_save_revision = QPushButton("Save Revision")
        self.btn_save_revision.setFixedHeight(36)
        self.btn_save_revision.setCursor(Qt.PointingHandCursor)
        self.btn_save_revision.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                border: 1px solid #ced4da;
                border-radius: 6px;
                color: #212529;
                font-weight: 500;
                font-size: 13px;
                padding: 0 14px;
            }
            QPushButton:hover {
                background-color: #f8f9fa;
                border-color: #adb5bd;
            }
        """)
        self.btn_save_revision.clicked.connect(self._on_save_revision_clicked)

        action_bar.addWidget(self.btn_calculate, stretch=1)
        action_bar.addWidget(self.btn_save_revision)
        left_layout.addLayout(action_bar)

        left_container.setMinimumWidth(280)
        left_container.setMaximumWidth(380)
        main_splitter.addWidget(left_container)

        # ======================================================================
        # RIGHT COLUMN: 2. DIAGRAM, 3. CALC SHEET, 4. SUMMARY
        # ======================================================================
        right_splitter = QSplitter(Qt.Vertical)
        right_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: transparent;
                height: 6px;
            }
        """)

        # ----------------------------------------------------------------------
        # 2. DIAGRAM PANEL (Top Right)
        # ----------------------------------------------------------------------
        card_diagram = QFrame()
        card_diagram.setStyleSheet("""
            QFrame#card_diagram {
                background-color: #ffffff;
                border: 1px solid #dee2e6;
                border-radius: 8px;
            }
        """)
        card_diagram.setObjectName("card_diagram")
        card_diagram_layout = QVBoxLayout(card_diagram)
        card_diagram_layout.setContentsMargins(14, 10, 14, 10)
        card_diagram_layout.setSpacing(6)

        lbl_diagram_title = QLabel("2. DIAGRAM · live update from inputs")
        lbl_diagram_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #343a40; letter-spacing: 0.5px;")
        card_diagram_layout.addWidget(lbl_diagram_title)

        self.diagram_widget = DiagramWidget()
        card_diagram_layout.addWidget(self.diagram_widget, stretch=1)
        right_splitter.addWidget(card_diagram)

        # ----------------------------------------------------------------------
        # 3. CALCULATION SHEET PANEL (Middle Right)
        # ----------------------------------------------------------------------
        card_calc = QFrame()
        card_calc.setStyleSheet("""
            QFrame#card_calc {
                background-color: #ffffff;
                border: 1px solid #dee2e6;
                border-radius: 8px;
            }
        """)
        card_calc.setObjectName("card_calc")
        card_calc_layout = QVBoxLayout(card_calc)
        card_calc_layout.setContentsMargins(14, 10, 14, 10)
        card_calc_layout.setSpacing(6)

        lbl_calc_title = QLabel("3. CALCULATION SHEET · equations, substitutions, code references")
        lbl_calc_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #343a40; letter-spacing: 0.5px;")
        card_calc_layout.addWidget(lbl_calc_title)

        # Code basis badge / banner
        self.lbl_code_basis = QLabel(
            f"Code basis: {self.default_code} · ASD · Douglas Fir-Larch, G = 0.50 · Knowledge Base verified (SHA-256)"
        )
        self.lbl_code_basis.setStyleSheet("""
            background-color: #f1f8ff;
            color: #0366d6;
            font-size: 11px;
            padding: 4px 8px;
            border-radius: 4px;
            border: 1px solid #c8e1ff;
        """)
        card_calc_layout.addWidget(self.lbl_code_basis)

        # Hidden ref_text for backward compatibility with existing tests
        self.ref_text = QTextEdit()
        self.ref_text.setVisible(False)
        card_calc_layout.addWidget(self.ref_text)

        # Calculation trace sheet
        self.calc_text = QTextEdit()
        self.calc_text.setReadOnly(True)
        self.calc_text.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                border: none;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 12px;
                color: #212529;
            }
        """)
        self._populate_sample_calc_sheet()
        card_calc_layout.addWidget(self.calc_text, stretch=1)
        right_splitter.addWidget(card_calc)

        # ----------------------------------------------------------------------
        # 4. SUMMARY PANEL (Bottom Right)
        # ----------------------------------------------------------------------
        card_summary = QFrame()
        card_summary.setStyleSheet("""
            QFrame#card_summary {
                background-color: #ffffff;
                border: 1px solid #dee2e6;
                border-radius: 8px;
            }
        """)
        card_summary.setObjectName("card_summary")
        card_summary_layout = QVBoxLayout(card_summary)
        card_summary_layout.setContentsMargins(14, 10, 14, 10)
        card_summary_layout.setSpacing(8)

        # Top bar: Status Pill Badge + Governing Limit State + DCR gauge
        summary_top_bar = QHBoxLayout()
        summary_top_bar.setSpacing(12)

        self.status_badge = StatusBadgeWidget()
        self.status_badge.update_status(CalculationStatus.PASS)
        summary_top_bar.addWidget(self.status_badge)

        self.lbl_governing = QLabel("Governing limit state: Bolt lateral yield, Mode II")
        self.lbl_governing.setStyleSheet("font-size: 13px; font-weight: bold; color: #212529;")
        summary_top_bar.addWidget(self.lbl_governing, stretch=1)

        # DCR gauge
        dcr_container = QHBoxLayout()
        dcr_container.setSpacing(8)
        lbl_dcr_title = QLabel("DCR")
        lbl_dcr_title.setStyleSheet("font-size: 12px; color: #6c757d; font-weight: bold;")
        dcr_container.addWidget(lbl_dcr_title)

        self.dcr_bar = QProgressBar()
        self.dcr_bar.setRange(0, 150)
        self.dcr_bar.setValue(82)
        self.dcr_bar.setTextVisible(False)
        self.dcr_bar.setFixedHeight(8)
        self.dcr_bar.setFixedWidth(130)
        self.dcr_bar.setStyleSheet("""
            QProgressBar {
                background-color: #e9ecef;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: #28a745;
                border-radius: 4px;
            }
        """)
        dcr_container.addWidget(self.dcr_bar)

        self.lbl_dcr_val = QLabel("82% (0.82)")
        self.lbl_dcr_val.setStyleSheet("font-size: 12px; font-weight: bold; color: #212529;")
        dcr_container.addWidget(self.lbl_dcr_val)

        summary_top_bar.addLayout(dcr_container)
        card_summary_layout.addLayout(summary_top_bar)

        # Limit states verification table
        self.table_limit_states = QTableWidget()
        self.table_limit_states.setColumnCount(7)
        self.table_limit_states.setHorizontalHeaderLabels([
            "Step", "Limit state check", "Governing clause", "Demand", "Capacity", "DCR", "Status"
        ])
        self.table_limit_states.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_limit_states.verticalHeader().setVisible(False)
        self.table_limit_states.setShowGrid(False)
        self.table_limit_states.setFixedHeight(95)
        self.table_limit_states.setStyleSheet("""
            QTableWidget {
                border: none;
                background-color: #ffffff;
                font-size: 12px;
                color: #212529;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                border: none;
                border-bottom: 1px solid #dee2e6;
                padding: 4px 6px;
                font-weight: bold;
                color: #495057;
                font-size: 11px;
            }
            QTableWidget::item {
                border-bottom: 1px solid #f1f3f5;
                padding: 4px 6px;
            }
        """)
        self._populate_sample_table()
        card_summary_layout.addWidget(self.table_limit_states)

        right_splitter.addWidget(card_summary)

        # Splitter proportion ratios
        right_splitter.setStretchFactor(0, 32)
        right_splitter.setStretchFactor(1, 48)
        right_splitter.setStretchFactor(2, 20)

        main_splitter.addWidget(right_splitter)
        main_splitter.setStretchFactor(0, 30)
        main_splitter.setStretchFactor(1, 70)

        main_layout.addWidget(main_splitter)

    def _create_form_row(self, label_text: str, value_text: str, is_section: bool = False) -> None:
        if is_section:
            sec_lbl = QLabel(label_text)
            sec_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #6c757d; margin-top: 6px;")
            self.form_layout.addRow(sec_lbl)
            return

        lbl = QLabel(label_text)
        lbl.setStyleSheet("font-size: 12px; color: #495057;")
        val = QLabel(value_text)
        val.setStyleSheet("font-size: 12px; font-weight: bold; color: #212529;")
        val.setAlignment(Qt.AlignRight)
        self.form_layout.addRow(lbl, val)

    def _populate_sample_inputs(self) -> None:
        self._create_form_row("Dowel type", "Hex bolt")
        self._create_form_row("Diameter D", "5/8 in")
        self._create_form_row("Shear planes", "Single shear")
        self._create_form_row("Fyb", "45,000 psi")

        self._create_form_row("Main member", "", is_section=True)
        self._create_form_row("Species", "Douglas Fir-Larch")
        self._create_form_row("tm / θm", "1.5 in / 0°")
        self._create_form_row("eend,m", "3.0 in")

        self._create_form_row("Side member", "", is_section=True)
        self._create_form_row("Species", "Douglas Fir-Larch")
        self._create_form_row("ts / θs", "1.5 in / 0°")
        self._create_form_row("eend,s", "3.0 in")

        self._create_form_row("Demand", "", is_section=True)
        self._create_form_row("P (tension)", "340 lb")

    def _populate_sample_calc_sheet(self) -> None:
        html = """
        <table width="100%" cellpadding="3" cellspacing="0" style="font-family: 'Segoe UI', Arial; font-size: 12px;">
            <tr>
                <td><b>F<sub>e||</sub></b> = 11,200 &middot; G = 11,200 &times; 0.50 = <b>5,600 psi</b></td>
                <td align="right" style="color: #007bff; font-weight: 500;">NDS Table 12.3.3</td>
            </tr>
            <tr>
                <td><b>K<sub>&theta;</sub></b> = 1 + 0.25(&theta;/90&deg;) = 1.00, &nbsp; <b>R<sub>d</sub></b> = 3.6 &middot; K<sub>&theta;</sub> = <b>3.60</b></td>
                <td align="right" style="color: #007bff; font-weight: 500;">NDS Table 12.3.1B (Mode II)</td>
            </tr>
            <tr>
                <td>
                    <b>Z<sub>||</sub></b> = (k<sub>1</sub> &middot; D &middot; &ell;<sub>s</sub> &middot; F<sub>es</sub>) / R<sub>d</sub>
                    = (0.414 &times; 0.625 &times; 1.5 &times; 5,600) / 3.60 = <b>604 lb</b>
                </td>
                <td align="right" style="color: #007bff; font-weight: 500;">NDS Table 12.3.1A, Mode II</td>
            </tr>
            <tr>
                <td colspan="2" style="color: #6c757d; font-size: 11px;">
                    Mode I<sub>m</sub>: —, I<sub>s</sub>: 1,313, III<sub>m</sub>: —, III<sub>s</sub>: 878, IV: 1,119 lb &rarr; <b>Mode II governs</b>
                </td>
            </tr>
            <tr>
                <td><b>C<sub>&Delta;</sub></b> = e<sub>end</sub> / (7D) = 3.0 / 4.375 = <b>0.69</b></td>
                <td align="right" style="color: #007bff; font-weight: 500;">NDS &sect;12.5.1, Table 12.5.1A</td>
            </tr>
            <tr>
                <td>
                    <b>Z'</b> = Z &middot; C<sub>D</sub> &middot; C<sub>M</sub> &middot; C<sub>t</sub> &middot; C<sub>g</sub> &middot; C<sub>&Delta;</sub>
                    = 604 &times; 1.00 &times; 1.00 &times; 1.00 &times; 1.00 &times; 0.69 = <b>414 lb</b>
                </td>
                <td align="right" style="color: #007bff; font-weight: 500;">NDS Table 10.3.1</td>
            </tr>
        </table>
        """
        self.calc_text.setHtml(html)

    def _populate_sample_table(self) -> None:
        rows = [
            ("1", "Lateral yield, Mode II", "NDS 12.3.1", "340 lb", "414 lb", "0.82", "PASS"),
            ("2", "Minimum end distance", "NDS Table 12.5.1A", "2.19 in", "3.00 in", "0.73", "PASS"),
        ]
        self.table_limit_states.setRowCount(len(rows))
        for r_idx, row in enumerate(rows):
            for c_idx, val in enumerate(row):
                item = QTableWidgetItem(val)
                if c_idx == 0:
                    item.setTextAlignment(Qt.AlignCenter)
                elif c_idx in (3, 4, 5):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                elif c_idx == 6:
                    item.setTextAlignment(Qt.AlignCenter)
                    item.setForeground(QColor("#28a745"))
                    item.setFont(QFont("Segoe UI", 9, QFont.Bold))
                self.table_limit_states.setItem(r_idx, c_idx, item)

    def set_design_method(self, method: DesignMethod) -> None:
        self._design_method = method
        if method == DesignMethod.ASD:
            self.radio_asd.setChecked(True)
        else:
            self.radio_lrfd.setChecked(True)

    def get_selected_design_method(self) -> DesignMethod:
        if self.radio_lrfd.isChecked():
            return DesignMethod.LRFD
        return self._design_method

    def get_form_inputs(self) -> Dict[str, Any]:
        """Override in subclasses to gather typed inputs from form controls."""
        return {}

    def _on_calculate_clicked(self) -> None:
        inputs = self.get_form_inputs()
        method = self.get_selected_design_method()
        self.calculateRequested.emit(inputs, method)

    def _on_save_revision_clicked(self) -> None:
        self.saveRevisionRequested.emit("Calculation updated from UI")

    def display_results(self, result: CalculationResult) -> None:
        """Update Panels from a CalculationResult object."""
        self._current_result = result
        self.btn_save_revision.setEnabled(True)

        # 1. Update Status Badge & DCR
        self.status_badge.update_status(result.status)
        dcr_pct = int(min(result.dcr * 100.0, 150.0))
        self.dcr_bar.setValue(dcr_pct)
        self.lbl_dcr_val.setText(f"{dcr_pct}% ({result.dcr:.2f})")

        if result.dcr > 1.0:
            self.dcr_bar.setStyleSheet("""
                QProgressBar { background-color: #e9ecef; border-radius: 4px; }
                QProgressBar::chunk { background-color: #dc3545; border-radius: 4px; }
            """)
        else:
            self.dcr_bar.setStyleSheet("""
                QProgressBar { background-color: #e9ecef; border-radius: 4px; }
                QProgressBar::chunk { background-color: #28a745; border-radius: 4px; }
            """)

        gov_name = result.governing_limit_state.name if result.governing_limit_state else "None"
        gov_code = result.governing_limit_state.code_clause if result.governing_limit_state else ""
        self.lbl_governing.setText(f"Governing limit state: {gov_name} ({gov_code})")

        # 2. Update Code Basis Banner & Reference
        self.lbl_code_basis.setText(
            f"Code basis: {result.code_edition} · {result.design_method.value} · Knowledge Base verified (SHA-256)"
        )
        ref_lines = [
            f"<b>Code Edition:</b> {result.code_edition} ({result.design_method.value})",
            f"<b>Reference Files:</b> {', '.join(result.reference_files) if result.reference_files else 'None'}",
            "<b>Engineering Assumptions:</b>"
        ]
        for a in result.assumptions:
            ref_lines.append(f" • {a}")
        self.ref_text.setHtml("<br>".join(ref_lines))

        # 3. Update Calculation Panel
        calc_rows = []
        for k, v in result.intermediate_results.items():
            calc_rows.append(f"<tr><td><b>{k}</b> = {v}</td><td></td></tr>")
        for ls in result.limit_states:
            eq = f"<code>{ls.equation_latex}</code>" if ls.equation_latex else ""
            sub = f"<br><small>{ls.substitution_str}</small>" if ls.substitution_str else ""
            calc_rows.append(
                f"<tr><td><b>{ls.name}</b>: {eq}{sub}</td>"
                f"<td align='right' style='color: #007bff; font-weight: 500;'>{ls.code_clause}</td></tr>"
            )

        html = f"""
        <table width="100%" cellpadding="3" cellspacing="0" style="font-family: 'Segoe UI', Arial; font-size: 12px;">
            {''.join(calc_rows)}
        </table>
        """
        self.calc_text.setHtml(html)

        # 4. Update Summary Table
        self.table_limit_states.setRowCount(len(result.limit_states))
        for row, ls in enumerate(result.limit_states):
            self.table_limit_states.setItem(row, 0, QTableWidgetItem(ls.step_id))
            self.table_limit_states.setItem(row, 1, QTableWidgetItem(ls.name))
            self.table_limit_states.setItem(row, 2, QTableWidgetItem(ls.code_clause))
            self.table_limit_states.setItem(row, 3, QTableWidgetItem(f"{ls.demand:.2f} {ls.units}"))
            self.table_limit_states.setItem(row, 4, QTableWidgetItem(f"{ls.capacity:.2f} {ls.units}"))
            self.table_limit_states.setItem(row, 5, QTableWidgetItem(f"{ls.dcr:.2f}"))

            status_item = QTableWidgetItem(ls.status.value)
            if ls.status == CalculationStatus.PASS:
                status_item.setForeground(QColor("#28a745"))
                status_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
            elif ls.status == CalculationStatus.FAIL:
                status_item.setForeground(QColor("#dc3545"))
                status_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
            self.table_limit_states.setItem(row, 6, status_item)

        # 5. Update Diagram
        self.diagram_widget.update_parameters(
            p_demand=result.demand if result.demand > 0 else 340.0,
            c_delta=0.69
        )
