import pytest

from app.services.nec_calc import ampacity, conduit_fill, egc_size, gec_size, voltage_drop


def test_ampacity_200a_conductor():
    r = ampacity("2/0", material="cu", ambient_c=25, num_conductors=3)
    assert r["value"] == 175.0
    assert "310.15" in r["nec_reference"]


def test_ampacity_continuous_derates():
    r = ampacity("4", material="cu", ambient_c=25, num_conductors=3, continuous=True)
    assert r["value"] == pytest.approx(85 / 1.25, rel=1e-3)


def test_voltage_drop_within_limit():
    r = voltage_drop("2/0", material="cu", amps=48, length_ft=80, phase=1, max_percent=3.0)
    assert r["value_percent"] is not None
    assert r["value_percent"] < 3.0
    assert r["warnings"] == []


def test_voltage_drop_warning():
    r = voltage_drop("12", material="cu", amps=20, length_ft=200, phase=1, max_percent=3.0)
    assert r["value_percent"] > 3.0
    assert any("exceeds" in w for w in r["warnings"])


def test_conduit_fill():
    r = conduit_fill("10", num_conductors=4, fill_percent=40.0)
    assert r["required_trade_size"] == "1/2"
    assert r["warnings"] == []


def test_conduit_fill_provided_too_small():
    r = conduit_fill("10", num_conductors=6, conduit_trade="1/2", fill_percent=40.0)
    assert any("exceeds" in w for w in r["warnings"])


def test_gec_size():
    r = gec_size("2/0")
    assert r["gec_size_cu"] == "4"


def test_egc_size():
    r = egc_size(50)
    assert r["egc_size_cu"] == "10"
    r2 = egc_size(200)
    assert r2["egc_size_cu"] == "6"