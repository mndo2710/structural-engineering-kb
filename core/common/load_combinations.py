"""ASCE 7-22 ASD and LRFD Load Combinations per SAD v1.0 & Master Rule 2."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from core.common.calculation_result import DesignMethod
from core.common.exceptions import InvalidLoadCombinationError


@dataclass(frozen=True)
class LoadCase:
    """Individual service load components."""
    dead: float = 0.0          # D
    live: float = 0.0          # L
    roof_live: float = 0.0     # Lr
    snow: float = 0.0          # S
    rain: float = 0.0          # R
    wind: float = 0.0          # W (Positive = downward/pressure, Negative = uplift/suction)
    seismic: float = 0.0       # E (Direct horizontal or combined vertical seismic effect)


@dataclass(frozen=True)
class CombinationEvaluation:
    """Evaluation result for a single load combination."""
    combo_id: str
    design_method: DesignMethod
    code_reference: str
    formula_str: str
    substitution_str: str
    result_value: float
    is_uplift_check: bool = False


@dataclass
class GoverningLoads:
    """Summary of governing loads and their corresponding combinations."""
    design_method: DesignMethod
    max_downward: float
    governing_downward_combo: CombinationEvaluation
    max_uplift: float
    governing_uplift_combo: CombinationEvaluation
    all_evaluated: List[CombinationEvaluation] = field(default_factory=list)


def evaluate_load_combinations(
    loads: LoadCase,
    method: DesignMethod,
    include_seismic: bool = True,
    include_wind: bool = True
) -> GoverningLoads:
    """
    Evaluate ASCE 7-22 Section 2.3 (LRFD) or Section 2.4 (ASD) load combinations.
    Strictly separates ASD and LRFD methods per Master Rule 2.
    """
    if not isinstance(method, DesignMethod):
        try:
            method = DesignMethod(str(method).upper())
        except ValueError:
            raise InvalidLoadCombinationError(f"Unsupported design method: {method}. Must be ASD or LRFD.")

    d = loads.dead
    l = loads.live
    lr_s_r = max(loads.roof_live, loads.snow, loads.rain)
    w = loads.wind
    e = loads.seismic

    evaluations: List[CombinationEvaluation] = []

    if method == DesignMethod.ASD:
        # ASCE 7-22 Section 2.4 - Basic ASD Combinations
        # Combo 1: D
        evaluations.append(CombinationEvaluation(
            combo_id="ASD-1",
            design_method=DesignMethod.ASD,
            code_reference="ASCE 7-22 Sec. 2.4.1 (1)",
            formula_str="D",
            substitution_str=f"{d:.2f}",
            result_value=d,
            is_uplift_check=False
        ))

        # Combo 2: D + L
        evaluations.append(CombinationEvaluation(
            combo_id="ASD-2",
            design_method=DesignMethod.ASD,
            code_reference="ASCE 7-22 Sec. 2.4.1 (2)",
            formula_str="D + L",
            substitution_str=f"{d:.2f} + {l:.2f}",
            result_value=d + l,
            is_uplift_check=False
        ))

        # Combo 3: D + (Lr or S or R)
        evaluations.append(CombinationEvaluation(
            combo_id="ASD-3",
            design_method=DesignMethod.ASD,
            code_reference="ASCE 7-22 Sec. 2.4.1 (3)",
            formula_str="D + (Lr or S or R)",
            substitution_str=f"{d:.2f} + {lr_s_r:.2f}",
            result_value=d + lr_s_r,
            is_uplift_check=False
        ))

        # Combo 4: D + 0.75 L + 0.75 (Lr or S or R)
        evaluations.append(CombinationEvaluation(
            combo_id="ASD-4",
            design_method=DesignMethod.ASD,
            code_reference="ASCE 7-22 Sec. 2.4.1 (4)",
            formula_str="D + 0.75*L + 0.75*(Lr or S or R)",
            substitution_str=f"{d:.2f} + 0.75*{l:.2f} + 0.75*{lr_s_r:.2f}",
            result_value=d + 0.75 * l + 0.75 * lr_s_r,
            is_uplift_check=False
        ))

        if include_wind:
            # Combo 5a: D + 0.6 W (Downward)
            evaluations.append(CombinationEvaluation(
                combo_id="ASD-5a",
                design_method=DesignMethod.ASD,
                code_reference="ASCE 7-22 Sec. 2.4.1 (5)",
                formula_str="D + 0.6*W",
                substitution_str=f"{d:.2f} + 0.6*({w:.2f})",
                result_value=d + 0.6 * w,
                is_uplift_check=False
            ))

            # Combo 6: D + 0.75 L + 0.75(0.6 W) + 0.75(Lr or S or R)
            evaluations.append(CombinationEvaluation(
                combo_id="ASD-6",
                design_method=DesignMethod.ASD,
                code_reference="ASCE 7-22 Sec. 2.4.1 (6)",
                formula_str="D + 0.75*L + 0.75*(0.6*W) + 0.75*(Lr or S or R)",
                substitution_str=f"{d:.2f} + 0.75*{l:.2f} + 0.75*(0.6*{w:.2f}) + 0.75*{lr_s_r:.2f}",
                result_value=d + 0.75 * l + 0.75 * (0.6 * w) + 0.75 * lr_s_r,
                is_uplift_check=False
            ))

            # Combo 7: 0.6 D + 0.6 W (Uplift / Overturning check)
            # Uplift wind is negative, net tension occurs when 0.6*w is negative and magnitude > 0.6*d
            evaluations.append(CombinationEvaluation(
                combo_id="ASD-7",
                design_method=DesignMethod.ASD,
                code_reference="ASCE 7-22 Sec. 2.4.1 (7)",
                formula_str="0.6*D + 0.6*W",
                substitution_str=f"0.6*{d:.2f} + 0.6*({w:.2f})",
                result_value=0.6 * d + 0.6 * w,
                is_uplift_check=True
            ))

        if include_seismic:
            # Combo 8: D + 0.7 E
            evaluations.append(CombinationEvaluation(
                combo_id="ASD-8",
                design_method=DesignMethod.ASD,
                code_reference="ASCE 7-22 Sec. 2.4.1 (8)",
                formula_str="D + 0.7*E",
                substitution_str=f"{d:.2f} + 0.7*({e:.2f})",
                result_value=d + 0.7 * e,
                is_uplift_check=False
            ))

            # Combo 9: D + 0.75(0.7 E) + 0.75 L + 0.75 S
            evaluations.append(CombinationEvaluation(
                combo_id="ASD-9",
                design_method=DesignMethod.ASD,
                code_reference="ASCE 7-22 Sec. 2.4.1 (9)",
                formula_str="D + 0.525*E + 0.75*L + 0.75*S",
                substitution_str=f"{d:.2f} + 0.525*{e:.2f} + 0.75*{l:.2f} + 0.75*{loads.snow:.2f}",
                result_value=d + 0.525 * e + 0.75 * l + 0.75 * loads.snow,
                is_uplift_check=False
            ))

            # Combo 10: 0.6 D + 0.7 E (Uplift / Overturning check)
            evaluations.append(CombinationEvaluation(
                combo_id="ASD-10",
                design_method=DesignMethod.ASD,
                code_reference="ASCE 7-22 Sec. 2.4.1 (10)",
                formula_str="0.6*D + 0.7*E",
                substitution_str=f"0.6*{d:.2f} + 0.7*({e:.2f})",
                result_value=0.6 * d + 0.7 * e,
                is_uplift_check=True
            ))

    elif method == DesignMethod.LRFD:
        # ASCE 7-22 Section 2.3 - Basic LRFD / Strength Combinations
        # Combo 1: 1.4 D
        evaluations.append(CombinationEvaluation(
            combo_id="LRFD-1",
            design_method=DesignMethod.LRFD,
            code_reference="ASCE 7-22 Sec. 2.3.1 (1)",
            formula_str="1.4*D",
            substitution_str=f"1.4*{d:.2f}",
            result_value=1.4 * d,
            is_uplift_check=False
        ))

        # Combo 2: 1.2 D + 1.6 L + 0.5 (Lr or S or R)
        evaluations.append(CombinationEvaluation(
            combo_id="LRFD-2",
            design_method=DesignMethod.LRFD,
            code_reference="ASCE 7-22 Sec. 2.3.1 (2)",
            formula_str="1.2*D + 1.6*L + 0.5*(Lr or S or R)",
            substitution_str=f"1.2*{d:.2f} + 1.6*{l:.2f} + 0.5*{lr_s_r:.2f}",
            result_value=1.2 * d + 1.6 * l + 0.5 * lr_s_r,
            is_uplift_check=False
        ))

        # Combo 3: 1.2 D + 1.6 (Lr or S or R) + (L or 0.5 W)
        wind_term = 0.5 * w if include_wind else 0.0
        combo3_var = max(l, wind_term)
        evaluations.append(CombinationEvaluation(
            combo_id="LRFD-3",
            design_method=DesignMethod.LRFD,
            code_reference="ASCE 7-22 Sec. 2.3.1 (3)",
            formula_str="1.2*D + 1.6*(Lr or S or R) + (L or 0.5*W)",
            substitution_str=f"1.2*{d:.2f} + 1.6*{lr_s_r:.2f} + {combo3_var:.2f}",
            result_value=1.2 * d + 1.6 * lr_s_r + combo3_var,
            is_uplift_check=False
        ))

        if include_wind:
            # Combo 4: 1.2 D + 1.0 W + L + 0.5 (Lr or S or R)
            evaluations.append(CombinationEvaluation(
                combo_id="LRFD-4",
                design_method=DesignMethod.LRFD,
                code_reference="ASCE 7-22 Sec. 2.3.1 (4)",
                formula_str="1.2*D + 1.0*W + L + 0.5*(Lr or S or R)",
                substitution_str=f"1.2*{d:.2f} + 1.0*({w:.2f}) + {l:.2f} + 0.5*{lr_s_r:.2f}",
                result_value=1.2 * d + 1.0 * w + l + 0.5 * lr_s_r,
                is_uplift_check=False
            ))

            # Combo 5: 0.9 D + 1.0 W (Uplift / Overturning check)
            evaluations.append(CombinationEvaluation(
                combo_id="LRFD-5",
                design_method=DesignMethod.LRFD,
                code_reference="ASCE 7-22 Sec. 2.3.1 (5)",
                formula_str="0.9*D + 1.0*W",
                substitution_str=f"0.9*{d:.2f} + 1.0*({w:.2f})",
                result_value=0.9 * d + 1.0 * w,
                is_uplift_check=True
            ))

        if include_seismic:
            # Combo 6: 1.2 D + 1.0 E + L + 0.2 S
            evaluations.append(CombinationEvaluation(
                combo_id="LRFD-6",
                design_method=DesignMethod.LRFD,
                code_reference="ASCE 7-22 Sec. 2.3.1 (6)",
                formula_str="1.2*D + 1.0*E + L + 0.2*S",
                substitution_str=f"1.2*{d:.2f} + 1.0*({e:.2f}) + {l:.2f} + 0.2*{loads.snow:.2f}",
                result_value=1.2 * d + 1.0 * e + l + 0.2 * loads.snow,
                is_uplift_check=False
            ))

            # Combo 7: 0.9 D + 1.0 E (Uplift / Overturning check)
            evaluations.append(CombinationEvaluation(
                combo_id="LRFD-7",
                design_method=DesignMethod.LRFD,
                code_reference="ASCE 7-22 Sec. 2.3.1 (7)",
                formula_str="0.9*D + 1.0*E",
                substitution_str=f"0.9*{d:.2f} + 1.0*({e:.2f})",
                result_value=0.9 * d + 1.0 * e,
                is_uplift_check=True
            ))

    # Determine governing downward (maximum positive force) and governing uplift (minimum/most negative force)
    downward_evals = [e for e in evaluations if not e.is_uplift_check]
    uplift_evals = [e for e in evaluations if e.is_uplift_check]

    gov_down = max(downward_evals, key=lambda x: x.result_value)
    # For uplift, the critical check is the most negative value (or minimum value)
    gov_up = min(uplift_evals, key=lambda x: x.result_value) if uplift_evals else gov_down

    return GoverningLoads(
        design_method=method,
        max_downward=gov_down.result_value,
        governing_downward_combo=gov_down,
        max_uplift=gov_up.result_value,
        governing_uplift_combo=gov_up,
        all_evaluated=evaluations
    )
