from app.services.load_calc.schemas import ApplianceInput, LoadCalcRequest
from app.services.load_calc.standard import calculate_standard


def test_basic_single_family():
    data = LoadCalcRequest(
        project_type="single_family",
        floor_area_sqft=2000,
        appliances=[
            ApplianceInput(name="Range", rating_kw=12),
            ApplianceInput(name="Dryer", rating_kw=5.5),
        ],
        hvac_cooling_va=5000,
    )

    result = calculate_standard(data)

    assert result.method == "standard"
    assert result.total_demand_va > 0
    assert result.recommended_service_amps >= 100
    assert any("Lighting" in item.description for item in result.line_items)
    assert any("Range" in item.description for item in result.line_items)


def test_lighting_demand_applied():
    data = LoadCalcRequest(
        project_type="single_family",
        floor_area_sqft=1000,
        appliances=[],
    )
    result = calculate_standard(data)

    lighting_item = next(i for i in result.line_items if "Table 220.42" in i.description)
    assert lighting_item.demand_va == 4575
