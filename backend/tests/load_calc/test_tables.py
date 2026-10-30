from app.services.load_calc.tables import (
    apply_appliance_demand,
    apply_lighting_demand_factors,
    get_dryer_demand,
    get_multifamily_demand_factor,
    get_range_demand,
)


class TestLightingDemandFactors:
    def test_under_3000_va(self):
        assert apply_lighting_demand_factors(2500) == 2500

    def test_exactly_3000_va(self):
        assert apply_lighting_demand_factors(3000) == 3000

    def test_between_3000_and_120000(self):
        assert apply_lighting_demand_factors(8000) == 4750

    def test_over_120000_va(self):
        expected = 3000 + (117000 * 0.35) + (30000 * 0.25)
        assert apply_lighting_demand_factors(150000) == expected


class TestRangeDemand:
    def test_single_12kw_range(self):
        assert get_range_demand(12.0, 1) == 8000

    def test_single_range_over_12kw(self):
        assert get_range_demand(14.0, 1) == 8800


class TestDryerDemand:
    def test_single_dryer_minimum(self):
        assert get_dryer_demand(4.0, 1) == 5000

    def test_single_dryer_normal(self):
        assert get_dryer_demand(5.5, 1) == 5500


class TestApplianceDemand:
    def test_less_than_four_appliances(self):
        assert apply_appliance_demand(3, 6000) == 6000

    def test_four_or_more_appliances(self):
        assert apply_appliance_demand(4, 8000) == 6000


class TestMultifamilyFactor:
    def test_three_units(self):
        assert get_multifamily_demand_factor(3) == 0.45

    def test_high_unit_count(self):
        assert get_multifamily_demand_factor(70) == 0.23
