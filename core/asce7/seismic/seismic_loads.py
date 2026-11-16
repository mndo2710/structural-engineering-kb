"""ASCE 7-22 Chapter 13 Nonstructural Component Seismic Force (Fp) Calculation Engine.

Conforms to SAD v1.0 Section 6.2 & Master Rules 2, 4, 5.
Retrieves architectural component coefficients (C_AR, R_po, Omega_0p) from
database/asce_7/v7_22/ASCE7-22_Table_13.5-1.csv via KnowledgeBaseService.
"""

from dataclasses import dataclass
import math
from typing import Any, Dict, Optional

from app.services.knowledge_base_service import KnowledgeBaseService
from core.common.validation import validate_non_negative, validate_positive


TABLE_13_5_1_FILE = "ASCE7-22_Table_13.5-1.csv"


@dataclass(frozen=True)
class SeismicComponentCoefficients:
    """Coefficients from ASCE 7-22 Table 13.5-1 for architectural components."""
    category: str
    element: str
    c_ar_below_grade: float
    c_ar_above_grade: float
    r_po: float
    omega_0p: float
    source_reference: str


def lookup_table_13_5_1(
    kb: KnowledgeBaseService,
    element_keyword: str = "Appendages"
) -> SeismicComponentCoefficients:
    """Lookup architectural component seismic parameters from ASCE7-22_Table_13.5-1.csv."""
    rows = kb.get_table_as_dicts(TABLE_13_5_1_FILE)
    keyword_lower = element_keyword.strip().lower()

    for row in rows:
        cat = str(row.get("Component Category", "")).strip()
        elem = str(row.get("Architectural Component or Element", "")).strip()
        if not cat or cat.startswith("Footnotes") or cat.startswith("["):
            continue
        if keyword_lower in cat.lower() or keyword_lower in elem.lower():
            c_below_raw = str(row.get("C_AR (Supported at or Below Grade Plane)", "1.0")).strip()
            c_above_raw = str(row.get("C_AR (Supported Above Grade Plane by a Structure)", "1.0")).strip()
            c_below = float(c_below_raw) if c_below_raw not in ("N/A", "") else float(c_above_raw)
            c_above = float(c_above_raw) if c_above_raw not in ("N/A", "") else c_below
            r_po = float(str(row.get("R_po", "1.5")).strip())
            omega_0p = float(str(row.get("Omega_0p [a]", "1.75")).strip())
            src = str(row.get("Source Reference", "ASCE 7-22 Table 13.5-1")).strip()
            return SeismicComponentCoefficients(
                category=cat,
                element=elem,
                c_ar_below_grade=c_below,
                c_ar_above_grade=c_above,
                r_po=r_po,
                omega_0p=omega_0p,
                source_reference=src,
            )

    # Default fallback to Appendages and Ornamentations if no specific keyword match
    return SeismicComponentCoefficients(
        category="Appendages and Ornamentations",
        element="All (includes attached awnings, canopies, architectural trellises, fins, and sunshades)",
        c_ar_below_grade=1.8,
        c_ar_above_grade=2.2,
        r_po=1.5,
        omega_0p=1.75,
        source_reference="ASCE 7-22 Table 13.5-1",
    )


def calculate_nonstructural_seismic_fp(
    kb: KnowledgeBaseService,
    sds_g: float,
    wp_lbs: float,
    z_ft: float,
    h_ft: float,
    ip: float = 1.0,
    sfrs_r: float = 6.5,
    sfrs_omega_0: float = 3.0,
    sfrs_ie: float = 1.0,
    element_keyword: str = "Appendages",
) -> Dict[str, Any]:
    """
    Calculate horizontal and vertical nonstructural seismic forces (Fp, Ev)
    per ASCE 7-22 Section 13.3.1 (Equations 13.3-1 through 13.3-6).
    """
    sds = validate_non_negative("S_DS", sds_g)
    wp = validate_positive("W_p", wp_lbs)
    z = validate_non_negative("z_ft", z_ft)
    h = validate_positive("h_ft", h_ft)
    ip_val = validate_positive("I_p", ip)
    r_bldg = validate_positive("R", sfrs_r)
    om_bldg = validate_positive("Omega_0", sfrs_omega_0)
    ie_bldg = validate_positive("I_e", sfrs_ie)

    coeffs = lookup_table_13_5_1(kb, element_keyword=element_keyword)

    if z <= 0.0:
        hf = 1.0
        r_mu = 1.0
        c_ar = coeffs.c_ar_below_grade
    else:
        ratio_zh = min(z / h, 1.0)
        hf = 1.0 + 2.5 * ratio_zh
        r_mu = max(1.3, math.sqrt((1.1 * r_bldg) / (ie_bldg * om_bldg)))
        c_ar = coeffs.c_ar_above_grade

    fp_calc = 0.4 * sds * ip_val * wp * (hf / r_mu) * (c_ar / coeffs.r_po)
    fp_min = 0.3 * sds * ip_val * wp
    fp_max = 1.6 * sds * ip_val * wp
    fp_gov = min(max(fp_calc, fp_min), fp_max)
    ev_lbs = 0.2 * sds * wp

    return {
        "C_AR": c_ar,
        "R_po": coeffs.r_po,
        "Omega_0p": coeffs.omega_0p,
        "H_f": round(hf, 4),
        "R_mu": round(r_mu, 4),
        "Fp_calc_lbs": round(fp_calc, 2),
        "Fp_min_lbs": round(fp_min, 2),
        "Fp_max_lbs": round(fp_max, 2),
        "Fp_gov_lbs": round(fp_gov, 2),
        "Ev_lbs": round(ev_lbs, 2),
        "Fp_overstrength_lbs": round(fp_gov * coeffs.omega_0p, 2),
        "reference_file": f"database/asce_7/v7_22/{TABLE_13_5_1_FILE}",
    }
