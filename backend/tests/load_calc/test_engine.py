from app.services.load_calc.engine import LoadCalcEngine
from app.services.load_calc.schemas import ApplianceInput, LoadCalcRequest


def test_engine_returns_multiple_methods():
    data = LoadCalcRequest(
        project_type="single_family",
        floor_area_sqft=2200,
        appliances=[
            ApplianceInput(name="Range", rating_kw=12),
            ApplianceInput(name="Dryer", rating_kw=5.5),
        ],
        hvac_cooling_va=5000,
        include_both_methods=True,
    )

    engine = LoadCalcEngine()
    results = engine.calculate(data)

    methods = [r.method for r in results]
    assert "standard" in methods
    assert "optional_220_82" in methods
    assert "optional_220_83" in methods
    assert len(results) >= 3


def test_engine_multifamily():
    data = LoadCalcRequest(
        project_type="multi_family",
        floor_area_sqft=1100,
        num_units=6,
        appliances=[ApplianceInput(name="Range", rating_kw=12)],
        include_both_methods=True,
    )

    results = LoadCalcEngine().calculate(data)
    methods = [r.method for r in results]

    assert "standard" in methods
    assert "optional_220_84" in methods
