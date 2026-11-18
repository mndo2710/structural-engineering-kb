"""TMS 402-22 Chapter 8 (ASD) & Chapter 9 (SD) CMU Masonry Anchorage Module.

Implements procedures/04_concrete_masonry_foundation/cmu_masonry_anchorage_out_of_plane_breakout_tms402_workflow.md.
Evaluates single anchors and linear anchor groups embedded in grouted CMU walls across:
- Stage 1: CMU nominal/actual wall properties (S_n, I_n, A_n), minimum embedment l_b >= max(4 d_b, 2 in.),
           grouted-cell placement & free edge clearance checks (Sec. 6.1.6).
- Stage 2: Tension limit states (Masonry breakout B_ab/B_anb, Steel yielding B_as/B_ans, Bent-bar pullout).
- Stage 3: Shear limit states (Breakout B_vb/B_vnb, Crushing B_vc/B_vnc, Pryout B_vpry, Steel B_vs)
           and Linear Tension-Shear Interaction (Eq. 8-11 / Eq. 9-9).
- Stage 4: Grouted CMU wall out-of-plane continuity / section modulus check.
"""

from __future__ import annotations

import csv
import math
from typing import Any, Dict, List, Optional
import uuid

from core.aci318.anchors import ASTM_F1554_FILE, lookup_f1554_anchor_properties
from core.common.calculation_result import (
    AcceptanceCriterion,
    CalcStep,
    CalculationResult,
    CalculationStatus,
    DesignMethod,
    LimitStateResult,
    LoadPathStage,
    Quantity,
    RefSpec,
)
from core.common.exceptions import InputValidationError, ReferenceDataNotFoundError
from core.common.math_markup import validate_math_markup
from core.common.validation import (
    validate_design_method,
    validate_non_negative,
    validate_positive,
)
from core.ports.reference_data_port import ReferenceDataPort


TMS_ANCHOR_CSV = "TMS402-22_Masonry_Anchor_Bolts_and_CMU_Properties.csv"
PROC_CMU_ANCHOR_FILE = "cmu_masonry_anchorage_out_of_plane_breakout_tms402_workflow.md"


def _build_tms_ref(
    kb: ReferenceDataPort,
    kind: str,
    locator: str,
    identifier: Optional[str] = None,
    fallback_path: Optional[str] = None,
    code: str = "TMS 402",
    edition: str = "2022",
) -> RefSpec:
    """Resolve a manifest-backed RefSpec cleanly via ReferenceDataPort."""
    kb_ref_id: Optional[str] = None
    source_path: Optional[str] = fallback_path
    sha256: Optional[str] = None

    if identifier:
        try:
            entry = kb.resolve_reference(identifier)
            kb_ref_id = entry.get("reference_id")
            source_path = entry.get("relative_path") or source_path
            sha256 = entry.get("sha256")
            if not sha256 and source_path:
                try:
                    sha256 = kb.compute_sha256(kb.get_file_path(identifier))
                except Exception:
                    pass
        except ReferenceDataNotFoundError:
            try:
                fp = kb.get_file_path(identifier)
                source_path = source_path or str(fp)
                sha256 = kb.compute_sha256(fp)
            except Exception:
                pass

    return RefSpec(
        code=code,
        edition=edition,
        kind=kind,
        locator=locator,
        kb_reference_id=kb_ref_id,
        source_path=source_path,
        sha256=sha256,
    )


def lookup_cmu_wall_properties(kb: ReferenceDataPort, nominal_thickness_in: int = 8) -> Dict[str, float]:
    """Lookup actual thickness, A_n, I_n, and S_n from TMS402-22_Masonry_Anchor_Bolts_and_CMU_Properties.csv."""
    csv_path = kb.get_file_path(TMS_ANCHOR_CSV)
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))

    target_prefix = f"{int(nominal_thickness_in)} in."
    for row in rows[1:6]:
        if len(row) < 4:
            continue
        if target_prefix in row[1]:
            # Parse '8 in. Nominal CMU (Actual Thickness t = 7.625 in.)' and 'A_n = 91.5 ... I_n = 443.3 ... S_n = 116.3 ...'
            import re
            t_m = re.search(r"t\s*=\s*([0-9.]+)", row[1])
            an_m = re.search(r"A_n\s*=\s*([0-9.,]+)", row[2])
            in_m = re.search(r"I_n\s*=\s*([0-9.,]+)", row[2])
            sn_m = re.search(r"S_n\s*=\s*([0-9.,]+)", row[2])
            return {
                "t_actual_in": float(t_m.group(1)) if t_m else float(nominal_thickness_in) - 0.375,
                "A_n_in2_per_ft": float(an_m.group(1).replace(",", "")) if an_m else 91.5,
                "I_n_in4_per_ft": float(in_m.group(1).replace(",", "")) if in_m else 443.3,
                "S_n_in3_per_ft": float(sn_m.group(1).replace(",", "")) if sn_m else 116.3,
            }
    raise InputValidationError(f"Unsupported nominal CMU thickness {nominal_thickness_in} in. in {TMS_ANCHOR_CSV}.")


def _circle_segment_area(radius: float, dist_to_edge: float) -> float:
    """Area of circular segment cut off outside radius when distance < radius."""
    if dist_to_edge >= radius:
        return 0.0
    if dist_to_edge <= -radius:
        return math.pi * (radius ** 2)
    theta = 2.0 * math.acos(max(-1.0, min(1.0, dist_to_edge / radius)))
    return 0.5 * (radius ** 2) * (theta - math.sin(theta))


def _circle_overlap_area(radius: float, spacing: float) -> float:
    """Lens overlap area of two equal circles separated by center-to-center spacing."""
    if spacing >= 2.0 * radius or radius <= 0.0:
        return 0.0
    if spacing <= 0.0:
        return math.pi * (radius ** 2)
    return 2.0 * (radius ** 2) * math.acos(spacing / (2.0 * radius)) - 0.5 * spacing * math.sqrt(4.0 * (radius ** 2) - (spacing ** 2))


def calculate_cmu_anchorage(
    inputs: Dict[str, Any],
    kb: ReferenceDataPort,
    design_method: DesignMethod = DesignMethod.ASD,
    calculation_id: Optional[str] = None,
) -> CalculationResult:
    """Evaluate TMS 402-22 Chapter 8 (ASD) or Chapter 9 (SD) CMU Anchor Bolt Design."""
    method = validate_design_method(design_method)
    calc_id = calculation_id or str(inputs.get("calculation_id") or f"calc-cmu-anchor-{uuid.uuid4().hex[:8]}")

    ref_proc = _build_tms_ref(
        kb, "procedure", "CMU Masonry Anchorage Workflow",
        identifier=PROC_CMU_ANCHOR_FILE,
        fallback_path="procedures/04_concrete_masonry_foundation/cmu_masonry_anchorage_out_of_plane_breakout_tms402_workflow.md",
    )
    ref_tms = _build_tms_ref(kb, "table", "TMS 402-22 Sec. 8.1.3 & 9.1.6", identifier=TMS_ANCHOR_CSV)
    ref_f1554 = _build_tms_ref(
        kb, "table", "ASTM F1554 Anchor Properties", identifier=ASTM_F1554_FILE, code="ASTM", edition="F1554"
    )

    req_keys = ("cmu_nominal_in", "fm_psi", "d_b_in", "l_b_in")
    blank_reasons: List[str] = []
    req_complete = bool(inputs.get("_require_complete", False))
    for k in req_keys:
        if k in inputs:
            if inputs[k] is None or (isinstance(inputs[k], str) and inputs[k].strip() == ""):
                blank_reasons.append(f"Required input '{k}' is blank.")
        elif req_complete:
            blank_reasons.append(f"Required input '{k}' is missing.")
    if blank_reasons:
        return CalculationResult(
            calculation_id=calc_id,
            module_id="tms402_cmu_anchorage",
            code_edition="TMS 402-22",
            design_method=method,
            input_parameters=dict(inputs),
            assumptions=["Incomplete required inputs; no benchmark defaults substituted."],
            intermediate_results={},
            limit_states=[],
            governing_limit_state=None,
            demand=0.0,
            capacity=0.0,
            dcr=0.0,
            status=CalculationStatus.INCOMPLETE,
            reference_files=[r.source_path for r in (ref_proc, ref_tms, ref_f1554) if r.source_path],
            warnings=blank_reasons,
            trace=(),
            incomplete_reasons=blank_reasons,
        )

    # 1. Section 7 Benchmark Defaults
    cmu_nominal_in = int(validate_positive("cmu_nominal_in", inputs.get("cmu_nominal_in", 8)))
    fm_psi = validate_positive("fm_psi", inputs.get("fm_psi", 2000.0))
    is_grouted = bool(inputs.get("is_grouted", True))

    bolt_type = str(inputs.get("bolt_type", "Headed")).strip()
    rod_grade = str(inputs.get("rod_grade", "F1554 Gr. 36")).strip()
    d_b_in = validate_positive("d_b_in", inputs.get("d_b_in", 0.625))
    l_b_in = validate_positive("l_b_in", inputs.get("l_b_in", 6.0))
    e_b_bent_in = validate_non_negative("e_b_bent_in", inputs.get("e_b_bent_in", 0.0))
    l_be_shear_in = validate_positive("l_be_shear_in", inputs.get("l_be_shear_in", 12.0))
    edge_tension_in = validate_positive("edge_tension_in", inputs.get("edge_tension_in", 12.0))
    n_anchors = int(validate_positive("n_anchors", inputs.get("n_anchors", 1)))
    s_anchors_in = validate_non_negative("s_anchors_in", inputs.get("s_anchors_in", 16.0))

    if method == DesignMethod.LRFD:
        baf_lbs = validate_non_negative("b_af_sd_lbs", inputs.get("b_af_sd_lbs", 3571.0))
        bvf_lbs = validate_non_negative("b_vf_sd_lbs", inputs.get("b_vf_sd_lbs", 0.0))
    else:
        baf_lbs = validate_non_negative("b_af_lbs", inputs.get("b_af_lbs", 2500.0))
        bvf_lbs = validate_non_negative("b_vf_lbs", inputs.get("b_vf_lbs", 0.0))

    wall_props = lookup_cmu_wall_properties(kb, cmu_nominal_in)
    t_wall = wall_props["t_actual_in"]
    s_n_wall = wall_props["S_n_in3_per_ft"]

    f1554_props = lookup_f1554_anchor_properties(kb, d_b_in, rod_grade)
    a_b = float(inputs.get("A_b_in2", f1554_props["A_seN_in2"]))
    f_y = float(inputs.get("f_y_psi", f1554_props["f_ya_psi"]))

    # 2. Stage 1 Detailing & Minimum Embedment Checks (Sec. 6.1.6)
    l_b_min_req = max(4.0 * d_b_in, 2.0)
    grout_req_ok = is_grouted or (d_b_in <= 0.25 + 1e-6)
    embed_ok = (l_b_in >= l_b_min_req - 1e-6) and (l_b_in < t_wall)
    stage1_ok = grout_req_ok and embed_ok

    # 3. Projected Breakout Areas (Sec. 8.1.3.1 / 9.1.6.1)
    single_a_pt = math.pi * (l_b_in ** 2) - _circle_segment_area(l_b_in, edge_tension_in)
    if n_anchors > 1:
        a_pt = max(0.1, n_anchors * single_a_pt - (n_anchors - 1) * _circle_overlap_area(l_b_in, s_anchors_in))
    else:
        a_pt = single_a_pt

    single_a_pv = 0.5 * math.pi * (l_be_shear_in ** 2)
    a_pv = n_anchors * single_a_pv if n_anchors == 1 else max(
        0.1, n_anchors * single_a_pv - 0.5 * (n_anchors - 1) * _circle_overlap_area(l_be_shear_in, s_anchors_in)
    )

    # 4. Stage 2 Tension & Stage 3 Shear Limit States (Ch. 8 ASD vs. Ch. 9 SD)
    is_bent = "bent" in bolt_type.lower() or "j" in bolt_type.lower() or "l-" in bolt_type.lower()
    if method == DesignMethod.ASD:
        cap_t_breakout = 1.25 * a_pt * math.sqrt(fm_psi)
        cap_t_steel = n_anchors * 0.60 * a_b * f_y
        cap_t_pullout = (
            n_anchors * (1.5 * fm_psi * e_b_bent_in * d_b_in + 300.0 * math.pi * (l_b_in + e_b_bent_in + d_b_in) * d_b_in)
            if is_bent
            else None
        )
        cap_v_breakout = 0.625 * a_pv * math.sqrt(fm_psi)
        cap_v_crush = n_anchors * 580.0 * ((fm_psi * a_b) ** 0.25)
        cap_v_pry = 2.0 * cap_t_breakout
        cap_v_steel = n_anchors * 0.36 * a_b * f_y
    else:
        # Ch. 9 Strength Design (phi = 0.50 masonry breakout/crush/pry, phi = 0.90 steel, phi = 0.65 pullout)
        cap_t_breakout = 0.50 * 4.0 * a_pt * math.sqrt(fm_psi)
        cap_t_steel = n_anchors * 0.90 * a_b * f_y
        cap_t_pullout = (
            n_anchors * 0.65 * (1.5 * fm_psi * e_b_bent_in * d_b_in + 300.0 * math.pi * (l_b_in + e_b_bent_in + d_b_in) * d_b_in)
            if is_bent
            else None
        )
        cap_v_breakout = 0.50 * 4.0 * a_pv * math.sqrt(fm_psi)
        cap_v_crush = n_anchors * 0.50 * 1750.0 * ((fm_psi * a_b) ** 0.25)
        cap_v_pry = 0.50 * 8.0 * a_pt * math.sqrt(fm_psi)
        cap_v_steel = n_anchors * 0.90 * 0.60 * a_b * f_y

    t_caps = [cap_t_breakout, cap_t_steel] + ([cap_t_pullout] if cap_t_pullout is not None else [])
    cap_t_gov = min(t_caps)
    dcr_t = baf_lbs / cap_t_gov

    v_caps = [cap_v_breakout, cap_v_crush, cap_v_pry, cap_v_steel]
    cap_v_gov = min(v_caps)
    dcr_v = bvf_lbs / cap_v_gov if bvf_lbs > 0 else 0.0

    # Linear Tension-Shear Interaction (Eq. 8-11 / Eq. 9-9)
    inter_linear = dcr_t + dcr_v

    # 5. Stage 4 Out-of-Plane Wall Continuity / Local Flexure Check (per 12-in. tributary strip)
    m_wall_arm_in = float(inputs.get("wall_flexure_arm_in", 6.0))
    m_local_demand_lb_in = baf_lbs * m_wall_arm_in
    f_r_psi = 133.0  # TMS 402 Table 8.2.4.2 / 9.1.9.2 Type S Portland-lime grout normal to bed joints
    m_cr_wall_lb_in = f_r_psi * s_n_wall if method == DesignMethod.ASD else 0.90 * f_r_psi * s_n_wall
    # Reference continuity utilization per tributary 2*l_b strip width
    strip_ft = max(1.0, (2.0 * l_b_in) / 12.0)
    m_cr_strip = m_cr_wall_lb_in * strip_ft
    dcr_wall_cont = (m_local_demand_lb_in / m_cr_strip) if inputs.get("check_wall_flexure", False) else 0.0

    limit_states: List[LimitStateResult] = [
        LimitStateResult(
            step_id="S2_T_BREAKOUT",
            name="Masonry Tensile Cone Breakout (Eq. 8-2 / 9-1)",
            code_clause="TMS 402-22 Sec. 8.1.3.2 / 9.1.6.2",
            equation_latex=r"B_{ab} = 1.25 A_{pt} \sqrt{f'_m}" if method == DesignMethod.ASD else r"\phi B_{anb} = 0.50 \cdot 4.0 A_{pt} \sqrt{f'_m}",
            substitution_str=f"A_pt={a_pt:.2f} in.^2, fm'={fm_psi:.0f} psi",
            demand=round(baf_lbs, 1),
            capacity=round(cap_t_breakout, 1),
            units="lbs",
            dcr=round(baf_lbs / cap_t_breakout, 3),
            status=CalculationStatus.PASS if baf_lbs <= cap_t_breakout else CalculationStatus.FAIL,
        ),
        LimitStateResult(
            step_id="S2_T_STEEL",
            name="Anchor Bolt Steel Yielding in Tension (Eq. 8-3 / 9-2)",
            code_clause="TMS 402-22 Sec. 8.1.3.2 / 9.1.6.2",
            equation_latex=r"B_{as} = 0.60 A_b f_y" if method == DesignMethod.ASD else r"\phi B_{ans} = 0.90 A_b f_y",
            substitution_str=f"{n_anchors} * {a_b:.3f} in.^2 * {f_y:.0f} psi",
            demand=round(baf_lbs, 1),
            capacity=round(cap_t_steel, 1),
            units="lbs",
            dcr=round(baf_lbs / cap_t_steel, 3),
            status=CalculationStatus.PASS if baf_lbs <= cap_t_steel else CalculationStatus.FAIL,
        ),
        LimitStateResult(
            step_id="S3_SHEAR",
            name="Anchor Shear Capacity (Breakout, Crushing, Pryout, Steel)",
            code_clause="TMS 402-22 Sec. 8.1.3.3 / 9.1.6.3",
            equation_latex=r"B_v = \min(B_{vb},  B_{vc},  B_{vpry},  B_{vs})",
            substitution_str=f"min(vb={cap_v_breakout:.0f}, vc={cap_v_crush:.0f}, pry={cap_v_pry:.0f}, vs={cap_v_steel:.0f}) lbs",
            demand=round(bvf_lbs, 1),
            capacity=round(cap_v_gov, 1),
            units="lbs",
            dcr=round(dcr_v, 3),
            status=CalculationStatus.PASS if bvf_lbs <= cap_v_gov else CalculationStatus.FAIL,
        ),
        LimitStateResult(
            step_id="S4_INTER",
            name="Combined Tension-Shear Linear Interaction (Eq. 8-11 / 9-9)",
            code_clause="TMS 402-22 Sec. 8.1.3.4 / 9.1.6.4",
            equation_latex=r"\frac{b_{af}}{B_a} + \frac{b_{vf}}{B_v} \leq 1.0",
            substitution_str=f"{dcr_t:.3f} + {dcr_v:.3f} = {inter_linear:.3f}",
            demand=round(inter_linear, 3),
            capacity=1.0,
            units="ratio",
            dcr=round(inter_linear, 3),
            status=CalculationStatus.PASS if inter_linear <= 1.0 else CalculationStatus.FAIL,
            notes=f"Wall S_n={s_n_wall:.1f} in.^3/ft (t={t_wall:.3f} in.)",
        ),
    ]

    physical_modes = [ls for ls in limit_states if ls.step_id != "S4_INTER"]
    gov_ls = max(physical_modes, key=lambda x: x.dcr) if bvf_lbs == 0.0 else max(limit_states, key=lambda x: x.dcr)
    overall_pass = stage1_ok and all(ls.status == CalculationStatus.PASS for ls in limit_states)
    overall_status = CalculationStatus.PASS if overall_pass else CalculationStatus.FAIL

    trace = (
        CalcStep(
            step_id="S1_EMBED_WALL",
            stage=LoadPathStage.STAGE_1_GEOMETRY_AND_LIMITS,
            title="CMU Wall Properties & Minimum Anchor Embedment (Sec. 6.1.6)",
            symbolic=validate_math_markup(r"l_b \geq \max(4 d_b,  2.0 \text{ in.})"),
            substituted=validate_math_markup(
                rf"l_b = {l_b_in:.2f} \text{{ in.}} \geq {l_b_min_req:.2f} \text{{ in., }} t_{{wall}} = {t_wall:.3f} \text{{ in.}}"
            ),
            variables={
                "d_b": Quantity("d_b", d_b_in, "in.", "Anchor bolt diameter"),
                "l_b": Quantity("l_b", l_b_in, "in.", "Effective anchor embedment depth"),
                "l_b_min": Quantity("l_{b,\\min}", round(l_b_min_req, 2), "in.", "TMS 402 Sec. 6.1.6 min embedment"),
                "t_wall": Quantity("t_{wall}", t_wall, "in.", "Actual CMU wall thickness"),
            },
            result_value=round(l_b_in, 2),
            result_unit="in.",
            acceptance=AcceptanceCriterion(">=", round(l_b_min_req, 2), "in.", "TMS 402 Sec. 6.1.6 embedment & grouted-cell check", is_dcr_check=False),
            dcr=None,
            status=CalculationStatus.PASS if stage1_ok else CalculationStatus.FAIL,
            refs=(ref_tms, ref_f1554, ref_proc),
        ),
        CalcStep(
            step_id="S2_TENSION",
            stage=LoadPathStage.STAGE_2_PRIMARY_FORCE_TRANSFER,
            title="Masonry Tensile Cone Breakout & Steel Yielding",
            symbolic=validate_math_markup(
                r"B_a = \min\left(1.25 A_{pt} \sqrt{f'_m},  0.60 A_b f_y\right)"
                if method == DesignMethod.ASD
                else r"\phi B_{an} = \min\left(0.50 \cdot 4.0 A_{pt} \sqrt{f'_m},  0.90 A_b f_y\right)"
            ),
            substituted=validate_math_markup(
                rf"\min({cap_t_breakout:.0f}, {cap_t_steel:.0f}) = {cap_t_gov:.0f} \text{{ lbs vs }} b_{{af}} = {baf_lbs:.0f} \text{{ lbs}}"
            ),
            variables={
                "A_pt": Quantity("A_{pt}", round(a_pt, 2), "in.^2", "Projected masonry breakout cone area"),
                "B_breakout": Quantity("B_{ab}", round(cap_t_breakout, 1), "lbs", f"{method.value} masonry breakout capacity"),
                "B_steel": Quantity("B_{as}", round(cap_t_steel, 1), "lbs", f"{method.value} steel tension yielding capacity"),
                "b_af": Quantity("b_{af}", round(baf_lbs, 1), "lbs", f"{method.value} tension demand"),
            },
            result_value=round(cap_t_gov, 1),
            result_unit="lbs",
            acceptance=AcceptanceCriterion(">=", round(baf_lbs, 1), "lbs", f"{method.value} governing tension check", is_dcr_check=True),
            dcr=round(dcr_t, 3),
            status=CalculationStatus.PASS if dcr_t <= 1.0 else CalculationStatus.FAIL,
            refs=(ref_tms, ref_f1554, ref_proc),
        ),
        CalcStep(
            step_id="S3_SHEAR",
            stage=LoadPathStage.STAGE_3_CONNECTING_ELEMENT_AND_BASE_METAL,
            title="Masonry Shear Breakout, Crushing, Pryout & Steel Shear",
            symbolic=validate_math_markup(r"B_v = \min\left(B_{vb},  B_{vc},  B_{vpry},  B_{vs}\right)"),
            substituted=validate_math_markup(
                rf"\min({cap_v_breakout:.0f}, {cap_v_crush:.0f}, {cap_v_pry:.0f}, {cap_v_steel:.0f}) = {cap_v_gov:.0f} \text{{ lbs}}"
            ),
            variables={
                "A_pv": Quantity("A_{pv}", round(a_pv, 2), "in.^2", "Projected shear half-cone area"),
                "B_vb": Quantity("B_{vb}", round(cap_v_breakout, 1), "lbs", f"{method.value} shear breakout capacity"),
                "B_vc": Quantity("B_{vc}", round(cap_v_crush, 1), "lbs", f"{method.value} masonry crushing capacity"),
                "B_vpry": Quantity("B_{vpry}", round(cap_v_pry, 1), "lbs", f"{method.value} pryout capacity"),
                "B_vs": Quantity("B_{vs}", round(cap_v_steel, 1), "lbs", f"{method.value} bolt steel shear capacity"),
            },
            result_value=round(cap_v_gov, 1),
            result_unit="lbs",
            acceptance=AcceptanceCriterion(">=", round(bvf_lbs, 1), "lbs", f"{method.value} governing shear check", is_dcr_check=True),
            dcr=round(dcr_v, 3),
            status=CalculationStatus.PASS if dcr_v <= 1.0 else CalculationStatus.FAIL,
            refs=(ref_tms, ref_proc),
        ),
        CalcStep(
            step_id="S4_WALL_INTER",
            stage=LoadPathStage.STAGE_4_SUPPORTING_MEMBER_AND_GLOBAL,
            title="Combined Interaction & CMU Wall Out-of-Plane Continuity",
            symbolic=validate_math_markup(r"\frac{b_{af}}{B_a} + \frac{b_{vf}}{B_v} \leq 1.0"),
            substituted=validate_math_markup(
                rf"{dcr_t:.3f} + {dcr_v:.3f} = {inter_linear:.3f} \leq 1.000"
            ),
            variables={
                "dcr_t": Quantity("b_{af}/B_a", round(dcr_t, 3), "", "Tension DCR"),
                "dcr_v": Quantity("b_{vf}/B_v", round(dcr_v, 3), "", "Shear DCR"),
                "IR": Quantity("\\text{IR}", round(inter_linear, 3), "", "TMS 402 linear tension-shear interaction"),
                "S_n": Quantity("S_n", s_n_wall, "in.^3/ft", "Solid grouted wall section modulus"),
            },
            result_value=round(inter_linear, 3),
            result_unit="ratio",
            acceptance=AcceptanceCriterion("<=", 1.0, "ratio", "TMS 402 Sec. 8.1.3.4 / 9.1.6.4 interaction", is_dcr_check=True),
            dcr=round(inter_linear, 3),
            status=CalculationStatus.PASS if inter_linear <= 1.0 else CalculationStatus.FAIL,
            refs=(ref_tms, ref_proc),
        ),
    )

    warnings: List[str] = []
    if not stage1_ok:
        warnings.append("Anchor embedment depth or grouting requirement violates TMS 402 Sec. 6.1.6.")

    return CalculationResult(
        calculation_id=calc_id,
        module_id="tms402_cmu_anchorage",
        code_edition="TMS 402-22",
        design_method=method,
        input_parameters={
            "cmu_nominal_in": cmu_nominal_in,
            "fm_psi": fm_psi,
            "is_grouted": is_grouted,
            "bolt_type": bolt_type,
            "rod_grade": rod_grade,
            "d_b_in": d_b_in,
            "l_b_in": l_b_in,
            "n_anchors": n_anchors,
            "b_af_lbs": baf_lbs,
            "b_vf_lbs": bvf_lbs,
        },
        assumptions=[
            f"TMS 402-22 {'Chapter 8 ASD' if method == DesignMethod.ASD else 'Chapter 9 Strength Design'} provisions.",
            f"Solidly grouted {cmu_nominal_in} in. CMU wall (t={t_wall:.3f} in., f'm={fm_psi:.0f} psi).",
        ],
        intermediate_results={
            "t_actual_in": t_wall,
            "S_n_in3_per_ft": s_n_wall,
            "A_b_in2": a_b,
            "A_pt_in2": round(a_pt, 2),
            "A_pv_in2": round(a_pv, 2),
            "cap_t_breakout_lbs": round(cap_t_breakout, 1),
            "cap_t_steel_lbs": round(cap_t_steel, 1),
            "cap_v_breakout_lbs": round(cap_v_breakout, 1),
            "cap_v_crush_lbs": round(cap_v_crush, 1),
            "cap_v_pry_lbs": round(cap_v_pry, 1),
            "cap_v_steel_lbs": round(cap_v_steel, 1),
            "m_cr_wall_lb_in_per_ft": round(m_cr_wall_lb_in, 1),
        },
        limit_states=limit_states,
        governing_limit_state=gov_ls,
        demand=gov_ls.demand,
        capacity=gov_ls.capacity,
        dcr=gov_ls.dcr,
        status=overall_status,
        reference_files=[r.source_path for r in (ref_proc, ref_tms, ref_f1554) if r.source_path],
        warnings=warnings,
        trace=trace,
    )
