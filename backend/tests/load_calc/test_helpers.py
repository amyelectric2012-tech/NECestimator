from app.services.load_calc.helpers import (
    apply_continuous_factor,
    largest_motor_or_hvac,
    recommend_service_size,
    va_from_kw,
)


def test_va_from_kw():
    assert va_from_kw(5.5) == 5500


def test_continuous_factor():
    assert apply_continuous_factor(4000, True) == 5000
    assert apply_continuous_factor(4000, False) == 4000


def test_recommend_service_size():
    assert recommend_service_size(12000) in [100, 125]
    assert recommend_service_size(28000) == 150
    assert recommend_service_size(45000) in [225, 400]


def test_largest_hvac():
    assert largest_motor_or_hvac(8000, 6000) == 8000
    assert largest_motor_or_hvac(5000, 9000) == 9000
