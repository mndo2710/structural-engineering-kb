"""Core common modules: calculation results, units, load combinations, validation, and exceptions."""

from core.common.calculation_result import (
    CalculationResult,
    CalculationStatus,
    DesignMethod,
    LimitStateResult,
)
from core.common.exceptions import (
    CalculationExecutionError,
    InputOutOfRangeError,
    InputValidationError,
    InvalidDesignMethodError,
    InvalidLoadCombinationError,
    MissingInputError,
    ReferenceDataNotFoundError,
    ReferenceIntegrityError,
    StructuralEngineeringError,
    UnitValidationError,
)
from core.common.load_combinations import (
    CombinationEvaluation,
    GoverningLoads,
    LoadCase,
    evaluate_load_combinations,
)
from core.common.units import (
    DensityUnit,
    DistributedLoadUnit,
    ForceUnit,
    LengthUnit,
    MomentUnit,
    StressUnit,
    convert_distributed_load,
    convert_force,
    convert_length,
    convert_moment,
    convert_stress,
    format_quantity,
    normalize_force_unit,
    normalize_length_unit,
    normalize_moment_unit,
    normalize_stress_unit,
)
from core.common.validation import (
    ValidationCollector,
    validate_design_method,
    validate_in_options,
    validate_non_negative,
    validate_positive,
    validate_range,
)

__all__ = [
    # Calculation Result
    "CalculationResult",
    "CalculationStatus",
    "DesignMethod",
    "LimitStateResult",
    # Exceptions
    "StructuralEngineeringError",
    "UnitValidationError",
    "InvalidDesignMethodError",
    "InvalidLoadCombinationError",
    "InputValidationError",
    "MissingInputError",
    "InputOutOfRangeError",
    "ReferenceDataNotFoundError",
    "ReferenceIntegrityError",
    "CalculationExecutionError",
    # Units
    "LengthUnit",
    "ForceUnit",
    "StressUnit",
    "DistributedLoadUnit",
    "MomentUnit",
    "DensityUnit",
    "convert_length",
    "convert_force",
    "convert_stress",
    "convert_distributed_load",
    "convert_moment",
    "format_quantity",
    "normalize_length_unit",
    "normalize_force_unit",
    "normalize_stress_unit",
    "normalize_moment_unit",
    # Load combinations
    "LoadCase",
    "CombinationEvaluation",
    "GoverningLoads",
    "evaluate_load_combinations",
    # Validation
    "validate_positive",
    "validate_non_negative",
    "validate_range",
    "validate_in_options",
    "validate_design_method",
    "ValidationCollector",
]
