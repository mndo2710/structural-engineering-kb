"""WP-9 Verification Tests: ReferenceDataPort decoupling, 4-stage CalcStep traces, and WP-0 baseline parity."""

import ast
import json
from pathlib import Path
import re
from typing import Any, Callable, Dict, Tuple

import pytest

from app.services.knowledge_base_service import KnowledgeBaseService
from core.asce7.wind.awning import calculate_awning_canopy_loads
from core.asce7.wind.guardrail import calculate_guardrail_loads
from core.asce7.wind.parapet import calculate_parapet_wind
from core.asce7.wind.roof_overhang import calculate_roof_overhang_wind
from core.asce7.wind.trellis import calculate_trellis_loads
from core.common.calculation_result import CalcStep, CalculationResult, CalculationStatus, DesignMethod
from core.common.math_markup import math_markup_to_rich_html, validate_math_markup
from core.nds.connections.simpson_connectors import (
    calculate_simpson_hanger_tie,
    lookup_simpson_hurricane_tie,
    lookup_simpson_joist_hanger,
)
from core.nds.fasteners.bolts import calculate_wood_bolt_connection
from core.nds.fasteners.nails_screws import calculate_wood_fastener_connection
from core.nds.lateral.diaphragms import calculate_wood_diaphragm
from core.nds.lateral.shear_walls import calculate_wood_shear_wall
from core.ports.reference_data_port import ReferenceDataPort


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REPO_ROOT = Path(__file__).resolve().parent.parent

_MODULES: Dict[str, Callable[..., CalculationResult]] = {
    "asce7_parapet_wind": calculate_parapet_wind,
    "asce7_roof_overhang": calculate_roof_overhang_wind,
    "asce7_awning_canopy": calculate_awning_canopy_loads,
    "asce7_trellis_loads": calculate_trellis_loads,
    "ibc_guardrail_loads": calculate_guardrail_loads,
    "wood_bolt_lateral": calculate_wood_bolt_connection,
    "wood_fastener_nds": calculate_wood_fastener_connection,
    "wood_shear_wall_sdpws": calculate_wood_shear_wall,
    "wood_diaphragm_sdpws": calculate_wood_diaphragm,
    "wood_simpson_hanger_tie": calculate_simpson_hanger_tie,
}

# Verified WP-0 baselines (demand, capacity, dcr, status, key intermediate_results)
_WP0_BASELINES: Dict[Tuple[str, DesignMethod], Dict[str, Any]] = {
    ("asce7_parapet_wind", DesignMethod.ASD): {
        "demand": 436.75,
        "capacity": 650.0,
        "dcr": 0.672,
        "status": CalculationStatus.PASS,
        "intermediate": {"q_p_psf": 32.77, "p_gov_unfactored_psf": 89.13, "w_factored_plf": 71.31},
    },
    ("asce7_parapet_wind", DesignMethod.LRFD): {
        "demand": 727.91,
        "capacity": 975.0,
        "dcr": 0.747,
        "status": CalculationStatus.PASS,
        "intermediate": {"q_p_psf": 32.77, "p_gov_unfactored_psf": 89.13, "w_factored_plf": 118.84},
    },
    ("asce7_roof_overhang", DesignMethod.ASD): {
        "demand": 409.6,
        "capacity": 685.0,
        "dcr": 0.598,
        "status": CalculationStatus.PASS,
        "intermediate": {"q_h_psf": 30.47, "GCp_oh_net_neg": -3.5, "p_oh_uplift_psf": 90.65, "w_net_oh_plf": 94.38},
    },
    ("asce7_roof_overhang", DesignMethod.LRFD): {
        "demand": 706.0,
        "capacity": 1027.5,
        "dcr": 0.687,
        "status": CalculationStatus.PASS,
        "intermediate": {"q_h_psf": 30.47, "GCp_oh_net_neg": -3.5, "p_oh_uplift_psf": 90.65, "w_net_oh_plf": 159.7},
    },
    ("asce7_awning_canopy", DesignMethod.ASD): {
        "demand": 3056.4,
        "capacity": 1600.0,
        "dcr": 1.91,
        "status": CalculationStatus.FAIL,
        "intermediate": {"q_h_psf": 30.47, "GCp_net_pos": 1.18, "GCp_net_neg": -1.48, "M_up_wall_lb_ft": 1184.85},
    },
    ("asce7_awning_canopy", DesignMethod.LRFD): {
        "demand": 4626.0,
        "capacity": 2400.0,
        "dcr": 1.927,
        "status": CalculationStatus.FAIL,
        "intermediate": {"q_h_psf": 30.47, "F_p_lbs": 307.81, "q_down_gov_plf": 370.08, "M_up_wall_lb_ft": 2064.75},
    },
    ("asce7_trellis_loads", DesignMethod.ASD): {
        "demand": 1571.99,
        "capacity": 2000.0,
        "dcr": 0.786,
        "status": CalculationStatus.PASS,
        "intermediate": {"q_z_psf": 28.78, "C_f": 1.8, "F_W_horiz_lbs": 1047.99, "V_post_lbs": 157.2},
    },
    ("asce7_trellis_loads", DesignMethod.LRFD): {
        "demand": 2619.99,
        "capacity": 3000.0,
        "dcr": 0.873,
        "status": CalculationStatus.PASS,
        "intermediate": {"q_z_psf": 28.78, "C_f": 1.8, "H_wind_factored_lbs": 1047.99, "V_post_lbs": 262.0},
    },
    ("ibc_guardrail_loads", DesignMethod.ASD): {
        "demand": 988.24,
        "capacity": 1250.0,
        "dcr": 0.791,
        "status": CalculationStatus.PASS,
        "intermediate": {"V_post_gov_lbs": 200.0, "M_base_gov_lb_ft": 700.0, "T_bolt_gov_lbs": 988.24},
    },
    ("ibc_guardrail_loads", DesignMethod.LRFD): {
        "demand": 1581.18,
        "capacity": 2000.0,
        "dcr": 0.791,
        "status": CalculationStatus.PASS,
        "intermediate": {"V_post_gov_lbs": 320.0, "M_base_gov_lb_ft": 1120.0, "T_bolt_gov_lbs": 1581.18},
    },
    ("wood_bolt_lateral", DesignMethod.ASD): {
        "demand": 340.0,
        "capacity": 416.8,
        "dcr": 0.816,
        "status": CalculationStatus.PASS,
        "intermediate": {"governing_yield_mode": "Mode II", "Z_ref_lbs": 604.1, "C_Delta": 0.69, "Z_prime_single_lbs": 416.8},
    },
    ("wood_bolt_lateral", DesignMethod.LRFD): {
        "demand": 2.19,
        "capacity": 3.0,
        "dcr": 0.729,
        "status": CalculationStatus.PASS,
        "intermediate": {"governing_yield_mode": "Mode II", "Z_ref_lbs": 604.1, "C_Delta": 0.69, "Z_prime_single_lbs": 719.6},
    },
    ("wood_fastener_nds", DesignMethod.ASD): {
        "demand": 550.0,
        "capacity": 635.1,
        "dcr": 0.866,
        "status": CalculationStatus.PASS,
        "intermediate": {"C_d": 0.76, "Z_ref_lbs": 208.8, "Z_prime_single_lbs": 158.8, "Z_alpha_single_lbs": 197.3},
    },
    ("wood_fastener_nds", DesignMethod.LRFD): {
        "demand": 550.0,
        "capacity": 1096.4,
        "dcr": 0.502,
        "status": CalculationStatus.PASS,
        "intermediate": {"C_d": 0.76, "Z_ref_lbs": 208.8, "Z_prime_single_lbs": 274.1, "Z_alpha_single_lbs": 340.6},
    },
    ("wood_shear_wall_sdpws", DesignMethod.ASD): {
        "demand": 5300.0,
        "capacity": 5645.0,
        "dcr": 0.939,
        "status": CalculationStatus.PASS,
        "intermediate": {"C_ar": 0.9375, "v_unit_demand_plf": 560.0, "v_unit_cap_plf": 623.4, "f_c_perp_psi": 498.0},
    },
    ("wood_shear_wall_sdpws", DesignMethod.LRFD): {
        "demand": 7550.0,
        "capacity": 8064.3,
        "dcr": 0.936,
        "status": CalculationStatus.PASS,
        "intermediate": {"C_ar": 0.9375, "v_unit_demand_plf": 800.0, "v_unit_cap_plf": 997.5, "story_drift_in": 2.754},
    },
    ("wood_diaphragm_sdpws", DesignMethod.ASD): {
        "demand": 378.0,
        "capacity": 385.0,
        "dcr": 0.982,
        "status": CalculationStatus.PASS,
        "intermediate": {"v_unit_demand_plf": 378.0, "v_unit_cap_plf": 385.0, "delta_dia_ASD_in": 0.629, "F_drag_lbs": 5670.0},
    },
    ("wood_diaphragm_sdpws", DesignMethod.LRFD): {
        "demand": 8100.0,
        "capacity": 8357.1,
        "dcr": 0.969,
        "status": CalculationStatus.PASS,
        "intermediate": {"v_unit_demand_plf": 540.0, "v_unit_cap_plf": 616.0, "T_chord_max_lbs": 9720.0, "F_drag_lbs": 8100.0},
    },
    ("wood_simpson_hanger_tie", DesignMethod.ASD): {
        "demand": 0.846,
        "capacity": 1.0,
        "dcr": 0.846,
        "status": CalculationStatus.PASS,
        "intermediate": {"P_allow_125_lbs": 5615.0, "U_allow_hgr_lbs": 3165.0, "unity_U_plus_F2": 0.846, "rule_75_max_dcr": 0.88},
    },
    ("wood_simpson_hanger_tie", DesignMethod.LRFD): {
        "demand": 0.604,
        "capacity": 1.0,
        "dcr": 0.604,
        "status": CalculationStatus.PASS,
        "intermediate": {"P_allow_125_lbs": 7861.0, "U_allow_hgr_lbs": 4431.0, "unity_U_plus_F2": 0.604, "rule_75_max_dcr": 0.628},
    },
}


@pytest.fixture(scope="module")
def kb() -> KnowledgeBaseService:
    service = KnowledgeBaseService()
    assert isinstance(service, ReferenceDataPort)
    return service


class TestCoreDependencyInversion:
    def test_zero_forbidden_imports_in_core(self):
        forbidden_prefixes = ("app", "gui", "storage", "exporters", "PySide6")
        violations = []
        for py_file in sorted((_REPO_ROOT / "core").rglob("*.py")):
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith(forbidden_prefixes):
                            violations.append(f"{py_file.relative_to(_REPO_ROOT)}: import {alias.name}")
                elif isinstance(node, ast.ImportFrom) and node.module:
                    if node.module.startswith(forbidden_prefixes):
                        violations.append(f"{py_file.relative_to(_REPO_ROOT)}: from {node.module}")
        assert violations == []


class TestTraceMigrationAllModules:
    @pytest.mark.parametrize("module_id", list(_MODULES.keys()))
    @pytest.mark.parametrize("method", [DesignMethod.ASD, DesignMethod.LRFD])
    def test_trace_structure_provenance_round_trip_and_parity(
        self, kb: KnowledgeBaseService, module_id: str, method: DesignMethod
    ):
        fn = _MODULES[module_id]
        result = fn({}, kb, design_method=method, calculation_id=f"wp9-{module_id}-{method.value}")

        # 1. Trace presence & Rule 5 4-stage monotonic ordering
        assert isinstance(result.trace, tuple)
        assert len(result.trace) >= 4
        stages = [step.stage for step in result.trace]
        assert stages == sorted(stages)
        assert {1, 2, 3, 4}.issubset(set(stages))

        # 2. Markup validation, variables, and grounded RefSpecs
        for step in result.trace:
            assert isinstance(step, CalcStep)
            assert step.symbolic != ""
            assert step.substituted != ""
            assert validate_math_markup(step.symbolic) == step.symbolic
            assert validate_math_markup(step.substituted) == step.substituted
            assert "&ell;" not in math_markup_to_rich_html(step.symbolic)
            assert "&ell;" not in math_markup_to_rich_html(step.substituted)
            assert len(step.refs) >= 1
            for ref in step.refs:
                if ref.kb_reference_id is not None:
                    entry = kb.resolve_reference(ref.kb_reference_id)
                    assert ref.sha256 is not None and _SHA256_RE.match(ref.sha256)
                    assert ref.sha256 == entry["sha256"]
                if ref.source_path is not None:
                    assert (_REPO_ROOT / ref.source_path).exists()

        # 3. Deterministic JSON round-trip
        payload = json.dumps(result.to_dict())
        restored = CalculationResult.from_dict(json.loads(payload))
        assert restored == result

        # 4. Exact WP-0 numerical baseline parity
        expected = _WP0_BASELINES[(module_id, method)]
        assert result.demand == expected["demand"]
        assert result.capacity == expected["capacity"]
        assert result.dcr == expected["dcr"]
        assert result.status == expected["status"]
        for k, v in expected["intermediate"].items():
            assert result.intermediate_results[k] == v


class TestDefectFixesAndAlternativeBranches:
    def test_simpson_hurricane_tie_no_dead_hanger_branch(self, kb: KnowledgeBaseService):
        tie = lookup_simpson_hurricane_tie(kb, model_no="HUS210-2", species_group="DF/SP")
        assert "U_allow_lbs" in tie
        assert "F1_allow_lbs" in tie
        assert "F2_allow_lbs" in tie
        assert "P_allow_125_lbs" not in tie

        # Joist hanger benchmark lookup remains unchanged
        hgr = lookup_simpson_joist_hanger(kb, model_no="HUS210-2", species_group="DF/SP")
        assert hgr["P_allow_100_lbs"] == pytest.approx(5115.0)
        assert hgr["P_allow_125_lbs"] == pytest.approx(5615.0)
        assert hgr["U_allow_160_lbs"] == pytest.approx(3165.0)

    def test_nails_screws_pure_withdrawal_preserves_zero_shear(self, kb: KnowledgeBaseService):
        pure_withdrawal = calculate_wood_fastener_connection(
            {"V_demand_lbs": 0.0, "T_demand_lbs": 120.0},
            kb,
            DesignMethod.ASD,
        )
        assert pure_withdrawal.input_parameters["V_demand_lbs"] == pytest.approx(0.0)
        assert pure_withdrawal.limit_states[0].demand == pytest.approx(0.0)
        assert pure_withdrawal.limit_states[1].demand == pytest.approx(120.0)

        explicit_zero = calculate_wood_fastener_connection(
            {"V_demand_lbs": 0.0, "T_demand_lbs": 0.0},
            kb,
            DesignMethod.ASD,
        )
        assert explicit_zero.input_parameters["V_demand_lbs"] == pytest.approx(0.0)

    def test_alternative_branches_emit_valid_traces(self, kb: KnowledgeBaseService):
        cases = [
            calculate_awning_canopy_loads({"support_type": "TieBack_Hanger"}, kb, DesignMethod.LRFD),
            calculate_trellis_loads({"support_condition": "Wall_Ledger"}, kb, DesignMethod.ASD),
            calculate_wood_bolt_connection(
                {"shear_planes": "Double Shear", "n_rows": 2, "n_bolts_per_row": 2},
                kb,
                DesignMethod.LRFD,
            ),
            calculate_wood_fastener_connection({"fastener_type": "Common Nail"}, kb, DesignMethod.ASD),
            calculate_wood_fastener_connection({"fastener_type": "Wood Screw"}, kb, DesignMethod.LRFD),
            calculate_wood_fastener_connection(
                {"fastener_type": "Simpson SDS Screw", "side_material": "14 ga Steel"},
                kb,
                DesignMethod.ASD,
            ),
        ]
        for res in cases:
            assert len(res.trace) >= 4
            stages = [s.stage for s in res.trace]
            assert stages == sorted(stages)
            assert CalculationResult.from_dict(json.loads(json.dumps(res.to_dict()))) == res
