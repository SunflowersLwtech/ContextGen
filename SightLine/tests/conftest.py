"""Shared pytest fixtures for SightLine Phase 2 backend tests."""

import sys
from pathlib import Path

# Ensure the SightLine package root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from lod.models import EphemeralContext, GPSData, SessionContext, UserProfile


# ---------------------------------------------------------------------------
# EphemeralContext fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def default_ephemeral() -> EphemeralContext:
    return EphemeralContext()


@pytest.fixture
def walking_ephemeral() -> EphemeralContext:
    return EphemeralContext(motion_state="walking", step_cadence=80)


@pytest.fixture
def running_ephemeral() -> EphemeralContext:
    return EphemeralContext(motion_state="running", step_cadence=150)


@pytest.fixture
def stationary_ephemeral() -> EphemeralContext:
    return EphemeralContext(motion_state="stationary", step_cadence=0)


@pytest.fixture
def vehicle_ephemeral() -> EphemeralContext:
    return EphemeralContext(motion_state="in_vehicle")


@pytest.fixture
def panic_ephemeral() -> EphemeralContext:
    return EphemeralContext(panic=True)


@pytest.fixture
def high_hr_ephemeral() -> EphemeralContext:
    return EphemeralContext(heart_rate=130)


@pytest.fixture
def noisy_ephemeral() -> EphemeralContext:
    """High ambient noise (>80 dB) — caps LOD to 1."""
    return EphemeralContext(ambient_noise_db=85)


@pytest.fixture
def commute_ephemeral() -> EphemeralContext:
    """Morning commute context — triggers Rule 2b LOD reduction."""
    return EphemeralContext(motion_state="stationary", time_context="morning_commute")


# ---------------------------------------------------------------------------
# SessionContext fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def default_session() -> SessionContext:
    return SessionContext()


# ---------------------------------------------------------------------------
# UserProfile fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def default_profile() -> UserProfile:
    return UserProfile.default()


@pytest.fixture
def minimal_profile() -> UserProfile:
    p = UserProfile.default()
    p.verbosity_preference = "minimal"
    return p


@pytest.fixture
def detailed_profile() -> UserProfile:
    p = UserProfile.default()
    p.verbosity_preference = "detailed"
    return p


@pytest.fixture
def advanced_daily_profile() -> UserProfile:
    p = UserProfile.default()
    p.om_level = "advanced"
    p.travel_frequency = "daily"
    return p
