"""Unit tests for PySide6 GUI base workspace, main window, and dialogs per SAD v1.0 Section 8."""

import os
import pytest

# Configure Qt for headless/offscreen execution
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from core.common.calculation_result import (
    CalculationResult,
    CalculationStatus,
    DesignMethod,
    LimitStateResult,
)
from gui.dialogs.add_calculation_dialog import AddCalculationDialog
from gui.widgets.base_workspace import BaseCalculationWorkspace, StatusBadgeWidget
from gui.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp():
    """Ensure a single QApplication instance exists for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def sample_calc_result():
    ls = LimitStateResult(
        step_id="S1",
        name="Parapet Wind Suction",
        code_clause="ASCE 7-22 Sec. 29.4",
        equation_latex="p = q_p \\cdot ((GC_{pn}) - (GC_{pi}))",
        substitution_str="25.5 psf * (1.8 - (-0.18))",
        demand=50.5,
        capacity=60.0,
        units="psf",
        dcr=0.84,
        status=CalculationStatus.PASS
    )
    return CalculationResult(
        calculation_id="test-cc-01",
        module_id="cc_parapet",
        code_edition="ASCE 7-22",
        design_method=DesignMethod.ASD,
        input_parameters={"V_mph": 115, "h_ft": 30, "parapet_ht_ft": 3.5},
        assumptions=["Risk Category II", "Exposure C"],
        intermediate_results={"qp_psf": 25.5, "GCpn": 1.8},
        limit_states=[ls],
        governing_limit_state=ls,
        demand=50.5,
        capacity=60.0,
        dcr=0.84,
        status=CalculationStatus.PASS,
        reference_files=["database/asce_7/v7_22/ch26_table_26_6_1_wind_directionality.csv"],
        software_version="1.0.0"
    )


class TestStatusBadgeWidget:
    def test_status_badge_updates(self, qapp):
        badge = StatusBadgeWidget()
        assert badge.text() == "INCOMPLETE"

        badge.update_status(CalculationStatus.PASS)
        assert badge.text() == "PASS"

        badge.update_status(CalculationStatus.FAIL)
        assert badge.text() == "FAIL"

        badge.update_status(CalculationStatus.REQUIRES_REVIEW)
        assert badge.text() == "REQUIRES REVIEW"

        badge.update_status(CalculationStatus.INVALID_INPUT)
        assert badge.text() == "INVALID INPUT"


class TestBaseCalculationWorkspace:
    def test_workspace_initialization(self, qapp):
        ws = BaseCalculationWorkspace(module_title="Parapet Wind", default_code="ASCE 7-22")
        assert ws.get_selected_design_method() == DesignMethod.ASD

        ws.radio_lrfd.setChecked(True)
        assert ws.get_selected_design_method() == DesignMethod.LRFD

    def test_workspace_display_results(self, qapp, sample_calc_result):
        ws = BaseCalculationWorkspace(module_title="Parapet Wind", default_code="ASCE 7-22")
        ws.display_results(sample_calc_result)

        assert ws.status_badge.text() == "PASS"
        assert ws.dcr_bar.value() == 84
        assert "Parapet Wind Suction" in ws.lbl_governing.text()
        assert ws.table_limit_states.rowCount() == 1
        assert ws.table_limit_states.item(0, 0).text() == "S1"
        assert ws.table_limit_states.item(0, 5).text() == "0.84"


class TestMainWindow:
    def test_main_window_init_and_navigation(self, qapp):
        win = MainWindow()
        # Top navigation has 4 main items (Dashboard, Projects, Reports, Settings)
        assert win.nav_list.count() == 4
        # Stacked pages has 8 module pages
        assert win.stacked_pages.count() == 8

        # Test switching top nav to Projects (page index 1)
        win.nav_list.setCurrentRow(1)
        assert win.stacked_pages.currentIndex() == 1

        # Test switching top nav to Reports (page index 6)
        win.nav_list.setCurrentRow(2)
        assert win.stacked_pages.currentIndex() == 6

        # Test switching calculation to C-02 (Wood Connections workspace, page index 3)
        win.select_calculation("C-02")
        assert win.stacked_pages.currentIndex() == 3
        assert "Truss heel bolt" in win.lbl_calc_title.text()

        # Test switching calculation to C-03 (Steel Connections workspace, page index 4)
        win.select_calculation("C-03")
        assert win.stacked_pages.currentIndex() == 4
        assert "Beam seat" in win.lbl_calc_title.text()

    def test_sidebar_collapse_toggle(self, qapp):
        win = MainWindow()
        win.show()
        assert not win.is_sidebar_collapsed
        assert not win.sidebar_expanded_widget.isHidden()
        assert win.sidebar_collapsed_widget.isHidden()

        # Toggle to collapsed rail
        win.toggle_sidebar()
        assert win.is_sidebar_collapsed
        assert win.sidebar_expanded_widget.isHidden()
        assert not win.sidebar_collapsed_widget.isHidden()

        # Toggle back to expanded
        win.toggle_sidebar()
        assert not win.is_sidebar_collapsed
        assert not win.sidebar_expanded_widget.isHidden()
        assert win.sidebar_collapsed_widget.isHidden()

    def test_segmented_design_method_toggle(self, qapp):
        win = MainWindow()
        assert win._current_design_method == DesignMethod.ASD

        win.set_active_design_method(DesignMethod.LRFD)
        assert win._current_design_method == DesignMethod.LRFD

        win.set_active_design_method(DesignMethod.ASD)
        assert win._current_design_method == DesignMethod.ASD


class TestAddCalculationDialog:
    def test_add_calc_dialog_init(self, qapp):
        dialog = AddCalculationDialog()
        assert dialog.list_categories.count() == 5
        assert dialog.list_categories.currentRow() == 2
        assert "WOOD CONNECTIONS" in dialog.lbl_category_header.text()

    def test_add_calc_dialog_category_switching(self, qapp):
        dialog = AddCalculationDialog()
        # Switch to Steel (AISC), row 3
        dialog.list_categories.setCurrentRow(3)
        assert "STEEL CONNECTIONS (AISC)" in dialog.lbl_category_header.text()
        assert len(dialog._card_widgets) > 0

    def test_add_calc_dialog_get_data(self, qapp):
        dialog = AddCalculationDialog()
        data = dialog.get_calculation_data()
        assert "name" in data
        assert "group" in data
        assert "template_id" in data
        assert "category" in data
        assert data["design_method"] == "ASD"
        assert data["start_from"] == "blank"
