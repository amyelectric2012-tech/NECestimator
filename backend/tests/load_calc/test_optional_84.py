from app.services.load_calc.optional_84 import calculate_optional_84
from app.services.load_calc.schemas import ApplianceInput, LoadCalcRequest


def test_multifamily_3_units():
    data = LoadCalcRequest(
        project_type="multi_family",
        floor_area_sqft=1200,
        num_units=3,
        appliances=[
            ApplianceInput(name="Range", rating_kw=12),
            ApplianceInput(name="Dryer", rating_kw=5.5),
        ],
    )

    result = calculate_optional_84(data)

    assert result.method == "optional_220_84"
    assert result.total_demand_va < result.total_connected_va
    assert result.total_demand_va > 0
