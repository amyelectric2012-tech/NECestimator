import pytest

from app.calculations.nec220 import (
    HVAC,
    Appliance,
    ProjectInput,
    calculate_all,
    lighting_demand_dwell,
    multifamily_demand_factor,
    optional_220_82,
    optional_220_84,
    range_demand,
    standard_method,
)


def test_lighting_demand():
    assert lighting_demand_dwell(3000) == 3000
    assert lighting_demand_dwell(5000) == 3000 + 0.35 * 2000
    assert lighting_demand_dwell(120000) == 3000 + 0.35 * 117000


def test_standard_basic():
    inp = ProjectInput(floor_area_sqft=1500, small_appliance_circuits=2, laundry_circuits=1)
    r = standard_method(inp)
    # general lighting 3*1500=4500
    assert r.general_lighting_va == 4500
    assert r.small_appliance_va == 3000
    assert r.laundry_va == 1500
    assert r.lighting_load_va == 9000
    # lighting demand: 3000 + 0.35*6000 = 5100
    assert r.lighting_demand_va == 3000 + 0.35 * 6000
    assert r.total_va == r.lighting_demand_va  # no other loads
    assert r.total_amps == r.total_va / 240
    assert r.recommended_service_amps >= r.total_amps


def test_fastened_75_percent():
    inp = ProjectInput(
        floor_area_sqft=1000,
        appliances=[Appliance("water_heater", 4500), Appliance("dishwasher", 1200),
                    Appliance("disposal", 800), Appliance("microwave", 1500)],
    )
    r = standard_method(inp)
    assert r.fastened_appliances_va == 4500 + 1200 + 800 + 1500
    assert r.fastened_demand_va == r.fastened_appliances_va * 0.75


def test_range_single():
    inp = ProjectInput(floor_area_sqft=1000, range_count=1, range_kw_each=8.0)
    r = standard_method(inp)
    assert r.range_connected_va == 8000
    assert r.range_demand_va == 8000  # Table 220.55 1 range = 8 kW


def test_range_over_12kw():
    inp = ProjectInput(floor_area_sqft=1000, range_count=1, range_kw_each=14.0)
    r = standard_method(inp)
    # base 8 kW, +5% per kW over 12: (14-12)=2 kW -> +10% -> 8.8 kW
    assert r.range_demand_va == 8800


def test_dryer_demand():
    # 1 dryer min 5000
    inp = ProjectInput(floor_area_sqft=1000, dryer_count=1, dryer_kw_each=4.0)
    r = standard_method(inp)
    assert r.dryer_connected_va == 5000
    assert r.dryer_demand_va == 5000
    # 5 dryers -> 85%
    inp2 = ProjectInput(floor_area_sqft=1000, dryer_count=5, dryer_kw_each=5.0)
    r2 = standard_method(inp2)
    assert r2.dryer_demand_va == 25000 * 0.85


def test_hvac_noncoincident():
    inp = ProjectInput(floor_area_sqft=1000, hvac=HVAC(cooling_va=5000, heating_va=10000))
    r = standard_method(inp)
    assert r.hvac_va == 10000


def test_motor_adder():
    inp = ProjectInput(floor_area_sqft=1000, largest_motor_va=3000)
    r = standard_method(inp)
    assert r.motor_adder_va == 750


def test_neutral():
    inp = ProjectInput(floor_area_sqft=1500, range_count=1, range_kw_each=8.0, dryer_count=1, dryer_kw_each=5.0)
    r = standard_method(inp)
    # neutral = lighting_demand + range*0.7 + dryer*0.7 (no fastened)
    assert r.neutral_va == r.lighting_demand_va + 8000 * 0.7 + 5000 * 0.7


def test_optional_220_82():
    inp = ProjectInput(floor_area_sqft=1500, small_appliance_circuits=2, laundry_circuits=1,
                       appliances=[Appliance("wh", 4500)], hvac=HVAC(cooling_va=3000, heating_va=8000))
    r = optional_220_82(inp)
    assert r.method == "optional_220_82"
    # general items = lighting 4500 + small 3000 + laundry 1500 + fastened 4500 = 13500 -> demand 10000 + 0.4*3500=11400
    assert r.breakdown["general_items"] == 4500 + 3000 + 1500 + 4500
    assert r.breakdown["general_demand"] == 10000 + 0.4 * 3500
    assert r.hvac_va == 5200.0  # fixed electric space heating, <4 units -> 65% of 8000 (NEC 220.82(C)(4))
    assert r.total_va == r.breakdown["general_demand"] + r.hvac_va


def test_optional_220_84():
    inp = ProjectInput(project_type="multi_family", floor_area_sqft=1000, num_units=10,
                       small_appliance_circuits=2, laundry_circuits=1,
                       appliances=[Appliance("wh", 4500)], range_count=1, range_kw_each=8.0,
                       dryer_count=1, dryer_kw_each=5.0, hvac=HVAC(cooling_va=3000))
    r = optional_220_84(inp)
    assert r.method == "optional_220_84"
    assert r.breakdown["demand_factor"] == 0.43  # 8-10 units
    assert r.total_va > 0


def test_multifamily_factor():
    assert multifamily_demand_factor(3) == 0.45
    assert multifamily_demand_factor(62) == 0.23
    assert multifamily_demand_factor(1) == 1.0


def test_calculate_all():
    inp = ProjectInput(floor_area_sqft=1200, num_units=4, project_type="multi_family")
    res = calculate_all(inp)
    assert "standard" in res
    assert "optional_220_82" in res
    assert "optional_220_84" in res


def test_service_recommendation():
    from app.calculations.nec220 import recommend_service_amps
    assert recommend_service_amps(95) == 125  # 95*1.1=104.5 -> 125? actually 100<104.5 so 125
    assert recommend_service_amps(180) == 200


def test_range_table_220_55_multiple():
    # 2 ranges not over 12kW -> 11 kW
    assert range_demand([8.0, 8.0]) == 11000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
