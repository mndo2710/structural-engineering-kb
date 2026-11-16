"""Unit tests for core/common/validation.py per SAD v1.0 Section 6.3."""

import pytest
from core.common.calculation_result import DesignMethod
from core.common.exceptions import (
    InputOutOfRangeError,
    InputValidationError,
    InvalidDesignMethodError,
    MissingInputError,
)
from core.common.validation import (
    ValidationCollector,
    validate_design_method,
    validate_in_options,
    validate_non_negative,
    validate_positive,
    validate_range,
)


class TestValidationUtils:
    def test_validate_positive(self):
        assert validate_positive("width", 5.5) == 5.5
        with pytest.raises(InputOutOfRangeError):
            validate_positive("width", 0.0)
        with pytest.raises(InputOutOfRangeError):
            validate_positive("width", -2.0)
        with pytest.raises(MissingInputError):
            validate_positive("width", None)

    def test_validate_non_negative(self):
        assert validate_non_negative("moment", 0.0) == 0.0
        assert validate_non_negative("moment", 12.5) == 12.5
        with pytest.raises(InputOutOfRangeError):
            validate_non_negative("moment", -0.01)

    def test_validate_range(self):
        assert validate_range("ratio", 0.5, 0.0, 1.0) == 0.5
        with pytest.raises(InputOutOfRangeError):
            validate_range("ratio", 1.5, 0.0, 1.0)
        with pytest.raises(InputOutOfRangeError):
            validate_range("ratio", -0.1, 0.0, 1.0)

    def test_validate_in_options(self):
        assert validate_in_options("grade", "A36", ["A36", "A992", "A572-50"]) == "A36"
        with pytest.raises(InputValidationError):
            validate_in_options("grade", "A500", ["A36", "A992"])

    def test_validate_design_method(self):
        assert validate_design_method("ASD") == DesignMethod.ASD
        assert validate_design_method("lrfd") == DesignMethod.LRFD
        with pytest.raises(InvalidDesignMethodError):
            validate_design_method("WSD")

    def test_validation_collector(self):
        collector = ValidationCollector()
        collector.check(True, "Passes")
        collector.check(False, "Error 1: Negative depth")
        collector.check(False, "Error 2: Unacceptable steel grade")
        with pytest.raises(InputValidationError) as exc_info:
            collector.raise_if_any()
        assert "Error 1" in str(exc_info.value)
        assert "Error 2" in str(exc_info.value)
