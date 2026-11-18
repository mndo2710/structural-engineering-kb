"""Day 15 Verification Tests: AISC 360-22 Structural Steel Connection Engines (core/aisc360/)."""

import ast
import json
from pathlib import Path
import re
from typing import Any, Callable, Dict, Tuple

import pytest

from app.services.knowledge_base_service import KnowledgeBaseService
from core.aisc360 import (
    calculate_steel_angle_connection,
    calculate_steel_base_plate,
    calculate_steel_bolted_connection,
    calculate_steel_hss_connection,
    calculate_steel_shear_tab,
    calculate_steel_welded_connection,
)
from core.common.calculation_result import CalcStep, CalculationResult, CalculationStatus, DesignMethod
from core.common.exceptions import InputValidationError
from core.common.math_markup import math_markup_to_rich_html, validate_math_markup
from core.ports.reference_data_port import ReferenceDataPort


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REPO_ROOT = Path(__file__).resolve().parent.parent

_STEEL_MODULES: Dict[str, Callable[..., CalculationResult]] = {
    "aisc_bolt_bearing": calculate_steel_bolted_connection,
    "aisc_welded_connection": calculate_steel_welded_connection,
    "aisc_shear_tab": calculate_steel_shear_tab,
    "aisc_angle_connection": calculate_steel_angle_connection,
    "aisc_base_plate": calculate_steel_base_plate,
    "aisc_hss_connection": calculate_steel_hss_connection,
}

# Verified Day 15 benchmarks matching Section 7 worked examples + authoritative CSVs
_DAY15_BENCHMARKS: Dict[Tuple[str, DesignMethod], Dict[str, Any]] = {
    ("aisc_bolt_bearing", DesignMethod.ASD): {
        "demand": 45.0,
        "capacity": 46.22,
        "dcr": 0.974,
        "status": CalculationStatus.PASS,
        "gov_step": "S4_RUPTURE",
    },
    ("aisc_bolt_bearing", DesignMethod.LRFD): {
        "demand": 68.0,
        "capacity": 69.33,
        "dcr": 0.981,
        "status": CalculationStatus.PASS,
        "gov_step": "S4_RUPTURE",
    },
    ("aisc_welded_connection", DesignMethod.ASD): {
        "demand": 3.48,
        "capacity": 3.712,
        "dcr": 0.938,
        "status": CalculationStatus.PASS,
        "gov_step": "S2_WELD",
    },
    ("aisc_welded_connection", DesignMethod.LRFD): {
        "demand": 5.22,
        "capacity": 5.568,
        "dcr": 0.938,
        "status": CalculationStatus.PASS,
        "gov_step": "S2_WELD",
    },
    ("aisc_shear_tab", DesignMethod.ASD): {
        "demand": 30.0,
        "capacity": 29.60,
        "dcr": 1.014,
        "status": CalculationStatus.FAIL,
        "gov_step": "S2_BOLT",
    },
    ("aisc_shear_tab", DesignMethod.LRFD): {
        "demand": 45.0,
        "capacity": 44.39,
        "dcr": 1.014,
        "status": CalculationStatus.FAIL,
        "gov_step": "S2_BOLT",
    },
    ("aisc_angle_connection", DesignMethod.ASD): {
        "demand": 12.0,
        "capacity": 14.83,
        "dcr": 0.809,
        "status": CalculationStatus.PASS,
        "gov_step": "S2_BOLT",
    },
    ("aisc_angle_connection", DesignMethod.LRFD): {
        "demand": 18.0,
        "capacity": 22.25,
        "dcr": 0.809,
        "status": CalculationStatus.PASS,
        "gov_step": "S2_BOLT",
    },
    ("aisc_base_plate", DesignMethod.ASD): {
        "demand": 2.944,
        "capacity": 2.944,
        "dcr": 1.000,
        "status": CalculationStatus.PASS,
        "gov_step": "S2_BEARING",
    },
    ("aisc_base_plate", DesignMethod.LRFD): {
        "demand": 4.420,
        "capacity": 4.420,
        "dcr": 1.000,
        "status": CalculationStatus.PASS,
        "gov_step": "S2_BEARING",
    },
    ("aisc_hss_connection", DesignMethod.ASD): {
        "demand": 160.0,
        "capacity": 276.08,
        "dcr": 0.580,
        "status": CalculationStatus.PASS,
        "gov_step": "S2_CHORD_MIP",
    },
    ("aisc_hss_connection", DesignMethod.LRFD): {
        "demand": 240.0,
        "capacity": 414.12,
        "dcr": 0.580,
        "status": CalculationStatus.PASS,
        "gov_step": "S2_CHORD_MIP",
    },
}


@pytest.fixture(scope="module")
def kb() -> KnowledgeBaseService:
    return KnowledgeBaseService()


def _assert_valid_trace_and_roundtrip(res: CalculationResult, kb: KnowledgeBaseService) -> None:
    assert len(res.trace) >= 4
    stages = [int(s.stage) for s in res.trace]
    assert stages == sorted(stages)
    assert set(stages) == {1, 2, 3, 4}

    seen_ids = set()
    for step in res.trace:
        assert isinstance(step, CalcStep)
        assert step.step_id not in seen_ids
        seen_ids.add(step.step_id)
        assert validate_math_markup(step.symbolic)
        assert validate_math_markup(step.substituted)
        assert "&ell;" not in math_markup_to_rich_html(step.substituted)
        assert len(step.refs) >= 1
        for ref in step.refs:
            if ref.kb_reference_id is not None:
                entry = kb.resolve_reference(ref.kb_reference_id)
                assert ref.sha256 is not None and _SHA256_RE.match(ref.sha256)
                assert ref.sha256 == entry["sha256"]
            if ref.source_path is not None:
                assert (_REPO_ROOT / ref.source_path).exists()

    roundtrip = CalculationResult.from_dict(json.loads(json.dumps(res.to_dict())))
    assert roundtrip == res


class TestArchitectureIsolationDay15:
    def test_core_aisc360_zero_concrete_app_or_gui_imports(self):
        forbidden = ("app.", "gui.", "storage.", "exporters.", "PySide6", "pandas")
        for py_file in sorted((_REPO_ROOT / "core" / "aisc360").glob("*.py")):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert not alias.name.startswith(forbidden), f"{py_file} imports {alias.name}"
                elif isinstance(node, ast.ImportFrom) and node.module:
                    assert not node.module.startswith(forbidden), f"{py_file} imports from {node.module}"

    def test_kb_satisfies_reference_data_port(self, kb: KnowledgeBaseService):
        assert isinstance(kb, ReferenceDataPort)


class TestDay15BenchmarksAndTraces:
    @pytest.mark.parametrize("module_id", list(_STEEL_MODULES.keys()))
    @pytest.mark.parametrize("method", [DesignMethod.ASD, DesignMethod.LRFD])
    def test_benchmark_outputs_and_4_stage_traces(
        self, module_id: str, method: DesignMethod, kb: KnowledgeBaseService
    ):
        fn = _STEEL_MODULES[module_id]
        res = fn({}, kb, method)
        assert res.module_id == module_id
        assert res.design_method == method
        assert res.governing_limit_state is not None

        _assert_valid_trace_and_roundtrip(res, kb)

        exp = _DAY15_BENCHMARKS[(module_id, method)]
        assert res.governing_limit_state.step_id == exp["gov_step"]
        assert res.demand == pytest.approx(exp["demand"], rel=1e-3)
        assert res.capacity == pytest.approx(exp["capacity"], rel=1e-3)
        assert res.dcr == pytest.approx(exp["dcr"], abs=0.002)
        assert res.status == exp["status"]


class TestDay15BranchesAndEdgeCases:
    def test_bolts_combined_tension_shear_and_eccentric_icor(self, kb: KnowledgeBaseService):
        res_inter = calculate_steel_bolted_connection(
            {"V_u_kips": 40.0, "T_bolt_u_kips": 25.0},
            kb,
            DesignMethod.LRFD,
        )
        assert any(ls.step_id == "S2_INTER" for ls in res_inter.limit_states)
        _assert_valid_trace_and_roundtrip(res_inter, kb)

        res_ecc = calculate_steel_bolted_connection(
            {"n_lines": 1, "n_bolts_per_line": 4, "s_in": 3.0, "e_x_in": 3.0, "V_a_kips": 25.0},
            kb,
            DesignMethod.ASD,
        )
        assert res_ecc.intermediate_results["C_icor"] == pytest.approx(2.81, abs=0.01)
        assert res_ecc.status == CalculationStatus.PASS

        res_bad_edge = calculate_steel_bolted_connection({"l_e_in": 0.5}, kb, DesignMethod.LRFD)
        assert res_bad_edge.status == CalculationStatus.FAIL

    def test_welds_alternative_configs_and_size_checks(self, kb: KnowledgeBaseService):
        res_dbl = calculate_steel_welded_connection(
            {"weld_config": "double_vertical", "d_w_in": 9.0, "e_face_in": 0.0, "V_u_kips": 50.0},
            kb,
            DesignMethod.LRFD,
        )
        assert res_dbl.intermediate_results["L_w_in"] == pytest.approx(18.0)
        assert res_dbl.status == CalculationStatus.PASS
        _assert_valid_trace_and_roundtrip(res_dbl, kb)

        res_too_small = calculate_steel_welded_connection(
            {"w_leg_in": 0.125, "t_plate_in": 0.50}, kb, DesignMethod.ASD
        )
        assert res_too_small.status == CalculationStatus.FAIL

    def test_shear_tab_hss_support_and_passing_load(self, kb: KnowledgeBaseService):
        res_hss_sup = calculate_steel_shear_tab(
            {"support_section": "HSS8x8x3/8", "support_grade": "A500 Gr. C", "V_u_kips": 42.0},
            kb,
            DesignMethod.LRFD,
        )
        assert res_hss_sup.status == CalculationStatus.PASS
        assert any("HSS" in s.title for s in res_hss_sup.trace)
        _assert_valid_trace_and_roundtrip(res_hss_sup, kb)

    def test_double_angle_double_shear_and_uncoped(self, kb: KnowledgeBaseService):
        res_2l = calculate_steel_angle_connection(
            {"connection_type": "Double Angle", "is_coped": False, "V_u_kips": 25.0},
            kb,
            DesignMethod.LRFD,
        )
        assert res_2l.intermediate_results["is_double_angle"] is True
        assert res_2l.status == CalculationStatus.PASS
        _assert_valid_trace_and_roundtrip(res_2l, kb)

    def test_base_plate_concentric_and_osha_failure(self, kb: KnowledgeBaseService):
        res_conc = calculate_steel_base_plate(
            {"P_u_kips": 250.0, "M_u_kip_in": 0.0, "V_u_kips": 5.0},
            kb,
            DesignMethod.LRFD,
        )
        assert res_conc.intermediate_results["T_rods_kips"] == pytest.approx(0.0)
        assert res_conc.status == CalculationStatus.PASS

        res_osha = calculate_steel_base_plate({"n_rods_total": 2}, kb, DesignMethod.ASD)
        assert res_osha.status == CalculationStatus.FAIL

    def test_hss_matched_beta_one_and_round_hss(self, kb: KnowledgeBaseService):
        res_beta1 = calculate_steel_hss_connection(
            {"branch_section": "HSS8x8x3/8", "chord_section": "HSS8x8x3/8", "M_u_ip_kip_in": 300.0},
            kb,
            DesignMethod.LRFD,
        )
        assert res_beta1.intermediate_results["beta"] == pytest.approx(1.0)
        assert res_beta1.status == CalculationStatus.PASS

        res_round = calculate_steel_hss_connection(
            {
                "chord_section": "HSS8.625X0.322",
                "branch_section": "HSS6.000X0.250",
                "chord_grade": "A500 Gr. B",
                "branch_grade": "A500 Gr. B",
                "M_u_ip_kip_in": 120.0,
                "P_uo_chord_kips": 40.0,
            },
            kb,
            DesignMethod.LRFD,
        )
        assert res_round.intermediate_results["beta"] == pytest.approx(6.0 / 8.63, abs=0.01)
        assert res_round.status == CalculationStatus.PASS
        _assert_valid_trace_and_roundtrip(res_round, kb)

    def test_blank_inputs_return_incomplete_and_negative_raises(self, kb: KnowledgeBaseService):
        inc = calculate_steel_bolted_connection({"d_b_in": None}, kb, DesignMethod.ASD)
        assert inc.status == CalculationStatus.INCOMPLETE
        assert inc.trace == ()
        assert len(inc.incomplete_reasons) >= 1

        with pytest.raises(InputValidationError):
            calculate_steel_base_plate({"fc_ksi": -4.0}, kb, DesignMethod.LRFD)
