"""Unit tests for core/common/load_combinations.py per ASCE 7-22 and Master Rule 2."""

import pytest
from core.common.calculation_result import DesignMethod
from core.common.exceptions import InvalidLoadCombinationError
from core.common.load_combinations import (
    GoverningLoads,
    LoadCase,
    evaluate_load_combinations,
)


class TestLoadCombinationsASD:
    def test_basic_gravity_asd(self):
        # D = 1000 lbs, L = 500 lbs
        loads = LoadCase(dead=1000.0, live=500.0)
        res = evaluate_load_combinations(loads, DesignMethod.ASD, include_wind=False, include_seismic=False)
        assert res.design_method == DesignMethod.ASD
        # Governing downward should be D + L = 1500
        assert res.max_downward == pytest.approx(1500.0)
        assert res.governing_downward_combo.combo_id == "ASD-2"

    def test_wind_downward_asd(self):
        # D = 1000, L = 500, W = 1200 (downward)
        loads = LoadCase(dead=1000.0, live=500.0, wind=1200.0)
        res = evaluate_load_combinations(loads, DesignMethod.ASD, include_wind=True, include_seismic=False)
        # ASD-5a: D + 0.6W = 1000 + 720 = 1720
        # ASD-6: D + 0.75L + 0.75(0.6W) = 1000 + 375 + 540 = 1915
        assert res.max_downward == pytest.approx(1915.0)
        assert res.governing_downward_combo.combo_id == "ASD-6"

    def test_uplift_wind_asd(self):
        # D = 1000, W = -2500 (uplift)
        loads = LoadCase(dead=1000.0, wind=-2500.0)
        res = evaluate_load_combinations(loads, DesignMethod.ASD, include_wind=True, include_seismic=False)
        # ASD-7: 0.6D + 0.6W = 600 - 1500 = -900 lbs (net tension/uplift)
        assert res.max_uplift == pytest.approx(-900.0)
        assert res.governing_uplift_combo.combo_id == "ASD-7"


class TestLoadCombinationsLRFD:
    def test_basic_gravity_lrfd(self):
        # D = 1000 lbs, L = 500 lbs
        loads = LoadCase(dead=1000.0, live=500.0)
        res = evaluate_load_combinations(loads, DesignMethod.LRFD, include_wind=False, include_seismic=False)
        assert res.design_method == DesignMethod.LRFD
        # LRFD-1: 1.4D = 1400
        # LRFD-2: 1.2D + 1.6L = 1200 + 800 = 2000 (governs)
        assert res.max_downward == pytest.approx(2000.0)
        assert res.governing_downward_combo.combo_id == "LRFD-2"

    def test_uplift_wind_lrfd(self):
        # D = 1000, W = -2500 (uplift)
        loads = LoadCase(dead=1000.0, wind=-2500.0)
        res = evaluate_load_combinations(loads, DesignMethod.LRFD, include_wind=True, include_seismic=False)
        # LRFD-5: 0.9D + 1.0W = 900 - 2500 = -1600 lbs
        assert res.max_uplift == pytest.approx(-1600.0)
        assert res.governing_uplift_combo.combo_id == "LRFD-5"

    def test_invalid_method(self):
        loads = LoadCase(dead=100.0)
        with pytest.raises(InvalidLoadCombinationError):
            evaluate_load_combinations(loads, "WORKING_STRESS")  # type: ignore
