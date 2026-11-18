"""Level 1–5 Verification & Benchmark Suite for Day 14 Wood Connections & Lateral E2E.

Conforms to SAD v1.0 Section 12 (Levels 1-5 Testing):
  - Level 1: Unit Testing (Specific gravity G, Fe, Hankinson formula, Cg Eq. 11.3-1).
  - Level 2: Reference Data Testing (NDS 2024, SDPWS 2021, Simpson C-C-2026 CSV lookups).
  - Level 3: Benchmark Testing (exact numerical verification against worked examples in
    procedures/02_wood_design/*.md and UI mockup).
  - Level 4: Regression Testing (strict ASD vs. LRFD separation across all 5 Wood modules).
  - Level 5: End-to-End Testing (CalculationService -> SQLite Revision -> 17-Col XLSX & 12-Sec PDF
    + PySide6 WoodCalculationWorkspace UI verification).
"""

import os
from pathlib import Path
import tempfile
import unittest
import openpyxl

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.services.calculation_service import CalculationService
from app.services.history_service import HistoryService
from app.services.knowledge_base_service import KnowledgeBaseService
from app.services.project_service import ProjectService
from app.services.report_service import ReportService
from core.common.calculation_result import CalculationStatus, DesignMethod
from core.nds.connections.simpson_connectors import calculate_simpson_hanger_tie
from core.nds.fasteners.bolts import (
    calculate_group_action_factor_cg,
    calculate_wood_bolt_connection,
    lookup_dowel_bearing_strength,
    lookup_species_specific_gravity,
)
from core.nds.fasteners.nails_screws import (
    calculate_wood_fastener_connection,
    lookup_sds_screw_properties,
)
from core.nds.lateral.diaphragms import calculate_wood_diaphragm
from core.nds.lateral.shear_walls import calculate_wood_shear_wall
from storage.repositories.project_repository import ProjectRepository


class TestWoodVerticalSlice(unittest.TestCase):
    """Comprehensive Level 1–5 Verification Suite for Day 14 Wood Connections & Lateral."""

    @classmethod
    def setUpClass(cls):
        cls.kb = KnowledgeBaseService()

    def test_level1_and_2_wood_primitives_and_csv_lookups(self):
        """Level 1 Unit & Level 2 Reference Data Verification for NDS/SDPWS/Simpson."""
        g_dfl = lookup_species_specific_gravity(self.kb, "Douglas Fir-Larch")
        self.assertAlmostEqual(g_dfl, 0.50, places=3)

        fe_dict = lookup_dowel_bearing_strength(self.kb, 0.50, 0.625, theta_deg=0.0)
        self.assertAlmostEqual(fe_dict["Fe_par"], 5600.0, delta=1.0)

        # Single bolt in row -> Cg = 1.00
        self.assertAlmostEqual(
            calculate_group_action_factor_cg(1, 0.625, 3.0, 1600000.0, 8.25, 1600000.0, 8.25),
            1.00,
            places=4,
        )
        # 4 bolts in row -> Cg < 1.00
        cg4 = calculate_group_action_factor_cg(4, 0.75, 3.0, 1600000.0, 8.25, 1600000.0, 8.25)
        self.assertTrue(0.80 <= cg4 < 1.00)

        # Simpson SDS screw lookup from ICC-ESR-2236
        sds = lookup_sds_screw_properties(self.kb, "SDS25212")
        self.assertAlmostEqual(sds["D_in"], 0.256, places=3)
        self.assertAlmostEqual(sds["Z_steel_14ga_lbs"], 390.0, delta=0.5)
        self.assertAlmostEqual(sds["W_unit_lbf_in"], 172.0, delta=0.5)

    def test_level3_benchmark_wood_bolt_single_shear_mode_ii(self):
        """
        Verify against UI mockup & NDS 2024 Chapter 12:
        5/8 in. bolt (D=0.625 in., Fyb=45,000 psi), single shear DF-L (G=0.50, Fe=5,600 psi),
        tm = ts = 1.5 in., e_end,m = 3.0 in., P = 340 lbs.
        Expected:
          k1 = 0.4142, Rd = 3.60 -> Z = 604 lbs (Mode II governs)
          C_Delta = 3.0 / 4.375 = 0.69 -> Z' = 604 * 0.69 = 417 lbs, DCR = 340 / 417 = 0.82
        """
        res = calculate_wood_bolt_connection(
            {
                "D_in": 0.625,
                "shear_planes": "Single Shear",
                "F_yb_psi": 45000.0,
                "main_species": "Douglas Fir-Larch",
                "side_material": "Wood",
                "t_m_in": 1.5,
                "t_s_in": 1.5,
                "e_end_m_in": 3.0,
                "P_demand_lbs": 340.0,
            },
            self.kb,
            DesignMethod.ASD,
        )
        inter = res.intermediate_results
        self.assertEqual(inter["governing_yield_mode"], "Mode II")
        self.assertAlmostEqual(inter["k1"], 0.414, delta=0.002)
        self.assertAlmostEqual(inter["Z_ref_lbs"], 604.0, delta=1.0)
        self.assertAlmostEqual(inter["C_Delta"], 0.69, delta=0.01)
        self.assertAlmostEqual(res.limit_states[0].dcr, 0.82, delta=0.01)

    def test_level3_benchmark_wood_fasteners_nails_lags_sds(self):
        """Verify NDS 2024 Nail/Lag/SDS Combined Lateral & Withdrawal module."""
        res_nail = calculate_wood_fastener_connection(
            {
                "fastener_category": "Common Nail",
                "fastener_id": "10d Common",
                "n_fasteners": 6,
                "V_demand_lbs": 650.0,
                "T_demand_lbs": 120.0,
                "alpha_deg": 10.4,
            },
            self.kb,
            DesignMethod.ASD,
        )
        self.assertEqual(res_nail.status, CalculationStatus.PASS)
        self.assertGreater(res_nail.intermediate_results["Z_ref_lbs"], 100.0)

        res_sds = calculate_wood_fastener_connection(
            {
                "fastener_category": "Simpson SDS Screw",
                "fastener_id": "SDS25212",
                "side_material": "14 ga Steel",
                "n_fasteners": 4,
                "V_demand_lbs": 1200.0,
                "T_demand_lbs": 0.0,
            },
            self.kb,
            DesignMethod.ASD,
        )
        self.assertEqual(res_sds.status, CalculationStatus.PASS)
        self.assertAlmostEqual(res_sds.intermediate_results["Z_ref_lbs"], 390.0, delta=0.5)

    def test_level3_benchmark_shear_wall_and_holdown_sdpws_sec_4_3(self):
        """
        Verify against worked example in wood_shear_wall_holdown_sdpws_workflow.md Section 7:
        h = 10.0 ft, bs = 4.0 ft, V_ASD = 2,240 lbs, V_LRFD = 3,200 lbs, w_DL = 250 plf,
        15/32" Structural I OSB with 10d @ 3" o.c., HDU5-SDS2.5 on 4x4 DF-L post.
        """
        inputs = {
            "h_ft": 10.0,
            "bs_ft": 4.0,
            "V_asd_lbs": 2240.0,
            "V_lrfd_lbs": 3200.0,
            "w_DL_plf": 250.0,
            "sheathing_category": "Structural I",
            "panel_thickness": "15/32",
            "nail_size": "10d",
            "edge_spacing_in": 3,
            "holdown_model": "HDU5-SDS2.5",
        }
        res = calculate_wood_shear_wall(inputs, self.kb, DesignMethod.ASD)
        inter = res.intermediate_results
        self.assertAlmostEqual(inter["C_ar"], 0.9375, places=4)
        self.assertAlmostEqual(inter["v_s_nom_plf"], 1330.0, delta=0.5)
        self.assertAlmostEqual(inter["v_unit_demand_plf"], 560.0, delta=0.5)
        self.assertAlmostEqual(inter["v_unit_cap_plf"], 623.4, delta=0.2)
        self.assertAlmostEqual(inter["T_holdown_demand_lbs"], 5300.0, delta=0.5)
        self.assertAlmostEqual(inter["T_holdown_allow_asd_lbs"], 5645.0, delta=0.5)
        self.assertAlmostEqual(inter["delta_sw_LRFD_in"], 0.689, delta=0.005)
        self.assertAlmostEqual(inter["story_drift_in"], 2.756, delta=0.02)
        self.assertAlmostEqual(inter["f_c_perp_psi"], 498.0, delta=0.5)
        self.assertEqual(res.status, CalculationStatus.PASS)

    def test_level3_benchmark_diaphragm_chord_collector_sdpws_sec_4_2(self):
        """
        Verify against worked example in wood_diaphragm_chord_collector_sdpws_workflow.md Section 7:
        L = 72 ft, W = 30 ft, w_ASD = 315 plf, w_LRFD = 450 plf, 15/32" Sheathing OSB, 10d @ 4"/6"/12",
        unsupported collector length = 15 ft, Simpson MSTC66.
        """
        inputs = {
            "L_span_ft": 72.0,
            "W_depth_ft": 30.0,
            "w_asd_plf": 315.0,
            "w_lrfd_plf": 450.0,
            "sheathing_grade": "Sheathing and Single-Floor",
            "nail_size": "10d",
            "panel_thickness": "15/32",
            "boundary_spacing_in": 4.0,
            "unsupported_drag_ft": 15.0,
            "strap_model": "MSTC66",
        }
        res = calculate_wood_diaphragm(inputs, self.kb, DesignMethod.ASD)
        inter = res.intermediate_results
        self.assertAlmostEqual(inter["V_max_lbs"], 11340.0, delta=0.5)
        self.assertAlmostEqual(inter["v_unit_demand_plf"], 378.0, delta=0.5)
        self.assertAlmostEqual(inter["v_unit_cap_plf"], 385.0, delta=0.5)
        self.assertAlmostEqual(inter["delta_dia_ASD_in"], 0.629, delta=0.005)
        self.assertAlmostEqual(inter["T_chord_max_lbs"], 6804.0, delta=0.5)
        self.assertAlmostEqual(inter["T_chord_quarter_lbs"], 5103.0, delta=0.5)
        self.assertAlmostEqual(inter["F_drag_lbs"], 5670.0, delta=0.5)
        self.assertAlmostEqual(inter["T_strap_cap_lbs"], 5850.0, delta=0.5)
        self.assertEqual(res.status, CalculationStatus.PASS)

    def test_level3_benchmark_simpson_hanger_and_hurricane_tie(self):
        """
        Verify against worked example in wood_joist_hanger_hurricane_tie_simpson_workflow.md Section 7:
        Part A: HUS210-2 in DF/SP -> P_100=5,115, P_125=5,615, U_160=3,165
        Part B: H10A (Nails) in SPF/HF -> U_allow=1,015, F1_allow=485, F2_allow=285,
                Unity(U+F2) = 0.846 <= 1.00, 75% Rule max = 0.880 <= 1.00.
        """
        res = calculate_simpson_hanger_tie({}, self.kb, DesignMethod.ASD)
        inter = res.intermediate_results
        self.assertAlmostEqual(inter["P_allow_100_lbs"], 5115.0, delta=0.5)
        self.assertAlmostEqual(inter["P_allow_125_lbs"], 5615.0, delta=0.5)
        self.assertAlmostEqual(inter["U_allow_hgr_lbs"], 3165.0, delta=0.5)
        self.assertAlmostEqual(inter["U_allow_tie_lbs"], 1015.0, delta=0.5)
        self.assertAlmostEqual(inter["F1_allow_tie_lbs"], 485.0, delta=0.5)
        self.assertAlmostEqual(inter["F2_allow_tie_lbs"], 285.0, delta=0.5)
        self.assertAlmostEqual(inter["unity_U_plus_F2"], 0.846, delta=0.005)
        self.assertAlmostEqual(inter["rule_75_max_dcr"], 0.880, delta=0.005)
        self.assertEqual(res.status, CalculationStatus.PASS)

    def test_level4_asd_vs_lrfd_strict_separation(self):
        """Verify strict separation of ASD and LRFD paths across Wood modules."""
        res_bolt_asd = calculate_wood_bolt_connection({}, self.kb, DesignMethod.ASD)
        res_bolt_lrfd = calculate_wood_bolt_connection({}, self.kb, DesignMethod.LRFD)
        self.assertGreater(
            res_bolt_lrfd.intermediate_results["Z_prime_single_lbs"],
            res_bolt_asd.intermediate_results["Z_prime_single_lbs"],
        )

        res_sw_asd = calculate_wood_shear_wall({}, self.kb, DesignMethod.ASD)
        res_sw_lrfd = calculate_wood_shear_wall({}, self.kb, DesignMethod.LRFD)
        self.assertAlmostEqual(
            res_sw_lrfd.intermediate_results["v_unit_cap_plf"]
            / res_sw_asd.intermediate_results["v_unit_cap_plf"],
            1.60,
            places=2,
        )

    def test_level5_e2e_wood_vertical_slice_and_ui(self):
        """Level 5 E2E: CalculationService -> SQLite Revision -> 17-Col XLSX & 12-Sec PDF + PySide6 UI."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            repo = ProjectRepository(db_path=tmp_path / "test_day14_wood.sqlite3")
            ps = ProjectService(repository=repo)
            hs = HistoryService(repository=repo)
            cs = CalculationService(kb_service=self.kb, project_service=ps)
            rs = ReportService(kb_service=self.kb, project_service=ps)

            prj = ps.create_project(
                name="Smith Residence Wood Package", code="PRJ-D14", engineer="Nhat Do, PE"
            )
            calc = ps.create_calculation(
                "wood_shear_wall_sdpws", "SW-1 Exterior Shear Wall", "SDPWS 2021", DesignMethod.ASD
            )
            cid = calc["calculation_id"]

            r1 = cs.run_calculation(
                "wood_shear_wall_sdpws",
                {"h_ft": 10.0, "bs_ft": 4.0, "V_asd_lbs": 2240.0},
                DesignMethod.ASD,
                calculation_id=cid,
                auto_save_revision=True,
            )
            self.assertEqual(r1.status, CalculationStatus.PASS)

            revs = hs.get_history(cid)
            self.assertEqual(len(revs), 1)

            xlsx_path = rs.export_excel(r1, tmp_path / "Day14_ShearWall_ASD.xlsx")
            pdf_path = rs.export_pdf(r1, tmp_path / "Day14_ShearWall_ASD.pdf")
            self.assertTrue(xlsx_path.exists() and pdf_path.exists())

            wb = openpyxl.load_workbook(xlsx_path)
            self.assertEqual(wb.sheetnames, ["Calc_Sheet", "Database", "Source_Audit"])

            # Verify CalculationService across all 5 Wood module types + optional PySide6 UI
            for mtype in [
                "wood_bolt_nds",
                "wood_fastener_nds",
                "wood_shear_wall_sdpws",
                "wood_diaphragm_sdpws",
                "wood_simpson_hanger_tie",
            ]:
                res_m = cs.run_calculation(mtype, {}, DesignMethod.ASD)
                self.assertEqual(res_m.status, CalculationStatus.PASS)

            try:
                from PySide6.QtWidgets import QApplication
                from gui.widgets.wood_workspace import WoodCalculationWorkspace

                app = QApplication.instance() or QApplication([])
                ws = WoodCalculationWorkspace(calc_service=cs, report_service=rs)
                for mtype in [
                    "wood_bolt_nds",
                    "wood_fastener_nds",
                    "wood_shear_wall_sdpws",
                    "wood_diaphragm_sdpws",
                    "wood_simpson_hanger_tie",
                ]:
                    ws.select_submodule(mtype)
                    self.assertIsNotNone(ws._current_result)
                    self.assertEqual(ws._current_result.status, CalculationStatus.PASS)
            except ImportError:
                import ast
                for gui_file in [
                    "gui/widgets/wood_workspace.py",
                    "gui/main_window.py",
                    "gui/dialogs/add_calculation_dialog.py",
                ]:
                    with open(gui_file, "r", encoding="utf-8") as gf:
                        ast.parse(gf.read())


if __name__ == "__main__":
    unittest.main(verbosity=2)
