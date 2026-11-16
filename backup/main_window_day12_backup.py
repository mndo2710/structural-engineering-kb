"""Main Desktop Window per SAD v1.0 Section 8.1, 8.2 & Mockup Architecture.

Features:
- Header bar: Hamburger menu button (☰), dynamic calculation title, segmented ASD/LRFD toggle.
- Expandable/Collapsible sidebar (232px expanded, 48px rail collapsed) with smooth animation.
- Grouped calculations ("Roof framing", "Level 2") with DCR badges and status indicators.
- Rail mode with numeric badge icons ("01", "02", "03!", "04", "05") and rich hover tooltips.
- Add Calculation modal dialog integration.
- 4-Panel Calculation Workspace integration for structural engineering modules.
"""

from typing import Any, Dict, List, Optional
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Signal
from PySide6.QtGui import QColor, QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from app.services.knowledge_base_service import KnowledgeBaseService
from app.services.project_service import ProjectService
from core.common.calculation_result import DesignMethod
from gui.dialogs.add_calculation_dialog import AddCalculationDialog
from gui.widgets.base_workspace import BaseCalculationWorkspace


class CalcItemWidget(QWidget):
    """Custom list row widget for calculations in expanded sidebar."""

    def __init__(self, calc_id: str, name: str, dcr_text: str, status_color: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        self.lbl_name = QLabel(name)
        self.lbl_name.setStyleSheet("color: #ced4da; font-size: 12px; background: transparent;")
        layout.addWidget(self.lbl_name, stretch=1)

        self.lbl_dcr = QLabel(dcr_text)
        self.lbl_dcr.setStyleSheet(f"color: {status_color}; font-size: 11px; font-weight: bold; background: transparent;")
        self.lbl_dcr.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.lbl_dcr)


class MainWindow(QMainWindow):
    """Main desktop application window with collapsible sidebar and modern 4-panel workspace."""

    def __init__(
        self,
        project_service: Optional[ProjectService] = None,
        kb_service: Optional[KnowledgeBaseService] = None,
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.project_service = project_service or ProjectService()
        self.kb_service = kb_service or KnowledgeBaseService()

        self.setWindowTitle("Structural Engineering Calculation Application — US Customary (V1.0)")
        self.resize(1320, 840)
        self.setMinimumSize(1024, 680)

        self.is_sidebar_collapsed = False
        self._current_design_method = DesignMethod.ASD

        # Calculation entries list metadata
        self.calculations: List[Dict[str, Any]] = [
            {
                "id": "C-01",
                "name": "C-01 Ledger to stud wall",
                "group": "Roof framing",
                "dcr_text": "0.62",
                "status_color": "#28a745",
                "badge": "01",
                "page_index": 2,
                "title": "C-01 · Ledger to stud wall — Wood Connections, Lateral (NDS 2018)",
                "tooltip": "C-01 · Ledger to stud wall\nWood lateral (NDS) · DCR 0.62 · PASS",
            },
            {
                "id": "C-02",
                "name": "C-02 Truss heel bolt",
                "group": "Roof framing",
                "dcr_text": "0.82",
                "status_color": "#28a745",
                "badge": "02",
                "page_index": 3,
                "title": "C-02 · Truss heel bolt — Wood Connections, Lateral (NDS 2018)",
                "tooltip": "C-02 · Truss heel bolt\nWood lateral (NDS) · DCR 0.82 · PASS",
            },
            {
                "id": "C-03",
                "name": "C-03 Beam seat (AISC)",
                "group": "Level 2",
                "dcr_text": "1.08 FAIL",
                "status_color": "#dc3545",
                "badge": "03!",
                "page_index": 4,
                "title": "C-03 · Beam seat (AISC) — Steel Connections (AISC 360-22)",
                "tooltip": "C-03 · Beam seat (AISC)\nSteel Connections · DCR 1.08 · FAIL",
            },
            {
                "id": "C-04",
                "name": "C-04 Anchor to CMU",
                "group": "Level 2",
                "dcr_text": "Incomplete",
                "status_color": "#adb5bd",
                "badge": "04",
                "page_index": 5,
                "title": "C-04 · Anchor to CMU — Concrete & CMU Anchorage (ACI 318 / TMS 402)",
                "tooltip": "C-04 · Anchor to CMU\nAnchorage (TMS 402) · Incomplete",
            },
            {
                "id": "C-05",
                "name": "C-05 Wind C&C (ASCE 7)",
                "group": "Level 2",
                "dcr_text": "OK",
                "status_color": "#28a745",
                "badge": "05",
                "page_index": 2,
                "title": "C-05 · Wind C&C (ASCE 7) — Components & Cladding (ASCE 7-22)",
                "tooltip": "C-05 · Wind C&C (ASCE 7)\nWind C&C (ASCE 7-22) · OK",
            },
        ]

        self._setup_ui()
        self._setup_status_bar()

    def _setup_ui(self) -> None:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ----------------------------------------------------------------------
        # SIDEBAR (Left Column, collapsible 232px <-> 48px)
        # ----------------------------------------------------------------------
        self.sidebar_frame = QFrame()
        self.sidebar_frame.setStyleSheet("background-color: #1e2328; color: #ced4da;")
        self.sidebar_frame.setFixedWidth(232)

        sidebar_main_layout = QVBoxLayout(self.sidebar_frame)
        sidebar_main_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_main_layout.setSpacing(0)

        # Container for Expanded View
        self.sidebar_expanded_widget = QWidget()
        exp_layout = QVBoxLayout(self.sidebar_expanded_widget)
        exp_layout.setContentsMargins(12, 12, 12, 12)
        exp_layout.setSpacing(10)

        # App Logo & Subtitle
        logo_box = QVBoxLayout()
        logo_box.setSpacing(2)
        lbl_app_logo = QLabel("STRUCTURAL APP")
        lbl_app_logo.setStyleSheet("font-size: 13px; font-weight: bold; color: #17a2b8; letter-spacing: 0.5px;")
        lbl_app_sub = QLabel("US Engineering V1.0")
        lbl_app_sub.setStyleSheet("font-size: 11px; color: #8e9aa8;")
        logo_box.addWidget(lbl_app_logo)
        logo_box.addWidget(lbl_app_sub)
        exp_layout.addLayout(logo_box)

        # Navigation List (Dashboard, Projects, Reports, Settings)
        self.nav_list = QListWidget()
        self.nav_list.setFixedHeight(130)
        self.nav_list.setFocusPolicy(Qt.NoFocus)
        self.nav_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.nav_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.nav_list.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
                color: #ced4da;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 6px 8px;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #343a40;
                color: #ffffff;
                font-weight: bold;
            }
            QListWidget::item:hover:!selected {
                background-color: #2b3035;
            }
        """)

        nav_items = [
            ("📊  Dashboard", 0),
            ("📁  Projects", 1),
            ("📑  Reports (PDF/XLSX)", 6),
            ("⚙️  Settings", 7),
        ]
        for label, p_idx in nav_items:
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, p_idx)
            self.nav_list.addItem(item)

        self.nav_list.currentRowChanged.connect(self._on_top_nav_changed)
        exp_layout.addWidget(self.nav_list)

        # Subtle divider
        div_sidebar = QFrame()
        div_sidebar.setFrameShape(QFrame.HLine)
        div_sidebar.setStyleSheet("color: #2c323b;")
        exp_layout.addWidget(div_sidebar)

        # Project Label & Name
        lbl_proj_header = QLabel("PROJECT")
        lbl_proj_header.setStyleSheet("font-size: 10px; font-weight: bold; color: #6c757d; letter-spacing: 0.5px;")
        exp_layout.addWidget(lbl_proj_header)

        self.lbl_project_name = QLabel("Smith Residence")
        self.lbl_project_name.setStyleSheet("font-size: 13px; font-weight: bold; color: #ffffff; margin-bottom: 2px;")
        exp_layout.addWidget(self.lbl_project_name)

        # + Add Calculation Button (Full Width, Blue)
        self.btn_add_calc = QPushButton("+ Add Calculation")
        self.btn_add_calc.setFixedHeight(34)
        self.btn_add_calc.setCursor(Qt.PointingHandCursor)
        self.btn_add_calc.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                border: none;
                border-radius: 6px;
                color: #ffffff;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #0069d9;
            }
            QPushButton:pressed {
                background-color: #0056b3;
            }
        """)
        self.btn_add_calc.clicked.connect(self._on_add_calculation_clicked)
        exp_layout.addWidget(self.btn_add_calc)

        # Calculation List Grouped by Sections
        self.calc_list = QListWidget()
        self.calc_list.setFocusPolicy(Qt.NoFocus)
        self.calc_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.calc_list.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
                color: #ced4da;
            }
            QListWidget::item {
                border-radius: 4px;
                padding: 1px 0px;
            }
            QListWidget::item:selected {
                background-color: #2c3542;
                border-left: 3px solid #007bff;
            }
            QListWidget::item:hover:!selected {
                background-color: #262c33;
            }
        """)
        self.calc_list.currentRowChanged.connect(self._on_calc_selected)
        exp_layout.addWidget(self.calc_list, stretch=1)

        # Bottom Hint Text (Italic Gray)
        lbl_drag_hint = QLabel("Drag to reorder. Order reflects in reports.")
        lbl_drag_hint.setStyleSheet("font-size: 10px; color: #6c757d; font-style: italic;")
        lbl_drag_hint.setWordWrap(True)
        exp_layout.addWidget(lbl_drag_hint)

        sidebar_main_layout.addWidget(self.sidebar_expanded_widget)

        # Container for Collapsed Rail View (48px)
        self.sidebar_collapsed_widget = QWidget()
        self.sidebar_collapsed_widget.setVisible(False)
        rail_layout = QVBoxLayout(self.sidebar_collapsed_widget)
        rail_layout.setContentsMargins(6, 10, 6, 10)
        rail_layout.setSpacing(10)
        rail_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        # Collapsed Nav Icons
        self.btn_rail_hamburger = QPushButton("☰")
        self.btn_rail_hamburger.setFixedSize(36, 36)
        self.btn_rail_hamburger.setCursor(Qt.PointingHandCursor)
        self.btn_rail_hamburger.setStyleSheet("background: transparent; border: none; color: white; font-size: 16px;")
        self.btn_rail_hamburger.clicked.connect(self.toggle_sidebar)
        rail_layout.addWidget(self.btn_rail_hamburger)

        rail_icons = [
            ("📊", 0, "Dashboard"),
            ("📁", 1, "Projects"),
            ("📑", 6, "Reports"),
            ("⚙️", 7, "Settings"),
        ]
        for icon_char, p_idx, tip in rail_icons:
            btn_icon = QPushButton(icon_char)
            btn_icon.setFixedSize(36, 32)
            btn_icon.setToolTip(tip)
            btn_icon.setCursor(Qt.PointingHandCursor)
            btn_icon.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    color: #ced4da;
                    font-size: 15px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #343a40;
                    color: white;
                }
            """)
            btn_icon.clicked.connect(lambda checked=False, idx=p_idx: self._switch_to_page(idx))
            rail_layout.addWidget(btn_icon)

        # Blue square "+" FAB button
        self.btn_rail_add = QPushButton("+")
        self.btn_rail_add.setFixedSize(34, 34)
        self.btn_rail_add.setToolTip("Add Calculation")
        self.btn_rail_add.setCursor(Qt.PointingHandCursor)
        self.btn_rail_add.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                border: none;
                border-radius: 6px;
                color: #ffffff;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0069d9;
            }
        """)
        self.btn_rail_add.clicked.connect(self._on_add_calculation_clicked)
        rail_layout.addWidget(self.btn_rail_add)

        # Divider in rail
        div_rail = QFrame()
        div_rail.setFrameShape(QFrame.HLine)
        div_rail.setStyleSheet("color: #2c323b;")
        rail_layout.addWidget(div_rail)

        # Collapsed Calc Badges Container
        self.rail_badge_layout = QVBoxLayout()
        self.rail_badge_layout.setSpacing(8)
        rail_layout.addLayout(self.rail_badge_layout)
        rail_layout.addStretch()

        sidebar_main_layout.addWidget(self.sidebar_collapsed_widget)
        root_layout.addWidget(self.sidebar_frame)

        # ----------------------------------------------------------------------
        # RIGHT AREA: Top Header Bar + Stacked Module Workspaces
        # ----------------------------------------------------------------------
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Top Header Bar
        header_bar = QFrame()
        header_bar.setFixedHeight(50)
        header_bar.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-bottom: 1px solid #dee2e6;
            }
        """)
        header_layout = QHBoxLayout(header_bar)
        header_layout.setContentsMargins(12, 0, 16, 0)
        header_layout.setSpacing(12)

        # Hamburger Button
        self.btn_hamburger = QPushButton("☰")
        self.btn_hamburger.setFixedSize(32, 32)
        self.btn_hamburger.setCursor(Qt.PointingHandCursor)
        self.btn_hamburger.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 18px;
                color: #212529;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
        """)
        self.btn_hamburger.clicked.connect(self.toggle_sidebar)
        header_layout.addWidget(self.btn_hamburger)

        # Calculation Title Label (Center/Left)
        self.lbl_calc_title = QLabel("C-02 · Truss heel bolt — Wood Connections, Lateral (NDS 2018)")
        self.lbl_calc_title.setStyleSheet("font-size: 14px; font-weight: 600; color: #212529;")
        header_layout.addWidget(self.lbl_calc_title, stretch=1)

        # Segmented ASD / LRFD Toggle Buttons (Right)
        segmented_container = QFrame()
        segmented_container.setFixedHeight(30)
        segmented_container.setStyleSheet("""
            QFrame {
                background-color: #e9ecef;
                border-radius: 15px;
                padding: 2px;
            }
        """)
        segmented_layout = QHBoxLayout(segmented_container)
        segmented_layout.setContentsMargins(2, 2, 2, 2)
        segmented_layout.setSpacing(2)

        self.btn_asd = QPushButton("ASD")
        self.btn_asd.setFixedSize(54, 26)
        self.btn_asd.setCursor(Qt.PointingHandCursor)
        self.btn_asd.clicked.connect(lambda: self.set_active_design_method(DesignMethod.ASD))

        self.btn_lrfd = QPushButton("LRFD")
        self.btn_lrfd.setFixedSize(54, 26)
        self.btn_lrfd.setCursor(Qt.PointingHandCursor)
        self.btn_lrfd.clicked.connect(lambda: self.set_active_design_method(DesignMethod.LRFD))

        segmented_layout.addWidget(self.btn_asd)
        segmented_layout.addWidget(self.btn_lrfd)
        header_layout.addWidget(segmented_container)

        right_layout.addWidget(header_bar)

        # ----------------------------------------------------------------------
        # Stacked Pages
        # ----------------------------------------------------------------------
        self.stacked_pages = QStackedWidget()

        # Page 0: Dashboard Placeholder
        self.page_dashboard = self._create_placeholder_page("Application Dashboard", "Project summary, recent calculations, and database status.")
        self.stacked_pages.addWidget(self.page_dashboard)

        # Page 1: Projects Management Placeholder
        self.page_projects = self._create_placeholder_page("Projects Management", "Create, open, archive, and manage engineering projects.")
        self.stacked_pages.addWidget(self.page_projects)

        # Page 2: C&C Loads Workspace (Base 4-Panel)
        self.page_cc = BaseCalculationWorkspace(module_title="Components & Cladding Loads", default_code="ASCE 7-22")
        self.stacked_pages.addWidget(self.page_cc)

        # Page 3: Wood Connections Workspace (Featured in Mockup)
        self.page_wood = BaseCalculationWorkspace(module_title="Wood Connections & Lateral", default_code="NDS 2018 / NDS 2024")
        self.stacked_pages.addWidget(self.page_wood)

        # Page 4: Steel Connections Workspace
        self.page_steel = BaseCalculationWorkspace(module_title="Steel Connections", default_code="AISC 360-22")
        self.stacked_pages.addWidget(self.page_steel)

        # Page 5: Concrete & CMU Anchorage Workspace
        self.page_concrete = BaseCalculationWorkspace(module_title="Concrete & CMU Anchorage", default_code="ACI 318-19 / TMS 402-22")
        self.stacked_pages.addWidget(self.page_concrete)

        # Page 6: Reports Export Placeholder
        self.page_reports = self._create_placeholder_page("Deliverable Reports", "Generate 17-col Arial 10pt Excel sheets and 12-section PDF reports.")
        self.stacked_pages.addWidget(self.page_reports)

        # Page 7: Settings & Cloud Sync Placeholder
        self.page_settings = self._create_placeholder_page("Settings & Cloud Sync", "Google Drive sync, unit system preferences, and reference manifest audit.")
        self.stacked_pages.addWidget(self.page_settings)

        right_layout.addWidget(self.stacked_pages, stretch=1)
        root_layout.addWidget(right_container, stretch=1)

        # Populate calculations in sidebar
        self._populate_calculations()
        self._update_segmented_toggle()

        # Select C-02 (Truss heel bolt) by default
        self.select_calculation("C-02")

    def _setup_status_bar(self) -> None:
        bar = QStatusBar(self)
        self.setStatusBar(bar)

        self.lbl_status_project = QLabel("Project: Smith Residence")
        self.lbl_status_kb = QLabel("Knowledge Base: 66 Tables / 26 Procedures (SHA-256 Verified)")
        self.lbl_status_engine = QLabel("Calculation Engine: Deterministic Python (Offline Ready)")

        bar.addWidget(self.lbl_status_project, stretch=1)
        bar.addWidget(self.lbl_status_kb, stretch=1)
        bar.addWidget(self.lbl_status_engine, stretch=1)

    def _create_placeholder_page(self, title: str, subtitle: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)

        h1 = QLabel(title)
        h1.setStyleSheet("font-size: 20px; font-weight: bold; color: #333;")
        h2 = QLabel(subtitle)
        h2.setStyleSheet("font-size: 14px; color: #666; margin-top: 6px;")

        layout.addWidget(h1, alignment=Qt.AlignCenter)
        layout.addWidget(h2, alignment=Qt.AlignCenter)
        return page

    def _populate_calculations(self) -> None:
        self.calc_list.clear()

        # Group items
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for c in self.calculations:
            g = c.get("group", "General")
            groups.setdefault(g, []).append(c)

        # Clear rail badge layout
        while self.rail_badge_layout.count() > 0:
            item = self.rail_badge_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for group_name, items in groups.items():
            # Add header item
            header_item = QListWidgetItem(group_name)
            header_item.setFlags(Qt.NoItemFlags)
            header_item.setForeground(QColor("#6c757d"))
            font = QFont("Segoe UI", 9, QFont.Bold)
            header_item.setFont(font)
            self.calc_list.addItem(header_item)

            for calc in items:
                # Expanded item
                list_item = QListWidgetItem()
                list_item.setSizeHint(CalcItemWidget(calc["id"], calc["name"], calc["dcr_text"], calc["status_color"]).sizeHint())
                list_item.setData(Qt.UserRole, calc["id"])
                self.calc_list.addItem(list_item)
                item_widget = CalcItemWidget(calc["id"], calc["name"], calc["dcr_text"], calc["status_color"])
                self.calc_list.setItemWidget(list_item, item_widget)

                # Collapsed Rail Badge
                btn_badge = QPushButton(calc["badge"])
                btn_badge.setFixedSize(34, 30)
                btn_badge.setToolTip(calc["tooltip"])
                btn_badge.setCursor(Qt.PointingHandCursor)
                btn_badge.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        border: 1px solid #343a40;
                        border-bottom: 3px solid {calc['status_color']};
                        border-radius: 4px;
                        color: #ced4da;
                        font-size: 11px;
                        font-weight: bold;
                    }}
                    QPushButton:hover {{
                        background-color: #2b3035;
                        color: white;
                    }}
                """)
                btn_badge.clicked.connect(lambda checked=False, cid=calc["id"]: self.select_calculation(cid))
                self.rail_badge_layout.addWidget(btn_badge)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        active_id = getattr(self, "_active_calc_id", "C-02") or "C-02"
        self.select_calculation(active_id)

    def select_calculation(self, calc_id: str) -> None:
        self._active_calc_id = calc_id
        self.nav_list.blockSignals(True)
        self.nav_list.setCurrentRow(-1)
        self.nav_list.blockSignals(False)

        for idx in range(self.calc_list.count()):
            item = self.calc_list.item(idx)
            if item and item.data(Qt.UserRole) == calc_id:
                self.calc_list.blockSignals(True)
                self.calc_list.setCurrentRow(idx)
                self.calc_list.blockSignals(False)
                self._activate_calculation(calc_id)
                break

    def _activate_calculation(self, calc_id: str) -> None:
        found: Optional[Dict[str, Any]] = None
        for c in self.calculations:
            if c["id"] == calc_id:
                found = c
                break

        if found:
            self.lbl_calc_title.setText(found["title"])
            self.stacked_pages.setCurrentIndex(found["page_index"])
            # Deselect top nav list
            self.nav_list.blockSignals(True)
            self.nav_list.setCurrentRow(-1)
            self.nav_list.blockSignals(False)

    def _on_calc_selected(self, row: int) -> None:
        item = self.calc_list.item(row)
        if not item or not item.data(Qt.UserRole):
            return
        self._activate_calculation(item.data(Qt.UserRole))

    def _on_top_nav_changed(self, row: int) -> None:
        if row < 0:
            return
        self._active_calc_id = ""
        item = self.nav_list.item(row)
        if item:
            p_idx = item.data(Qt.UserRole)
            self._switch_to_page(p_idx)
            # Deselect calc list
            self.calc_list.blockSignals(True)
            self.calc_list.setCurrentRow(-1)
            self.calc_list.blockSignals(False)

    def _switch_to_page(self, index: int) -> None:
        if 0 <= index < self.stacked_pages.count():
            self.stacked_pages.setCurrentIndex(index)
            # Update title
            titles = {
                0: "Dashboard — Project Overview & Database Status",
                1: "Projects — Smith Residence",
                6: "Reports — Plan Check Calculation Packages (PDF / XLSX)",
                7: "Settings — US Engineering Conventions & Cloud Sync",
            }
            if index in titles:
                self.lbl_calc_title.setText(titles[index])

    def toggle_sidebar(self) -> None:
        """Smoothly toggle sidebar between expanded (232px) and collapsed rail (48px)."""
        self.is_sidebar_collapsed = not self.is_sidebar_collapsed
        target_width = 48 if self.is_sidebar_collapsed else 232

        self.sidebar_expanded_widget.setVisible(not self.is_sidebar_collapsed)
        self.sidebar_collapsed_widget.setVisible(self.is_sidebar_collapsed)

        self.anim = QPropertyAnimation(self.sidebar_frame, b"maximumWidth")
        self.anim.setDuration(120)
        self.anim.setEasingCurve(QEasingCurve.InOutQuad)
        self.anim.setStartValue(self.sidebar_frame.width())
        self.anim.setEndValue(target_width)

        self.anim_min = QPropertyAnimation(self.sidebar_frame, b"minimumWidth")
        self.anim_min.setDuration(120)
        self.anim_min.setEasingCurve(QEasingCurve.InOutQuad)
        self.anim_min.setStartValue(self.sidebar_frame.width())
        self.anim_min.setEndValue(target_width)

        self.anim.start()
        self.anim_min.start()

    def set_active_design_method(self, method: DesignMethod) -> None:
        """Switch design method (ASD vs LRFD) and propagate to active workspace."""
        self._current_design_method = method
        self._update_segmented_toggle()

        # Update currently active workspace if applicable
        current_widget = self.stacked_pages.currentWidget()
        if isinstance(current_widget, BaseCalculationWorkspace):
            current_widget.set_design_method(method)

    def _update_segmented_toggle(self) -> None:
        if self._current_design_method == DesignMethod.ASD:
            self.btn_asd.setStyleSheet("""
                QPushButton {
                    background-color: #1e2328;
                    color: #ffffff;
                    border: none;
                    border-radius: 13px;
                    font-size: 11px;
                    font-weight: bold;
                }
            """)
            self.btn_lrfd.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #495057;
                    border: none;
                    border-radius: 13px;
                    font-size: 11px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    color: #1e2328;
                }
            """)
        else:
            self.btn_lrfd.setStyleSheet("""
                QPushButton {
                    background-color: #1e2328;
                    color: #ffffff;
                    border: none;
                    border-radius: 13px;
                    font-size: 11px;
                    font-weight: bold;
                }
            """)
            self.btn_asd.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #495057;
                    border: none;
                    border-radius: 13px;
                    font-size: 11px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    color: #1e2328;
                }
            """)

    def _on_add_calculation_clicked(self) -> None:
        """Open Add Calculation Dialog and append created calculation."""
        dialog = AddCalculationDialog(self)
        if dialog.exec() == AddCalculationDialog.Accepted:
            data = dialog.get_calculation_data()
            cid = f"C-{len(self.calculations) + 1:02d}"
            name = f"{cid} · {data['name'].split('·')[-1].strip()}"
            new_calc = {
                "id": cid,
                "name": name,
                "group": data.get("group", "General"),
                "dcr_text": "Incomplete",
                "status_color": "#adb5bd",
                "badge": f"{len(self.calculations) + 1:02d}",
                "page_index": 3 if "wood" in data["template_id"] else 2,
                "title": f"{cid} · {data['name']} ({data['category']})",
                "tooltip": f"{cid} · {data['name']}\n{data['category']} · Incomplete",
            }
            self.calculations.append(new_calc)
            self._populate_calculations()
            self.select_calculation(cid)


def run_app() -> None:
    """Launch the main desktop GUI application."""
    import sys
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
