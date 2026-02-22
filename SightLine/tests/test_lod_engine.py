"""Tests for SightLine LOD decision engine."""

from lod.lod_engine import LODDecisionLog, decide_lod, should_speak
from lod.models import EphemeralContext, SessionContext, UserProfile


# =====================================================================
# decide_lod() — Rule 0: PANIC flag
# =====================================================================


def test_panic_flag_forces_lod1(panic_ephemeral, default_session, default_profile):
    lod, log = decide_lod(panic_ephemeral, default_session, default_profile)
    assert lod == 1
    assert any("PANIC" in r for r in log.triggered_rules)


def test_panic_flag_overrides_stationary(default_session, default_profile):
    ctx = EphemeralContext(motion_state="stationary", step_cadence=0, panic=True)
    lod, _ = decide_lod(ctx, default_session, default_profile)
    assert lod == 1


# =====================================================================
# decide_lod() — Rule 1: Heart rate
# =====================================================================


def test_high_heart_rate_forces_lod1(high_hr_ephemeral, default_session, default_profile):
    lod, log = decide_lod(high_hr_ephemeral, default_session, default_profile)
    assert lod == 1
    assert any("HR=" in r for r in log.triggered_rules)


def test_normal_heart_rate_no_override(default_session, default_profile):
    ctx = EphemeralContext(heart_rate=75)
    lod, log = decide_lod(ctx, default_session, default_profile)
    assert not any("Rule1" in r for r in log.triggered_rules)


def test_heart_rate_none_skips_rule(default_session, default_profile):
    ctx = EphemeralContext(heart_rate=None)
    lod, log = decide_lod(ctx, default_session, default_profile)
    assert not any("Rule1" in r for r in log.triggered_rules)


# =====================================================================
# decide_lod() — Rule 2: Motion state baseline
# =====================================================================


def test_running_is_lod1(running_ephemeral, default_session, default_profile):
    lod, _ = decide_lod(running_ephemeral, default_session, default_profile)
    assert lod == 1


def test_high_cadence_is_lod1(default_session, default_profile):
    ctx = EphemeralContext(motion_state="walking", step_cadence=130)
    lod, _ = decide_lod(ctx, default_session, default_profile)
    assert lod == 1


def test_walking_fast_is_lod1(walking_ephemeral, default_session, default_profile):
    # walking_ephemeral has cadence=80 which is >= 60
    lod, _ = decide_lod(walking_ephemeral, default_session, default_profile)
    assert lod == 1


def test_walking_slow_is_lod2(default_session, default_profile):
    ctx = EphemeralContext(motion_state="walking", step_cadence=50)
    lod, _ = decide_lod(ctx, default_session, default_profile)
    assert lod == 2


def test_stationary_is_lod3(stationary_ephemeral, default_session, default_profile):
    lod, _ = decide_lod(stationary_ephemeral, default_session, default_profile)
    assert lod == 3


def test_vehicle_is_lod3(vehicle_ephemeral, default_session, default_profile):
    lod, _ = decide_lod(vehicle_ephemeral, default_session, default_profile)
    assert lod == 3


def test_cycling_is_lod1(default_session, default_profile):
    ctx = EphemeralContext(motion_state="cycling")
    lod, _ = decide_lod(ctx, default_session, default_profile)
    assert lod == 1


# =====================================================================
# decide_lod() — Rule 3: Ambient noise override
# =====================================================================


def test_loud_noise_caps_lod1(default_session, default_profile):
    ctx = EphemeralContext(motion_state="stationary", ambient_noise_db=85)
    lod, log = decide_lod(ctx, default_session, default_profile)
    assert lod == 1
    assert any("noise" in r.lower() for r in log.triggered_rules)


def test_moderate_noise_no_effect(default_session, default_profile):
    ctx = EphemeralContext(motion_state="stationary", ambient_noise_db=65)
    lod, _ = decide_lod(ctx, default_session, default_profile)
    assert lod == 3


# =====================================================================
# decide_lod() — Rule 4: Space transition boost
# =====================================================================


def test_space_transition_boosts_to_lod2(default_profile):
    ctx = EphemeralContext(motion_state="walking", step_cadence=80)
    session = SessionContext(recent_space_transition=True)
    lod, log = decide_lod(ctx, session, default_profile)
    assert lod >= 2
    assert any("space_transition" in r for r in log.triggered_rules)


# =====================================================================
# decide_lod() — Rule 5: Verbosity preference
# =====================================================================


def test_minimal_pref_decreases_lod(stationary_ephemeral, default_session, minimal_profile):
    lod, log = decide_lod(stationary_ephemeral, default_session, minimal_profile)
    assert lod == 2  # 3 - 1 = 2


def test_detailed_pref_increases_lod(default_session, detailed_profile):
    ctx = EphemeralContext(motion_state="walking", step_cadence=50)
    lod, _ = decide_lod(ctx, default_session, detailed_profile)
    assert lod == 3  # 2 + 1 = 3


# =====================================================================
# decide_lod() — Rule 6: Advanced O&M
# =====================================================================


def test_advanced_daily_decreases_lod(stationary_ephemeral, default_session, advanced_daily_profile):
    lod, _ = decide_lod(stationary_ephemeral, default_session, advanced_daily_profile)
    assert lod == 2  # 3 - 1 = 2


# =====================================================================
# decide_lod() — Rule 7: User override
# =====================================================================


def test_user_detail_request_forces_lod3(walking_ephemeral, default_profile):
    session = SessionContext(user_requested_detail=True)
    lod, log = decide_lod(walking_ephemeral, session, default_profile)
    assert lod == 3
    assert any("user_requested_detail" in r for r in log.triggered_rules)


def test_user_stop_forces_lod1(stationary_ephemeral, default_profile):
    session = SessionContext(user_said_stop=True)
    lod, log = decide_lod(stationary_ephemeral, session, default_profile)
    assert lod == 1
    assert any("user_said_stop" in r for r in log.triggered_rules)


# =====================================================================
# decide_lod() — Gesture override
# =====================================================================


def test_gesture_lod_up(default_session, default_profile):
    ctx = EphemeralContext(motion_state="walking", step_cadence=50, user_gesture="lod_up")
    lod, log = decide_lod(ctx, default_session, default_profile)
    assert lod == 3  # base LOD 2 + 1 = 3
    assert any("lod_up" in r for r in log.triggered_rules)


def test_gesture_lod_down(default_session, default_profile):
    ctx = EphemeralContext(motion_state="walking", step_cadence=50, user_gesture="lod_down")
    lod, log = decide_lod(ctx, default_session, default_profile)
    assert lod == 1  # base LOD 2 - 1 = 1
    assert any("lod_down" in r for r in log.triggered_rules)


# =====================================================================
# LODDecisionLog
# =====================================================================


def test_decision_log_has_triggered_rules(walking_ephemeral, default_session, default_profile):
    _, log = decide_lod(walking_ephemeral, default_session, default_profile)
    assert len(log.triggered_rules) > 0


def test_decision_log_to_debug_dict(walking_ephemeral, default_session, default_profile):
    _, log = decide_lod(walking_ephemeral, default_session, default_profile)
    d = log.to_debug_dict()
    assert "lod" in d
    assert "prev" in d
    assert "reason" in d
    assert "rules" in d
    assert isinstance(d["rules"], list)


# =====================================================================
# should_speak()
# =====================================================================


def test_safety_warning_always_speaks():
    assert should_speak("safety_warning", current_lod=1, step_cadence=120, ambient_noise_db=90) is True


def test_low_value_high_noise_no_speak():
    assert should_speak("atmosphere", current_lod=1, step_cadence=80, ambient_noise_db=85) is False


def test_navigation_normal_conditions():
    assert should_speak("navigation", current_lod=2, step_cadence=50, ambient_noise_db=50) is True
