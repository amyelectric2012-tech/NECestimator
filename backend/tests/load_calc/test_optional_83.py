from app.services.load_calc.optional_83 import calculate_optional_83
from app.services.load_calc.schemas import ApplianceInput, LoadCalcRequest


def test_optional_83_with_hvac():
    data = LoadCalcRequest(
        project_type="single_family",
        floor_area_sqft=1800,
        appliances=[
            ApplianceInput(name="Range", rating_kw=11),
            ApplianceInput(name="Dryer", rating_kw=5),
        ],
        hvac_cooling_va=5500,
    )

    result = calculate_optional_83(data)

    assert result.method == "optional_220_83"
    assert "220.83(B)" in " ".join(result.calculation_notes)
    assert result.recommended_service_amps >= 100
