"""Tests for SightLine telemetry parser."""

from telemetry.telemetry_parser import parse_telemetry, parse_telemetry_to_ephemeral


# =====================================================================
# parse_telemetry() — semantic text output
# =====================================================================


def test_walking_state_description():
    result = parse_telemetry({"motion_state": "walking"})
    assert "walking" in result.lower()


def test_high_noise_warning():
    result = parse_telemetry({"ambient_noise_db": 85})
    assert "loud" in result.lower() or "difficulty hearing" in result.lower()


def test_elevated_heart_rate():
    result = parse_telemetry({"heart_rate": 125})
    assert "elevated" in result.lower()


def test_gps_location_format():
    result = parse_telemetry({"gps": {"latitude": 37.7749, "longitude": -122.4194}})
    assert "Location:" in result


def test_heading_cardinal():
    result = parse_telemetry({"heading": 90})
    assert "East" in result


def test_empty_data_fallback():
    result = parse_telemetry({})
    assert "No sensor data available" in result


# =====================================================================
# parse_telemetry_to_ephemeral() — structured context
# =====================================================================


def test_ephemeral_motion_state_mapping():
    ctx = parse_telemetry_to_ephemeral({"motion_state": "automotive"})
    assert ctx.motion_state == "in_vehicle"


def test_ephemeral_unknown_motion_default():
    ctx = parse_telemetry_to_ephemeral({"motion_state": "unknown"})
    assert ctx.motion_state == "stationary"


def test_ephemeral_gps_parsing():
    ctx = parse_telemetry_to_ephemeral({
        "gps": {"latitude": 37.77, "longitude": -122.42, "accuracy": 5.0, "speed": 1.2}
    })
    assert ctx.gps is not None
    assert abs(ctx.gps.lat - 37.77) < 0.01
    assert abs(ctx.gps.lng - (-122.42)) < 0.01
    assert ctx.gps.accuracy == 5.0
    assert ctx.gps.speed == 1.2


def test_ephemeral_heart_rate_none():
    ctx = parse_telemetry_to_ephemeral({})
    assert ctx.heart_rate is None


def test_ephemeral_panic_flag():
    ctx = parse_telemetry_to_ephemeral({"panic": True})
    assert ctx.panic is True


def test_ephemeral_invalid_values():
    ctx = parse_telemetry_to_ephemeral({"step_cadence": "abc", "ambient_noise_db": "xyz"})
    assert ctx.step_cadence == 0.0
    assert ctx.ambient_noise_db == 50.0
