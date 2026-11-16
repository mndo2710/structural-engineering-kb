"""Input parameter validation utilities per SAD v1.0 Section 6.3."""

from typing import Any, List, Optional, Sequence, Union
from core.common.calculation_result import DesignMethod
from core.common.exceptions import (
    InputOutOfRangeError,
    InputValidationError,
    InvalidDesignMethodError,
    MissingInputError,
)


def validate_positive(name: str, value: Optional[float]) -> float:
    """Validate that a required numerical parameter is strictly greater than zero."""
    if value is None:
        raise MissingInputError(f"Required input '{name}' is missing.")
    try:
        val = float(value)
    except (ValueError, TypeError):
        raise InputValidationError(f"Input '{name}' must be a numerical value, got '{value}'.")
    if val <= 0.0:
        raise InputOutOfRangeError(f"Input '{name}' must be strictly positive (> 0), got {val}.")
    return val


def validate_non_negative(name: str, value: Optional[float]) -> float:
    """Validate that a required numerical parameter is non-negative (>= 0)."""
    if value is None:
        raise MissingInputError(f"Required input '{name}' is missing.")
    try:
        val = float(value)
    except (ValueError, TypeError):
        raise InputValidationError(f"Input '{name}' must be a numerical value, got '{value}'.")
    if val < 0.0:
        raise InputOutOfRangeError(f"Input '{name}' cannot be negative, got {val}.")
    return val


def validate_range(
    name: str,
    value: Optional[float],
    min_val: Optional[float] = None,
    max_val: Optional[float] = None,
    inclusive: bool = True
) -> float:
    """Validate that a numerical value is within specified bounds."""
    if value is None:
        raise MissingInputError(f"Required input '{name}' is missing.")
    try:
        val = float(value)
    except (ValueError, TypeError):
        raise InputValidationError(f"Input '{name}' must be a numerical value, got '{value}'.")

    if min_val is not None:
        if inclusive and val < min_val:
            raise InputOutOfRangeError(f"Input '{name}' = {val} is below minimum allowed {min_val}.")
        elif not inclusive and val <= min_val:
            raise InputOutOfRangeError(f"Input '{name}' = {val} must be strictly greater than {min_val}.")

    if max_val is not None:
        if inclusive and val > max_val:
            raise InputOutOfRangeError(f"Input '{name}' = {val} exceeds maximum allowed {max_val}.")
        elif not inclusive and val >= max_val:
            raise InputOutOfRangeError(f"Input '{name}' = {val} must be strictly less than {max_val}.")

    return val


def validate_in_options(name: str, value: Any, options: Sequence[Any]) -> Any:
    """Validate that a value belongs to an allowable set of options."""
    if value not in options:
        raise InputValidationError(
            f"Input '{name}' has invalid value '{value}'. Allowed options: {list(options)}"
        )
    return value


def validate_design_method(method: Union[str, DesignMethod]) -> DesignMethod:
    """Validate and normalize structural design method (ASD or LRFD)."""
    if isinstance(method, DesignMethod):
        return method
    normalized = str(method).strip().upper()
    if normalized in ("ASD", "ALLOWABLE_STRESS_DESIGN"):
        return DesignMethod.ASD
    if normalized in ("LRFD", "STRENGTH_DESIGN"):
        return DesignMethod.LRFD
    raise InvalidDesignMethodError(
        f"Unsupported design method: '{method}'. Strictly 'ASD' or 'LRFD' per Master Rule 2."
    )


class ValidationCollector:
    """Collects multiple validation errors before raising a consolidated exception."""

    def __init__(self) -> None:
        self.errors: List[str] = []

    def check(self, condition: bool, error_message: str) -> None:
        """Add an error message if condition is False."""
        if not condition:
            self.errors.append(error_message)

    def raise_if_any(self) -> None:
        """Raise consolidated InputValidationError if any errors were recorded."""
        if self.errors:
            msg = "Validation failed with the following errors:\n - " + "\n - ".join(self.errors)
            raise InputValidationError(msg)
