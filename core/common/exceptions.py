"""Domain-specific exceptions for structural calculations per SAD v1.0."""


class StructuralEngineeringError(Exception):
    """Base exception for all structural engineering application errors."""
    pass


class UnitValidationError(StructuralEngineeringError):
    """Raised when an invalid unit or incompatible unit conversion is specified."""
    pass


class InvalidDesignMethodError(StructuralEngineeringError):
    """Raised when an invalid or unsupported design method (not ASD or LRFD) is specified."""
    pass


class InvalidLoadCombinationError(StructuralEngineeringError):
    """Raised when an invalid load combination is evaluated or ASD/LRFD are mixed."""
    pass


class InputValidationError(StructuralEngineeringError):
    """Raised when calculation input parameters fail validation checks."""
    pass


class MissingInputError(InputValidationError):
    """Raised when a required input parameter is omitted."""
    pass


class InputOutOfRangeError(InputValidationError):
    """Raised when a numeric parameter is outside physically or code-permitted bounds."""
    pass


class ReferenceDataNotFoundError(StructuralEngineeringError):
    """Raised when a requested CSV table, row, or procedure cannot be found."""
    pass


class ReferenceIntegrityError(StructuralEngineeringError):
    """Raised when a reference file checksum or encoding fails verification."""
    pass


class CalculationExecutionError(StructuralEngineeringError):
    """Raised when a calculation module fails during numerical evaluation."""
    pass
