"""Add Calculation Dialog per SAD v1.0 Section 8.

Modal dialog allowing structural engineers to browse calculation templates
across ASCE 7, NDS, AISC, and ACI/TMS codes, configure calculation name and group,
and instantiate new calculation workspaces.
"""

from typing import Any, Dict, List, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QBrush
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class TemplateThumbnailWidget(QWidget):
    """Schematic thumbnail drawing matching engineering calculation templates."""

    def __init__(self, template_type: str = "wood_bolt", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.template_type = template_type
        self.setFixedHeight(120)
        self.setMinimumWidth(220)
        self.setStyleSheet("background-color: #fafbfc; border: 1px solid #e1e4e8; border-radius: 6px;")

    def set_template_type(self, template_type: str) -> None:
        self.template_type = template_type
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # Background fill
        painter.fillRect(0, 0, w, h, QColor("#f8f9fa"))

        if "wood" in self.template_type or "bolt" in self.template_type:
            # Draw wood lap splice with through-bolt
            wood_color = QColor("#fde6cf")
            border_pen = QPen(QColor("#495057"), 1.5)
            painter.setPen(border_pen)

            # Left/Main member
            painter.setBrush(QBrush(wood_color))
            m1_x, m1_y, m1_w, m1_h = int(w * 0.18), int(h * 0.28), int(w * 0.45), int(h * 0.22)
            painter.drawRect(m1_x, m1_y, m1_w, m1_h)

            # Right/Side member
            m2_x, m2_y, m2_w, m2_h = int(w * 0.35), int(h * 0.48), int(w * 0.45), int(h * 0.22)
            painter.drawRect(m2_x, m2_y, m2_w, m2_h)

            # Bolt through both members
            bolt_color = QColor("#e67e22")
            bolt_pen = QPen(QColor("#b95b12"), 1.5)
            painter.setPen(bolt_pen)
            painter.setBrush(QBrush(bolt_color))
            bx = int(w * 0.46)
            painter.drawRoundedRect(bx, int(h * 0.20), int(w * 0.05), int(h * 0.58), 2, 2)

            # Force arrows
            arrow_pen = QPen(QColor("#d96818"), 2)
            painter.setPen(arrow_pen)
            # Left arrow <-
            painter.drawLine(int(w * 0.16), int(h * 0.39), int(w * 0.10), int(h * 0.39))
            painter.drawLine(int(w * 0.12), int(h * 0.34), int(w * 0.10), int(h * 0.39))
            painter.drawLine(int(w * 0.12), int(h * 0.44), int(w * 0.10), int(h * 0.39))
            # Right arrow ->
            painter.drawLine(int(w * 0.82), int(h * 0.59), int(w * 0.88), int(h * 0.59))
            painter.drawLine(int(w * 0.86), int(h * 0.54), int(w * 0.88), int(h * 0.59))
            painter.drawLine(int(w * 0.86), int(h * 0.64), int(w * 0.88), int(h * 0.59))

        elif "loads" in self.template_type or "parapet" in self.template_type:
            # Draw wall with parapet and wind arrows
            painter.setPen(QPen(QColor("#495057"), 1.5))
            painter.setBrush(QBrush(QColor("#e9ecef")))
            # Roof slab
            painter.drawRect(int(w * 0.25), int(h * 0.45), int(w * 0.55), int(h * 0.12))
            # Parapet wall
            painter.drawRect(int(w * 0.25), int(h * 0.18), int(w * 0.10), int(h * 0.65))

            # Wind force arrows
            wind_pen = QPen(QColor("#007bff"), 2)
            painter.setPen(wind_pen)
            for y_pct in (0.25, 0.40, 0.55):
                py = int(h * y_pct)
                painter.drawLine(int(w * 0.08), py, int(w * 0.22), py)
                painter.drawLine(int(w * 0.18), py - 4, int(w * 0.22), py)
                painter.drawLine(int(w * 0.18), py + 4, int(w * 0.22), py)

        elif "steel" in self.template_type:
            # Draw steel girder with shear tab
            painter.setPen(QPen(QColor("#212529"), 2))
            painter.setBrush(QBrush(QColor("#ced4da")))
            # Column flange
            painter.drawRect(int(w * 0.15), int(h * 0.15), int(w * 0.12), int(h * 0.70))
            # Shear tab plate
            painter.setBrush(QBrush(QColor("#6c757d")))
            painter.drawRect(int(w * 0.27), int(h * 0.30), int(w * 0.15), int(h * 0.40))
            # Beam web
            painter.setBrush(QBrush(QColor("#e9ecef")))
            painter.drawRect(int(w * 0.35), int(h * 0.25), int(w * 0.48), int(h * 0.50))
            # Bolts
            painter.setBrush(QBrush(QColor("#ffc107")))
            painter.setPen(QPen(QColor("#333333"), 1))
            for by_pct in (0.38, 0.50, 0.62):
                painter.drawEllipse(int(w * 0.38), int(h * by_pct), 8, 8)

        else:
            # Concrete anchor
            painter.setPen(QPen(QColor("#495057"), 1.5))
            painter.setBrush(QBrush(QColor("#e2e3e5")))
            painter.drawRect(int(w * 0.20), int(h * 0.45), int(w * 0.60), int(h * 0.45))
            # Embedded anchor rod
            painter.setBrush(QBrush(QColor("#007bff")))
            painter.drawRect(int(w * 0.47), int(h * 0.20), int(w * 0.06), int(h * 0.50))
            # Base plate
            painter.setBrush(QBrush(QColor("#343a40")))
            painter.drawRect(int(w * 0.35), int(h * 0.40), int(w * 0.30), int(h * 0.08))


class TemplateCardWidget(QFrame):
    """Clickable template selection card with title, subtitle, and selected state."""

    clicked = Signal(str)

    def __init__(self, template_id: str, title: str, subtitle: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.template_id = template_id
        self.title = title
        self.subtitle = subtitle
        self._is_selected = False

        self.setCursor(Qt.PointingHandCursor)
        self._setup_ui()
        self.set_selected(False)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(3)

        self.lbl_title = QLabel(self.title)
        self.lbl_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #212529;")

        self.lbl_subtitle = QLabel(self.subtitle)
        self.lbl_subtitle.setStyleSheet("font-size: 11px; color: #6c757d;")
        self.lbl_subtitle.setWordWrap(True)

        layout.addWidget(self.lbl_title)
        layout.addWidget(self.lbl_subtitle)

    def set_selected(self, selected: bool) -> None:
        self._is_selected = selected
        if selected:
            self.setStyleSheet("""
                TemplateCardWidget {
                    background-color: #f0f7ff;
                    border: 2px solid #007bff;
                    border-radius: 8px;
                }
            """)
        else:
            self.setStyleSheet("""
                TemplateCardWidget {
                    background-color: #ffffff;
                    border: 1px solid #dee2e6;
                    border-radius: 8px;
                }
                TemplateCardWidget:hover {
                    background-color: #f8f9fa;
                    border: 1px solid #adb5bd;
                }
            """)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.template_id)
        super().mousePressEvent(event)


class AddCalculationDialog(QDialog):
    """Add Calculation Dialog matching the 3-column mockup architecture."""

    TEMPLATES_DATA = {
        "Wood (NDS)": [
            {
                "id": "wood_bolt_lateral",
                "title": "Bolt / dowel — lateral",
                "subtitle": "Single and double shear · yield modes I–IV · NDS Ch. 12",
                "default_name": "C-06 · Bolt connection",
                "default_group": "Roof framing",
                "preview_type": "wood_bolt",
            },
            {
                "id": "wood_nail_lateral",
                "title": "Nail / wood screw — lateral",
                "subtitle": "NDS Ch. 12",
                "default_name": "C-07 · Nail connection",
                "default_group": "Roof framing",
                "preview_type": "wood_bolt",
            },
            {
                "id": "wood_screw_withdrawal",
                "title": "Lag screw / nail — withdrawal",
                "subtitle": "NDS 12.2",
                "default_name": "C-08 · Lag screw withdrawal",
                "default_group": "Roof framing",
                "preview_type": "wood_bolt",
            },
            {
                "id": "wood_combined_lateral_withdrawal",
                "title": "Combined lateral + withdrawal",
                "subtitle": "NDS 12.4",
                "default_name": "C-09 · Combined fastener check",
                "default_group": "Roof framing",
                "preview_type": "wood_bolt",
            },
        ],
        "Loads (ASCE 7)": [
            {
                "id": "asce7_parapet_wind",
                "title": "Parapet wind pressure",
                "subtitle": "Component & Cladding net pressure · ASCE 7-22 Sec. 29.4",
                "default_name": "C-10 · Roof parapet wind",
                "default_group": "Roof framing",
                "preview_type": "loads",
            },
            {
                "id": "asce7_roof_overhang",
                "title": "Roof overhang wind pressure",
                "subtitle": "ASCE 7-22 Section 30.7",
                "default_name": "C-11 · Eaves overhang",
                "default_group": "Roof framing",
                "preview_type": "loads",
            },
            {
                "id": "asce7_awning_canopy",
                "title": "Awning and canopy loads",
                "subtitle": "ASCE 7-22 Section 30.9",
                "default_name": "C-12 · Entry canopy wind",
                "default_group": "Level 1",
                "preview_type": "loads",
            },
        ],
        "Steel (AISC)": [
            {
                "id": "aisc_shear_tab",
                "title": "Shear tab (single-plate) connection",
                "subtitle": "AISC 360-22 Part 10",
                "default_name": "C-13 · Beam shear tab",
                "default_group": "Level 2",
                "preview_type": "steel",
            },
            {
                "id": "aisc_bolt_bearing",
                "title": "Bolted connection in shear",
                "subtitle": "AISC 360-22 Section J3",
                "default_name": "C-14 · Bolted lap splice",
                "default_group": "Level 2",
                "preview_type": "steel",
            },
            {
                "id": "aisc_base_plate",
                "title": "Column base plate & anchor rods",
                "subtitle": "AISC Design Guide 1 / AISC 360-22",
                "default_name": "C-15 · HSS base plate",
                "default_group": "Foundations",
                "preview_type": "steel",
            },
        ],
        "Concrete / CMU (ACI / TMS)": [
            {
                "id": "aci318_anchor_tension_shear",
                "title": "Cast-in anchor in tension & shear",
                "subtitle": "ACI 318-19 Chapter 17 breakout & pullout",
                "default_name": "C-16 · Foundation anchor bolts",
                "default_group": "Foundations",
                "preview_type": "concrete",
            },
            {
                "id": "tms402_cmu_anchorage",
                "title": "CMU anchor bolt breakout",
                "subtitle": "TMS 402-22 Section 9.1.6",
                "default_name": "C-17 · CMU wall anchor",
                "default_group": "Level 2",
                "preview_type": "concrete",
            },
        ],
        "Recent": [
            {
                "id": "wood_bolt_lateral",
                "title": "Bolt / dowel — lateral",
                "subtitle": "NDS Ch. 12 · Recently used in Smith Residence",
                "default_name": "C-06 · Bolt connection",
                "default_group": "Roof framing",
                "preview_type": "wood_bolt",
            },
            {
                "id": "asce7_parapet_wind",
                "title": "Parapet wind pressure",
                "subtitle": "ASCE 7-22 Section 29.4",
                "default_name": "C-10 · Roof parapet wind",
                "default_group": "Roof framing",
                "preview_type": "loads",
            },
        ],
    }

    CATEGORY_DISPLAY_HEADERS = {
        "Wood (NDS)": "WOOD CONNECTIONS (NDS)",
        "Loads (ASCE 7)": "COMPONENTS & CLADDING LOADS (ASCE 7)",
        "Steel (AISC)": "STEEL CONNECTIONS (AISC)",
        "Concrete / CMU (ACI / TMS)": "CONCRETE & CMU ANCHORAGE (ACI / TMS)",
        "Recent": "RECENT TEMPLATES",
    }

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Calculation")
        self.resize(850, 560)
        self.setMinimumSize(780, 500)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }
        """)

        self._active_category = "Wood (NDS)"
        self._active_template: Dict[str, Any] = self.TEMPLATES_DATA["Wood (NDS)"][0]
        self._card_widgets: List[TemplateCardWidget] = []

        self._setup_ui()
        self._populate_templates()

    def _setup_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 16, 20, 16)
        root_layout.setSpacing(14)

        # ----------------------------------------------------------------------
        # Top Header Bar: Title + Search Bar + Close button
        # ----------------------------------------------------------------------
        header_bar = QHBoxLayout()
        header_bar.setSpacing(16)

        lbl_dialog_title = QLabel("Add Calculation")
        lbl_dialog_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #212529;")
        header_bar.addWidget(lbl_dialog_title)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search calculation type (bolt, anchor, shear tab, wind...)")
        self.txt_search.setStyleSheet("""
            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #ced4da;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                color: #495057;
            }
            QLineEdit:focus {
                border: 1px solid #007bff;
            }
        """)
        self.txt_search.textChanged.connect(self._on_search_text_changed)
        header_bar.addWidget(self.txt_search, stretch=1)

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(28, 28)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
                font-size: 14px;
                color: #6c757d;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #212529;
            }
        """)
        btn_close.clicked.connect(self.reject)
        header_bar.addWidget(btn_close)

        root_layout.addLayout(header_bar)

        # Subtle horizontal divider
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Plain)
        divider.setStyleSheet("color: #e9ecef;")
        root_layout.addWidget(divider)

        # ----------------------------------------------------------------------
        # 3-Column Body Layout
        # ----------------------------------------------------------------------
        body_layout = QHBoxLayout()
        body_layout.setSpacing(16)

        # Column 1: Categories List
        col1_container = QWidget()
        col1_layout = QVBoxLayout(col1_container)
        col1_layout.setContentsMargins(0, 0, 0, 0)
        col1_layout.setSpacing(4)
        col1_container.setFixedWidth(170)

        self.list_categories = QListWidget()
        self.list_categories.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_categories.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_categories.setStyleSheet("""
            QListWidget {
                border: none;
                background-color: transparent;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 8px 12px;
                border-radius: 6px;
                color: #495057;
                font-weight: 500;
                margin-bottom: 2px;
            }
            QListWidget::item:selected {
                background-color: #e7f1ff;
                color: #007bff;
                font-weight: bold;
            }
            QListWidget::item:hover:!selected {
                background-color: #f8f9fa;
            }
        """)

        categories = [
            "Recent",
            "Loads (ASCE 7)",
            "Wood (NDS)",
            "Steel (AISC)",
            "Concrete / CMU (ACI / TMS)",
        ]
        for cat in categories:
            self.list_categories.addItem(cat)

        # Default select Wood (NDS)
        self.list_categories.setCurrentRow(2)
        self.list_categories.currentRowChanged.connect(self._on_category_changed)
        col1_layout.addWidget(self.list_categories)
        body_layout.addWidget(col1_container)

        # Column 2: Template Card List
        col2_container = QWidget()
        col2_layout = QVBoxLayout(col2_container)
        col2_layout.setContentsMargins(0, 0, 0, 0)
        col2_layout.setSpacing(8)

        self.lbl_category_header = QLabel("WOOD CONNECTIONS (NDS)")
        self.lbl_category_header.setStyleSheet("font-size: 11px; font-weight: bold; color: #6c757d; letter-spacing: 0.5px;")
        col2_layout.addWidget(self.lbl_category_header)

        scroll_templates = QScrollArea()
        scroll_templates.setWidgetResizable(True)
        scroll_templates.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_templates.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        self.templates_scroll_widget = QWidget()
        self.templates_scroll_layout = QVBoxLayout(self.templates_scroll_widget)
        self.templates_scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.templates_scroll_layout.setSpacing(8)
        self.templates_scroll_layout.addStretch()

        scroll_templates.setWidget(self.templates_scroll_widget)
        col2_layout.addWidget(scroll_templates)
        body_layout.addWidget(col2_container, stretch=1)

        # Column 3: Preview & Configuration
        col3_container = QWidget()
        col3_layout = QVBoxLayout(col3_container)
        col3_layout.setContentsMargins(0, 0, 0, 0)
        col3_layout.setSpacing(12)
        col3_container.setFixedWidth(270)

        # Schematic thumbnail preview
        self.thumbnail_preview = TemplateThumbnailWidget("wood_bolt")
        col3_layout.addWidget(self.thumbnail_preview)

        # Name Input
        lbl_name = QLabel("Name")
        lbl_name.setStyleSheet("font-size: 11px; font-weight: bold; color: #495057;")
        col3_layout.addWidget(lbl_name)

        self.txt_calc_name = QLineEdit("C-06 · Bolt connection")
        self.txt_calc_name.setStyleSheet("""
            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #ced4da;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
                color: #212529;
            }
            QLineEdit:focus {
                border: 1px solid #007bff;
            }
        """)
        col3_layout.addWidget(self.txt_calc_name)

        # Group Input
        lbl_group = QLabel("Group")
        lbl_group.setStyleSheet("font-size: 11px; font-weight: bold; color: #495057;")
        col3_layout.addWidget(lbl_group)

        self.txt_calc_group = QLineEdit("Roof framing")
        self.txt_calc_group.setStyleSheet("""
            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #ced4da;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
                color: #212529;
            }
            QLineEdit:focus {
                border: 1px solid #007bff;
            }
        """)
        col3_layout.addWidget(self.txt_calc_group)

        # Design Method Display
        lbl_method_title = QLabel("Design method")
        lbl_method_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #495057;")
        col3_layout.addWidget(lbl_method_title)

        self.lbl_method_val = QLabel("ASD (from project settings)")
        self.lbl_method_val.setStyleSheet("font-size: 12px; color: #6c757d; margin-bottom: 4px;")
        col3_layout.addWidget(self.lbl_method_val)

        # Start from options
        lbl_start_from = QLabel("Start from")
        lbl_start_from.setStyleSheet("font-size: 11px; font-weight: bold; color: #495057;")
        col3_layout.addWidget(lbl_start_from)

        self.radio_blank = QRadioButton("Blank")
        self.radio_blank.setChecked(True)
        self.radio_blank.setStyleSheet("font-size: 12px; color: #212529;")

        self.radio_duplicate = QRadioButton("Duplicate C-02 · Truss heel bolt")
        self.radio_duplicate.setStyleSheet("font-size: 12px; color: #212529;")

        self.btn_group_start_from = QButtonGroup(self)
        self.btn_group_start_from.addButton(self.radio_blank)
        self.btn_group_start_from.addButton(self.radio_duplicate)

        col3_layout.addWidget(self.radio_blank)
        col3_layout.addWidget(self.radio_duplicate)
        col3_layout.addStretch()

        body_layout.addWidget(col3_container)
        root_layout.addLayout(body_layout, stretch=1)

        # ----------------------------------------------------------------------
        # Bottom Action Bar: Cancel and Add & Open
        # ----------------------------------------------------------------------
        divider2 = QFrame()
        divider2.setFrameShape(QFrame.HLine)
        divider2.setFrameShadow(QFrame.Plain)
        divider2.setStyleSheet("color: #e9ecef;")
        root_layout.addWidget(divider2)

        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(10)
        bottom_bar.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setFixedSize(90, 34)
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                border: 1px solid #ced4da;
                border-radius: 6px;
                color: #495057;
                font-weight: 500;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #f8f9fa;
                border-color: #adb5bd;
            }
        """)
        self.btn_cancel.clicked.connect(self.reject)
        bottom_bar.addWidget(self.btn_cancel)

        self.btn_add_and_open = QPushButton("Add && Open")
        self.btn_add_and_open.setFixedSize(110, 34)
        self.btn_add_and_open.setCursor(Qt.PointingHandCursor)
        self.btn_add_and_open.setStyleSheet("""
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
        self.btn_add_and_open.clicked.connect(self.accept)
        bottom_bar.addWidget(self.btn_add_and_open)

        root_layout.addLayout(bottom_bar)

    def _on_category_changed(self, row: int) -> None:
        item = self.list_categories.item(row)
        if not item:
            return
        cat_name = item.text()
        self._active_category = cat_name
        hdr = self.CATEGORY_DISPLAY_HEADERS.get(cat_name, cat_name.upper())
        self.lbl_category_header.setText(hdr)
        self._populate_templates()

    def _on_search_text_changed(self, text: str) -> None:
        self._populate_templates(filter_text=text.strip().lower())

    def _populate_templates(self, filter_text: str = "") -> None:
        # Clear existing card widgets
        for card in self._card_widgets:
            card.setParent(None)
            card.deleteLater()
        self._card_widgets.clear()

        # Gather template list based on active category or search filter
        all_templates = []
        if filter_text:
            for cat, t_list in self.TEMPLATES_DATA.items():
                for t in t_list:
                    if filter_text in t["title"].lower() or filter_text in t["subtitle"].lower():
                        all_templates.append(t)
            self.lbl_category_header.setText(f"SEARCH RESULTS ({len(all_templates)})")
        else:
            all_templates = self.TEMPLATES_DATA.get(self._active_category, [])
            hdr = self.CATEGORY_DISPLAY_HEADERS.get(self._active_category, self._active_category.upper())
            self.lbl_category_header.setText(hdr)

        selected_first = False
        for idx, t in enumerate(all_templates):
            card = TemplateCardWidget(
                template_id=t["id"],
                title=t["title"],
                subtitle=t["subtitle"]
            )
            card.clicked.connect(self._on_template_selected)
            self.templates_scroll_layout.insertWidget(idx, card)
            self._card_widgets.append(card)

            # Auto-select the first card if matches active or default
            if not selected_first:
                card.set_selected(True)
                self._update_preview_and_config(t)
                selected_first = True
            else:
                card.set_selected(False)

    def _on_template_selected(self, template_id: str) -> None:
        # Update card selection state
        for card in self._card_widgets:
            card.set_selected(card.template_id == template_id)

        # Find matching template data
        found: Optional[Dict[str, Any]] = None
        for t_list in self.TEMPLATES_DATA.values():
            for t in t_list:
                if t["id"] == template_id:
                    found = t
                    break
            if found:
                break

        if found:
            self._update_preview_and_config(found)

    def _update_preview_and_config(self, template_data: Dict[str, Any]) -> None:
        self._active_template = template_data
        self.thumbnail_preview.set_template_type(template_data.get("preview_type", "wood_bolt"))
        self.txt_calc_name.setText(template_data.get("default_name", "New Calculation"))
        self.txt_calc_group.setText(template_data.get("default_group", "General"))

    def get_calculation_data(self) -> Dict[str, Any]:
        """Return the configuration dictionary for the created calculation."""
        start_from = "blank" if self.radio_blank.isChecked() else "duplicate"
        return {
            "name": self.txt_calc_name.text().strip(),
            "group": self.txt_calc_group.text().strip(),
            "template_id": self._active_template.get("id", "wood_bolt_lateral"),
            "category": self._active_category,
            "design_method": "ASD",
            "start_from": start_from,
        }
