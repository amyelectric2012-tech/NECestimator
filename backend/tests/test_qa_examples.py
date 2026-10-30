import sys

sys.path.insert(0, ".")

from app.calculations.nec220 import (
    HVAC,
    Appliance,
    ProjectInput,
    optional_220_84,
    standard_method,
)


def test_qa_1500_basic():
    inp = ProjectInput(floor_area_sqft=1500, num_units=1, small_appliance_circuits=2, laundry_circuits=1,
        appliances=[Appliance("water_heater", 4500), Appliance("dishwasher", 1200), Appliance("disposal", 800)],
        range_count=1, range_kw_each=8.0, dryer_count=1, dryer_kw_each=5.0,
        hvac=HVAC(cooling_va=3000), largest_motor_va=3000)
    r = standard_method(inp)
    assert r.total_va == 28350
    assert r.recommended_service_amps == 150
    assert r.neutral_va == 20700


def test_qa_2400_full():
    inp = ProjectInput(floor_area_sqft=2400, num_units=1, small_appliance_circuits=2, laundry_circuits=1,
        appliances=[Appliance("water_heater", 4500), Appliance("dishwasher", 1200), Appliance("disposal", 900),
                    Appliance("microwave", 1500), Appliance("refrigerator", 800)],
        range_count=1, range_kw_each=12.0, dryer_count=1, dryer_kw_each=5.5,
        hvac=HVAC(cooling_va=5000), largest_motor_va=4000)
    r = standard_method(inp)
    assert r.total_va == 32220
    assert r.recommended_service_amps == 150


def test_qa_4unit_multi():
    inp = ProjectInput(floor_area_sqft=900, num_units=4, small_appliance_circuits=2, laundry_circuits=1,
        appliances=[Appliance("water_heater", 4500), Appliance("dishwasher", 1200)],
        range_count=1, range_kw_each=8.0, dryer_count=1, dryer_kw_each=5.0,
        hvac=HVAC(cooling_va=3000), largest_motor_va=2000)
    r = optional_220_84(inp)
    assert r.total_va == 55620
    assert r.recommended_service_amps == 300
