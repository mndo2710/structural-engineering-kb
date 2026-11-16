"""ASCE 7-22 Chapter 30 Low-Rise C&C External Pressure Coefficients (GCp) Engine.

Conforms to SAD v1.0 Section 6.2 & Master Rules 2, 4, 5.
Evaluates Wall (Figure 30.3-1 / Table C30.3-1) and Gable Roof (Figures 30.3-2A/B / Tables C30.3-2 & C30.3-3)
external pressure coefficients (GCp) as a function of Effective Wind Area A (ft^2).
"""

import math
from typing import Dict, Tuple

from app.services.knowledge_base_service import KnowledgeBaseService
from core.common.validation import validate_non_negative, validate_positive


TABLE_C30_3_1_FILE = "ASCE7-22_Table_C30.3-1.csv"
TABLE_C30_3_2_FILE = "ASCE7-22_Table_C30.3-2_C30.3-3.csv"


def lookup_wall_gcp(
    kb: KnowledgeBaseService,
    effective_area_ft2: float,
    zone: str = "Zone 4",
    roof_slope_deg: float = 0.0,
) -> Dict[str, float]:
    """
    Lookup external wall pressure coefficients (GCp)+ and (GCp)- from ASCE7-22_Table_C30.3-1.csv.
    Applies Note 5 10% reduction factor (0.90) when roof slope theta <= 10 deg.
    """
    area = validate_positive("Effective Wind Area A (ft^2)", effective_area_ft2)
    theta = validate_non_negative("Roof Slope theta (deg)", roof_slope_deg)
    z_norm = "Zone 5" if "5" in str(zone) else "Zone 4"

    df = kb.get_table(TABLE_C30_3_1_FILE)
    gcp_pos = 1.0
    gcp_neg = -1.1 if z_norm == "Zone 4" else -1.4

    for _, row in df.iterrows():
        p_dir = str(row.iloc[0]).strip()
        r_zone = str(row.iloc[1]).strip()
        if p_dir not in ("Positive", "Negative"):
            continue

        a_min = float(str(row.iloc[4]).strip())
        a_max = float(str(row.iloc[5]).strip())
        c0 = float(str(row.iloc[6]).strip())
        c1 = float(str(row.iloc[7]).strip())

        # Match positive (Zones 4 and 5)
        if p_dir == "Positive":
            if (a_min == 0 and area <= a_max) or (a_min < area <= a_max) or (a_min == 500 and area > 500):
                gcp_pos = c0 + c1 * math.log10(max(area, 1.0))

        # Match negative (Zone 4 or Zone 5)
        elif p_dir == "Negative" and r_zone == z_norm:
            if (a_min == 0 and area <= a_max) or (a_min < area <= a_max) or (a_min == 500 and area > 500):
                gcp_neg = c0 + c1 * math.log10(max(area, 1.0))

    slope_factor = 0.90 if theta <= 10.0 else 1.00
    return {
        "zone": z_norm,
        "effective_area_ft2": round(area, 2),
        "slope_reduction_factor": slope_factor,
        "GCp_pos_raw": round(gcp_pos, 4),
        "GCp_neg_raw": round(gcp_neg, 4),
        "GCp_pos": round(gcp_pos * slope_factor, 4),
        "GCp_neg": round(gcp_neg * slope_factor, 4),
    }


def lookup_roof_gcp(
    kb: KnowledgeBaseService,
    effective_area_ft2: float,
    zone: str = "Zone 2",
    roof_slope_deg: float = 5.0,
    parapet_height_ft: float = 0.0,
) -> Dict[str, float]:
    """
    Lookup external roof pressure coefficients (GCp)+ and (GCp)- from ASCE7-22_Table_C30.3-2_C30.3-3.csv.
    Applies Note 5 parapet relief if parapet_height_ft >= 3.0 ft on low-slope roof (theta <= 7 deg):
      - Negative (GCp) in Zone 3 equals Zone 2.
    """
    area = validate_positive("Effective Wind Area A (ft^2)", effective_area_ft2)
    theta = validate_non_negative("Roof Slope theta (deg)", roof_slope_deg)
    h_par = validate_non_negative("Parapet Height h_par (ft)", parapet_height_ft)

    slope_key = "theta <= 7 deg" if theta <= 7.0 else "7 deg < theta <= 20 deg"
    z_clean = str(zone).strip()
    if "1'" in z_clean and theta <= 7.0:
        z_target = "Zone 1'"
    elif "3" in z_clean:
        z_target = "Zone 3"
    elif "2" in z_clean:
        z_target = "Zone 2"
    else:
        z_target = "Zone 1"

    # Parapet relief per Figure 30.3-2A Note 5
    effective_neg_zone = "Zone 2" if (theta <= 7.0 and h_par >= 3.0 and z_target == "Zone 3") else z_target

    df = kb.get_table(TABLE_C30_3_2_FILE)
    gcp_pos = 0.3 if theta <= 7.0 else 0.6
    gcp_neg = -2.3 if theta <= 7.0 else -2.5

    for _, row in df.iterrows():
        s_range = str(row.iloc[1]).strip()
        p_dir = str(row.iloc[2]).strip()
        r_zone = str(row.iloc[3]).strip()
        if s_range != slope_key or p_dir not in ("Positive", "Negative"):
            continue

        a_min = float(str(row.iloc[6]).strip())
        a_max = float(str(row.iloc[7]).strip())
        c0 = float(str(row.iloc[8]).strip())
        c1 = float(str(row.iloc[9]).strip())

        in_range = (
            (a_min == 0 and area <= a_max)
            or (a_min < area <= a_max)
            or (a_max >= 5000 and area > a_min)
        )
        if not in_range:
            continue

        if p_dir == "Positive":
            gcp_pos = c0 + c1 * math.log10(max(area, 1.0))
        elif p_dir == "Negative" and r_zone == effective_neg_zone:
            gcp_neg = c0 + c1 * math.log10(max(area, 1.0))

    return {
        "zone": z_target,
        "effective_neg_zone": effective_neg_zone,
        "roof_slope_deg": theta,
        "effective_area_ft2": round(area, 2),
        "GCp_pos": round(gcp_pos, 4),
        "GCp_neg": round(gcp_neg, 4),
    }
