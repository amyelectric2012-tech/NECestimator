from app.services.load_calc.optional_82 import calculate_optional_82
from app.services.load_calc.schemas import ApplianceInput, LoadCalcRequest


def test_optional_82_basic():
    data = LoadCalcRequest(
        project_type="single_family",
        floor_area_sqft=2400,
        appliances=[
            ApplianceInput(name="Range", rating_kw=12),
            ApplianceInput(name="Dryer", rating_kw=5.5),
            ApplianceInput(name="Water Heater", rating_kw=4.5),
        ],
        hvac_cooling_va=6000,
    )

    result = calculate_optional_82(data)

    assert result.method == "optional_220_82"
    assert result.total_demand_va > 10000
    assert result.recommended_service_amps >= 100
    assert result.total_demand_va < result.total_connected_va
