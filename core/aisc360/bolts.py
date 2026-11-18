"""ANSI/AISC 360-22 Chapter J Steel Bolted Connection Module.

Implements procedures/03_steel_design/steel_bolted_connection_aisc_workflow.md.
Evaluates Dual ASD/LRFD bolt hole & spacing detailing (Tables J3.3-J3.5),
bearing-type / slip-critical bolt shear & combined tension-shear (Table J3.2, Sec. J3.7, J3.8),
eccentric bolt group ICOR capacity (AISC Manual Part 7), bolt bearing/tear-out (Sec. J3.10),
block shear rupture (Sec. J4.3), and plate gross tension yielding / net rupture (Sec. J4.1).
Also provides shared manifest-backed AISC lookup helpers for core/aisc360/.
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


MATERIAL_GRADES_FILE = "material_grades.csv"
SHAPES_DATABASE_FILE = "shapes_database.csv"
TABLE_J2_4_FILE = "AISC360-22_Table_J2.4.csv"
TABLE_J2_5_FILE = "AISC360-22_Table_J2.5_Welded_Joints.csv"
TABLE_J3_2_FILE = "AISC360-22_Table_J3.2_Bolt_Strength.csv"
TABLE_J3_3_FILE = "AISC360-22_Table_J3.3_J3.4_J3.5_Bolt_Holes_and_Edge_Distances.csv"
PART7_ICOR_FILE = "AISC_Manual_16th_Part7_Eccentric_Bolt_C_Coefficients.csv"
PART10_SHEAR_FILE = "AISC_Manual_16th_Part10_Shear_Tab_and_Single_Angle_Design.csv"
DG1_BASE_PLATE_FILE = "AISC_DG1_Base_Plate_and_Anchor_Rod_Design.csv"
TABLE_K3_2_K4_2_FILE = "AISC360-22_Table_K3.2_K4.2_HSS_Connections.csv"
PROC_BOLTS_FILE = "steel_bolted_connection_aisc_workflow.md"


def _build_aisc_ref(
    kb: ReferenceDataPort,
    kind: str,
    locator: str,
    identifier: Optional[str] = None,
    fallback_path: Optional[str] = None,
    code: str = "AISC 360",
    edition: str = "2022",
) -> RefSpec:
    """Resolve a manifest-backed RefSpec cleanly via ReferenceDataPort without inventing IDs."""
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
                    file_path = kb.get_file_path(identifier)
                    sha256 = kb.compute_sha256(file_path)
                except Exception:
                    pass
        except ReferenceDataNotFoundError:
            try:
                file_path = kb.get_file_path(identifier)
                if source_path is None:
                    source_path = str(file_path)
                sha256 = kb.compute_sha256(file_path)
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


def _parse_fraction(value: Any, default: float = 0.0) -> float:
    """Parse fractional US structural dimensions such as '3/4', '1-13/16', or '15  1/2'."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text or text in {"–", "-", "N/A", "NA"}:
        return default
    # Strip trailing parenthetical notes e.g. '1.333 (1-3/8)'
    text = text.split("(")[0].strip()
    try:
        return float(text)
    except ValueError:
        pass
    # Match mixed fraction like '1-13/16' or '15  1/2'
    m = re.match(r"^([+-]?\d+)\s*[-\s]\s*(\d+)\s*/\s*(\d+)$", text)
    if m:
        whole = float(m.group(1))
        num = float(m.group(2))
        den = float(m.group(3))
        sign = -1.0 if whole < 0 else 1.0
        return sign * (abs(whole) + num / den)
    # Match simple fraction '13/16'
    m = re.match(r"^([+-]?\d+)\s*/\s*(\d+)$", text)
    if m:
        return float(m.group(1)) / float(m.group(2))
    return default


def _check_blank_inputs(
    inputs: Dict[str, Any],
    required_keys: Sequence[str],
) -> List[str]:
    """Detect explicitly blank required fields or blank-start mode per F-06 policy."""
    reasons: List[str] = []
    require_complete = bool(inputs.get("_require_complete", False))
    for key in required_keys:
        if key in inputs:
            val = inputs[key]
            if val is None or (isinstance(val, str) and val.strip() == ""):
                reasons.append(f"Required input '{key}' is blank.")
        elif require_complete:
            reasons.append(f"Required input '{key}' is missing.")
    return reasons


def _make_incomplete_result(
    calc_id: str,
    module_id: str,
    code_edition: str,
    method: DesignMethod,
    inputs: Dict[str, Any],
    reasons: List[str],
    refs: Sequence[RefSpec],
) -> CalculationResult:
    """Return a clean INCOMPLETE CalculationResult with zero sample-fallback outputs."""
    return CalculationResult(
        calculation_id=calc_id,
        module_id=module_id,
        code_edition=code_edition,
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
        reference_files=[r.source_path for r in refs if r.source_path],
        warnings=list(reasons),
        trace=(),
        incomplete_reasons=list(reasons),
    )


def _validated_markup(expr: str) -> str:
    """Ensure trace math strings strictly comply with the restricted math markup subset."""
    return validate_math_markup(expr)


def lookup_material_grade(kb: ReferenceDataPort, material: str = "A36") -> Dict[str, float]:
    """Lookup ASTM steel material yield and tensile strength (Fy, Fu, E in ksi)."""
    norm = material.strip().upper().replace("GR.", "GR").replace("GRADE", "GR")
    # Support F1554 anchor rod specs cleanly
    f1554_map = {
        "F1554 GR 36": {"Fy_ksi": 36.0, "Fu_ksi": 58.0, "E_ksi": 29000.0},
        "F1554 GR 55": {"Fy_ksi": 55.0, "Fu_ksi": 75.0, "E_ksi": 29000.0},
        "F1554 GR 105": {"Fy_ksi": 105.0, "Fu_ksi": 125.0, "E_ksi": 29000.0},
        "A572 GR 50": {"Fy_ksi": 50.0, "Fu_ksi": 65.0, "E_ksi": 29000.0},
        "A500 GR C": {"Fy_ksi": 50.0, "Fu_ksi": 62.0, "E_ksi": 29000.0},
        "A500 GR B": {"Fy_ksi": 42.0, "Fu_ksi": 58.0, "E_ksi": 29000.0},
        "A1085": {"Fy_ksi": 50.0, "Fu_ksi": 65.0, "E_ksi": 29000.0},
    }
    clean_key = re.sub(r"\s+", " ", norm)
    for k, vals in f1554_map.items():
        if k in clean_key or clean_key.replace("ASTM ", "") == k:
            return dict(vals)

    csv_path = kb.get_file_path(MATERIAL_GRADES_FILE)
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        spec = row["ASTM_Spec"].strip().upper()
        grade = row["Grade"].strip().upper()
        if spec in clean_key and (grade in clean_key or spec in {"A36", "A992"}):
            return {
                "Fy_ksi": float(row["Fy_ksi"]),
                "Fu_ksi": float(row["Fu_ksi"]),
                "E_ksi": float(row["E_ksi"]),
            }
    raise InputValidationError(f"Unsupported steel material grade: '{material}'")


def lookup_shape_imperial(kb: ReferenceDataPort, section_name: str) -> Dict[str, Any]:
    """Lookup AISC 16th Edition steel shape properties in US Customary units.

    Note: shapes_database.csv repeats headers for metric columns later in the row,
    so we intentionally map ONLY the first (Imperial) column index per header name.
    """
    target = section_name.strip().upper().replace(" ", "")
    csv_path = kb.get_file_path(SHAPES_DATABASE_FILE)
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        headers = next(reader)
        col_idx: Dict[str, int] = {}
        for i, h in enumerate(headers):
            if h not in col_idx:
                col_idx[h] = i
        lbl_i = col_idx["AISC_Manual_Label"]
        for row in reader:
            if len(row) <= lbl_i:
                continue
            lbl = row[lbl_i].strip().upper().replace(" ", "")
            if lbl == target:
                def _g(col: str, default: float = 0.0) -> float:
                    idx = col_idx.get(col)
                    if idx is None or idx >= len(row):
                        return default
                    return _parse_fraction(row[idx], default)

                return {
                    "Type": row[col_idx["Type"]].strip(),
                    "label": row[lbl_i].strip(),
                    "A": _g("A"),
                    "d": _g("d"),
                    "Ht": _g("Ht"),
                    "h": _g("h"),
                    "OD": _g("OD"),
                    "bf": _g("bf"),
                    "B": _g("B"),
                    "b": _g("b"),
                    "tw": _g("tw"),
                    "tf": _g("tf"),
                    "t": _g("t"),
                    "tnom": _g("tnom"),
                    "tdes": _g("tdes"),
                    "kdes": _g("kdes"),
                    "kdet": _g("kdet"),
                    "T": _g("T"),
                    "Ix": _g("Ix"),
                    "Zx": _g("Zx"),
                    "Sx": _g("Sx"),
                    "Iy": _g("Iy"),
                    "Zy": _g("Zy"),
                    "Sy": _g("Sy"),
                    "b_t": _g("b/t"),
                    "b_tdes": _g("b/tdes"),
                    "h_tw": _g("h/tw"),
                    "h_tdes": _g("h/tdes"),
                    "D_t": _g("D/t"),
                }
    raise InputValidationError(f"Steel shape '{section_name}' not found in shapes_database.csv.")


def lookup_bolt_properties(
    kb: ReferenceDataPort,
    bolt_grade: str = "A325",
    thread_condition: str = "N",
    d_b_in: float = 0.75,
    fu_rod_ksi: Optional[float] = None,
) -> Dict[str, Any]:
    """Lookup bolt F_nt, F_nv, phi, Omega (Table J3.2) and A_b, T_b (Table J3.1)."""
    csv_path = kb.get_file_path(TABLE_J3_2_FILE)
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))

    grade_u = bolt_grade.strip().upper()
    thr_u = thread_condition.strip().upper()
    is_x = thr_u.startswith("X") or "EXCLUD" in thr_u

    f_nt = 0.0
    f_nv = 0.0
    phi_val = 0.75
    omega_val = 2.0
    desc = ""

    # Match rows 1..9 of Table J3.2
    for row in rows[1:10]:
        if len(row) < 7:
            continue
        r_desc = row[0].strip()
        r_spec = row[1].strip().upper()
        r_thr = row[2].strip().upper()
        is_row_x = "(X)" in r_desc.upper() or (
            "EXCLUDED FROM" in r_thr and "NOT EXCLUDED" not in r_thr
        )

        matched = False
        if "A307" in grade_u and "A307" in r_spec:
            matched = True
        elif any(g in grade_u for g in ("A325", "F1852", "GROUP A")) and "A325" in r_spec:
            matched = is_row_x == is_x
        elif any(g in grade_u for g in ("A490", "F2280", "GROUP B")) and "A490" in r_spec:
            matched = is_row_x == is_x
        elif any(g in grade_u for g in ("F3043", "F3111", "GROUP C")) and "F3043" in r_spec:
            matched = is_row_x == is_x
        elif any(g in grade_u for g in ("F1554", "THREADED")) and "F1554" in r_spec:
            matched = is_row_x == is_x

        if matched:
            desc = r_desc
            phi_val = float(row[5])
            omega_val = float(row[6])
            fnt_str = row[3].strip()
            fnv_str = row[4].strip()
            if "F_u" in fnt_str or "F_u" in fnv_str:
                fu = fu_rod_ksi if fu_rod_ksi is not None else 58.0
                f_nt = 0.75 * fu
                f_nv = (0.563 if is_x else 0.450) * fu
            else:
                f_nt = float(fnt_str)
                f_nv = float(fnv_str)
            break

    if f_nt <= 0.0:
        raise InputValidationError(f"Unsupported bolt grade '{bolt_grade}' in Table J3.2.")

    # Lookup A_b and T_b from Supplemental Table J3.1 (rows 13..21)
    a_b = math.pi * (d_b_in ** 2) / 4.0
    t_b_kips = 0.0
    for row in rows[13:22]:
        if len(row) < 5:
            continue
        row_d = _parse_fraction(row[0], -1.0)
        if abs(row_d - d_b_in) <= 1e-4:
            a_b = float(row[1])
            if "A325" in grade_u or "GROUP A" in grade_u:
                t_b_kips = _parse_fraction(row[2], 0.0)
            elif "A490" in grade_u or "GROUP B" in grade_u:
                t_b_kips = _parse_fraction(row[3], 0.0)
            elif "GROUP C" in grade_u:
                t_b_kips = _parse_fraction(row[4], 0.0)
            break

    return {
        "description": desc,
        "F_nt_ksi": f_nt,
        "F_nv_ksi": f_nv,
        "phi": phi_val,
        "Omega": omega_val,
        "A_b_in2": a_b,
        "T_b_kips": t_b_kips,
    }


def lookup_hole_and_edge_limits(
    kb: ReferenceDataPort,
    d_b_in: float,
    hole_type: str = "STD",
) -> Dict[str, float]:
    """Lookup bolt hole dimensions, C2 edge increments, and min spacing from Tables J3.3-J3.5."""
    csv_path = kb.get_file_path(TABLE_J3_3_FILE)
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))

    ht = hole_type.strip().upper()
    matched_row: Optional[List[str]] = None
    for row in rows[1:9]:
        if len(row) < 11:
            continue
        if "OVER" in row[0].upper():
            if d_b_in > 1.25:
                matched_row = row
                break
        elif abs(_parse_fraction(row[0], -1.0) - d_b_in) <= 1e-4:
            matched_row = row
            break

    if matched_row is None:
        # Interpolate/compute general code expression
        d_std = d_b_in + (0.0625 if d_b_in < 1.0 else 0.125)
        d_ovs = d_b_in + (0.125 if d_b_in <= 0.875 else 0.25 if d_b_in == 1.0 else 0.3125)
        le_min_std = 1.25 * d_b_in
        c2 = 0.0 if ht == "STD" else (0.125 if ht == "OVS" else 0.1875)
        s_min = 2.667 * d_b_in
        s_pref = 3.0 * d_b_in
        d_h = d_ovs if ht == "OVS" else d_std
    else:
        if "OVER" in matched_row[0].upper():
            d_std = d_b_in + 0.125
            d_ovs = d_b_in + 0.3125
            le_min_std = 1.25 * d_b_in
            s_min = 2.667 * d_b_in
            s_pref = 3.0 * d_b_in
            c2_ovs = 0.125
            c2_ssl = 0.1875
            c2_lsl = 0.75 * d_b_in
        else:
            d_std = _parse_fraction(matched_row[1])
            d_ovs = _parse_fraction(matched_row[2])
            le_min_std = _parse_fraction(matched_row[5])
            c2_ovs = _parse_fraction(matched_row[6])
            c2_ssl = _parse_fraction(matched_row[7])
            c2_lsl = _parse_fraction(matched_row[8])
            s_min = _parse_fraction(matched_row[9])
            s_pref = _parse_fraction(matched_row[10])

        if ht in ("OVS", "OVERSIZED"):
            d_h = d_ovs
            c2 = c2_ovs
        elif ht in ("SSL", "SHORT_SLOT", "SHORT-SLOT"):
            d_h = d_std
            c2 = c2_ssl
        elif ht in ("LSL", "LONG_SLOT", "LONG-SLOT"):
            d_h = d_std
            c2 = c2_lsl
        else:
            d_h = d_std
            c2 = 0.0

    return {
        "d_h_in": d_h,
        "d_h_eff_in": d_h + 0.0625,
        "le_min_in": le_min_std + c2,
        "c2_in": c2,
        "s_min_in": s_min,
        "s_pref_in": s_pref,
    }


def lookup_icor_c_coefficient(
    kb: ReferenceDataPort,
    n_bolts: int,
    e_x_in: float,
    spacing_in: float = 3.0,
) -> Tuple[float, float]:
    """Lookup AISC Manual Part 7 Table 7-6 C coefficient and C' for single vertical row.

    Interpolates linearly across e_x in Table 7-6 CSV for s = 3.0 in. If spacing differs
    from 3.0 in. or n_bolts > 12, scales linearly via elastic vector ICOR fallback.
    """
    if n_bolts <= 1:
        return (1.0, 0.0)
    if e_x_in <= 0.0:
        return (float(n_bolts), 0.0)

    csv_path = kb.get_file_path(PART7_ICOR_FILE)
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))

    ex_cols = [0.0, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0, 10.0, 12.0]
    table_map: Dict[int, Tuple[List[float], float]] = {}
    for row in rows[1:12]:
        if len(row) < 11:
            continue
        n_val = int(row[0])
        c_vals = [float(n_val)] + [float(x) for x in row[1:10]]
        c_prime = float(row[10])
        table_map[n_val] = (c_vals, c_prime)

    def _interp_row(n_i: int, e_target: float) -> Tuple[float, float]:
        c_vals, cp = table_map[n_i]
        if e_target >= ex_cols[-1]:
            # Asymptotic pure moment C ~ C' / e_x
            return (min(c_vals[-1], cp / e_target), cp)
        for j in range(len(ex_cols) - 1):
            e0, e1 = ex_cols[j], ex_cols[j + 1]
            if e0 <= e_target <= e1:
                t = (e_target - e0) / (e1 - e0)
                return (c_vals[j] + t * (c_vals[j + 1] - c_vals[j]), cp)
        return (c_vals[0], cp)

    if abs(spacing_in - 3.0) <= 0.15 and 2 <= n_bolts <= 12:
        return _interp_row(n_bolts, e_x_in)

    # Elastic bolt-group vector fallback when non-standard spacing or >12 bolts
    y_coords = [(i - (n_bolts - 1) / 2.0) * spacing_in for i in range(n_bolts)]
    sum_r2 = sum(y ** 2 for y in y_coords)
    y_max = max(abs(y) for y in y_coords)
    r_v = 1.0 / n_bolts
    r_m = (e_x_in * y_max) / sum_r2 if sum_r2 > 0 else 0.0
    c_elastic = 1.0 / math.hypot(r_v, r_m)
    cp_est = sum_r2 / y_max if y_max > 0 else 0.0
    return (c_elastic, cp_est)


def calculate_steel_bolted_connection(
    inputs: Dict[str, Any],
    kb: ReferenceDataPort,
    design_method: DesignMethod = DesignMethod.ASD,
    calculation_id: Optional[str] = None,
) -> CalculationResult:
    """Evaluate AISC 360-22 Chapter J bolted steel connection across all 4 load-path stages."""
    method = validate_design_method(design_method)
    calc_id = calculation_id or str(inputs.get("calculation_id") or f"calc-steel-bolts-{uuid.uuid4().hex[:8]}")

    ref_proc = _build_aisc_ref(
        kb, "procedure", "Steel Bolted Connection Workflow",
        identifier=PROC_BOLTS_FILE,
        fallback_path="procedures/03_steel_design/steel_bolted_connection_aisc_workflow.md",
    )
    ref_j3_2 = _build_aisc_ref(kb, "table", "Table J3.2 & Table J3.1", identifier=TABLE_J3_2_FILE)
    ref_j3_3 = _build_aisc_ref(kb, "table", "Tables J3.3, J3.4, J3.5", identifier=TABLE_J3_3_FILE)
    ref_mat = _build_aisc_ref(kb, "table", "ASTM Material Grades", identifier=MATERIAL_GRADES_FILE)
    ref_part7 = _build_aisc_ref(kb, "table", "AISC Manual Table 7-6 (ICOR)", identifier=PART7_ICOR_FILE)

    req_keys = ("d_b_in", "bolt_grade", "t_plate_in", "w_plate_in", "n_bolts_per_line", "n_lines")
    blank_reasons = _check_blank_inputs(inputs, req_keys)
    if blank_reasons:
        return _make_incomplete_result(
            calc_id, "aisc_bolt_bearing", "AISC 360-22 (16th Ed.)", method, inputs, blank_reasons,
            [ref_proc, ref_j3_2, ref_j3_3, ref_mat],
        )

    # 1. Parse inputs (Section 7 benchmark fixture when inputs={})
    d_b_in = validate_positive("d_b_in", inputs.get("d_b_in", 0.75))
    bolt_grade = str(inputs.get("bolt_grade", "A325")).strip()
    thread_cond = str(inputs.get("thread_condition", "N")).strip().upper()
    hole_type = str(inputs.get("hole_type", "STD")).strip().upper()
    n_shear_planes = int(validate_positive("n_shear_planes", inputs.get("n_shear_planes", 1)))
    n_bolts_per_line = int(validate_positive("n_bolts_per_line", inputs.get("n_bolts_per_line", 2)))
    n_lines = int(validate_positive("n_lines", inputs.get("n_lines", 2)))
    s_in = validate_positive("s_in", inputs.get("s_in", 3.0))
    l_e_in = validate_positive("l_e_in", inputs.get("l_e_in", 1.5))
    g_in = validate_positive("g_in", inputs.get("g_in", 3.0))
    e_x_in = validate_non_negative("e_x_in", inputs.get("e_x_in", 0.0))

    plate_grade = str(inputs.get("plate_grade", "A36")).strip()
    t_plate_in = validate_positive("t_plate_in", inputs.get("t_plate_in", 0.375))
    w_plate_in = validate_positive("w_plate_in", inputs.get("w_plate_in", 6.0))
    u_shear_lag = validate_positive("U_shear_lag", inputs.get("U_shear_lag", 1.0))
    deformation_considered = bool(inputs.get("deformation_considered", True))

    mat = lookup_material_grade(kb, plate_grade)
    fy_ksi = float(inputs.get("Fy_ksi", mat["Fy_ksi"]))
    fu_ksi = float(inputs.get("Fu_ksi", mat["Fu_ksi"]))

    # Strict ASD vs LRFD load selection
    if method == DesignMethod.LRFD:
        v_shear_demand = validate_non_negative(
            "V_u_kips", inputs.get("V_u_kips", inputs.get("T_u_kips", 68.0))
        )
        t_bolt_demand = validate_non_negative("T_bolt_u_kips", inputs.get("T_bolt_u_kips", 0.0))
    else:
        v_shear_demand = validate_non_negative(
            "V_a_kips", inputs.get("V_a_kips", inputs.get("T_a_kips", 45.0))
        )
        t_bolt_demand = validate_non_negative("T_bolt_a_kips", inputs.get("T_bolt_a_kips", 0.0))

    n_total = n_bolts_per_line * n_lines

    # 2. CSV Lookups (Tables J3.2, J3.3-J3.5, Part 7)
    bolt_props = lookup_bolt_properties(kb, bolt_grade, thread_cond, d_b_in, fu_rod_ksi=fu_ksi)
    hole_props = lookup_hole_and_edge_limits(kb, d_b_in, hole_type)

    a_b = bolt_props["A_b_in2"]
    f_nt = bolt_props["F_nt_ksi"]
    f_nv = bolt_props["F_nv_ksi"]
    phi_bolt = bolt_props["phi"]
    omega_bolt = bolt_props["Omega"]

    d_h = hole_props["d_h_in"]
    d_h_eff = hole_props["d_h_eff_in"]
    le_min_req = hole_props["le_min_in"]
    s_min_req = hole_props["s_min_in"]
    le_max_lim = min(12.0 * t_plate_in, 6.0)
    s_max_lim = min(24.0 * t_plate_in, 12.0)

    # 3. Stage 1 Detailing Checks
    detailing_ok = (l_e_in >= le_min_req) and (s_in >= s_min_req)
    dcr_edge = le_min_req / l_e_in
    dcr_spacing = s_min_req / s_in

    # 4. Stage 2 Primary Force Transfer: Bolt Shear, ICOR Eccentricity, Combined Tension-Shear
    r_nv_single = f_nv * a_b * n_shear_planes
    if e_x_in > 0.0 and n_lines == 1:
        c_icor, _ = lookup_icor_c_coefficient(kb, n_bolts_per_line, e_x_in, spacing_in=s_in)
    elif e_x_in > 0.0:
        # Multi-line elastic ICOR capacity ratio
        y_vals = [(i - (n_bolts_per_line - 1) / 2.0) * s_in for i in range(n_bolts_per_line)]
        x_vals = [(j - (n_lines - 1) / 2.0) * g_in for j in range(n_lines)]
        sum_r2 = sum(x ** 2 + y ** 2 for x in x_vals for y in y_vals)
        max_rx = max(abs(x) for x in x_vals)
        max_ry = max(abs(y) for y in y_vals)
        rv = 1.0 / n_total
        rm_y = (e_x_in * max_rx) / sum_r2 if sum_r2 > 0 else 0.0
        rm_x = (e_x_in * max_ry) / sum_r2 if sum_r2 > 0 else 0.0
        c_icor = 1.0 / math.hypot(rv + rm_y, rm_x)
    else:
        c_icor = float(n_total)

    r_n_bolt_shear = c_icor * r_nv_single
    cap_bolt_shear = phi_bolt * r_n_bolt_shear if method == DesignMethod.LRFD else r_n_bolt_shear / omega_bolt
    dcr_bolt_shear = v_shear_demand / cap_bolt_shear

    # Combined Tension and Shear (Sec. J3.7 Eq. J3-3a / J3-3b) when tension is also present
    f_rv = (v_shear_demand / (n_total * a_b * n_shear_planes)) if v_shear_demand > 0 else 0.0
    if method == DesignMethod.LRFD:
        f_nt_prime = min(f_nt, 1.3 * f_nt - (f_nt / (phi_bolt * f_nv)) * f_rv)
        cap_bolt_tension = phi_bolt * max(0.0, f_nt_prime) * a_b * n_total
    else:
        f_nt_prime = min(f_nt, 1.3 * f_nt - (omega_bolt * f_nt / f_nv) * f_rv)
        cap_bolt_tension = (max(0.0, f_nt_prime) * a_b * n_total) / omega_bolt
    dcr_bolt_tension = (t_bolt_demand / cap_bolt_tension) if t_bolt_demand > 0 and cap_bolt_tension > 0 else (99.0 if t_bolt_demand > 0 else 0.0)

    # 5. Stage 3 Connecting Element: Bolt Bearing/Tear-Out & Block Shear Rupture
    l_c_edge = max(0.0, l_e_in - 0.5 * d_h)
    l_c_int = max(0.0, s_in - d_h)
    c_tear = 1.2 if deformation_considered else 1.5
    c_brg = 2.4 if deformation_considered else 3.0

    r_n_brg_cap = c_brg * d_b_in * t_plate_in * fu_ksi
    r_n_edge_bolt = min(c_tear * l_c_edge * t_plate_in * fu_ksi, r_n_brg_cap)
    r_n_int_bolt = min(c_tear * l_c_int * t_plate_in * fu_ksi, r_n_brg_cap)
    r_n_bearing = n_lines * (r_n_edge_bolt + max(0, n_bolts_per_line - 1) * r_n_int_bolt)
    cap_bearing = 0.75 * r_n_bearing if method == DesignMethod.LRFD else r_n_bearing / 2.00
    dcr_bearing = v_shear_demand / cap_bearing

    # Block shear rupture (Sec. J4.3 Eq. J4-5): U-block between gauge lines (n_lines >= 2) or edge block
    if n_lines >= 2:
        n_shear_planes_bs = 2
        a_gv = n_shear_planes_bs * (l_e_in + (n_bolts_per_line - 1) * s_in) * t_plate_in
        a_nv = n_shear_planes_bs * max(
            0.0, (l_e_in + (n_bolts_per_line - 1) * s_in) - (n_bolts_per_line - 0.5) * d_h_eff
        ) * t_plate_in
        a_nt = max(0.0, (g_in * (n_lines - 1) - (n_lines - 1) * d_h_eff)) * t_plate_in
    else:
        a_gv = (l_e_in + (n_bolts_per_line - 1) * s_in) * t_plate_in
        a_nv = max(0.0, (l_e_in + (n_bolts_per_line - 1) * s_in) - (n_bolts_per_line - 0.5) * d_h_eff) * t_plate_in
        w_edge_t = max(0.5 * w_plate_in, l_e_in)
        a_nt = max(0.0, (w_edge_t - 0.5 * d_h_eff)) * t_plate_in

    u_bs = 1.0
    r_n_bs = min(
        0.60 * fu_ksi * a_nv + u_bs * fu_ksi * a_nt,
        0.60 * fy_ksi * a_gv + u_bs * fu_ksi * a_nt,
    )
    cap_bs = 0.75 * r_n_bs if method == DesignMethod.LRFD else r_n_bs / 2.00
    dcr_bs = v_shear_demand / cap_bs

    # 6. Stage 4 Connected Plate Gross Tension Yielding & Net Section Rupture (Sec. J4.1)
    a_g = w_plate_in * t_plate_in
    a_n = max(0.0, w_plate_in - n_lines * d_h_eff) * t_plate_in
    a_e = u_shear_lag * a_n

    p_n_yield = fy_ksi * a_g
    cap_plate_yield = 0.90 * p_n_yield if method == DesignMethod.LRFD else p_n_yield / 1.67
    dcr_plate_yield = v_shear_demand / cap_plate_yield

    p_n_rupture = fu_ksi * a_e
    cap_plate_rupture = 0.75 * p_n_rupture if method == DesignMethod.LRFD else p_n_rupture / 2.00
    dcr_plate_rupture = v_shear_demand / cap_plate_rupture

    # 7. Assemble LimitStates and 4-Stage Trace
    limit_states: List[LimitStateResult] = [
        LimitStateResult(
            step_id="S2_BOLT",
            name="Bolt Group Shear Capacity (Table J3.2)",
            code_clause="AISC 360-22 Sec. J3.6 / Table J3.2",
            equation_latex=r"\phi R_n = \phi \cdot C \cdot F_{nv} \cdot A_b \cdot n_s" if method == DesignMethod.LRFD else r"R_n / \Omega = C \cdot F_{nv} \cdot A_b \cdot n_s / \Omega",
            substitution_str=f"{c_icor:.3f} * {f_nv:.1f} ksi * {a_b:.4f} in.^2 * {n_shear_planes}",
            demand=round(v_shear_demand, 2),
            capacity=round(cap_bolt_shear, 2),
            units="kips",
            dcr=round(dcr_bolt_shear, 3),
            status=CalculationStatus.PASS if dcr_bolt_shear <= 1.0 else CalculationStatus.FAIL,
            notes=f"{n_total}x {d_b_in:.3f} in. {bolt_grade}-{thread_cond}, C={c_icor:.3f}",
        ),
        LimitStateResult(
            step_id="S3_BEARING",
            name="Plate Bolt Bearing & Tear-Out (Sec. J3.10)",
            code_clause="AISC 360-22 Eq. J3-6a",
            equation_latex=r"R_n = \sum \min(1.2 \cdot l_c \cdot t \cdot F_u,  2.4 \cdot d_b \cdot t \cdot F_u)",
            substitution_str=f"R_n_edge={r_n_edge_bolt:.2f} kips, R_n_int={r_n_int_bolt:.2f} kips",
            demand=round(v_shear_demand, 2),
            capacity=round(cap_bearing, 2),
            units="kips",
            dcr=round(dcr_bearing, 3),
            status=CalculationStatus.PASS if dcr_bearing <= 1.0 else CalculationStatus.FAIL,
            notes=f"l_c,edge={l_c_edge:.3f} in., l_c,int={l_c_int:.3f} in.",
        ),
        LimitStateResult(
            step_id="S3_BLOCK",
            name="Plate Block Shear Rupture (Sec. J4.3)",
            code_clause="AISC 360-22 Eq. J4-5",
            equation_latex=r"R_n = \min(0.6 F_u A_{nv} + U_{bs} F_u A_{nt},  0.6 F_y A_{gv} + U_{bs} F_u A_{nt})",
            substitution_str=f"Agv={a_gv:.3f}, Anv={a_nv:.3f}, Ant={a_nt:.3f} in.^2",
            demand=round(v_shear_demand, 2),
            capacity=round(cap_bs, 2),
            units="kips",
            dcr=round(dcr_bs, 3),
            status=CalculationStatus.PASS if dcr_bs <= 1.0 else CalculationStatus.FAIL,
            notes=f"U_bs={u_bs:.2f}",
        ),
        LimitStateResult(
            step_id="S4_YIELD",
            name="Connected Plate Gross Tension Yielding (Sec. J4.1)",
            code_clause="AISC 360-22 Eq. J4-1",
            equation_latex=r"P_n = F_y \cdot A_g",
            substitution_str=f"{fy_ksi:.1f} ksi * {a_g:.3f} in.^2",
            demand=round(v_shear_demand, 2),
            capacity=round(cap_plate_yield, 2),
            units="kips",
            dcr=round(dcr_plate_yield, 3),
            status=CalculationStatus.PASS if dcr_plate_yield <= 1.0 else CalculationStatus.FAIL,
        ),
        LimitStateResult(
            step_id="S4_RUPTURE",
            name="Connected Plate Net Section Rupture (Sec. J4.1)",
            code_clause="AISC 360-22 Eq. J4-2",
            equation_latex=r"P_n = F_u \cdot A_e",
            substitution_str=f"{fu_ksi:.1f} ksi * {a_e:.3f} in.^2",
            demand=round(v_shear_demand, 2),
            capacity=round(cap_plate_rupture, 2),
            units="kips",
            dcr=round(dcr_plate_rupture, 3),
            status=CalculationStatus.PASS if dcr_plate_rupture <= 1.0 else CalculationStatus.FAIL,
            notes=f"d_h,eff={d_h_eff:.4f} in.",
        ),
    ]

    if t_bolt_demand > 0.0:
        limit_states.append(
            LimitStateResult(
                step_id="S2_INTER",
                name="Combined Bolt Tension & Shear (Sec. J3.7)",
                code_clause="AISC 360-22 Eq. J3-3a / J3-3b",
                equation_latex=r"F'_{nt} = 1.3 F_{nt} - \frac{F_{nt}}{\phi F_{nv}} f_{rv}" if method == DesignMethod.LRFD else r"F'_{nt} = 1.3 F_{nt} - \frac{\Omega F_{nt}}{F_{nv}} f_{rv}",
                substitution_str=f"F'_nt={f_nt_prime:.2f} ksi, f_rv={f_rv:.2f} ksi",
                demand=round(t_bolt_demand, 2),
                capacity=round(cap_bolt_tension, 2),
                units="kips",
                dcr=round(dcr_bolt_tension, 3),
                status=CalculationStatus.PASS if dcr_bolt_tension <= 1.0 else CalculationStatus.FAIL,
            )
        )

    gov_ls = max(limit_states, key=lambda x: x.dcr)
    overall_pass = detailing_ok and all(ls.status == CalculationStatus.PASS for ls in limit_states)
    overall_status = CalculationStatus.PASS if overall_pass else CalculationStatus.FAIL

    if method == DesignMethod.LRFD:
        bolt_sym = _validated_markup(r"\phi R_n = \phi \cdot C \cdot F_{nv} \cdot A_b \cdot n_s")
        bolt_sub = _validated_markup(rf"0.75 \cdot {c_icor:.3f} \cdot {f_nv:.1f} \cdot {a_b:.4f} \cdot {n_shear_planes} = {cap_bolt_shear:.2f} \text{{ kips}}")
        brg_sym = _validated_markup(r"\phi R_{n,\text{brg}} = \phi \cdot \sum \min\left(1.2 \cdot l_c \cdot t \cdot F_u, 2.4 \cdot d_b \cdot t \cdot F_u\right)")
        brg_sub = _validated_markup(rf"0.75 \cdot {r_n_bearing:.2f} = {cap_bearing:.2f} \text{{ kips}}")
        bs_sym = _validated_markup(r"\phi R_{n,\text{bs}} = \phi \cdot \min\left(0.6 F_u A_{nv} + U_{bs} F_u A_{nt}, 0.6 F_y A_{gv} + U_{bs} F_u A_{nt}\right)")
        bs_sub = _validated_markup(rf"0.75 \cdot {r_n_bs:.2f} = {cap_bs:.2f} \text{{ kips}}")
        py_sym = _validated_markup(r"\phi P_{n,y} = 0.90 \cdot F_y \cdot A_g")
        py_sub = _validated_markup(rf"0.90 \cdot {fy_ksi:.1f} \cdot {a_g:.3f} = {cap_plate_yield:.2f} \text{{ kips}}")
        pr_sym = _validated_markup(r"\phi P_{n,r} = 0.75 \cdot F_u \cdot A_e")
        pr_sub = _validated_markup(rf"0.75 \cdot {fu_ksi:.1f} \cdot {a_e:.3f} = {cap_plate_rupture:.2f} \text{{ kips}}")
    else:
        bolt_sym = _validated_markup(r"\frac{R_n}{\Omega} = \frac{C \cdot F_{nv} \cdot A_b \cdot n_s}{\Omega}")
        bolt_sub = _validated_markup(rf"\frac{{{c_icor:.3f} \cdot {f_nv:.1f} \cdot {a_b:.4f} \cdot {n_shear_planes}}}{{2.00}} = {cap_bolt_shear:.2f} \text{{ kips}}")
        brg_sym = _validated_markup(r"\frac{R_{n,\text{brg}}}{\Omega} = \frac{\sum \min\left(1.2 \cdot l_c \cdot t \cdot F_u, 2.4 \cdot d_b \cdot t \cdot F_u\right)}{2.00}")
        brg_sub = _validated_markup(rf"\frac{{{r_n_bearing:.2f}}}{{2.00}} = {cap_bearing:.2f} \text{{ kips}}")
        bs_sym = _validated_markup(r"\frac{R_{n,\text{bs}}}{\Omega} = \frac{\min\left(0.6 F_u A_{nv} + U_{bs} F_u A_{nt}, 0.6 F_y A_{gv} + U_{bs} F_u A_{nt}\right)}{2.00}")
        bs_sub = _validated_markup(rf"\frac{{{r_n_bs:.2f}}}{{2.00}} = {cap_bs:.2f} \text{{ kips}}")
        py_sym = _validated_markup(r"\frac{P_{n,y}}{\Omega} = \frac{F_y \cdot A_g}{1.67}")
        py_sub = _validated_markup(rf"\frac{{{fy_ksi:.1f} \cdot {a_g:.3f}}}{{1.67}} = {cap_plate_yield:.2f} \text{{ kips}}")
        pr_sym = _validated_markup(r"\frac{P_{n,r}}{\Omega} = \frac{F_u \cdot A_e}{2.00}")
        pr_sub = _validated_markup(rf"\frac{{{fu_ksi:.1f} \cdot {a_e:.3f}}}{{2.00}} = {cap_plate_rupture:.2f} \text{{ kips}}")

    trace_steps: List[CalcStep] = [
        CalcStep(
            step_id="S1_DETAIL",
            stage=LoadPathStage.STAGE_1_GEOMETRY_AND_LIMITS,
            title="Bolt Hole, Spacing & Edge Distance Detailing Limits",
            symbolic=_validated_markup(r"l_e \geq l_{e,\min}, l_e \text{ and } s \geq 2.667 d_b"),
            substituted=_validated_markup(
                rf"l_e = {l_e_in:.3f} \text{{ in.}} \geq {le_min_req:.3f} \text{{ in., }} s = {s_in:.3f} \text{{ in.}} \geq {s_min_req:.3f} \text{{ in.}}"
            ),
            variables={
                "d_b": Quantity("d_b", d_b_in, "in.", "Nominal bolt diameter"),
                "d_h": Quantity("d_h", round(d_h, 4), "in.", "Hole diameter (Table J3.3)"),
                "l_e": Quantity("l_e", l_e_in, "in.", "Provided edge distance"),
                "l_e_min": Quantity("l_{e,\\min}", round(le_min_req, 3), "in.", "Minimum edge distance (Table J3.4/J3.5)"),
                "s": Quantity("s", s_in, "in.", "Provided bolt spacing"),
                "s_min": Quantity("s_{\\min}", round(s_min_req, 3), "in.", "Minimum bolt spacing (Sec. J3.3)"),
            },
            result_value=round(l_e_in, 3),
            result_unit="in.",
            acceptance=AcceptanceCriterion(
                ">=",
                round(le_min_req, 3),
                "in.",
                f"Detailing geometry check (l_e <= {le_max_lim:.2f} in., s <= {s_max_lim:.2f} in.)",
                is_dcr_check=False,
            ),
            dcr=None,
            status=CalculationStatus.PASS if detailing_ok else CalculationStatus.FAIL,
            refs=(ref_j3_3, ref_proc),
        ),
        CalcStep(
            step_id="S2_BOLT_SHEAR",
            stage=LoadPathStage.STAGE_2_PRIMARY_FORCE_TRANSFER,
            title="Bolt Group Shear Capacity (ICOR / Concentric)",
            symbolic=bolt_sym,
            substituted=bolt_sub,
            variables={
                "C": Quantity("C", round(c_icor, 3), "", "Effective bolt group count / ICOR coefficient"),
                "F_nv": Quantity("F_{nv}", f_nv, "ksi", "Nominal bolt shear stress (Table J3.2)"),
                "A_b": Quantity("A_b", round(a_b, 4), "in.^2", "Nominal unthreaded bolt area"),
                "V_demand": Quantity("V", round(v_shear_demand, 2), "kips", f"{method.value} applied shear/transfer force"),
                "R_bolt": Quantity("R_{bolt}", round(cap_bolt_shear, 2), "kips", f"{method.value} bolt shear capacity"),
            },
            result_value=round(cap_bolt_shear, 2),
            result_unit="kips",
            acceptance=AcceptanceCriterion(">=", round(v_shear_demand, 2), "kips", f"{method.value} bolt shear strength", is_dcr_check=True),
            dcr=round(dcr_bolt_shear, 3),
            status=CalculationStatus.PASS if dcr_bolt_shear <= 1.0 else CalculationStatus.FAIL,
            refs=(ref_j3_2, ref_part7, ref_proc),
        ),
    ]

    if t_bolt_demand > 0.0:
        trace_steps.append(
            CalcStep(
                step_id="S2_INTER",
                stage=LoadPathStage.STAGE_2_PRIMARY_FORCE_TRANSFER,
                title="Combined Tension and Shear in Bearing-Type Bolts (Sec. J3.7)",
                symbolic=_validated_markup(
                    r"F'_{nt} = 1.3 F_{nt} - \frac{F_{nt}}{\phi F_{nv}} f_{rv}"
                    if method == DesignMethod.LRFD
                    else r"F'_{nt} = 1.3 F_{nt} - \frac{\Omega F_{nt}}{F_{nv}} f_{rv}"
                ),
                substituted=_validated_markup(
                    rf"F'_{{nt}} = {f_nt_prime:.2f} \text{{ ksi, }} T_{{cap}} = {cap_bolt_tension:.2f} \text{{ kips}}"
                ),
                variables={
                    "f_rv": Quantity("f_{rv}", round(f_rv, 2), "ksi", "Required bolt shear stress"),
                    "F_nt_prime": Quantity("F'_{nt}", round(f_nt_prime, 2), "ksi", "Modified nominal tensile stress"),
                    "T_demand": Quantity("T", round(t_bolt_demand, 2), "kips", "Applied bolt tension"),
                    "T_cap": Quantity("T_{cap}", round(cap_bolt_tension, 2), "kips", f"{method.value} modified tension capacity"),
                },
                result_value=round(cap_bolt_tension, 2),
                result_unit="kips",
                acceptance=AcceptanceCriterion(">=", round(t_bolt_demand, 2), "kips", "Combined tension-shear check", is_dcr_check=True),
                dcr=round(dcr_bolt_tension, 3),
                status=CalculationStatus.PASS if dcr_bolt_tension <= 1.0 else CalculationStatus.FAIL,
                refs=(ref_j3_2, ref_proc),
            )
        )

    trace_steps.extend([
        CalcStep(
            step_id="S3_BEARING",
            stage=LoadPathStage.STAGE_3_CONNECTING_ELEMENT_AND_BASE_METAL,
            title="Plate Bolt Bearing & Tear-Out Check (Sec. J3.10)",
            symbolic=brg_sym,
            substituted=brg_sub,
            variables={
                "l_c_edge": Quantity("l_{c,edge}", round(l_c_edge, 3), "in.", "Edge bolt clear tear-out distance"),
                "l_c_int": Quantity("l_{c,int}", round(l_c_int, 3), "in.", "Interior bolt clear distance"),
                "t": Quantity("t", t_plate_in, "in.", "Plate thickness"),
                "F_u": Quantity("F_u", fu_ksi, "ksi", "Specified minimum tensile strength"),
                "R_brg": Quantity("R_{brg}", round(cap_bearing, 2), "kips", f"{method.value} bearing/tear-out capacity"),
            },
            result_value=round(cap_bearing, 2),
            result_unit="kips",
            acceptance=AcceptanceCriterion(">=", round(v_shear_demand, 2), "kips", f"{method.value} bolt bearing check", is_dcr_check=True),
            dcr=round(dcr_bearing, 3),
            status=CalculationStatus.PASS if dcr_bearing <= 1.0 else CalculationStatus.FAIL,
            refs=(ref_mat, RefSpec("AISC 360", "2022", "section", "Sec. J3.10 Eq. J3-6a"), ref_proc),
        ),
        CalcStep(
            step_id="S3_BLOCK",
            stage=LoadPathStage.STAGE_3_CONNECTING_ELEMENT_AND_BASE_METAL,
            title="Plate Block Shear Rupture Check (Sec. J4.3)",
            symbolic=bs_sym,
            substituted=bs_sub,
            variables={
                "A_gv": Quantity("A_{gv}", round(a_gv, 3), "in.^2", "Gross shear area"),
                "A_nv": Quantity("A_{nv}", round(a_nv, 3), "in.^2", "Net shear area"),
                "A_nt": Quantity("A_{nt}", round(a_nt, 3), "in.^2", "Net tension area"),
                "R_bs": Quantity("R_{bs}", round(cap_bs, 2), "kips", f"{method.value} block shear capacity"),
            },
            result_value=round(cap_bs, 2),
            result_unit="kips",
            acceptance=AcceptanceCriterion(">=", round(v_shear_demand, 2), "kips", f"{method.value} block shear check", is_dcr_check=True),
            dcr=round(dcr_bs, 3),
            status=CalculationStatus.PASS if dcr_bs <= 1.0 else CalculationStatus.FAIL,
            refs=(ref_mat, RefSpec("AISC 360", "2022", "section", "Sec. J4.3 Eq. J4-5"), ref_proc),
        ),
        CalcStep(
            step_id="S4_YIELD",
            stage=LoadPathStage.STAGE_4_SUPPORTING_MEMBER_AND_GLOBAL,
            title="Connected Plate Gross Section Tension Yielding (Sec. J4.1)",
            symbolic=py_sym,
            substituted=py_sub,
            variables={
                "F_y": Quantity("F_y", fy_ksi, "ksi", "Specified minimum yield stress"),
                "A_g": Quantity("A_g", round(a_g, 3), "in.^2", "Gross plate cross-sectional area"),
                "P_y_cap": Quantity("P_{y,cap}", round(cap_plate_yield, 2), "kips", f"{method.value} gross yielding capacity"),
            },
            result_value=round(cap_plate_yield, 2),
            result_unit="kips",
            acceptance=AcceptanceCriterion(">=", round(v_shear_demand, 2), "kips", f"{method.value} gross tension yielding check", is_dcr_check=True),
            dcr=round(dcr_plate_yield, 3),
            status=CalculationStatus.PASS if dcr_plate_yield <= 1.0 else CalculationStatus.FAIL,
            refs=(ref_mat, RefSpec("AISC 360", "2022", "section", "Sec. J4.1(a) Eq. J4-1"), ref_proc),
        ),
        CalcStep(
            step_id="S4_RUPTURE",
            stage=LoadPathStage.STAGE_4_SUPPORTING_MEMBER_AND_GLOBAL,
            title="Connected Plate Net Section Tension Rupture (Sec. J4.1)",
            symbolic=pr_sym,
            substituted=pr_sub,
            variables={
                "F_u": Quantity("F_u", fu_ksi, "ksi", "Specified minimum tensile strength"),
                "A_e": Quantity("A_e", round(a_e, 3), "in.^2", "Effective net area (U * A_n)"),
                "P_r_cap": Quantity("P_{r,cap}", round(cap_plate_rupture, 2), "kips", f"{method.value} net tension rupture capacity"),
            },
            result_value=round(cap_plate_rupture, 2),
            result_unit="kips",
            acceptance=AcceptanceCriterion(">=", round(v_shear_demand, 2), "kips", f"{method.value} net tension rupture check", is_dcr_check=True),
            dcr=round(dcr_plate_rupture, 3),
            status=CalculationStatus.PASS if dcr_plate_rupture <= 1.0 else CalculationStatus.FAIL,
            refs=(ref_mat, RefSpec("AISC 360", "2022", "section", "Sec. J4.1(b) Eq. J4-2 & Sec. B4.3b"), ref_proc),
        ),
    ])

    warnings: List[str] = []
    if not detailing_ok:
        warnings.append(
            f"Bolt detailing fails Tables J3.3-J3.5: l_e={l_e_in:.3f} in. (min {le_min_req:.3f}), "
            f"s={s_in:.3f} in. (min {s_min_req:.3f})."
        )
    if l_e_in > le_max_lim or s_in > s_max_lim:
        warnings.append(
            f"Max edge/spacing check Sec. J3.5: l_e <= {le_max_lim:.2f} in., s <= {s_max_lim:.2f} in."
        )

    return CalculationResult(
        calculation_id=calc_id,
        module_id="aisc_bolt_bearing",
        code_edition="AISC 360-22 (16th Ed.)",
        design_method=method,
        input_parameters={
            "d_b_in": d_b_in,
            "bolt_grade": bolt_grade,
            "thread_condition": thread_cond,
            "hole_type": hole_type,
            "n_shear_planes": n_shear_planes,
            "n_bolts_per_line": n_bolts_per_line,
            "n_lines": n_lines,
            "s_in": s_in,
            "l_e_in": l_e_in,
            "g_in": g_in,
            "e_x_in": e_x_in,
            "plate_grade": plate_grade,
            "t_plate_in": t_plate_in,
            "w_plate_in": w_plate_in,
            "V_demand_kips": v_shear_demand,
            "T_bolt_demand_kips": t_bolt_demand,
        },
        assumptions=[
            "Standard bearing-type bolt check per AISC 360-22 Chapter J.",
            "Net section width deducts d_h + 1/16 in. per AISC 360-22 Section B4.3b.",
            "Bolt deformation at service load is considered unless explicitly overridden.",
        ],
        intermediate_results={
            "A_b_in2": round(a_b, 4),
            "d_h_in": round(d_h, 4),
            "d_h_eff_in": round(d_h_eff, 4),
            "F_nv_ksi": f_nv,
            "F_nt_ksi": f_nt,
            "C_icor": round(c_icor, 3),
            "Fy_ksi": fy_ksi,
            "Fu_ksi": fu_ksi,
            "cap_bolt_shear_kips": round(cap_bolt_shear, 2),
            "cap_bearing_kips": round(cap_bearing, 2),
            "cap_block_shear_kips": round(cap_bs, 2),
            "cap_plate_yield_kips": round(cap_plate_yield, 2),
            "cap_plate_rupture_kips": round(cap_plate_rupture, 2),
        },
        limit_states=limit_states,
        governing_limit_state=gov_ls,
        demand=gov_ls.demand,
        capacity=gov_ls.capacity,
        dcr=gov_ls.dcr,
        status=overall_status,
        reference_files=[
            r.source_path
            for r in (ref_proc, ref_j3_2, ref_j3_3, ref_mat, ref_part7)
            if r.source_path
        ],
        warnings=warnings,
        trace=tuple(trace_steps),
    )
