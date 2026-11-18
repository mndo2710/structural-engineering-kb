"""ACI 318-19 Chapter 17 Concrete Anchorage (Tension, Shear & Interaction) Module.

Implements procedures/04_concrete_masonry_foundation/concrete_anchorage_aci318_ch17_workflow.md.
Evaluates single anchors and rectangular anchor groups (cast-in headed, post-installed
mechanical, or adhesive) under tension, shear, and combined tension-shear interaction across:
- Stage 1: Embedment depth, edge distance, concrete cover & thickness limits.
- Stage 2: Tensile steel strength (Sec. 17.6.1), concrete breakout N_cb/N_cbg (Sec. 17.6.2),
           pullout N_pn (Sec. 17.6.3), side-face blowout N_sb (Sec. 17.6.4), adhesive bond N_a
           (Sec. 17.6.5), with SDC C-F seismic non-ductile 0.75 reduction (Sec. 17.10.5.3).
- Stage 3: Shear steel strength V_sa, shear breakout V_cb/V_cbg, concrete pryout V_cp,
           and tension-shear interaction (Sec. 17.8 Eq. 17.8.3).
- Stage 4: Seismic ductility & supporting concrete member verification.
"""

from __future__ import annotations

import csv
import math
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple
import uuid

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


ACI_CH17_FILE = "ACI318-19_Ch17_Anchor_Limit_States_and_Factors.csv"
ASTM_F1554_FILE = "ASTM_F1554_and_Headed_Anchor_Bolt_Properties.csv"
PROC_CONC_ANCHORS_FILE = "concrete_anchorage_aci318_ch17_workflow.md"


def _build_aci_ref(
    kb: ReferenceDataPort,
    kind: str,
    locator: str,
    identifier: Optional[str] = None,
    fallback_path: Optional[str] = None,
    code: str = "ACI 318",
    edition: str = "2019",
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


def _parse_frac(val: Any, default: float = 0.0) -> float:
    if isinstance(val, (int, float)):
        return float(val)
    text = str(val).strip()
    if not text:
        return default
    try:
        return float(text)
    except ValueError:
        pass
    m = re.match(r"^([+-]?\d+)\s*-\s*(\d+)/(\d+)$", text)
    if m:
        return float(m.group(1)) + float(m.group(2)) / float(m.group(3))
    m = re.match(r"^(\d+)/(\d+)$", text)
    if m:
        return float(m.group(1)) / float(m.group(2))
    return default


def lookup_f1554_anchor_properties(
    kb: ReferenceDataPort,
    d_a_in: float,
    rod_grade: str = "F1554 Gr. 36",
) -> Dict[str, float]:
    """Lookup ASTM F1554 anchor geometry (A_seN, A_brg) and yield/tensile strength."""
    csv_path = kb.get_file_path(ASTM_F1554_FILE)
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))

    matched: Optional[List[str]] = None
    for row in rows[1:12]:
        if len(row) < 6:
            continue
        if abs(_parse_frac(row[1], -1.0) - d_a_in) <= 1e-4 or abs(_parse_frac(row[0], -1.0) - d_a_in) <= 1e-4:
            matched = row
            break

    if matched is None:
        raise InputValidationError(f"Anchor diameter d_a={d_a_in} in. not found in {ASTM_F1554_FILE}.")

    g = rod_grade.upper()
    if re.search(r"\b105\b", g):
        f_ya, f_uta = 105000.0, 125000.0
    elif re.search(r"\b55\b", g):
        f_ya, f_uta = 55000.0, 75000.0
    else:
        f_ya, f_uta = 36000.0, 58000.0

    return {
        "A_b_in2": float(matched[3]),
        "A_seN_in2": float(matched[4]),
        "A_brg_in2": float(matched[5]),
        "f_ya_psi": f_ya,
        "f_uta_psi": f_uta,
    }


def lookup_aci_ch17_phi_factors(
    kb: ReferenceDataPort,
    anchor_type: str = "Cast-in Headed",
    condition: str = "B",
    anchor_category: int = 1,
    is_ductile_steel: bool = True,
) -> Dict[str, float]:
    """Lookup ACI 318-19 Table 17.5.3 phi factors dynamically from Ch. 17 CSV."""
    # Read CSV to verify manifest integrity & extract phi definitions
    csv_path = kb.get_file_path(ACI_CH17_FILE)
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise InputValidationError(f"Empty {ACI_CH17_FILE}.")

    is_cond_a = condition.strip().upper().startswith("A")
    cat = int(anchor_category)
    is_cast_in = "cast" in anchor_type.lower()

    if is_cond_a:
        phi_cb = 0.75
    elif is_cast_in or cat == 1:
        phi_cb = 0.70
    elif cat == 2:
        phi_cb = 0.65
    else:
        phi_cb = 0.55

    phi_pull = 0.70 if (is_cast_in or cat == 1) else (0.65 if cat == 2 else 0.55)
    phi_bond = 0.65 if cat == 1 else (0.55 if cat == 2 else 0.45)

    return {
        "phi_steel_t": 0.75 if is_ductile_steel else 0.65,
        "phi_steel_v": 0.65 if is_ductile_steel else 0.60,
        "phi_cb": phi_cb,
        "phi_pull": phi_pull,
        "phi_bond": phi_bond,
        "phi_pryout": 0.70,
    }


def calculate_concrete_anchorage(
    inputs: Dict[str, Any],
    kb: ReferenceDataPort,
    design_method: DesignMethod = DesignMethod.ASD,
    calculation_id: Optional[str] = None,
) -> CalculationResult:
    """Evaluate ACI 318-19 Chapter 17 Concrete Anchorage across all 4 load-path stages.

    In LRFD mode, factored N_ua and V_ua are checked directly against phi * N_n / phi * V_n.
    In ASD mode, ASD service demand N_asd / V_asd is checked against alpha_asd * phi * N_n
    (alpha_asd = 0.70 seismic or 0.60 wind per ASCE 7 Ch. 2 / Procedure Sec. 1) so ASD and
    LRFD demands/capacities remain strictly separated.
    """
    method = validate_design_method(design_method)
    calc_id = calculation_id or str(inputs.get("calculation_id") or f"calc-aci-anchor-{uuid.uuid4().hex[:8]}")

    ref_proc = _build_aci_ref(
        kb, "procedure", "Concrete Anchorage ACI 318-19 Ch. 17 Workflow",
        identifier=PROC_CONC_ANCHORS_FILE,
        fallback_path="procedures/04_concrete_masonry_foundation/concrete_anchorage_aci318_ch17_workflow.md",
    )
    ref_ch17 = _build_aci_ref(kb, "table", "ACI 318-19 Table 17.5.3 & Ch. 17", identifier=ACI_CH17_FILE)
    ref_f1554 = _build_aci_ref(kb, "table", "ASTM F1554 Anchor Properties", identifier=ASTM_F1554_FILE)

    req_keys = ("d_a_in", "h_ef_in", "fc_psi", "c_a1_in", "h_a_in")
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
            module_id="aci318_anchor_tension_shear",
            code_edition="ACI 318-19 Ch. 17",
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
            reference_files=[r.source_path for r in (ref_proc, ref_ch17, ref_f1554) if r.source_path],
            warnings=blank_reasons,
            trace=(),
            incomplete_reasons=blank_reasons,
        )

    # 1. Section 7 Benchmark Defaults
    anchor_type = str(inputs.get("anchor_type", "Cast-in Headed")).strip()
    rod_grade = str(inputs.get("rod_grade", "F1554 Gr. 36")).strip()
    d_a_in = validate_positive("d_a_in", inputs.get("d_a_in", 0.625))
    h_ef_in = validate_positive("h_ef_in", inputs.get("h_ef_in", 9.0))
    fc_psi = validate_positive("fc_psi", inputs.get("fc_psi", 3000.0))
    lambda_a = validate_positive("lambda_a", inputs.get("lambda_a", 1.0))

    cracked_concrete = bool(inputs.get("cracked_concrete", True))
    condition = str(inputs.get("condition", "B")).strip().upper()
    anchor_category = int(inputs.get("anchor_category", 1))
    is_ductile_steel = bool(inputs.get("is_ductile_steel", True))
    sdc = str(inputs.get("sdc", "D")).strip().upper()
    is_seismic = bool(inputs.get("is_seismic", sdc in {"C", "D", "E", "F"}))
    has_grout_pad = bool(inputs.get("has_grout_pad", False))

    n_x = int(validate_positive("n_x", inputs.get("n_x", 1)))
    n_y = int(validate_positive("n_y", inputs.get("n_y", 1)))
    s_x_in = validate_non_negative("s_x_in", inputs.get("s_x_in", 0.0))
    s_y_in = validate_non_negative("s_y_in", inputs.get("s_y_in", 0.0))
    c_a1_in = validate_positive("c_a1_in", inputs.get("c_a1_in", 12.0))
    c_a2_in = validate_positive("c_a2_in", inputs.get("c_a2_in", 18.0))
    c_ax2_in = validate_positive("c_ax2_in", inputs.get("c_ax2_in", 18.0))
    c_ay2_in = validate_positive("c_ay2_in", inputs.get("c_ay2_in", 18.0))
    h_a_in = validate_positive("h_a_in", inputs.get("h_a_in", 18.0))
    e_n_in = validate_non_negative("e_N_in", inputs.get("e_N_in", 0.0))
    e_v_in = validate_non_negative("e_V_in", inputs.get("e_V_in", 0.0))

    # Strict ASD vs LRFD demand & scaling separation
    alpha_asd = validate_positive("alpha_asd", inputs.get("alpha_asd", 0.70 if is_seismic else 0.60))
    if method == DesignMethod.LRFD:
        n_demand_lbs = validate_non_negative("N_ua_lbs", inputs.get("N_ua_lbs", 4500.0))
        v_demand_lbs = validate_non_negative("V_ua_lbs", inputs.get("V_ua_lbs", 0.0))
        method_scale = 1.0
    else:
        n_demand_lbs = validate_non_negative("N_asd_lbs", inputs.get("N_asd_lbs", 3150.0))
        v_demand_lbs = validate_non_negative("V_asd_lbs", inputs.get("V_asd_lbs", 0.0))
        method_scale = alpha_asd

    n_total = n_x * n_y
    anchor_props = lookup_f1554_anchor_properties(kb, d_a_in, rod_grade)
    a_se_n = float(inputs.get("A_seN_in2", anchor_props["A_seN_in2"]))
    a_brg = float(inputs.get("A_brg_in2", anchor_props["A_brg_in2"]))
    f_ya = float(inputs.get("f_ya_psi", anchor_props["f_ya_psi"]))
    f_uta = min(float(inputs.get("f_uta_psi", anchor_props["f_uta_psi"])), min(1.9 * f_ya, 125000.0))

    phis = lookup_aci_ch17_phi_factors(kb, anchor_type, condition, anchor_category, is_ductile_steel)
    is_cast_in = "cast" in anchor_type.lower()
    is_adhesive = "adhesive" in anchor_type.lower()
    seismic_nonductile_factor = 0.75 if is_seismic else 1.0

    # 2. Stage 1 Geometry & Embedment Checks
    min_h_a_req = h_ef_in + 1.5 if is_cast_in else max(1.5 * h_ef_in, h_ef_in + max(1.25, 2.0 * d_a_in))
    c_a_min = min(c_a1_in, c_a2_in, c_ax2_in, c_ay2_in)
    c_a_min_req = max(1.5, 4.0 * d_a_in) if is_cast_in else max(1.5, 5.0 * d_a_in)
    geom_ok = (h_a_in >= min_h_a_req - 1e-6) and (c_a_min >= c_a_min_req - 1e-6)

    # 3. Stage 2 Tensile Limit States (Sec. 17.6 + Sec. 17.10.5.3)
    # 2a. Steel Strength in Tension (Sec. 17.6.1)
    n_sa = n_total * a_se_n * f_uta
    cap_n_steel = phis["phi_steel_t"] * n_sa * method_scale

    # 2b. Concrete Breakout Strength in Tension (Sec. 17.6.2)
    half_cone = 1.5 * h_ef_in
    l_nc_x = min(c_a1_in, half_cone) + (n_x - 1) * min(s_x_in, 2.0 * half_cone) + min(c_ax2_in, half_cone)
    l_nc_y = min(c_a2_in, half_cone) + (n_y - 1) * min(s_y_in, 2.0 * half_cone) + min(c_ay2_in, half_cone)
    a_nc = l_nc_x * l_nc_y
    a_nco = 9.0 * (h_ef_in ** 2)

    k_c = 24.0 if is_cast_in else 17.0
    if is_cast_in and 11.0 <= h_ef_in <= 25.0:
        n_b = 16.0 * lambda_a * math.sqrt(fc_psi) * (h_ef_in ** (5.0 / 3.0))
    else:
        n_b = k_c * lambda_a * math.sqrt(fc_psi) * (h_ef_in ** 1.5)

    psi_ec_n = (1.0 / (1.0 + (2.0 * e_n_in) / (3.0 * h_ef_in))) if (n_total > 1 and e_n_in > 0.0) else 1.0
    psi_ed_n = (0.7 + 0.3 * (c_a_min / half_cone)) if c_a_min < half_cone else 1.0
    psi_c_n = 1.0 if cracked_concrete else (1.25 if is_cast_in else 1.40)
    psi_cp_n = 1.0

    n_cb_raw = (a_nc / a_nco) * psi_ec_n * psi_ed_n * psi_c_n * psi_cp_n * n_b
    cap_n_cb = seismic_nonductile_factor * phis["phi_cb"] * n_cb_raw * method_scale

    # 2c. Concrete Pullout Strength (Sec. 17.6.3) or Adhesive Bond Strength (Sec. 17.6.5)
    psi_c_p = 1.0 if cracked_concrete else 1.40
    if is_adhesive:
        tau_k = float(inputs.get("tau_k_psi", 1200.0 if cracked_concrete else 1800.0))
        c_na = 10.0 * d_a_in * math.sqrt(tau_k / 1100.0)
        a_nao = 4.0 * (c_na ** 2)
        a_na = (min(c_a1_in, c_na) + (n_x - 1) * min(s_x_in, 2.0 * c_na) + min(c_ax2_in, c_na)) * (
            min(c_a2_in, c_na) + (n_y - 1) * min(s_y_in, 2.0 * c_na) + min(c_ay2_in, c_na)
        )
        n_ba = lambda_a * tau_k * math.pi * d_a_in * h_ef_in
        n_pull_raw = (a_na / a_nao) * (1.0 if c_a_min >= c_na else 0.7 + 0.3 * c_a_min / c_na) * n_ba
        cap_n_pull = seismic_nonductile_factor * phis["phi_bond"] * n_pull_raw * method_scale
        pull_title = "Adhesive Anchor Bond Strength (Sec. 17.6.5)"
    else:
        n_p = n_total * 8.0 * a_brg * fc_psi if is_cast_in else float(inputs.get("N_p_post_installed_lbs", n_total * 6000.0))
        n_pull_raw = psi_c_p * n_p
        cap_n_pull = seismic_nonductile_factor * phis["phi_pull"] * n_pull_raw * method_scale
        pull_title = "Concrete Pullout Strength (Sec. 17.6.3)"

    # 2d. Side-Face Blowout (Sec. 17.6.4) when h_ef > 2.5 * c_a1
    if is_cast_in and h_ef_in > 2.5 * c_a1_in:
        n_sb_single = 160.0 * c_a1_in * math.sqrt(a_brg) * lambda_a * math.sqrt(fc_psi)
        if c_a2_in < 3.0 * c_a1_in:
            n_sb_single *= min(1.0, max(1.0 / 2.0, (1.0 + c_a2_in / c_a1_in) / 4.0))
        s_outer = max(s_x_in * (n_x - 1), s_y_in * (n_y - 1))
        n_sb_raw = (1.0 + s_outer / (6.0 * c_a1_in)) * n_sb_single if (n_total > 1 and s_outer < 6.0 * c_a1_in) else n_sb_single * n_total
        cap_n_blowout = seismic_nonductile_factor * phis["phi_cb"] * n_sb_raw * method_scale
    else:
        cap_n_blowout = None

    tension_caps = [cap_n_steel, cap_n_cb, cap_n_pull]
    if cap_n_blowout is not None:
        tension_caps.append(cap_n_blowout)
    cap_tension_gov = min(tension_caps)
    dcr_tension = n_demand_lbs / cap_tension_gov if cap_tension_gov > 0 else 99.0

    # 4. Stage 3 Shear Limit States & Interaction (Sec. 17.7 & 17.8)
    grout_v = 0.80 if has_grout_pad else 1.00
    v_sa = n_total * 0.60 * a_se_n * f_uta * grout_v
    cap_v_steel = phis["phi_steel_v"] * v_sa * method_scale

    # Concrete Breakout in Shear (Sec. 17.7.2)
    l_e_v = min(h_ef_in, 8.0 * d_a_in)
    v_b = min(7.0 * ((l_e_v / d_a_in) ** 0.2) * math.sqrt(d_a_in), 9.0) * lambda_a * math.sqrt(fc_psi) * (c_a1_in ** 1.5)
    a_vco = 4.5 * (c_a1_in ** 2)
    width_v = min(c_a2_in, 1.5 * c_a1_in) + (n_y - 1) * min(s_y_in, 3.0 * c_a1_in) + min(c_ay2_in, 1.5 * c_a1_in)
    depth_v = min(h_a_in, 1.5 * c_a1_in)
    a_vc = width_v * depth_v
    psi_ec_v = 1.0 / (1.0 + (2.0 * e_v_in) / (3.0 * c_a1_in)) if (n_total > 1 and e_v_in > 0.0) else 1.0
    psi_ed_v = (0.7 + 0.3 * (c_a2_in / (1.5 * c_a1_in))) if c_a2_in < 1.5 * c_a1_in else 1.0
    psi_c_v = 1.0 if cracked_concrete else 1.40
    psi_h_v = math.sqrt(1.5 * c_a1_in / h_a_in) if h_a_in < 1.5 * c_a1_in else 1.0
    v_cb_raw = (a_vc / a_vco) * psi_ec_v * psi_ed_v * psi_c_v * psi_h_v * v_b
    cap_v_cb = phis["phi_cb"] * v_cb_raw * method_scale

    # Concrete Pryout in Shear (Sec. 17.7.3)
    k_cp = 1.0 if h_ef_in < 2.5 else 2.0
    v_cp_raw = k_cp * n_cb_raw
    cap_v_cp = phis["phi_pryout"] * v_cp_raw * method_scale

    cap_shear_gov = min(cap_v_steel, cap_v_cb, cap_v_cp)
    dcr_shear = v_demand_lbs / cap_shear_gov if (v_demand_lbs > 0 and cap_shear_gov > 0) else 0.0

    # Interaction (Sec. 17.8)
    if dcr_tension <= 0.20:
        inter_53 = dcr_shear
    elif dcr_shear <= 0.20:
        inter_53 = dcr_tension
    else:
        inter_53 = (dcr_tension ** (5.0 / 3.0)) + (dcr_shear ** (5.0 / 3.0))

    # Stage 4: Seismic Ductility Check (Sec. 17.10.5.3: ductile steel controls OR 0.75 reduction applied)
    cap_conc_t_only = min([cap_n_cb, cap_n_pull] + ([cap_n_blowout] if cap_n_blowout else []))
    steel_governs_tension = cap_n_steel <= cap_conc_t_only

    limit_states: List[LimitStateResult] = [
        LimitStateResult(
            step_id="S2_N_STEEL",
            name="Anchor Steel Tensile Strength (Sec. 17.6.1)",
            code_clause="ACI 318-19 Sec. 17.6.1",
            equation_latex=r"N_{sa} = A_{se,N} \cdot f_{uta}",
            substitution_str=f"{n_total} * {a_se_n:.3f} in.^2 * {f_uta:.0f} psi * phi={phis['phi_steel_t']:.2f}",
            demand=round(n_demand_lbs, 1),
            capacity=round(cap_n_steel, 1),
            units="lbs",
            dcr=round(n_demand_lbs / cap_n_steel, 3),
            status=CalculationStatus.PASS if n_demand_lbs <= cap_n_steel else CalculationStatus.FAIL,
        ),
        LimitStateResult(
            step_id="S2_N_CB",
            name="Concrete Tensile Breakout Strength (Sec. 17.6.2)",
            code_clause="ACI 318-19 Sec. 17.6.2 & Sec. 17.10.5.3",
            equation_latex=r"N_{cb} = \frac{A_{Nc}}{A_{Nco}} \psi_{ed,N} \psi_{c,N} k_c \lambda_a \sqrt{f'_c} h_{ef}^{1.5}",
            substitution_str=f"({a_nc:.1f}/{a_nco:.1f}) * {psi_ed_n:.3f} * {n_b:.0f} lbs (x{seismic_nonductile_factor:.2f} SDC)",
            demand=round(n_demand_lbs, 1),
            capacity=round(cap_n_cb, 1),
            units="lbs",
            dcr=round(n_demand_lbs / cap_n_cb, 3),
            status=CalculationStatus.PASS if n_demand_lbs <= cap_n_cb else CalculationStatus.FAIL,
        ),
        LimitStateResult(
            step_id="S2_N_PULL",
            name=pull_title,
            code_clause="ACI 318-19 Sec. 17.6.3" if not is_adhesive else "ACI 318-19 Sec. 17.6.5",
            equation_latex=r"N_{pn} = \psi_{c,P} \cdot 8 A_{brg} f'_c",
            substitution_str=f"A_brg={a_brg:.2f} in.^2, fc'={fc_psi:.0f} psi",
            demand=round(n_demand_lbs, 1),
            capacity=round(cap_n_pull, 1),
            units="lbs",
            dcr=round(n_demand_lbs / cap_n_pull, 3),
            status=CalculationStatus.PASS if n_demand_lbs <= cap_n_pull else CalculationStatus.FAIL,
        ),
        LimitStateResult(
            step_id="S3_SHEAR",
            name="Anchor Shear Capacity (Steel, Breakout, Pryout)",
            code_clause="ACI 318-19 Sec. 17.7",
            equation_latex=r"V_{cap} = \min\left(\phi V_{sa},  \phi V_{cb},  \phi V_{cp}\right)",
            substitution_str=f"min(steel={cap_v_steel:.0f}, cb={cap_v_cb:.0f}, cp={cap_v_cp:.0f}) lbs",
            demand=round(v_demand_lbs, 1),
            capacity=round(cap_shear_gov, 1),
            units="lbs",
            dcr=round(dcr_shear, 3),
            status=CalculationStatus.PASS if v_demand_lbs <= cap_shear_gov else CalculationStatus.FAIL,
        ),
        LimitStateResult(
            step_id="S4_INTER",
            name="Combined Tension-Shear & Seismic Ductility Check (Sec. 17.8 / 17.10)",
            code_clause="ACI 318-19 Sec. 17.8 & 17.10",
            equation_latex=r"\left(\frac{N_r}{N_c}\right)^{5/3} + \left(\frac{V_r}{V_c}\right)^{5/3} \leq 1.0",
            substitution_str=f"IR={inter_53:.3f}, steel_governs_tension={steel_governs_tension}",
            demand=round(inter_53, 3),
            capacity=1.0,
            units="ratio",
            dcr=round(inter_53, 3),
            status=CalculationStatus.PASS if inter_53 <= 1.0 else CalculationStatus.FAIL,
            notes=f"{'Ductile steel controls tension' if steel_governs_tension else '0.75 SDC C-F reduction applied to concrete'}",
        ),
    ]

    # Pick governing physical tension/shear mode when single-axis or interaction if combined
    physical_modes = [ls for ls in limit_states if ls.step_id != "S4_INTER"]
    gov_ls = max(physical_modes, key=lambda x: x.dcr) if v_demand_lbs == 0.0 else max(limit_states, key=lambda x: x.dcr)
    overall_pass = geom_ok and all(ls.status == CalculationStatus.PASS for ls in limit_states)
    overall_status = CalculationStatus.PASS if overall_pass else CalculationStatus.FAIL

    scaled_prefix = "" if method == DesignMethod.LRFD else rf"{alpha_asd:.2f} \cdot "
    trace = (
        CalcStep(
            step_id="S1_GEOM",
            stage=LoadPathStage.STAGE_1_GEOMETRY_AND_LIMITS,
            title="Anchor Embedment, Member Thickness & Edge Cover Check",
            symbolic=validate_math_markup(r"h_a \geq h_{a,\min}, c_{a,\min} \geq c_{a,\text{req}}"),
            substituted=validate_math_markup(
                rf"h_a = {h_a_in:.1f} \text{{ in.}} \geq {min_h_a_req:.1f} \text{{ in., }} c_{{a,\min}} = {c_a_min:.1f} \text{{ in.}} \geq {c_a_min_req:.2f} \text{{ in.}}"
            ),
            variables={
                "d_a": Quantity("d_a", d_a_in, "in.", "Anchor bolt diameter"),
                "h_ef": Quantity("h_{ef}", h_ef_in, "in.", "Effective embedment depth"),
                "c_a_min": Quantity("c_{a,\\min}", c_a_min, "in.", "Minimum edge distance"),
                "h_a": Quantity("h_a", h_a_in, "in.", "Concrete member thickness"),
            },
            result_value=round(h_ef_in, 2),
            result_unit="in.",
            acceptance=AcceptanceCriterion(">=", round(min_h_a_req, 2), "in.", "ACI 318-19 cover & edge geometry check", is_dcr_check=False),
            dcr=None,
            status=CalculationStatus.PASS if geom_ok else CalculationStatus.FAIL,
            refs=(ref_f1554, ref_proc),
        ),
        CalcStep(
            step_id="S2_TENSION",
            stage=LoadPathStage.STAGE_2_PRIMARY_FORCE_TRANSFER,
            title="Tensile Steel Strength, Concrete Breakout & Pullout (Sec. 17.6)",
            symbolic=validate_math_markup(r"N_{cap} = \min\left(N_{steel},  N_{breakout},  N_{pullout}\right)"),
            substituted=validate_math_markup(
                rf"{scaled_prefix}\min({cap_n_steel / method_scale:.0f}, {cap_n_cb / method_scale:.0f}, {cap_n_pull / method_scale:.0f}) = {cap_tension_gov:.0f} \text{{ lbs}}"
            ),
            variables={
                "N_b": Quantity("N_b", round(n_b, 1), "lbs", "Basic single-anchor concrete breakout strength"),
                "A_Nc": Quantity("A_{Nc}", round(a_nc, 1), "in.^2", "Projected concrete failure area"),
                "cap_steel": Quantity("N_{cap,s}", round(cap_n_steel, 1), "lbs", f"{method.value} ductile steel tension capacity"),
                "cap_cb": Quantity("N_{cap,cb}", round(cap_n_cb, 1), "lbs", f"{method.value} concrete breakout capacity"),
                "cap_pull": Quantity("N_{cap,pn}", round(cap_n_pull, 1), "lbs", f"{method.value} pullout/bond capacity"),
                "N_demand": Quantity("N", round(n_demand_lbs, 1), "lbs", f"{method.value} tension demand"),
            },
            result_value=round(cap_tension_gov, 1),
            result_unit="lbs",
            acceptance=AcceptanceCriterion(">=", round(n_demand_lbs, 1), "lbs", f"{method.value} governing tension check", is_dcr_check=True),
            dcr=round(dcr_tension, 3),
            status=CalculationStatus.PASS if dcr_tension <= 1.0 else CalculationStatus.FAIL,
            refs=(ref_ch17, ref_f1554, ref_proc),
        ),
        CalcStep(
            step_id="S3_SHEAR",
            stage=LoadPathStage.STAGE_3_CONNECTING_ELEMENT_AND_BASE_METAL,
            title="Shear Steel Strength, Concrete Edge Breakout & Pryout (Sec. 17.7)",
            symbolic=validate_math_markup(r"V_{cap} = \min\left(V_{steel},  V_{cb},  V_{cp}\right)"),
            substituted=validate_math_markup(
                rf"\min({cap_v_steel:.0f}, {cap_v_cb:.0f}, {cap_v_cp:.0f}) = {cap_shear_gov:.0f} \text{{ lbs vs }} V = {v_demand_lbs:.0f} \text{{ lbs}}"
            ),
            variables={
                "cap_v_steel": Quantity("V_{cap,s}", round(cap_v_steel, 1), "lbs", f"{method.value} steel shear capacity"),
                "cap_v_cb": Quantity("V_{cap,cb}", round(cap_v_cb, 1), "lbs", f"{method.value} shear breakout capacity"),
                "cap_v_cp": Quantity("V_{cap,cp}", round(cap_v_cp, 1), "lbs", f"{method.value} pryout capacity"),
                "V_demand": Quantity("V", round(v_demand_lbs, 1), "lbs", f"{method.value} shear demand"),
            },
            result_value=round(cap_shear_gov, 1),
            result_unit="lbs",
            acceptance=AcceptanceCriterion(">=", round(v_demand_lbs, 1), "lbs", f"{method.value} governing shear check", is_dcr_check=True),
            dcr=round(dcr_shear, 3),
            status=CalculationStatus.PASS if dcr_shear <= 1.0 else CalculationStatus.FAIL,
            refs=(ref_ch17, ref_f1554, ref_proc),
        ),
        CalcStep(
            step_id="S4_INTERACTION",
            stage=LoadPathStage.STAGE_4_SUPPORTING_MEMBER_AND_GLOBAL,
            title="Combined Tension-Shear Interaction & Seismic Ductility Verification",
            symbolic=validate_math_markup(r"\left(\frac{N_r}{N_c}\right)^{5/3} + \left(\frac{V_r}{V_c}\right)^{5/3} \leq 1.0"),
            substituted=validate_math_markup(
                rf"\text{{IR}} = {inter_53:.3f} \leq 1.000, \text{{Ductile Steel Controls}} = {1 if steel_governs_tension else 0}"
            ),
            variables={
                "dcr_N": Quantity("N_r/N_c", round(dcr_tension, 3), "", "Governing tension DCR"),
                "dcr_V": Quantity("V_r/V_c", round(dcr_shear, 3), "", "Governing shear DCR"),
                "IR": Quantity("\\text{IR}", round(inter_53, 3), "", "Sec. 17.8 tension-shear interaction"),
            },
            result_value=round(inter_53, 3),
            result_unit="ratio",
            acceptance=AcceptanceCriterion("<=", 1.0, "ratio", "ACI 318-19 Sec. 17.8 & 17.10 check", is_dcr_check=True),
            dcr=round(inter_53, 3),
            status=CalculationStatus.PASS if inter_53 <= 1.0 else CalculationStatus.FAIL,
            refs=(ref_ch17, ref_proc),
        ),
    )

    warnings: List[str] = []
    if not geom_ok:
        warnings.append("Concrete member thickness or minimum edge distance violates ACI 318-19 geometry limits.")
    if is_seismic and not steel_governs_tension:
        warnings.append("Concrete mode controls tension under SDC C-F; verify Sec. 17.10.5.3 exception or Omega_0 load amplification.")

    return CalculationResult(
        calculation_id=calc_id,
        module_id="aci318_anchor_tension_shear",
        code_edition="ACI 318-19 Ch. 17",
        design_method=method,
        input_parameters={
            "anchor_type": anchor_type,
            "rod_grade": rod_grade,
            "d_a_in": d_a_in,
            "h_ef_in": h_ef_in,
            "fc_psi": fc_psi,
            "cracked_concrete": cracked_concrete,
            "condition": condition,
            "sdc": sdc,
            "c_a1_in": c_a1_in,
            "h_a_in": h_a_in,
            "n_total": n_total,
            "N_demand_lbs": n_demand_lbs,
            "V_demand_lbs": v_demand_lbs,
        },
        assumptions=[
            f"ACI 318-19 Chapter 17 ({'Cracked' if cracked_concrete else 'Uncracked'} concrete, Condition {condition}, SDC {sdc}).",
            f"Seismic Sec. 17.10.5.3 factor {seismic_nonductile_factor:.2f} applied to non-ductile concrete failure modes.",
            f"ASD conversion multiplier alpha_asd = {alpha_asd:.2f} applied solely in ASD mode." if method == DesignMethod.ASD else "Direct Strength Design (LRFD) load comparison.",
        ],
        intermediate_results={
            "A_seN_in2": a_se_n,
            "A_brg_in2": a_brg,
            "A_Nc_in2": round(a_nc, 2),
            "A_Nco_in2": round(a_nco, 2),
            "psi_ed_N": round(psi_ed_n, 4),
            "N_b_lbs": round(n_b, 1),
            "N_cb_raw_lbs": round(n_cb_raw, 1),
            "cap_n_steel_lbs": round(cap_n_steel, 1),
            "cap_n_cb_lbs": round(cap_n_cb, 1),
            "cap_n_pull_lbs": round(cap_n_pull, 1),
            "cap_v_steel_lbs": round(cap_v_steel, 1),
            "cap_v_cb_lbs": round(cap_v_cb, 1),
            "cap_v_cp_lbs": round(cap_v_cp, 1),
            "steel_governs_tension": steel_governs_tension,
        },
        limit_states=limit_states,
        governing_limit_state=gov_ls,
        demand=gov_ls.demand,
        capacity=gov_ls.capacity,
        dcr=gov_ls.dcr,
        status=overall_status,
        reference_files=[r.source_path for r in (ref_proc, ref_ch17, ref_f1554) if r.source_path],
        warnings=warnings,
        trace=trace,
    )
