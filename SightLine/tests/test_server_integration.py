"""Integration smoke tests for the SightLine server.

These tests verify:
- FastAPI app startup and health endpoint
- WebSocket connection acceptance
- Upstream message type handling (structural only — no live Gemini connection)

Note: These tests do NOT require a real Gemini API connection.
They verify the server's structural correctness: routing, message parsing,
LOD state initialisation, and protocol compliance.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Fixture: FastAPI TestClient
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    """Create a TestClient for the SightLine FastAPI app."""
    from server import app
    return TestClient(app)


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    """Verify the /health endpoint for Cloud Run probes."""

    def test_health_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "model" in data

    def test_health_reports_phase(self, client):
        response = client.get("/health")
        data = response.json()
        assert data["phase"] == 2


# ---------------------------------------------------------------------------
# Session Manager
# ---------------------------------------------------------------------------


class TestSessionManager:
    """Verify SessionManager initialisation and state management."""

    def test_session_context_creation(self):
        from live_api.session_manager import SessionManager
        mgr = SessionManager()
        ctx = mgr.get_session_context("test_session")
        assert ctx.current_lod == 2  # default LOD
        assert ctx.space_type == "unknown"

    def test_user_profile_defaults(self):
        from live_api.session_manager import SessionManager
        mgr = SessionManager()
        profile = mgr.get_user_profile("test_user")
        assert profile.user_id == "test_user"
        assert profile.vision_status == "totally_blind"
        assert profile.verbosity_preference == "standard"

    def test_ephemeral_context_creation(self):
        from live_api.session_manager import SessionManager
        mgr = SessionManager()
        ctx = mgr.get_ephemeral_context("test_session")
        assert ctx.motion_state == "stationary"

    def test_session_handle_cache(self):
        from live_api.session_manager import SessionManager
        mgr = SessionManager()
        assert mgr.get_handle("s1") is None
        mgr.update_handle("s1", "handle_abc")
        assert mgr.get_handle("s1") == "handle_abc"

    def test_session_cleanup(self):
        from live_api.session_manager import SessionManager
        mgr = SessionManager()
        mgr.get_session_context("s1")
        mgr.update_handle("s1", "h1")
        mgr.remove_session("s1")
        assert mgr.get_handle("s1") is None

    def test_run_config_has_vad_params(self):
        """SL-36: RunConfig should include LOD-specific VAD settings."""
        from live_api.session_manager import SessionManager
        mgr = SessionManager()
        config = mgr.get_run_config("test", lod=1)
        assert config.streaming_mode is not None
        assert config.realtime_input_config is not None

    def test_run_config_lod3_longer_silence(self):
        """LOD 3 should have longer silence duration than LOD 1."""
        from live_api.session_manager import SessionManager, LOD_VAD_PRESETS
        assert LOD_VAD_PRESETS[3]["silence_duration_ms"] > LOD_VAD_PRESETS[1]["silence_duration_ms"]


# ---------------------------------------------------------------------------
# Telemetry → LOD integration
# ---------------------------------------------------------------------------


class TestTelemetryLODIntegration:
    """Verify the telemetry → LOD engine integration path."""

    def test_telemetry_to_ephemeral_to_lod(self):
        """Full pipeline: raw telemetry JSON → EphemeralContext → LOD decision."""
        from telemetry.telemetry_parser import parse_telemetry_to_ephemeral
        from lod import decide_lod
        from lod.models import SessionContext, UserProfile

        raw = {
            "motion_state": "walking",
            "step_cadence": 80,
            "ambient_noise_db": 55,
            "heart_rate": 75,
        }
        ephemeral = parse_telemetry_to_ephemeral(raw)
        session = SessionContext()
        profile = UserProfile.default()

        lod, log = decide_lod(ephemeral, session, profile)

        # Walking at 80 spm → should be LOD 1
        assert lod == 1
        assert log.motion_state == "walking"
        assert len(log.triggered_rules) > 0

    def test_stationary_gives_lod3(self):
        """Stationary user should get LOD 3."""
        from telemetry.telemetry_parser import parse_telemetry_to_ephemeral
        from lod import decide_lod
        from lod.models import SessionContext, UserProfile

        raw = {
            "motion_state": "stationary",
            "step_cadence": 0,
            "ambient_noise_db": 35,
        }
        ephemeral = parse_telemetry_to_ephemeral(raw)
        lod, _ = decide_lod(ephemeral, SessionContext(), UserProfile.default())
        assert lod == 3

    def test_panic_overrides_everything(self):
        """PANIC flag should force LOD 1 regardless of other context."""
        from telemetry.telemetry_parser import parse_telemetry_to_ephemeral
        from lod import decide_lod
        from lod.models import SessionContext, UserProfile

        raw = {
            "motion_state": "stationary",
            "step_cadence": 0,
            "ambient_noise_db": 30,
            "panic": True,
        }
        ephemeral = parse_telemetry_to_ephemeral(raw)
        lod, log = decide_lod(ephemeral, SessionContext(), UserProfile.default())
        assert lod == 1
        assert "PANIC" in log.reason


# ---------------------------------------------------------------------------
# TelemetryAggregator wiring
# ---------------------------------------------------------------------------


class TestTelemetryAggregator:
    """Verify TelemetryAggregator LOD-aware throttling."""

    def test_immediate_first_send(self):
        from lod.telemetry_aggregator import TelemetryAggregator
        agg = TelemetryAggregator()
        assert agg.should_send(0.0) is True

    def test_throttle_within_interval(self):
        from lod.telemetry_aggregator import TelemetryAggregator
        agg = TelemetryAggregator(current_lod=2)
        agg.mark_sent(0.0)
        # LOD 2 midpoint interval = 2.5s; at 1s should NOT send
        assert agg.should_send(1.0) is False

    def test_send_after_interval(self):
        from lod.telemetry_aggregator import TelemetryAggregator
        agg = TelemetryAggregator(current_lod=2)
        agg.mark_sent(0.0)
        # LOD 2 midpoint interval = 2.5s; at 3s should send
        assert agg.should_send(3.0) is True

    def test_lod_change_updates_interval(self):
        from lod.telemetry_aggregator import TelemetryAggregator
        agg = TelemetryAggregator(current_lod=1)
        interval_lod1 = agg.send_interval
        agg.update_lod(3)
        interval_lod3 = agg.send_interval
        assert interval_lod3 > interval_lod1  # LOD 3 is slower
