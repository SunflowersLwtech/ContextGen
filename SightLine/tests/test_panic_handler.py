"""Tests for SightLine PANIC handler."""

import time
from unittest.mock import patch

from lod.panic_handler import (
    HR_PANIC_THRESHOLD,
    PANIC_COOLDOWN_SEC,
    PanicHandler,
)


def test_explicit_panic_flag():
    h = PanicHandler()
    assert h.evaluate(heart_rate=75, panic_flag=True) is True
    assert h.is_active is True


def test_high_heart_rate_triggers():
    h = PanicHandler()
    assert h.evaluate(heart_rate=130) is True
    assert h.is_active is True


def test_normal_heart_rate_no_trigger():
    h = PanicHandler()
    assert h.evaluate(heart_rate=75) is False
    assert h.is_active is False


def test_heart_rate_spike_triggers():
    h = PanicHandler()
    # First reading at 75 bpm
    h.evaluate(heart_rate=75)
    # Spike to 115 within the same time window (delta=40 > 30)
    assert h.evaluate(heart_rate=115) is True


def test_cooldown_suppresses_duplicate():
    h = PanicHandler()
    # First trigger
    assert h.evaluate(heart_rate=130) is True
    # Second trigger within cooldown should be suppressed
    assert h.evaluate(heart_rate=135) is False


def test_cooldown_elapsed_retriggers():
    h = PanicHandler()
    assert h.evaluate(heart_rate=130) is True

    # Simulate time passing beyond cooldown
    h._last_panic_time = time.monotonic() - (PANIC_COOLDOWN_SEC + 1)
    assert h.evaluate(heart_rate=130) is True


def test_reset_clears_state():
    h = PanicHandler()
    h.evaluate(heart_rate=130)
    assert h.is_active is True
    h.reset()
    assert h.is_active is False
    assert h._prev_hr is None


def test_none_heart_rate_no_crash():
    h = PanicHandler()
    assert h.evaluate(heart_rate=None) is False
    assert h.is_active is False
