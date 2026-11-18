"""Day 16 Verification Tests: ACI 318-19 Concrete & TMS 402-22 CMU Anchorage Engines."""

import ast
import json
from pathlib import Path
import re
from typing import Any, Callable, Dict, Tuple

import pytest

from app.services.knowledge_base_service import KnowledgeBaseService
from core.aci318 import calculate_concrete_anchorage
from core.common.calculation_result import CalcStep, CalculationResult, CalculationStatus, DesignMethod
from core.common.exceptions import InputValidationError
from core.common.math_markup import math_markup_to_rich_html, validate_math_markup
from core.ports.reference_data_port import ReferenceDataPort
from core.tms402 import calculate_cmu_anchorage, calculate_embedded_steel_post


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REPO_ROOT = Path(__file__).resolve().parent.parent

_CONCRETE_CMU_MODULES: Dict[str, Callable[..., CalculationResult]] = {
    "aci318_anchor_tension_shear": calculate_concrete_anchorage,
    "tms402_cmu_anchorage": calculate_cmu_anchorage,
    "tms402_embedded_post": calculate_embedded_steel_post,
}

# Verified Day 16 benchmarks matching Section 7 worked examples + authoritative CSVs
_DAY16_BENCHMARKS: Dict[Tuple[str, DesignMethod], Dict[str, Any]] = {
    ("aci318_anchor_tension_shear", DesignMethod.ASD): {
        "demand": 3150.0,
        "capacity": 6881.7,
        "dcr": 0.458,
        "status": CalculationStatus.PASS,
        "gov_step": "S2_N_STEEL",
    },
    ("aci318_anchor_tension_shear", DesignMethod.LRFD): {
        "demand": 4500.0,
        "capacity": 9831.0,
        "dcr": 0.458,
        "status": CalculationStatus.PASS,
        "gov_step": "S2_N_STEEL",
    },
    ("tms402_cmu_anchorage", DesignMethod.ASD): {
        "demand": 2500.0,
        "capacity": 4881.6,
        "dcr": 0.512,
        "status": CalculationStatus.PASS,
        "gov_step": "S2_T_STEEL",
    },
    ("tms402_cmu_anchorage", DesignMethod.LRFD): {
        "demand": 3571.0,
        "capacity": 7322.4,
        "dcr": 0.488,
        "status": CalculationStatus.PASS,
        "gov_step": "S2_T_STEEL",
    },
    ("tms402_embedded_post", DesignMethod.ASD): {
        "demand": 6.30,
        "capacity": 8.00,
        "dcr": 0.787,
        "status": CalculationStatus.PASS,
        "gov_step": "S3_BEARING",
    },
    ("tms402_embedded_post", DesignMethod.LRFD): {
        "demand": 8.16,
        "capacity": 9.82,
        "dcr": 0.831,
        "status": CalculationStatus.PASS,
        "gov_step": "S4_BOND_BEAM",
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


class TestArchitectureIsolationDay16:
    def test_core_aci318_and_tms402_zero_concrete_app_or_gui_imports(self):
        forbidden = ("app.", "gui.", "storage.", "exporters.", "PySide6", "pandas")
        for pkg in ("aci318", "tms402"):
            for py_file in sorted((_REPO_ROOT / "core" / pkg).glob("*.py")):
                tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            assert not alias.name.startswith(forbidden), f"{py_file} imports {alias.name}"
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        assert not node.module.startswith(forbidden), f"{py_file} imports from {node.module}"

    def test_kb_satisfies_reference_data_port(self, kb: KnowledgeBaseService):
        assert isinstance(kb, ReferenceDataPort)


class TestDay16BenchmarksAndTraces:
    @pytest.mark.parametrize("module_id", list(_CONCRETE_CMU_MODULES.keys()))
    @pytest.mark.parametrize("method", [DesignMethod.ASD, DesignMethod.LRFD])
    def test_benchmark_outputs_and_4_stage_traces(
        self, module_id: str, method: DesignMethod, kb: KnowledgeBaseService
    ):
        fn = _CONCRETE_CMU_MODULES[module_id]
        res = fn({}, kb, method)
        assert res.module_id == module_id
        assert res.design_method == method
        assert res.governing_limit_state is not None

        _assert_valid_trace_and_roundtrip(res, kb)

        exp = _DAY16_BENCHMARKS[(module_id, method)]
        assert res.governing_limit_state.step_id == exp["gov_step"]
        assert res.demand == pytest.approx(exp["demand"], rel=1e-3)
        assert res.capacity == pytest.approx(exp["capacity"], rel=1e-3)
        assert res.dcr == pytest.approx(exp["dcr"], abs=0.002)
        assert res.status == exp["status"]


class TestDay16BranchesAndEdgeCases:
    def test_aci318_group_combined_shear_and_adhesive_branch(self, kb: KnowledgeBaseService):
        res_grp = calculate_concrete_anchorage(
            {
                "n_x": 2,
                "n_y": 2,
                "s_x_in": 8.0,
                "s_y_in": 8.0,
                "N_ua_lbs": 12000.0,
                "V_ua_lbs": 6000.0,
            },
            kb,
            DesignMethod.LRFD,
        )
        assert res_grp.status == CalculationStatus.PASS
        assert res_grp.governing_limit_state.step_id in {"S4_INTER", "S2_N_STEEL", "S3_SHEAR"}
        _assert_valid_trace_and_roundtrip(res_grp, kb)

        res_adh = calculate_concrete_anchorage(
            {"anchor_type": "Adhesive", "tau_k_psi": 1350.0, "N_ua_lbs": 4000.0},
            kb,
            DesignMethod.LRFD,
        )
        assert res_adh.status == CalculationStatus.PASS
        _assert_valid_trace_and_roundtrip(res_adh, kb)

    def test_cmu_anchorage_group_overlap_bent_bar_and_embed_fail(self, kb: KnowledgeBaseService):
        res_grp = calculate_cmu_anchorage(
            {
                "bolt_type": "Bent Bar",
                "e_b_bent_in": 2.0,
                "n_anchors": 2,
                "s_anchors_in": 8.0,
                "b_af_lbs": 2500.0,
                "b_vf_lbs": 1200.0,
            },
            kb,
            DesignMethod.ASD,
        )
        assert res_grp.intermediate_results["A_pt_in2"] > 113.10
        assert res_grp.status == CalculationStatus.PASS
        _assert_valid_trace_and_roundtrip(res_grp, kb)

        res_short = calculate_cmu_anchorage({"l_b_in": 1.5}, kb, DesignMethod.ASD)
        assert res_short.status == CalculationStatus.FAIL

    def test_embedded_post_flagpole_path_and_overload(self, kb: KnowledgeBaseService):
        res_flagpole = calculate_embedded_steel_post(
            {
                "transfer_path": "bearing_stress_block",
                "medium": "CONCRETE",
                "t_wall_in": 12.0,
                "L_e_in": 36.0,
                "H_post_in": 48.0,
                "S1_bearing_psf_per_ft": 4500.0,
                "V_a_kips": 1.20,
            },
            kb,
            DesignMethod.ASD,
        )
        assert res_flagpole.status == CalculationStatus.PASS
        _assert_valid_trace_and_roundtrip(res_flagpole, kb)

        res_fail = calculate_embedded_steel_post({"V_u_kips": 6.0}, kb, DesignMethod.LRFD)
        assert res_fail.status == CalculationStatus.FAIL

    def test_blank_inputs_return_incomplete_and_invalid_raises(self, kb: KnowledgeBaseService):
        inc = calculate_concrete_anchorage({"fc_psi": ""}, kb, DesignMethod.LRFD)
        assert inc.status == CalculationStatus.INCOMPLETE
        assert inc.trace == ()

        inc_cmu = calculate_cmu_anchorage({"_require_complete": True}, kb, DesignMethod.ASD)
        assert inc_cmu.status == CalculationStatus.INCOMPLETE

        with pytest.raises(InputValidationError):
            calculate_embedded_steel_post({"fm_psi": 0.0}, kb, DesignMethod.ASD)
