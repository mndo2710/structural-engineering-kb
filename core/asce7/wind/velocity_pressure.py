"""ASCE 7-22 Chapter 26 Wind Velocity Pressure (qz, qh, qp) Calculation Engine.

Conforms to SAD v1.0 Section 6.2 & Master Rules 2, 4, 5.
Retrieves Kd, Ke, Kz/Kh, and GCpi from verified CSV lookup tables in
database/asce_7/v7_22/ via KnowledgeBaseService.
"""

import math
import re
from typing import Any, Dict, Tuple

from app.services.knowledge_base_service import KnowledgeBaseService
from core.common.validation import (
    validate_in_options,
    validate_non_negative,
    validate_positive,
)


TABLE_26_6_1_FILE = "ASCE7-22_Table_26.6-1.csv"
TABLE_26_9_1_FILE = "ASCE7-22_Table_26.9-1.csv"
TABLE_26_10_1_FILE = "ASCE7-22_Table_26.10-1.csv"
TABLE_26_13_1_FILE = "ASCE7-22_Table_26.13-1.csv"


def lookup_kd(kb: KnowledgeBaseService, structure_type: str = "Components and Cladding") -> float:
    """Lookup Wind Directionality Factor Kd from ASCE7-22_Table_26.6-1.csv."""
    df = kb.get_table(TABLE_26_6_1_FILE)
    target = structure_type.strip().lower()
    for _, row in df.iterrows():
        s_type = str(row.iloc[0]).strip()
        val_str = str(row.iloc[1]).strip()
        if target in s_type.lower() and val_str and val_str != "nan":
            m = re.search(r"([0-9]+\.[0-9]+)", val_str)
            if m:
                return float(m.group(1))
    return 0.85


def lookup_ke(kb: KnowledgeBaseService, elevation_ft: float = 0.0) -> float:
    """
    Lookup Ground Elevation Factor Ke from ASCE7-22_Table_26.9-1.csv
    with linear interpolation across tabulated rows (or Note 2 exact exponential formula).
    """
    z_e = float(elevation_ft)
    if z_e <= 0.0:
        return 1.00

    df = kb.get_table(TABLE_26_9_1_FILE)
    pts = []
    for _, row in df.iterrows():
        ft_str = str(row.iloc[0]).strip().replace(",", "")
        ke_str = str(row.iloc[2]).strip()
        if re.match(r"^[0-9]+(\.[0-9]+)?$", ft_str) and re.match(r"^[0-9]+(\.[0-9]+)?$", ke_str):
            pts.append((float(ft_str), float(ke_str)))

    pts.sort(key=lambda x: x[0])
    if not pts:
        return round(math.exp(-0.0000362 * z_e), 4)

    if z_e <= pts[0][0]:
        return pts[0][1]
    if z_e >= pts[-1][0]:
        return round(math.exp(-0.0000362 * z_e), 4)

    for i in range(len(pts) - 1):
        z0, k0 = pts[i]
        z1, k1 = pts[i + 1]
        if z0 <= z_e <= z1:
            if z1 == z0:
                return k0
            return round(k0 + (k1 - k0) * (z_e - z0) / (z1 - z0), 4)

    return 1.00


def lookup_kz(
    kb: KnowledgeBaseService,
    height_ft: float,
    exposure: str = "C",
    use_ch28_exp_b_floor: bool = False,
) -> float:
    """
    Lookup Velocity Pressure Exposure Coefficient Kz or Kh from ASCE7-22_Table_26.10-1.csv.
    Supports Exposure B, C, and D with linear interpolation per Note 3.
    """
    exp = validate_in_options("Exposure Category", exposure.strip().upper(), ["B", "C", "D"])
    z = validate_positive("Height z or h (ft)", height_ft)

    col_idx = {"B": 2, "C": 3, "D": 4}[exp]
    df = kb.get_table(TABLE_26_10_1_FILE)

    pts = []
    for _, row in df.iterrows():
        h_raw = str(row.iloc[0]).strip()
        val_raw = str(row.iloc[col_idx]).strip()
        if not h_raw or h_raw == "nan" or not val_raw or val_raw == "nan":
            continue

        # Parse height (e.g., "0-15" -> 15.0, "20" -> 20.0)
        if h_raw == "0-15":
            h_val = 15.0
        elif re.match(r"^[0-9]+(\.[0-9]+)?$", h_raw):
            h_val = float(h_raw)
        else:
            continue

        # Parse Kz (e.g., "0.57 (0.70) [a]" -> 0.57 or 0.70 if Ch. 28 floor applies)
        nums = re.findall(r"[0-9]+\.[0-9]+", val_raw)
        if not nums:
            continue
        k_val = float(nums[1]) if (use_ch28_exp_b_floor and len(nums) > 1) else float(nums[0])
        pts.append((h_val, k_val))

    pts.sort(key=lambda x: x[0])
    if z <= 15.0:
        return pts[0][1]
    if z >= pts[-1][0]:
        return pts[-1][1]

    for i in range(len(pts) - 1):
        z0, k0 = pts[i]
        z1, k1 = pts[i + 1]
        if z0 <= z <= z1:
            if z1 == z0:
                return k0
            return round(k0 + (k1 - k0) * (z - z0) / (z1 - z0), 4)

    return pts[-1][1]


def lookup_gcpi(kb: KnowledgeBaseService, enclosure: str = "Enclosed") -> Tuple[float, float]:
    """
    Lookup Internal Pressure Coefficient (GCpi) from ASCE7-22_Table_26.13-1.csv.
    Returns (positive_gcpi, negative_gcpi).
    """
    df = kb.get_table(TABLE_26_13_1_FILE)
    target = enclosure.strip().lower()
    for _, row in df.iterrows():
        enc_str = str(row.iloc[0]).strip().lower()
        val_str = str(row.iloc[3]).strip()
        if target in enc_str and val_str and val_str != "nan":
            nums = re.findall(r"[+-]?[0-9]+\.[0-9]+", val_str)
            if len(nums) >= 2:
                return float(nums[0]), float(nums[1])
            elif len(nums) == 1:
                v = abs(float(nums[0]))
                return v, -v

    if "partially enclosed" in target:
        return 0.55, -0.55
    if "open" in target and "partially" not in target:
        return 0.0, 0.0
    return 0.18, -0.18


def calculate_velocity_pressure(
    kb: KnowledgeBaseService,
    v_mph: float,
    z_ft: float,
    exposure: str = "C",
    kzt: float = 1.0,
    elevation_ft: float = 0.0,
    structure_type: str = "Components and Cladding",
) -> Dict[str, Any]:
    """
    Calculate velocity pressure qz (psf) at height z per ASCE 7-22 Eq. (26.10-1):
        qz = 0.00256 * Kz * Kzt * Ke * V^2
    Note: Per ASCE 7-22 Eq. 26.10-1, Kd is applied in the pressure/force equations (e.g., p = qh * Kd * GCp).
    """
    v = validate_positive("Basic Wind Speed V (mph)", v_mph)
    z = validate_positive("Height z (ft)", z_ft)
    k_zt = validate_positive("Topographic Factor Kzt", kzt)
    z_e = validate_non_negative("Site Elevation ze (ft)", elevation_ft)

    k_d = lookup_kd(kb, structure_type=structure_type)
    k_e = lookup_ke(kb, elevation_ft=z_e)
    k_z = lookup_kz(kb, height_ft=z, exposure=exposure)

    qz_psf = 0.00256 * k_z * k_zt * k_e * (v ** 2)

    return {
        "V_mph": v,
        "z_ft": z,
        "exposure": exposure.strip().upper(),
        "Kd": k_d,
        "Kz": k_z,
        "Kzt": k_zt,
        "Ke": k_e,
        "qz_psf": round(qz_psf, 2),
        "qz_kd_psf": round(qz_psf * k_d, 2),
        "equation_str": "q_z = 0.00256 * K_z * K_zt * K_e * V^2",
        "substitution_str": f"0.00256 * {k_z:.2f} * {k_zt:.2f} * {k_e:.2f} * ({v:.1f})^2 = {qz_psf:.2f} psf",
        "reference_files": [
            f"database/asce_7/v7_22/{TABLE_26_6_1_FILE}",
            f"database/asce_7/v7_22/{TABLE_26_9_1_FILE}",
            f"database/asce_7/v7_22/{TABLE_26_10_1_FILE}",
        ],
    }
