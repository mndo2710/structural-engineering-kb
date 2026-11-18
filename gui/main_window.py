"""Main Desktop Window per SAD v1.1 Section 8 (WP-5 & WP-6).

Features:
- Header bar: Hamburger menu button (☰), dynamic calculation title, segmented ASD/LRFD toggle.
- Expandable/Collapsible sidebar (232px expanded, 48px rail collapsed) with 120ms animation.
- Persistent grouped calculation items backed by ProjectService & SQLite Schema v2.
- Drag-to-reorder and right-click context menu (Rename, Duplicate, Move to Group, Delete).
- Add Calculation modal dialog wired to ModuleRegistry & ProjectService.add_item().
- Schema-driven 4-Panel WorkspaceHost bound to pure-Python WorkspaceController.
"""

import importlib
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QSize, Signal
from PySide6.QtGui import QColor, QFont, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from app.controllers import WorkspaceController
from app.models import CalculationStatus, DesignMethod, WorkspaceViewModel
from app.registry import get_module_registry
from app.services.calculation_service import CalculationService
from app.services.history_service import HistoryService
from app.services.knowledge_base_service import KnowledgeBaseService
from app.services.project_service import ProjectService
from app.services.report_service import ReportService
from gui.dialogs.add_calculation_dialog import AddCalculationDialog
from gui.widgets.base_workspace import BaseCalculationWorkspace
from gui.widgets.workspace_host import WorkspaceHost


_ICONS_DIR = Path(__file__).resolve().parent / "assets" / "icons"


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


class SidebarCalcListWidget(QListWidget):
    """QListWidget supporting internal drag-and-drop reordering across group headers."""

    itemDroppedOrderChanged = Signal(str, object, int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)

    def dropEvent(self, event) -> None:
        current = self.currentItem()
        moved_calc_id = current.data(Qt.UserRole) if current else None
        super().dropEvent(event)
        if not moved_calc_id:
            return

        # Determine target group and 0-based index within that group
        current_group_id: Optional[str] = None
        index_in_group = 0
        for row in range(self.count()):
            it = self.item(row)
            if it is None:
                continue
            role_id = it.data(Qt.UserRole)
            if not role_id:
                current_group_id = it.data(Qt.UserRole + 1)
                index_in_group = 0
                continue
            if role_id == moved_calc_id:
                self.itemDroppedOrderChanged.emit(str(moved_calc_id), current_group_id, index_in_group)
                return
            index_in_group += 1


class MainWindow(QMainWindow):
    """Main desktop application window with collapsible sidebar and 4-panel WorkspaceHost."""

    def __init__(
        self,
        project_service: Optional[ProjectService] = None,
        kb_service: Optional[KnowledgeBaseService] = None,
        workspace_controller: Optional[WorkspaceController] = None,
        cloud_sync_service: Any = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.kb_service = kb_service or KnowledgeBaseService()
        self.registry = get_module_registry()
        self.project_service = project_service or ProjectService(registry=self.registry)
        self.calc_service = CalculationService(
            kb_service=self.kb_service,
            project_service=self.project_service,
            registry=self.registry,
        )
        self.history_service = HistoryService(repository=self.project_service.repository)
        self.report_service = ReportService(kb_service=self.kb_service, project_service=self.project_service)
        self.cloud_sync_service = cloud_sync_service
        self.report_output_dir: Optional[Path] = None
        self.workspace_controller = workspace_controller or WorkspaceController(
            project_service=self.project_service,
            calculation_service=self.calc_service,
            history_service=self.history_service,
            knowledge_base_service=self.kb_service,
            registry=self.registry,
        )

        self.setWindowTitle("Structural Engineering Calculation Application — US Customary (V1.0)")
        self.resize(1320, 840)
        self.setMinimumSize(1024, 680)

        self.is_sidebar_collapsed = False
        self._current_design_method = DesignMethod.ASD
        self._active_calc_id = ""

        # Initialize active project and seed default demo items only if project has 0 items
        self._active_project = self.project_service.ensure_active_project()
        if not self.project_service.list_items():
            self._seed_initial_project_items()

        self.calculations: List[Dict[str, Any]] = []

        self._setup_ui()
        self._setup_status_bar()
        self._sync_calculations_from_project()
        self._populate_calculations()
        self._update_segmented_toggle()

        # Select C-02 if available, otherwise first calculation item
        default_target = "C-02" if self._find_calc_entry("C-02") else (
            self.calculations[0]["id"] if self.calculations else ""
        )
        if default_target:
            self.select_calculation(default_target)

    def _seed_initial_project_items(self) -> None:
        """Seed initial C-01..C-05 demonstration items into an empty project."""
        c1 = self.project_service.add_item(
            module_id="wood_fastener_nds",
            title="Ledger to stud wall",
            group_name="Roof framing",
            start_from="blank",
        )
        bm1 = self.registry.get_benchmark_inputs("wood_fastener_nds")
        self.workspace_controller.load(c1["calculation_id"])
        for k, v in bm1.items():
            self.workspace_controller.edit_field(c1["calculation_id"], k, v, autosave=False)
        self.project_service.save_draft(c1["calculation_id"], bm1)
        self.workspace_controller.run(c1["calculation_id"])

        c2 = self.project_service.add_item(
            module_id="wood_bolt_lateral",
            title="Truss heel bolt",
            group_name="Roof framing",
            start_from="blank",
        )
        bm2 = self.registry.get_benchmark_inputs("wood_bolt_lateral")
        self.workspace_controller.load(c2["calculation_id"])
        for k, v in bm2.items():
            self.workspace_controller.edit_field(c2["calculation_id"], k, v, autosave=False)
        self.project_service.save_draft(c2["calculation_id"], bm2)
        self.workspace_controller.run(c2["calculation_id"])

        self.project_service.add_item(
            module_id="aisc_shear_tab",
            title="Beam seat (AISC)",
            group_name="Level 2",
            start_from="blank",
        )
        self.project_service.add_item(
            module_id="tms402_cmu_anchorage",
            title="Anchor to CMU",
            group_name="Level 2",
            start_from="blank",
        )

        c5 = self.project_service.add_item(
            module_id="asce7_parapet_wind",
            title="Wind C&C (ASCE 7)",
            group_name="Level 2",
            start_from="blank",
        )
        bm5 = self.registry.get_benchmark_inputs("asce7_parapet_wind")
        self.workspace_controller.load(c5["calculation_id"])
        for k, v in bm5.items():
            self.workspace_controller.edit_field(c5["calculation_id"], k, v, autosave=False)
        self.project_service.save_draft(c5["calculation_id"], bm5)
        self.workspace_controller.run(c5["calculation_id"])

    def _resolve_page_index_for_template(self, template_id: str) -> int:
        spec = self.registry.get(template_id)
        if spec is not None:
            if spec.category == "Wood (NDS)":
                return 3
            if spec.category == "Loads (ASCE 7)":
                return 2
            if spec.category == "Steel (AISC)":
                return 4
            if spec.category == "Concrete / CMU (ACI / TMS)":
                return 5
        return 3 if "wood" in template_id else 2

    def _sync_calculations_from_project(self) -> None:
        """Project ordered SQLite items from ProjectService into sidebar metadata list."""
        items = self.project_service.list_items()
        entries: List[Dict[str, Any]] = []
        for rec in items:
            cid_uuid = rec["calculation_id"]
            item_num = int(rec.get("item_number") or 0)
            display_code = rec.get("display_code") or (f"C-{item_num:02d}" if item_num > 0 else cid_uuid[:6])
            raw_title = str(rec.get("title") or "Calculation").strip()
            clean_title = re.sub(r"^(?:C-\d+\s*[·\-:]\s*)+", "", raw_title).strip() or raw_title

            mod_id = rec.get("module_id", "")
            spec = self.registry.get(mod_id)
            spec_title = spec.title if spec else mod_id
            code_ed = rec.get("code_edition") or self.registry.resolve_code_display(mod_id)

            status_str = rec.get("status", CalculationStatus.INCOMPLETE.value)
            last_dcr = rec.get("last_dcr")
            is_stale = False
            if cid_uuid in self.workspace_controller._draft_inputs:
                vm = self.workspace_controller.load(cid_uuid)
                is_stale = vm.is_stale
                status_str = vm.status.value
                last_dcr = vm.summary.dcr

            if status_str == CalculationStatus.INCOMPLETE.value or last_dcr is None:
                dcr_text = "Incomplete"
                status_color = "#adb5bd"
                badge = f"{item_num:02d}" if item_num > 0 else "--"
            elif status_str == CalculationStatus.INVALID_INPUT.value:
                dcr_text = "Invalid"
                status_color = "#6f42c1"
                badge = f"{item_num:02d}!" if item_num > 0 else "!"
            elif is_stale:
                dcr_text = f"{float(last_dcr):.2f} STALE"
                status_color = "#fd7e14"
                badge = f"{item_num:02d}*" if item_num > 0 else "*"
            elif status_str == CalculationStatus.FAIL.value or float(last_dcr) > 1.0:
                dcr_text = f"{float(last_dcr):.2f} FAIL"
                status_color = "#dc3545"
                badge = f"{item_num:02d}!" if item_num > 0 else "!"
            else:
                dcr_text = f"{float(last_dcr):.2f}"
                status_color = "#28a745"
                badge = f"{item_num:02d}" if item_num > 0 else "--"

            entries.append({
                "id": display_code,
                "calculation_id": cid_uuid,
                "name": f"{display_code} · {clean_title}",
                "raw_title": clean_title,
                "group": rec.get("group_name") or "General",
                "group_id": rec.get("group_id"),
                "dcr_text": dcr_text,
                "status_color": status_color,
                "badge": badge,
                "page_index": self._resolve_page_index_for_template(mod_id),
                "module_id": mod_id,
                "title": f"{display_code} · {clean_title} — {spec_title} ({code_ed})",
                "tooltip": f"{display_code} · {clean_title}\n{spec_title} ({code_ed}) · {dcr_text}",
            })
        self.calculations = entries

    def _find_calc_entry(self, calc_id_or_code: str) -> Optional[Dict[str, Any]]:
        for c in self.calculations:
            if c["id"] == calc_id_or_code or c["calculation_id"] == calc_id_or_code:
                return c
        for c in self.calculations:
            if c["raw_title"].startswith(calc_id_or_code) or c["name"].startswith(calc_id_or_code):
                return c
        return None

    @staticmethod
    def _load_svg_icon(filename: str) -> QIcon:
        path = _ICONS_DIR / filename
        return QIcon(str(path)) if path.is_file() else QIcon()

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

        # Navigation List (Dashboard, Projects, Reports, Settings) with local SVG icons
        self.nav_list = QListWidget()
        self.nav_list.setFixedHeight(130)
        self.nav_list.setIconSize(QSize(16, 16))
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
            ("Dashboard", 0, "dashboard.svg"),
            ("Projects", 1, "projects.svg"),
            ("Reports (PDF/XLSX)", 6, "reports.svg"),
            ("Settings", 7, "settings.svg"),
        ]
        for label, p_idx, icon_file in nav_items:
            item = QListWidgetItem(self._load_svg_icon(icon_file), label)
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

        self.lbl_project_name = QLabel(self._active_project.get("name", "Smith Residence"))
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

        # Calculation List Grouped by Sections (with drag-to-reorder & context menu)
        self.calc_list = SidebarCalcListWidget()
        self.calc_list.setFocusPolicy(Qt.NoFocus)
        self.calc_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.calc_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.calc_list.customContextMenuRequested.connect(self._on_calc_list_context_menu)
        self.calc_list.itemDroppedOrderChanged.connect(self._on_sidebar_item_dropped)
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
            ("dashboard.svg", 0, "Dashboard"),
            ("projects.svg", 1, "Projects"),
            ("reports.svg", 6, "Reports"),
            ("settings.svg", 7, "Settings"),
        ]
        for icon_file, p_idx, tip in rail_icons:
            btn_icon = QPushButton()
            btn_icon.setIcon(self._load_svg_icon(icon_file))
            btn_icon.setIconSize(QSize(16, 16))
            btn_icon.setFixedSize(36, 32)
            btn_icon.setToolTip(tip)
            btn_icon.setCursor(Qt.PointingHandCursor)
            btn_icon.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    color: #ced4da;
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
        # RIGHT AREA: Top Header Bar + Stacked Module Workspaces (exact 8 pages)
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

        # Calculation Title Label
        self.lbl_calc_title = QLabel("Structural Engineering Workspace")
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
        # Stacked Pages (8 pages preserving exact indices 0..7)
        # ----------------------------------------------------------------------
        self.stacked_pages = QStackedWidget()

        # Page 0: Live Project Dashboard
        self.page_dashboard = self._build_dashboard_page()
        self.stacked_pages.addWidget(self.page_dashboard)

        # Page 1: Functional Projects Management
        self.page_projects = self._build_projects_page()
        self.stacked_pages.addWidget(self.page_projects)

        # Page 2: C&C Loads WorkspaceHost
        self.page_cc = WorkspaceHost(
            controller=self.workspace_controller,
            module_title="Components & Cladding Loads",
            default_code=self.registry.resolve_code_display("asce7_parapet_wind"),
            report_service=self.report_service,
        )
        self.stacked_pages.addWidget(self.page_cc)

        # Page 3: Wood Connections WorkspaceHost
        self.page_wood = WorkspaceHost(
            controller=self.workspace_controller,
            module_title="Wood Connections & Lateral",
            default_code=self.registry.resolve_code_display("wood_bolt_lateral"),
            report_service=self.report_service,
        )
        self.stacked_pages.addWidget(self.page_wood)

        # Page 4: Steel Connections WorkspaceHost
        self.page_steel = WorkspaceHost(
            controller=self.workspace_controller,
            module_title="Steel Connections",
            default_code=self.registry.resolve_code_display("aisc_shear_tab"),
            report_service=self.report_service,
        )
        self.stacked_pages.addWidget(self.page_steel)

        # Page 5: Concrete & CMU Anchorage WorkspaceHost
        self.page_concrete = WorkspaceHost(
            controller=self.workspace_controller,
            module_title="Concrete & CMU Anchorage",
            default_code=self.registry.resolve_code_display("ACI_TMS"),
            report_service=self.report_service,
        )
        self.stacked_pages.addWidget(self.page_concrete)

        # Page 6: Functional Deliverable Reports
        self.page_reports = self._build_reports_page()
        self.stacked_pages.addWidget(self.page_reports)

        # Page 7: Functional Settings & Cloud Sync
        self.page_settings = self._build_settings_page()
        self.stacked_pages.addWidget(self.page_settings)

        for host in (self.page_cc, self.page_wood, self.page_steel, self.page_concrete):
            host.itemStateChanged.connect(self._on_workspace_item_state_changed)
            host.statusMessageRequested.connect(self._on_workspace_status_message)

        self._refresh_auxiliary_pages()

        right_layout.addWidget(self.stacked_pages, stretch=1)
        root_layout.addWidget(right_container, stretch=1)

    def _setup_status_bar(self) -> None:
        bar = QStatusBar(self)
        self.setStatusBar(bar)

        prj_name = self._active_project.get("name", "Smith Residence")
        manifest = getattr(self.kb_service, "manifest_data", {}) or {}
        refs = manifest.get("references", [])
        csv_count = manifest.get("total_csv_tables") or sum(
            1 for r in refs if str(r.get("relative_path", "")).startswith("database/")
        )
        proc_count = manifest.get("total_procedures") or sum(
            1 for r in refs if str(r.get("relative_path", "")).startswith("procedures/")
        )

        self.lbl_status_project = QLabel(f"Project: {prj_name}")
        self.lbl_status_kb = QLabel(
            f"Knowledge Base: {csv_count} Tables / {proc_count} Procedures (SHA-256 Verified)"
        )
        self.lbl_status_engine = QLabel("Calculation Engine: Deterministic Python (Offline Ready)")

        bar.addWidget(self.lbl_status_project, stretch=1)
        bar.addWidget(self.lbl_status_kb, stretch=1)
        bar.addWidget(self.lbl_status_engine, stretch=1)

    def _on_workspace_status_message(self, msg: str) -> None:
        if hasattr(self, "lbl_status_engine"):
            self.lbl_status_engine.setText(msg)

    def _on_workspace_item_state_changed(self, item_id: str, vm: WorkspaceViewModel) -> None:
        """Keep sidebar DCR/status/stale badges synced whenever a WorkspaceHost item updates."""
        self._sync_calculations_from_project()
        self._populate_calculations(preserve_selection=item_id)
        self._refresh_auxiliary_pages()
        entry = self._find_calc_entry(item_id)
        if entry:
            self.lbl_calc_title.setText(entry["title"])
        self._current_design_method = vm.design_method
        self._update_segmented_toggle()

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

    def _build_dashboard_page(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet("background-color: #f8f9fa;")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        hdr = QLabel("Application Dashboard")
        hdr.setStyleSheet("font-size: 18px; font-weight: bold; color: #1b365d;")
        layout.addWidget(hdr)

        self.lbl_dash_project = QLabel("")
        self.lbl_dash_project.setStyleSheet("font-size: 13px; color: #343a40;")
        layout.addWidget(self.lbl_dash_project)

        self.lbl_dash_counts = QLabel("")
        self.lbl_dash_counts.setStyleSheet(
            "background-color: #ffffff; border: 1px solid #dee2e6; border-radius: 6px; "
            "padding: 12px; font-size: 13px; color: #212529;"
        )
        layout.addWidget(self.lbl_dash_counts)

        self.lbl_dash_kb = QLabel("")
        self.lbl_dash_kb.setStyleSheet(
            "background-color: #ffffff; border: 1px solid #dee2e6; border-radius: 6px; "
            "padding: 12px; font-size: 12px; color: #495057;"
        )
        layout.addWidget(self.lbl_dash_kb)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("+ Add Calculation Item")
        btn_add.setFixedHeight(32)
        btn_add.setStyleSheet(
            "background-color: #007bff; color: #ffffff; border: none; border-radius: 5px; padding: 0 14px; font-weight: bold;"
        )
        btn_add.clicked.connect(self._on_add_calculation_clicked)

        btn_open_reports = QPushButton("Open Deliverable Reports")
        btn_open_reports.setFixedHeight(32)
        btn_open_reports.clicked.connect(lambda: self._switch_to_page(6))
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_open_reports)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)
        layout.addStretch(1)
        return page

    def _build_projects_page(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet("background-color: #f8f9fa;")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        hdr = QLabel("Projects Management")
        hdr.setStyleSheet("font-size: 18px; font-weight: bold; color: #1b365d;")
        layout.addWidget(hdr)

        self.lbl_active_project_summary = QLabel("")
        self.lbl_active_project_summary.setStyleSheet(
            "background-color: #eef4fb; border: 1px solid #b8c9dc; border-radius: 6px; "
            "padding: 10px 12px; font-size: 13px; font-weight: 600; color: #1b365d;"
        )
        layout.addWidget(self.lbl_active_project_summary)

        grp_existing = QGroupBox("Existing Projects")
        grp_existing_layout = QVBoxLayout(grp_existing)
        self.list_projects_widget = QListWidget()
        self.list_projects_widget.setMinimumHeight(140)
        grp_existing_layout.addWidget(self.list_projects_widget)

        self.btn_switch_project = QPushButton("Switch Active Project")
        self.btn_switch_project.setFixedHeight(32)
        self.btn_switch_project.setCursor(Qt.PointingHandCursor)
        self.btn_switch_project.clicked.connect(self._on_switch_project_clicked)
        grp_existing_layout.addWidget(self.btn_switch_project, alignment=Qt.AlignLeft)
        layout.addWidget(grp_existing)

        grp_new = QGroupBox("Create New Engineering Project")
        form = QFormLayout(grp_new)
        self.txt_new_project_name = QLineEdit()
        self.txt_new_project_name.setPlaceholderText("e.g., Oak Street Seismic Retrofit")
        self.txt_new_project_code = QLineEdit()
        self.txt_new_project_code.setPlaceholderText("e.g., PRJ-2026-002")
        self.txt_new_project_engineer = QLineEdit()
        self.txt_new_project_engineer.setPlaceholderText("e.g., Jane Doe, PE")
        form.addRow("Project Name:", self.txt_new_project_name)
        form.addRow("Project Code:", self.txt_new_project_code)
        form.addRow("Engineer of Record:", self.txt_new_project_engineer)

        self.btn_create_project = QPushButton("Create & Activate Project")
        self.btn_create_project.setFixedHeight(32)
        self.btn_create_project.setCursor(Qt.PointingHandCursor)
        self.btn_create_project.setStyleSheet(
            "background-color: #007bff; color: #ffffff; border: none; border-radius: 5px; padding: 0 14px; font-weight: bold;"
        )
        self.btn_create_project.clicked.connect(self._on_create_project_clicked)
        form.addRow("", self.btn_create_project)
        layout.addWidget(grp_new)
        layout.addStretch(1)
        return page

    def _build_reports_page(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet("background-color: #f8f9fa;")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        hdr = QLabel("Deliverable Reports — Ordered Multi-Item Packages")
        hdr.setStyleSheet("font-size: 18px; font-weight: bold; color: #1b365d;")
        layout.addWidget(hdr)

        sub = QLabel(
            "Select calculation items (ordered identically to sidebar tree) and export unified "
            "Rule 6 17-column Excel (.xlsx) or 12-section Plan-Check PDF (.pdf) packages."
        )
        sub.setWordWrap(True)
        sub.setStyleSheet("font-size: 12px; color: #495057;")
        layout.addWidget(sub)

        self.list_report_items = QListWidget()
        self.list_report_items.setMinimumHeight(180)
        layout.addWidget(self.list_report_items)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self.btn_export_project_xlsx = QPushButton("Export Project Package — XLSX (17-Col)")
        self.btn_export_project_xlsx.setFixedHeight(34)
        self.btn_export_project_xlsx.setCursor(Qt.PointingHandCursor)
        self.btn_export_project_xlsx.setStyleSheet(
            "background-color: #1F4E78; color: #ffffff; border: none; border-radius: 5px; padding: 0 14px; font-weight: bold;"
        )
        self.btn_export_project_xlsx.clicked.connect(lambda: self.export_selected_project_package("xlsx"))

        self.btn_export_project_pdf = QPushButton("Export Project Package — PDF (12-Sec)")
        self.btn_export_project_pdf.setFixedHeight(34)
        self.btn_export_project_pdf.setCursor(Qt.PointingHandCursor)
        self.btn_export_project_pdf.setStyleSheet(
            "background-color: #007bff; color: #ffffff; border: none; border-radius: 5px; padding: 0 14px; font-weight: bold;"
        )
        self.btn_export_project_pdf.clicked.connect(lambda: self.export_selected_project_package("pdf"))

        btn_row.addWidget(self.btn_export_project_xlsx)
        btn_row.addWidget(self.btn_export_project_pdf)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        self.lbl_report_export_status = QLabel("Ready to export project calculation package.")
        self.lbl_report_export_status.setWordWrap(True)
        self.lbl_report_export_status.setStyleSheet("font-size: 12px; color: #495057; padding-top: 4px;")
        layout.addWidget(self.lbl_report_export_status)
        layout.addStretch(1)
        return page

    def _build_settings_page(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet("background-color: #f8f9fa;")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        hdr = QLabel("Settings, Active Code Registry & Cloud Sync")
        hdr.setStyleSheet("font-size: 18px; font-weight: bold; color: #1b365d;")
        layout.addWidget(hdr)

        grp_defaults = QGroupBox("Project Design Method & Active Code Editions")
        form = QFormLayout(grp_defaults)
        self.combo_default_method = QComboBox()
        self.combo_default_method.addItems(["ASD", "LRFD"])
        self.combo_default_method.currentTextChanged.connect(self._on_default_method_changed)
        form.addRow("Default Design Method:", self.combo_default_method)

        self.lbl_active_codes_summary = QLabel(self._format_active_codes_summary())
        self.lbl_active_codes_summary.setWordWrap(True)
        self.lbl_active_codes_summary.setStyleSheet("font-size: 12px; color: #343a40;")
        form.addRow("Active Code Registry:", self.lbl_active_codes_summary)
        layout.addWidget(grp_defaults)

        grp_kb = QGroupBox("Knowledge Base Integrity & Google Drive Raw Sync")
        kb_layout = QVBoxLayout(grp_kb)
        action_row = QHBoxLayout()
        self.btn_verify_kb = QPushButton("Verify Local Knowledge Base (92 SHA-256)")
        self.btn_verify_kb.setFixedHeight(32)
        self.btn_verify_kb.setCursor(Qt.PointingHandCursor)
        self.btn_verify_kb.clicked.connect(self._on_verify_kb_clicked)

        self.btn_sync_cloud = QPushButton("Sync Knowledge Base (Google Drive Raw)")
        self.btn_sync_cloud.setFixedHeight(32)
        self.btn_sync_cloud.setCursor(Qt.PointingHandCursor)
        self.btn_sync_cloud.clicked.connect(self._on_sync_cloud_clicked)

        action_row.addWidget(self.btn_verify_kb)
        action_row.addWidget(self.btn_sync_cloud)
        action_row.addStretch(1)
        kb_layout.addLayout(action_row)

        self.lbl_settings_status = QLabel("Deterministic offline runtime ready.")
        self.lbl_settings_status.setWordWrap(True)
        self.lbl_settings_status.setStyleSheet("font-size: 12px; color: #495057; padding-top: 6px;")
        kb_layout.addWidget(self.lbl_settings_status)
        layout.addWidget(grp_kb)
        layout.addStretch(1)
        return page

    def _format_active_codes_summary(self) -> str:
        reg_path = Path(__file__).resolve().parent.parent / "config" / "active_code_registry.json"
        try:
            data = json.loads(reg_path.read_text(encoding="utf-8"))
            codes = data.get("active_codes", data)
            if isinstance(codes, dict):
                return " · ".join(f"{k}: {v}" for k, v in codes.items() if not isinstance(v, (dict, list)))
        except Exception:
            pass
        return (
            f"{self.registry.resolve_code_display('asce7_parapet_wind')} · "
            f"{self.registry.resolve_code_display('wood_bolt_lateral')} · "
            f"{self.registry.resolve_code_display('aisc_shear_tab')} · "
            f"{self.registry.resolve_code_display('ACI_TMS')}"
        )

    def _refresh_auxiliary_pages(self) -> None:
        """Synchronize Dashboard, Projects, Reports, and Settings pages with active SQLite state."""
        active = self.project_service.get_active_project() or self._active_project or {}
        self._active_project = active
        prj_name = active.get("name", "Default Project")
        prj_code = active.get("code", "PRJ-001")
        prj_eng = active.get("engineer", "Structural Engineer")
        if hasattr(self, "lbl_status_project"):
            self.lbl_status_project.setText(f"Project: {prj_name}")

        # Page 0: Dashboard
        if hasattr(self, "lbl_dash_project"):
            self.lbl_dash_project.setText(f"Active Project: {prj_name} ({prj_code}) — Engineer: {prj_eng}")
            total = len(self.calculations)
            n_inc = sum(1 for c in self.calculations if c["dcr_text"] == "Incomplete")
            n_stale = sum(1 for c in self.calculations if "STALE" in c["dcr_text"])
            n_fail = sum(1 for c in self.calculations if "FAIL" in c["dcr_text"])
            n_pass = max(0, total - n_inc - n_stale - n_fail)
            self.lbl_dash_counts.setText(
                f"Items: {total}  |  PASS: {n_pass}  |  FAIL: {n_fail}  |  STALE: {n_stale}  |  INCOMPLETE: {n_inc}"
            )
            self.lbl_dash_kb.setText(
                f"Verified Modules: {len(self.registry.list_canonical_verified_ids())} canonical "
                f"({len(self.registry.list_modules())} catalog templates)  |  "
                f"Manifest Refs: {len((getattr(self.kb_service, 'manifest_data', {}) or {}).get('references', []))}"
            )

        # Page 1: Projects
        if hasattr(self, "list_projects_widget"):
            self.lbl_active_project_summary.setText(
                f"Active Project: {prj_name} ({prj_code}) · Engineer: {prj_eng}"
            )
            self.list_projects_widget.clear()
            active_id = active.get("project_id")
            for p in self.project_service.list_projects():
                marker = " [ACTIVE]" if p.get("project_id") == active_id else ""
                item = QListWidgetItem(f"{p.get('name')} ({p.get('code', '')}){marker}")
                item.setData(Qt.UserRole, p.get("project_id"))
                self.list_projects_widget.addItem(item)
                if p.get("project_id") == active_id:
                    self.list_projects_widget.setCurrentItem(item)

        # Page 6: Reports
        if hasattr(self, "list_report_items"):
            prev_unchecked = {
                self.list_report_items.item(i).data(Qt.UserRole)
                for i in range(self.list_report_items.count())
                if self.list_report_items.item(i).checkState() == Qt.Unchecked
            }
            self.list_report_items.clear()
            for c in self.calculations:
                li = QListWidgetItem(f"{c['name']}  [{c['group']}] — {c['dcr_text']}")
                li.setData(Qt.UserRole, c["calculation_id"])
                li.setFlags(li.flags() | Qt.ItemIsUserCheckable)
                li.setCheckState(Qt.Unchecked if c["calculation_id"] in prev_unchecked else Qt.Checked)
                self.list_report_items.addItem(li)

        # Page 7: Settings
        if hasattr(self, "combo_default_method"):
            defaults = self.project_service.get_project_defaults()
            def_method = str(defaults.get("default_design_method", "ASD")).upper()
            self.combo_default_method.blockSignals(True)
            idx = self.combo_default_method.findText(def_method)
            if idx >= 0:
                self.combo_default_method.setCurrentIndex(idx)
            self.combo_default_method.blockSignals(False)

    def _on_switch_project_clicked(self) -> None:
        curr = self.list_projects_widget.currentItem()
        if curr is None:
            return
        target_id = str(curr.data(Qt.UserRole) or "")
        if not target_id:
            return
        proj = self.project_service.set_active_project(target_id)
        if proj is not None:
            self._active_project = proj
            self._active_calc_id = ""
            self._sync_calculations_from_project()
            self._populate_calculations()
            self._refresh_auxiliary_pages()
            self._on_workspace_status_message(f"Switched active project to: {proj.get('name')}")

    def _on_create_project_clicked(self) -> None:
        name = self.txt_new_project_name.text().strip()
        if not name:
            self.lbl_active_project_summary.setText("Enter a Project Name before creating a project.")
            return
        code = self.txt_new_project_code.text().strip() or "PRJ-NEW"
        engineer = self.txt_new_project_engineer.text().strip() or "Structural Engineer, PE"
        created = self.project_service.create_project(name=name, code=code, engineer=engineer)
        self.project_service.set_active_project(created["project_id"])
        self._active_project = created
        self._active_calc_id = ""
        self.txt_new_project_name.clear()
        self.txt_new_project_code.clear()
        self.txt_new_project_engineer.clear()
        self._sync_calculations_from_project()
        self._populate_calculations()
        self._refresh_auxiliary_pages()
        self._on_workspace_status_message(f"Created & activated project: {created['name']} ({created['code']})")

    def export_selected_project_package(self, fmt: str, output_path: Optional[Path] = None) -> Optional[Path]:
        """Export checked calculation items in exact sidebar order to XLSX or PDF."""
        selected_ids: List[str] = []
        for idx in range(self.list_report_items.count()):
            it = self.list_report_items.item(idx)
            if it.checkState() == Qt.Checked and it.data(Qt.UserRole):
                selected_ids.append(str(it.data(Qt.UserRole)))
        if not selected_ids:
            self.lbl_report_export_status.setText("Select at least one calculation item to export.")
            return None

        active = self.project_service.get_active_project() or self._active_project or {}
        safe_code = re.sub(r"[^A-Za-z0-9_-]+", "_", str(active.get("code") or "project"))
        out_dir = self.report_output_dir or Path("storage/exports")
        ext = "xlsx" if fmt.lower() == "xlsx" else "pdf"
        target = Path(output_path) if output_path else (out_dir / f"{safe_code}_package.{ext}")

        if ext == "xlsx":
            saved = self.report_service.export_project_excel(
                target,
                item_ids=selected_ids,
                controller=self.workspace_controller,
            )
        else:
            saved = self.report_service.export_project_pdf(
                target,
                item_ids=selected_ids,
                controller=self.workspace_controller,
            )
        msg = f"Exported {len(selected_ids)} item(s) to {saved}"
        self.lbl_report_export_status.setText(msg)
        self._on_workspace_status_message(msg)
        return saved

    def _on_default_method_changed(self, method_text: str) -> None:
        if not method_text:
            return
        self.project_service.set_project_defaults(method_text)
        self.lbl_settings_status.setText(f"Updated project default design method to {method_text}.")

    def _on_verify_kb_clicked(self) -> None:
        report = self.kb_service.verify_integrity()
        msg = (
            f"KB Integrity: {report['verified_count']}/{report['total_registered']} verified "
            f"(missing: {report['missing_count']}, mismatches: {report['mismatch_count']})"
        )
        self.lbl_settings_status.setText(msg)
        self._on_workspace_status_message(msg)

    def _get_cloud_sync_service(self) -> Any:
        if self.cloud_sync_service is not None:
            return self.cloud_sync_service
        mod = importlib.import_module("cloud.drive_sync_service")
        self.cloud_sync_service = mod.CloudSyncService(repository=self.project_service.repository)
        return self.cloud_sync_service

    def _on_sync_cloud_clicked(self) -> None:
        sync_svc = self._get_cloud_sync_service()
        res = sync_svc.sync_knowledge_base()
        conn = getattr(getattr(res, "connection_status", None), "value", getattr(res, "connection_status", "OFFLINE"))
        msg = f"Cloud Sync ({conn}): status={res.status}, files_synced={res.files_synced}"
        self.lbl_settings_status.setText(msg)
        self._on_workspace_status_message(msg)

    def _populate_calculations(self, preserve_selection: Optional[str] = None) -> None:
        target_sel = preserve_selection or self._active_calc_id
        self.calc_list.blockSignals(True)
        self.calc_list.clear()

        groups: Dict[str, List[Dict[str, Any]]] = {}
        for c in self.calculations:
            g = c.get("group", "General")
            groups.setdefault(g, []).append(c)

        while self.rail_badge_layout.count() > 0:
            item = self.rail_badge_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        selected_row = -1
        for group_name, items in groups.items():
            header_item = QListWidgetItem(group_name)
            header_item.setFlags(Qt.NoItemFlags)
            header_item.setData(Qt.UserRole + 1, items[0].get("group_id"))
            header_item.setForeground(QColor("#6c757d"))
            header_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
            self.calc_list.addItem(header_item)

            for calc in items:
                list_item = QListWidgetItem()
                row_widget = CalcItemWidget(calc["id"], calc["name"], calc["dcr_text"], calc["status_color"])
                list_item.setSizeHint(row_widget.sizeHint())
                list_item.setData(Qt.UserRole, calc["calculation_id"])
                list_item.setData(Qt.UserRole + 1, calc["id"])
                list_item.setFlags(
                    Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled
                )
                self.calc_list.addItem(list_item)
                self.calc_list.setItemWidget(list_item, row_widget)

                if target_sel in (calc["id"], calc["calculation_id"]):
                    selected_row = self.calc_list.count() - 1

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
                btn_badge.clicked.connect(
                    lambda checked=False, cid=calc["calculation_id"]: self.select_calculation(cid)
                )
                self.rail_badge_layout.addWidget(btn_badge)

        if selected_row >= 0:
            self.calc_list.setCurrentRow(selected_row)
        self.calc_list.blockSignals(False)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        active_id = self._active_calc_id or (self.calculations[0]["id"] if self.calculations else "")
        if active_id:
            self.select_calculation(active_id)

    def select_calculation(self, calc_id: str) -> None:
        """Select a calculation item by display_code (e.g. 'C-02') or UUID and bind WorkspaceHost."""
        entry = self._find_calc_entry(calc_id)
        if entry is None:
            return
        self._active_calc_id = entry["calculation_id"]

        self.nav_list.blockSignals(True)
        self.nav_list.setCurrentRow(-1)
        self.nav_list.blockSignals(False)

        for idx in range(self.calc_list.count()):
            item = self.calc_list.item(idx)
            if item and item.data(Qt.UserRole) == entry["calculation_id"]:
                self.calc_list.blockSignals(True)
                self.calc_list.setCurrentRow(idx)
                self.calc_list.blockSignals(False)
                break

        self._activate_calculation(entry["calculation_id"])

    def _activate_calculation(self, calc_id: str) -> None:
        found = self._find_calc_entry(calc_id)
        if not found:
            return

        self._active_calc_id = found["calculation_id"]
        self.lbl_calc_title.setText(found["title"])
        self.stacked_pages.setCurrentIndex(found["page_index"])

        target_ws = self.stacked_pages.currentWidget()
        if isinstance(target_ws, WorkspaceHost):
            vm = target_ws.bind_item(found["calculation_id"])
            self._current_design_method = vm.design_method
            self._update_segmented_toggle()

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
            self.calc_list.blockSignals(True)
            self.calc_list.setCurrentRow(-1)
            self.calc_list.blockSignals(False)

    def _switch_to_page(self, index: int) -> None:
        if 0 <= index < self.stacked_pages.count():
            self._refresh_auxiliary_pages()
            self.stacked_pages.setCurrentIndex(index)
            titles = {
                0: "Dashboard — Project Overview & Database Status",
                1: f"Projects — {self._active_project.get('name', 'Smith Residence')}",
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

    # --------------------------------------------------------------------------
    # Sidebar Item Operations: Add, Reorder, Rename, Duplicate, Delete (WP-5)
    # --------------------------------------------------------------------------
    def _on_sidebar_item_dropped(self, calc_id: str, group_id: Optional[str], new_index: int) -> None:
        self.move_calculation_item(calc_id, group_id, new_index)

    def move_calculation_item(
        self,
        item_id_or_code: str,
        target_group_name_or_id: Optional[str],
        new_index: int,
    ) -> bool:
        entry = self._find_calc_entry(item_id_or_code)
        if not entry:
            return False

        target_gid: Optional[str] = None
        if target_group_name_or_id:
            groups = self.project_service.list_groups()
            matched = next(
                (
                    g for g in groups
                    if g["group_id"] == target_group_name_or_id
                    or g["name"].strip().lower() == target_group_name_or_id.strip().lower()
                ),
                None,
            )
            if matched is not None:
                target_gid = matched["group_id"]
            else:
                target_gid = self.project_service.ensure_group(target_group_name_or_id)["group_id"]

        ok = self.project_service.move_item(entry["calculation_id"], target_gid, new_index)
        self._sync_calculations_from_project()
        self._populate_calculations(preserve_selection=entry["calculation_id"])
        return ok

    def rename_calculation_item(self, item_id_or_code: str, new_title: str) -> bool:
        entry = self._find_calc_entry(item_id_or_code)
        if not entry:
            return False
        ok = self.project_service.rename_item(entry["calculation_id"], new_title)
        self._sync_calculations_from_project()
        self._populate_calculations(preserve_selection=entry["calculation_id"])
        if self._active_calc_id == entry["calculation_id"]:
            updated_entry = self._find_calc_entry(entry["calculation_id"])
            if updated_entry:
                self.lbl_calc_title.setText(updated_entry["title"])
        return ok

    def duplicate_calculation_item(self, item_id_or_code: str, new_title: Optional[str] = None) -> Optional[str]:
        entry = self._find_calc_entry(item_id_or_code)
        if not entry:
            return None
        dup = self.project_service.duplicate_item(entry["calculation_id"], new_title=new_title)
        self._sync_calculations_from_project()
        self._populate_calculations()
        self.select_calculation(dup["calculation_id"])
        return dup["calculation_id"]

    def delete_calculation_item(self, item_id_or_code: str) -> bool:
        entry = self._find_calc_entry(item_id_or_code)
        if not entry:
            return False
        cid = entry["calculation_id"]
        ok = self.project_service.delete_item(cid)
        self._sync_calculations_from_project()
        self._populate_calculations()
        if self._active_calc_id == cid:
            self._active_calc_id = ""
            if self.calculations:
                self.select_calculation(self.calculations[0]["calculation_id"])
        return ok

    def _on_calc_list_context_menu(self, pos) -> None:
        item = self.calc_list.itemAt(pos)
        if not item or not item.data(Qt.UserRole):
            return
        cid = str(item.data(Qt.UserRole))
        entry = self._find_calc_entry(cid)
        if not entry:
            return

        menu = QMenu(self)
        act_rename = menu.addAction("Rename...")
        act_duplicate = menu.addAction("Duplicate")
        move_menu = menu.addMenu("Move to Group")
        group_actions = {}
        for grp in self.project_service.list_groups():
            act_g = move_menu.addAction(grp["name"])
            group_actions[act_g] = grp["group_id"]
        menu.addSeparator()
        act_delete = menu.addAction("Delete")

        chosen = menu.exec(self.calc_list.mapToGlobal(pos))
        if chosen is None:
            return
        if chosen == act_rename:
            new_name, ok = QInputDialog.getText(self, "Rename Calculation", "Title:", text=entry["raw_title"])
            if ok and new_name.strip():
                self.rename_calculation_item(cid, new_name.strip())
        elif chosen == act_duplicate:
            self.duplicate_calculation_item(cid)
        elif chosen in group_actions:
            self.move_calculation_item(cid, group_actions[chosen], 0)
        elif chosen == act_delete:
            self.delete_calculation_item(cid)

    def _on_add_calculation_clicked(self) -> None:
        """Open Add Calculation Dialog and create persisted calculation item."""
        active_entry = self._find_calc_entry(self._active_calc_id) if self._active_calc_id else None
        active_label = active_entry["name"] if active_entry else ""
        default_method = self.project_service.get_project_defaults().get("default_design_method", "ASD")

        dialog = AddCalculationDialog(
            self,
            registry=self.registry,
            active_item_label=active_label,
            default_design_method=default_method,
        )
        if dialog.exec() == AddCalculationDialog.Accepted:
            data = dialog.get_calculation_data()
            self._add_calculation_from_data(data)

    def _add_calculation_from_data(self, data: Dict[str, Any]) -> str:
        """Create and open a persisted calculation item from AddCalculationDialog payload."""
        raw_name = str(data.get("name", "New Calculation")).strip()
        clean_title = raw_name.split("·")[-1].strip() if "·" in raw_name else raw_name
        template_id = data["template_id"]
        start_from = data.get("start_from", "blank")
        group_name = data.get("group", "General")

        active_entry = self._find_calc_entry(self._active_calc_id) if self._active_calc_id else None
        source_id = active_entry["calculation_id"] if (start_from == "duplicate" and active_entry) else None

        created = self.project_service.add_item(
            module_id=template_id,
            title=clean_title,
            group_name=group_name,
            start_from=start_from,
            source_item_id=source_id,
            design_method=data.get("design_method"),
        )
        cid = created["calculation_id"]
        self._sync_calculations_from_project()
        self._populate_calculations()
        self.select_calculation(cid)
        return created.get("display_code") or cid


def run_app() -> None:
    """Launch the main desktop GUI application."""
    import sys
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
