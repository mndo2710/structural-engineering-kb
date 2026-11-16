"""Level 1–5 Verification & Benchmark Suite for Day 13 C&C Vertical Slice E2E.

Conforms to SAD v1.0 Section 12 (Levels 1-5 Testing):
  - Level 1: Unit Testing (velocity pressure, Kz/Ke/Kd, GCp, Ch. 13 seismic Fp).
  - Level 2: Reference Data Testing (CSV encoding, SHA-256 integrity, table lookup).
  - Level 3: Benchmark Testing (exact numerical verification against worked examples in
    procedures/01_loads_and_seismic/*.md).
  - Level 4: Regression Testing (strict ASD vs. LRFD load factor separation).
  - Level 5: End-to-End Testing (Input -> Validation -> KB Lookup -> Calculation ->
    SQLite Revision -> 17-Col Arial 10pt XLSX & 12-Section PDF Export -> PySide6 GUI).
"""

import os
from pathlib import Path
import openpyxl
import pytest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from app.services.calculation_service import CalculationService
from app.services.history_service import HistoryService
from app.services.knowledge_base_service import KnowledgeBaseService
from app.services.project_service import ProjectService
from app.services.report_service import ReportService
from core.asce7.seismic.seismic_loads import calculate_nonstructural_seismic_fp
from core.asce7.wind.awning import calculate_awning_canopy_loads
from core.asce7.wind.guardrail import calculate_guardrail_loads
from core.asce7.wind.parapet import calculate_parapet_wind
from core.asce7.wind.roof_overhang import calculate_roof_overhang_wind
from core.asce7.wind.trellis import calculate_trellis_loads
from core.asce7.wind.velocity_pressure import calculate_velocity_pressure, lookup_kz
from core.common.calculation_result import CalculationStatus, DesignMethod
from gui.main_window import MainWindow
from gui.widgets.cc_workspace import CCCalculationWorkspace
from storage.repositories.project_repository import ProjectRepository


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture(scope="module")
def kb_service():
    return KnowledgeBaseService()


class TestLevel1And2WindAndSeismicPrimitives:
    """Level 1 Unit & Level 2 Reference Data Verification."""

    def test_kz_table_lookup_and_interpolation(self, kb_service):
        # At z = 15 ft, Exposure C -> Kz = 0.85; at z = 20 ft, Exposure C -> Kz = 0.90
        assert lookup_kz(kb_service, 15.0, "C") == pytest.approx(0.85, abs=1e-3)
        assert lookup_kz(kb_service, 20.0, "C") == pytest.approx(0.90, abs=1e-3)
        # Midpoint z = 17.5 ft -> interpolated 0.875
        assert lookup_kz(kb_service, 17.5, "C") == pytest.approx(0.875, abs=1e-3)

    def test_velocity_pressure_equation_26_10_1(self, kb_service):
        # V = 115 mph, z = 20 ft, Exp C (Kz = 0.90), Kzt = 1.0, Ke = 1.0 -> qh = 0.00256 * 0.90 * 115^2 = 30.47 psf
        res = calculate_velocity_pressure(kb_service, v_mph=115.0, z_ft=20.0, exposure="C")
        assert res["Kz"] == pytest.approx(0.90, abs=1e-3)
        assert res["Kd"] == pytest.approx(0.85, abs=1e-3)
        assert res["qz_psf"] == pytest.approx(30.47, abs=0.02)

    def test_nonstructural_seismic_fp_chapter_13(self, kb_service):
        res = calculate_nonstructural_seismic_fp(
            kb_service,
            sds_g=1.0,
            wp_lbs=360.0,
            z_ft=10.0,
            h_ft=20.0,
            element_keyword="Appendages",
        )
        assert res["C_AR"] == pytest.approx(2.2)
        assert res["R_po"] == pytest.approx(1.5)
        assert res["Omega_0p"] == pytest.approx(1.75)
        assert res["H_f"] == pytest.approx(2.25)
        assert res["Fp_min_lbs"] == pytest.approx(108.0)
        assert res["Fp_max_lbs"] == pytest.approx(576.0)
        assert res["Fp_min_lbs"] <= res["Fp_gov_lbs"] <= res["Fp_max_lbs"]


class TestLevel3And4CCBenchmarkModules:
    """Level 3 Benchmark Verification against Worked Procedure Examples & Level 4 ASD/LRFD Separation."""

    def test_benchmark_awning_canopy_section_30_11(self, kb_service):
        """
        Verify against worked example in cc_awning_canopy_loads_workflow.md Section 5:
        Bc = 5.0 ft, Sb = 6.0 ft, hc = 10.0 ft, h = he = 20.0 ft, Exp C, V = 115 mph, w_D = 12 psf.
        Expected:
          qh = 30.47 psf
          GCp_net_pos = +1.18 -> p_net_pos = +30.56 psf
          GCp_net_neg = -1.48 -> p_net_neg = -38.33 psf
          ASD net uplift moment at wall M_up_wall = 1,185 lb-ft
        """
        inputs = {
            "V_mph": 115.0,
            "exposure": "C",
            "h_roof_ft": 20.0,
            "he_ft": 20.0,
            "hc_ft": 10.0,
            "Bc_ft": 5.0,
            "Sb_ft": 6.0,
            "w_D_psf": 12.0,
            "w_Lr_psf": 20.0,
            "SDS_g": 1.0,
            "support_type": "Cantilever_Bracket",
        }
        res_asd = calculate_awning_canopy_loads(inputs, kb_service, DesignMethod.ASD)
        inter = res_asd.intermediate_results
        assert inter["q_h_psf"] == pytest.approx(30.47, abs=0.05)
        assert inter["GCp_net_pos"] == pytest.approx(1.18, abs=0.02)
        assert inter["GCp_net_neg"] == pytest.approx(-1.48, abs=0.02)
        assert inter["p_net_pos_psf"] == pytest.approx(30.56, abs=0.2)
        assert inter["p_net_neg_psf"] == pytest.approx(-38.33, abs=0.2)
        assert inter["M_up_wall_lb_ft"] == pytest.approx(1185.0, abs=5.0)

        # Level 4: Verify LRFD produces strictly higher factored demand than ASD
        res_lrfd = calculate_awning_canopy_loads(inputs, kb_service, DesignMethod.LRFD)
        assert res_lrfd.demand > res_asd.demand

    def test_benchmark_open_trellis_section_29_4(self, kb_service):
        """
        Verify against worked example in cc_trellis_open_wind_seismic_workflow.md Section 5:
        12 ft x 16 ft plan, z = Hp = 10 ft, Np = 4 posts, Exp C, V = 115 mph, Af_eff = 28.0 ft^2, epsilon = 0.18.
        Expected:
          qz = 28.78 psf, Cf = 1.8
          F_W_horiz = 28.78 * 0.85 * 0.85 * 1.8 * 28.0 = 1,048 lbs
          ASD post shear (0.6W, when SDS=0): V_post = 157.2 lbs/post, M_base = 1,572 lb-ft/post
        """
        inputs = {
            "V_mph": 115.0,
            "exposure": "C",
            "z_top_ft": 10.0,
            "Hp_ft": 10.0,
            "Lt_ft": 16.0,
            "Bt_ft": 12.0,
            "Af_eff_ft2": 28.0,
            "epsilon_elev": 0.18,
            "num_posts": 4,
            "w_D_psf": 8.0,
            "SDS_g": 0.0,  # isolate pure wind benchmark
        }
        res_asd = calculate_trellis_loads(inputs, kb_service, DesignMethod.ASD)
        inter = res_asd.intermediate_results
        assert inter["q_z_psf"] == pytest.approx(28.78, abs=0.05)
        assert inter["C_f"] == pytest.approx(1.80, abs=0.01)
        assert inter["F_W_horiz_lbs"] == pytest.approx(1048.0, abs=2.0)
        assert inter["V_post_lbs"] == pytest.approx(157.2, abs=0.5)
        assert inter["M_base_lb_ft"] == pytest.approx(1572.0, abs=5.0)

    def test_benchmark_guardrail_ibc_1607_9(self, kb_service):
        """
        Verify against worked example in guardrail_handrail_loads_ibc_workflow.md Section 5:
        R-3_Residential, H_guard = 42 in., S_post = 5.0 ft, e_fas = 0 in., N_t = 2 bolts, d_bolt = 4.25 in.
        Expected:
          V_post_ASD = 200 lbs
          M_base_ASD = 700 lb-ft = 8,400 lb-in.
          T_bolt_ASD = 8,400 / (2 * 4.25) = 988.24 lbs/bolt
          T_bolt_LRFD = 1.6 * 988.24 = 1,581.18 lbs/bolt
        """
        inputs = {
            "occupancy": "R-3_Residential",
            "H_guard_in": 42.0,
            "S_post_ft": 5.0,
            "e_fas_in": 0.0,
            "p_W_psf": 15.0,
            "epsilon_guard": 0.20,
            "N_t_bolts": 2,
            "d_bolt_in": 4.25,
        }
        res_asd = calculate_guardrail_loads(inputs, kb_service, DesignMethod.ASD)
        assert res_asd.intermediate_results["V_post_gov_lbs"] == pytest.approx(200.0, abs=0.1)
        assert res_asd.intermediate_results["M_base_gov_lb_ft"] == pytest.approx(700.0, abs=0.1)
        assert res_asd.intermediate_results["T_bolt_gov_lbs"] == pytest.approx(988.24, abs=0.2)

        res_lrfd = calculate_guardrail_loads(inputs, kb_service, DesignMethod.LRFD)
        assert res_lrfd.intermediate_results["T_bolt_gov_lbs"] == pytest.approx(1581.18, abs=0.3)

    def test_parapet_and_overhang_calculations(self, kb_service):
        res_par = calculate_parapet_wind(
            {"V_mph": 115.0, "exposure": "C", "h_roof_ft": 25.0, "h_par_ft": 3.5},
            kb_service,
            DesignMethod.ASD,
        )
        assert res_par.status == CalculationStatus.PASS
        assert len(res_par.limit_states) == 3

        res_oh = calculate_roof_overhang_wind(
            {"V_mph": 115.0, "exposure": "C", "h_roof_ft": 20.0, "L_oh_ft": 2.5, "roof_slope_deg": 15.0},
            kb_service,
            DesignMethod.ASD,
        )
        assert res_oh.status == CalculationStatus.PASS
        # Verify combined overhang GCp = -2.5 - (+1.0) = -3.5 for A <= 10 ft^2 in Zone 2 (theta = 15 deg)
        assert res_oh.intermediate_results["GCp_oh_net_neg"] == pytest.approx(-3.50, abs=0.05)


class TestLevel5EndToEndVerticalSlice:
    """Level 5 End-to-End Test: Service -> SQLite Revision -> 17-Col Excel & 12-Sec PDF -> PySide6 GUI."""

    def test_e2e_cc_vertical_slice_workflow(self, tmp_path, kb_service, qapp):
        db_file = tmp_path / "test_day13_e2e.sqlite3"
        repo = ProjectRepository(db_path=db_file)
        prj_service = ProjectService(repository=repo)
        hist_service = HistoryService(repository=repo)
        calc_service = CalculationService(kb_service=kb_service, project_service=prj_service)
        report_service = ReportService(kb_service=kb_service, project_service=prj_service)

        # 1. Create project and C&C calculation record
        prj = prj_service.create_project(
            name="Day 13 C&C Benchmark Project",
            code="PRJ-D13",
            client="City Plan Check",
            engineer="Nhat Do, PE",
        )
        calc_rec = prj_service.create_calculation(
            module_id="asce7_parapet_wind",
            title="C-05 · Roof Parapet Wind Check",
            code_edition="ASCE 7-22",
            design_method=DesignMethod.ASD,
        )
        calc_id = calc_rec["calculation_id"]

        # 2. Run calculation via CalculationService & auto-save Revision 1
        res_rev1 = calc_service.run_calculation(
            module_id="asce7_parapet_wind",
            inputs={"V_mph": 115.0, "h_roof_ft": 25.0, "h_par_ft": 3.5},
            design_method=DesignMethod.ASD,
            calculation_id=calc_id,
            auto_save_revision=True,
            change_notes="Initial ASD parapet calculation",
        )
        assert res_rev1.status == CalculationStatus.PASS

        # 3. Run Revision 2 with higher wind speed V = 130 mph and verify HistoryService diff
        res_rev2 = calc_service.run_calculation(
            module_id="asce7_parapet_wind",
            inputs={"V_mph": 130.0, "h_roof_ft": 25.0, "h_par_ft": 3.5},
            design_method=DesignMethod.ASD,
            calculation_id=calc_id,
            auto_save_revision=True,
            change_notes="Increased V to 130 mph per Risk Category III",
        )
        diff = hist_service.compare_revisions(calc_id, 1, 2)
        assert "V_mph" in diff["input_diffs"]
        assert diff["result_diffs"]["current_dcr"] > diff["result_diffs"]["previous_dcr"]

        # 4. Export to 17-Column Arial 10pt Excel Workbook (.xlsx) and verify Rule 6 compliance
        xlsx_path = tmp_path / "Day13_Parapet_Report.xlsx"
        saved_xlsx = report_service.export_excel(res_rev2, xlsx_path)
        assert saved_xlsx.exists()

        wb = openpyxl.load_workbook(saved_xlsx)
        assert wb.sheetnames == ["Calc_Sheet", "Database", "Source_Audit"]
        ws_calc = wb["Calc_Sheet"]
        assert ws_calc.row_dimensions[1].height == 18.0
        assert ws_calc.cell(row=1, column=1).font.name == "Arial"

        # 5. Export to 12-Section ReportLab PDF Report (.pdf) and verify non-empty PDF header
        pdf_path = tmp_path / "Day13_Parapet_Report.pdf"
        saved_pdf = report_service.export_pdf(res_rev2, pdf_path)
        assert saved_pdf.exists()
        assert saved_pdf.read_bytes().startswith(b"%PDF-")

        # 6. Verify PySide6 CCCalculationWorkspace & MainWindow integration
        cc_ws = CCCalculationWorkspace(
            calc_service=calc_service,
            project_service=prj_service,
            report_service=report_service,
        )
        for mod_id in calc_service.list_supported_modules():
            cc_ws.select_submodule(mod_id)
            assert cc_ws._current_result is not None
            assert cc_ws._current_result.module_id == mod_id
            assert cc_ws.table_limit_states.rowCount() >= 2

        win = MainWindow(project_service=prj_service, kb_service=kb_service)
        win.select_calculation("C-05")
        assert win.stacked_pages.currentIndex() == 2
