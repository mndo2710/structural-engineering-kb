"""US Customary Unit Conversion and Formatting per SAD v1.0 & Master Rule 2."""

from enum import Enum
from typing import Dict, Union
from core.common.exceptions import UnitValidationError


class LengthUnit(str, Enum):
    INCH = "in."
    FOOT = "ft"


class ForceUnit(str, Enum):
    POUND = "lbs"
    KIP = "kips"


class StressUnit(str, Enum):
    PSI = "psi"
    KSI = "ksi"
    PSF = "psf"
    KSF = "ksf"


class DistributedLoadUnit(str, Enum):
    PLF = "plf"
    KLF = "klf"


class MomentUnit(str, Enum):
    LB_IN = "lb-in."
    LB_FT = "lb-ft"
    KIP_IN = "kip-in."
    KIP_FT = "kip-ft"


class DensityUnit(str, Enum):
    PCF = "pcf"
    PCI = "pci"


# Normalization mapping for standard user/CSV strings
LENGTH_ALIASES: Dict[str, LengthUnit] = {
    "in": LengthUnit.INCH,
    "in.": LengthUnit.INCH,
    "inch": LengthUnit.INCH,
    "inches": LengthUnit.INCH,
    "\"": LengthUnit.INCH,
    "ft": LengthUnit.FOOT,
    "ft.": LengthUnit.FOOT,
    "foot": LengthUnit.FOOT,
    "feet": LengthUnit.FOOT,
    "'": LengthUnit.FOOT,
}

FORCE_ALIASES: Dict[str, ForceUnit] = {
    "lb": ForceUnit.POUND,
    "lbs": ForceUnit.POUND,
    "pound": ForceUnit.POUND,
    "pounds": ForceUnit.POUND,
    "k": ForceUnit.KIP,
    "kip": ForceUnit.KIP,
    "kips": ForceUnit.KIP,
}

STRESS_ALIASES: Dict[str, StressUnit] = {
    "psi": StressUnit.PSI,
    "ksi": StressUnit.KSI,
    "psf": StressUnit.PSF,
    "ksf": StressUnit.KSF,
}

DIST_LOAD_ALIASES: Dict[str, DistributedLoadUnit] = {
    "plf": DistributedLoadUnit.PLF,
    "klf": DistributedLoadUnit.KLF,
    "lb/ft": DistributedLoadUnit.PLF,
    "lbs/ft": DistributedLoadUnit.PLF,
    "k/ft": DistributedLoadUnit.KLF,
    "kips/ft": DistributedLoadUnit.KLF,
}

MOMENT_ALIASES: Dict[str, MomentUnit] = {
    "lb-in": MomentUnit.LB_IN,
    "lb-in.": MomentUnit.LB_IN,
    "lbin": MomentUnit.LB_IN,
    "lb-ft": MomentUnit.LB_FT,
    "lb-ft.": MomentUnit.LB_FT,
    "lbft": MomentUnit.LB_FT,
    "kip-in": MomentUnit.KIP_IN,
    "kip-in.": MomentUnit.KIP_IN,
    "kipin": MomentUnit.KIP_IN,
    "kip-ft": MomentUnit.KIP_FT,
    "kip-ft.": MomentUnit.KIP_FT,
    "kipft": MomentUnit.KIP_FT,
    "k-ft": MomentUnit.KIP_FT,
    "k-in": MomentUnit.KIP_IN,
}


def normalize_length_unit(unit: Union[str, LengthUnit]) -> LengthUnit:
    """Normalize length unit string to LengthUnit enum."""
    if isinstance(unit, LengthUnit):
        return unit
    key = str(unit).strip().lower()
    if key in LENGTH_ALIASES:
        return LENGTH_ALIASES[key]
    raise UnitValidationError(f"Invalid length unit: '{unit}'. Permitted: 'in.', 'ft'")


def normalize_force_unit(unit: Union[str, ForceUnit]) -> ForceUnit:
    """Normalize force unit string to ForceUnit enum."""
    if isinstance(unit, ForceUnit):
        return unit
    key = str(unit).strip().lower()
    if key in FORCE_ALIASES:
        return FORCE_ALIASES[key]
    raise UnitValidationError(f"Invalid force unit: '{unit}'. Permitted: 'lbs', 'kips'")


def normalize_stress_unit(unit: Union[str, StressUnit]) -> StressUnit:
    """Normalize stress/pressure unit string to StressUnit enum."""
    if isinstance(unit, StressUnit):
        return unit
    key = str(unit).strip().lower()
    if key in STRESS_ALIASES:
        return STRESS_ALIASES[key]
    raise UnitValidationError(f"Invalid stress unit: '{unit}'. Permitted: 'psi', 'ksi', 'psf', 'ksf'")


def normalize_moment_unit(unit: Union[str, MomentUnit]) -> MomentUnit:
    """Normalize moment unit string to MomentUnit enum."""
    if isinstance(unit, MomentUnit):
        return unit
    key = str(unit).strip().lower()
    if key in MOMENT_ALIASES:
        return MOMENT_ALIASES[key]
    raise UnitValidationError(f"Invalid moment unit: '{unit}'. Permitted: 'lb-in.', 'lb-ft', 'kip-in.', 'kip-ft'")


def convert_length(value: float, from_unit: Union[str, LengthUnit], to_unit: Union[str, LengthUnit]) -> float:
    """Convert length between in. and ft."""
    u_from = normalize_length_unit(from_unit)
    u_to = normalize_length_unit(to_unit)
    if u_from == u_to:
        return float(value)
    if u_from == LengthUnit.INCH and u_to == LengthUnit.FOOT:
        return float(value) / 12.0
    if u_from == LengthUnit.FOOT and u_to == LengthUnit.INCH:
        return float(value) * 12.0
    raise UnitValidationError(f"Unsupported conversion: {u_from} to {u_to}")


def convert_force(value: float, from_unit: Union[str, ForceUnit], to_unit: Union[str, ForceUnit]) -> float:
    """Convert force between lbs and kips."""
    u_from = normalize_force_unit(from_unit)
    u_to = normalize_force_unit(to_unit)
    if u_from == u_to:
        return float(value)
    if u_from == ForceUnit.POUND and u_to == ForceUnit.KIP:
        return float(value) / 1000.0
    if u_from == ForceUnit.KIP and u_to == ForceUnit.POUND:
        return float(value) * 1000.0
    raise UnitValidationError(f"Unsupported conversion: {u_from} to {u_to}")


def convert_stress(value: float, from_unit: Union[str, StressUnit], to_unit: Union[str, StressUnit]) -> float:
    """Convert stress/pressure among psi, ksi, psf, ksf."""
    u_from = normalize_stress_unit(from_unit)
    u_to = normalize_stress_unit(to_unit)
    if u_from == u_to:
        return float(value)

    # Base unit: psi
    to_psi = {
        StressUnit.PSI: 1.0,
        StressUnit.KSI: 1000.0,
        StressUnit.PSF: 1.0 / 144.0,
        StressUnit.KSF: 1000.0 / 144.0,
    }
    from_psi = {
        StressUnit.PSI: 1.0,
        StressUnit.KSI: 1.0 / 1000.0,
        StressUnit.PSF: 144.0,
        StressUnit.KSF: 144.0 / 1000.0,
    }
    val_psi = float(value) * to_psi[u_from]
    return val_psi * from_psi[u_to]


def convert_distributed_load(
    value: float,
    from_unit: Union[str, DistributedLoadUnit],
    to_unit: Union[str, DistributedLoadUnit]
) -> float:
    """Convert linear distributed load between plf and klf."""
    u_from = DIST_LOAD_ALIASES.get(str(from_unit).strip().lower())
    u_to = DIST_LOAD_ALIASES.get(str(to_unit).strip().lower())
    if not u_from or not u_to:
        raise UnitValidationError(f"Invalid distributed load units: {from_unit} or {to_unit}")
    if u_from == u_to:
        return float(value)
    if u_from == DistributedLoadUnit.PLF and u_to == DistributedLoadUnit.KLF:
        return float(value) / 1000.0
    if u_from == DistributedLoadUnit.KLF and u_to == DistributedLoadUnit.PLF:
        return float(value) * 1000.0
    raise UnitValidationError(f"Unsupported conversion: {u_from} to {u_to}")


def convert_moment(value: float, from_unit: Union[str, MomentUnit], to_unit: Union[str, MomentUnit]) -> float:
    """Convert moment among lb-in., lb-ft, kip-in., kip-ft."""
    u_from = normalize_moment_unit(from_unit)
    u_to = normalize_moment_unit(to_unit)
    if u_from == u_to:
        return float(value)

    # Base unit: lb-in.
    to_lb_in = {
        MomentUnit.LB_IN: 1.0,
        MomentUnit.LB_FT: 12.0,
        MomentUnit.KIP_IN: 1000.0,
        MomentUnit.KIP_FT: 12000.0,
    }
    from_lb_in = {
        MomentUnit.LB_IN: 1.0,
        MomentUnit.LB_FT: 1.0 / 12.0,
        MomentUnit.KIP_IN: 1.0 / 1000.0,
        MomentUnit.KIP_FT: 1.0 / 12000.0,
    }
    val_lb_in = float(value) * to_lb_in[u_from]
    return val_lb_in * from_lb_in[u_to]


def format_quantity(value: float, unit: str, precision: int = 2) -> str:
    """Format numerical value with its unit string per US engineering standards."""
    return f"{value:.{precision}f} {unit}"
