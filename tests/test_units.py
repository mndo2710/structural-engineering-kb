"""Unit tests for core/common/units.py per Master Rule 2 (US Customary Units)."""

import pytest
from core.common.exceptions import UnitValidationError
from core.common.units import (
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


class TestLengthConversion:
    def test_in_to_ft(self):
        assert convert_length(12.0, "in.", "ft") == pytest.approx(1.0)
        assert convert_length(6.0, LengthUnit.INCH, LengthUnit.FOOT) == pytest.approx(0.5)

    def test_ft_to_in(self):
        assert convert_length(2.5, "ft", "in.") == pytest.approx(30.0)
        assert convert_length(1.0, LengthUnit.FOOT, LengthUnit.INCH) == pytest.approx(12.0)

    def test_identity(self):
        assert convert_length(15.2, "in.", "in.") == pytest.approx(15.2)

    def test_aliases(self):
        assert normalize_length_unit("inch") == LengthUnit.INCH
        assert normalize_length_unit("feet") == LengthUnit.FOOT

    def test_invalid_unit(self):
        with pytest.raises(UnitValidationError):
            convert_length(10.0, "meters", "in.")


class TestForceConversion:
    def test_lb_to_kip(self):
        assert convert_force(1500.0, "lbs", "kips") == pytest.approx(1.5)

    def test_kip_to_lb(self):
        assert convert_force(2.25, "kips", "lbs") == pytest.approx(2250.0)

    def test_aliases(self):
        assert normalize_force_unit("lb") == ForceUnit.POUND
        assert normalize_force_unit("kip") == ForceUnit.KIP


class TestStressConversion:
    def test_psi_to_ksi(self):
        assert convert_stress(4000.0, "psi", "ksi") == pytest.approx(4.0)

    def test_ksi_to_psi(self):
        assert convert_stress(36.0, "ksi", "psi") == pytest.approx(36000.0)

    def test_psi_to_psf(self):
        # 1 psi = 144 psf
        assert convert_stress(10.0, "psi", "psf") == pytest.approx(1440.0)

    def test_psf_to_psi(self):
        assert convert_stress(144.0, "psf", "psi") == pytest.approx(1.0)

    def test_ksf_to_psi(self):
        # 1 ksf = 1000 psf = 1000/144 psi
        assert convert_stress(1.44, "ksf", "psi") == pytest.approx(10.0)


class TestDistributedLoadConversion:
    def test_plf_to_klf(self):
        assert convert_distributed_load(1200.0, "plf", "klf") == pytest.approx(1.2)

    def test_klf_to_plf(self):
        assert convert_distributed_load(3.5, "klf", "plf") == pytest.approx(3500.0)


class TestMomentConversion:
    def test_lb_ft_to_lb_in(self):
        assert convert_moment(100.0, "lb-ft", "lb-in.") == pytest.approx(1200.0)

    def test_kip_ft_to_kip_in(self):
        assert convert_moment(10.0, "kip-ft", "kip-in.") == pytest.approx(120.0)

    def test_kip_in_to_lb_in(self):
        assert convert_moment(5.0, "kip-in.", "lb-in.") == pytest.approx(5000.0)

    def test_kip_ft_to_lb_in(self):
        assert convert_moment(1.0, "kip-ft", "lb-in.") == pytest.approx(12000.0)


class TestFormatting:
    def test_format_quantity(self):
        assert format_quantity(12.3456, "in.", 2) == "12.35 in."
        assert format_quantity(1500.0, "lbs", 0) == "1500 lbs"
