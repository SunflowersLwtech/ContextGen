"""SightLine LOD Decision Engine.

Rule-based (non-LLM) engine that fuses three context layers
(Ephemeral, Session, Profile) into a LOD 1/2/3 decision in <1 ms.

Decision priority (high → low):
    1. PANIC interrupt (heart_rate > 120)
    2. Motion-state baseline
    3. Ambient noise override
    4. Space transition boost
    5. User verbosity preference
    6. O&M level adjustment
    7. Explicit user override (final)

Every decision produces an explainable ``LODDecisionLog``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from lod.models import EphemeralContext, SessionContext, UserProfile

logger = logging.getLogger("sightline.lod")

# ---------------------------------------------------------------------------
# LOD Decision Log — explainable audit trail (SL-39)
# ---------------------------------------------------------------------------


@dataclass
class LODDecisionLog:
    """Complete explainable record of a single LOD decision."""

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Input snapshot
    motion_state: str = ""
    step_cadence: float = 0.0
    ambient_noise_db: float = 70.0
    heart_rate: float | None = None
    panic: bool = False
    space_transition: bool = False
    verbosity_preference: str = "standard"
    om_level: str = "intermediate"
    travel_frequency: str = "weekly"
    user_override: str | None = None  # "detail" | "stop" | None

    # Decision trace
    triggered_rules: list[str] = field(default_factory=list)
    base_lod_before_adjustments: int = 2

    # Output
    previous_lod: int = 2
    final_lod: int = 2
    reason: str = ""

    def to_debug_dict(self) -> dict:
        """Compact dict for DebugOverlay / WebSocket ``debug_lod`` event."""
        return {
            "lod": self.final_lod,
            "prev": self.previous_lod,
            "reason": self.reason,
            "rules": self.triggered_rules,
            "hr": self.heart_rate,
            "motion": self.motion_state,
            "cadence": self.step_cadence,
            "noise_db": self.ambient_noise_db,
            "panic": self.panic,
        }


# ---------------------------------------------------------------------------
# Speech-cost thresholds (§3.2 "发声有成本")
# ---------------------------------------------------------------------------

# Base threshold that info_value must exceed to trigger speech
BASE_SPEECH_THRESHOLD = 3.0

INFO_VALUES: dict[str, float] = {
    "safety_warning": 10.0,
    "navigation": 8.0,
    "face_recognition": 7.0,
    "spatial_description": 5.0,
    "object_enumeration": 3.0,
    "atmosphere": 1.0,
}


def should_speak(
    info_type: str,
    current_lod: int,
    step_cadence: float = 0.0,
    ambient_noise_db: float = 70.0,
) -> bool:
    """Determine whether the agent should vocalise this information.

    Safety warnings always pass.  Everything else is gated by the
    combined movement + noise penalty on top of ``BASE_SPEECH_THRESHOLD``.
    """
    info_value = INFO_VALUES.get(info_type, 1.0)
    if info_value >= 10.0:
        return True  # safety always speaks

    movement_penalty = (step_cadence / 60.0) * 2.0
    noise_penalty = max(0.0, (ambient_noise_db - 60) * 0.1)
    threshold = BASE_SPEECH_THRESHOLD + movement_penalty + noise_penalty

    return info_value > threshold


# ---------------------------------------------------------------------------
# Core LOD decision function
# ---------------------------------------------------------------------------


def decide_lod(
    ephemeral: EphemeralContext,
    session: SessionContext,
    profile: UserProfile,
) -> tuple[int, LODDecisionLog]:
    """Fuse three context layers and return (lod, log).

    Returns
    -------
    (lod, log) : tuple[int, LODDecisionLog]
        lod in {1, 2, 3}; log contains full decision trace.
    """
    def _to_float(value, default: float) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    def _to_opt_float(value) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    motion_state = getattr(ephemeral, "motion_state", "stationary") or "stationary"
    step_cadence = _to_float(getattr(ephemeral, "step_cadence", 0.0), 0.0)
    _raw_noise = getattr(ephemeral, "ambient_noise_db", None)
    if _raw_noise is None:
        logger.debug("ambient_noise_db missing; defaulting to conservative 70dB")
        ambient_noise_db = 70.0
    else:
        ambient_noise_db = _to_float(_raw_noise, 70.0)
    heart_rate = _to_opt_float(getattr(ephemeral, "heart_rate", None))
    panic = bool(getattr(ephemeral, "panic", False))
    _raw_gesture = getattr(ephemeral, "user_gesture", None)
    if isinstance(_raw_gesture, str) and _raw_gesture.strip():
        user_gesture = _raw_gesture.strip().lower()
        if user_gesture not in ("lod_up", "lod_down", "tap", "shake"):
            logger.warning("Unknown user_gesture: %r", user_gesture)
            user_gesture = None
    else:
        user_gesture = None

    recent_space_transition = bool(getattr(session, "recent_space_transition", False))
    user_requested_detail = bool(getattr(session, "user_requested_detail", False))
    user_said_stop = bool(getattr(session, "user_said_stop", False))
    previous_lod = int(getattr(session, "current_lod", 2) or 2)

    verbosity_preference = getattr(profile, "verbosity_preference", "standard") or "standard"
    om_level = getattr(profile, "om_level", "intermediate") or "intermediate"
    travel_frequency = getattr(profile, "travel_frequency", "weekly") or "weekly"

    log = LODDecisionLog(
        motion_state=motion_state,
        step_cadence=step_cadence,
        ambient_noise_db=ambient_noise_db,
        heart_rate=heart_rate,
        panic=panic,
        space_transition=recent_space_transition,
        verbosity_preference=verbosity_preference,
        om_level=om_level,
        travel_frequency=travel_frequency,
        previous_lod=previous_lod,
    )

    # ── Rule 0: Explicit PANIC flag from iOS ──────────────────────────
    if panic:
        log.triggered_rules.append("Rule0:PANIC_flag→LOD1")
        log.final_lod = 1
        log.reason = "PANIC flag set by client"
        logger.warning("PANIC flag active → LOD 1")
        return 1, log

    # ── Rule 1: Heart-rate PANIC (only if watch connected) ────────────
    if heart_rate is not None and heart_rate > 120:
        log.triggered_rules.append(f"Rule1:HR={heart_rate:.0f}>120→LOD1")
        log.final_lod = 1
        log.reason = f"PANIC: heart_rate={heart_rate:.0f}>120"
        logger.warning("Heart-rate PANIC (%.0f bpm) → LOD 1", heart_rate)
        return 1, log

    # ── Rule 2: Motion-state baseline ─────────────────────────────────
    if motion_state == "running" or step_cadence >= 120:
        base_lod = 1
        log.triggered_rules.append("Rule2:running→LOD1")
    elif motion_state == "walking":
        if step_cadence < 60:
            base_lod = 2  # slow exploration
            log.triggered_rules.append("Rule2:slow_walk(<60spm)→LOD2")
        else:
            base_lod = 1  # normal walking
            log.triggered_rules.append("Rule2:walking(≥60spm)→LOD1")
    elif motion_state == "in_vehicle":
        base_lod = 3
        log.triggered_rules.append("Rule2:in_vehicle→LOD3")
    elif motion_state == "cycling":
        base_lod = 1
        log.triggered_rules.append("Rule2:cycling→LOD1")
    else:  # stationary
        base_lod = 3
        log.triggered_rules.append("Rule2:stationary→LOD3")

    log.base_lod_before_adjustments = base_lod

    # ── Rule 2b: Time-of-day adjustment ─────────────────────────────
    time_context = getattr(ephemeral, "time_context", "unknown") or "unknown"
    if time_context in ("morning_commute", "late_night") and base_lod > 1:
        base_lod = max(1, base_lod - 1)
        log.triggered_rules.append(f"Rule2b:{time_context}→-1")

    # ── Rule 3: Ambient noise override ────────────────────────────────
    if ambient_noise_db > 80:
        if base_lod > 1:
            log.triggered_rules.append(f"Rule3:noise={ambient_noise_db:.0f}dB>80→cap_LOD1")
        base_lod = min(base_lod, 1)

    # ── Rule 4: Space transition boost ────────────────────────────────
    if recent_space_transition:
        if base_lod < 2:
            log.triggered_rules.append("Rule4:space_transition→boost_LOD2")
        base_lod = max(base_lod, 2)

    # ── Rule 5: User verbosity preference ─────────────────────────────
    if verbosity_preference == "minimal":
        prev = base_lod
        base_lod = max(1, base_lod - 1)
        if base_lod != prev:
            log.triggered_rules.append("Rule5:minimal_pref→-1")
    elif verbosity_preference == "detailed":
        prev = base_lod
        base_lod = min(3, base_lod + 1)
        if base_lod != prev:
            log.triggered_rules.append("Rule5:detailed_pref→+1")

    # ── Rule 6: O&M expert adjustment ─────────────────────────────────
    if om_level == "advanced" and travel_frequency == "daily":
        prev = base_lod
        base_lod = max(1, base_lod - 1)
        if base_lod != prev:
            log.triggered_rules.append("Rule6:advanced_daily→-1")

    # ── Rule 7: Explicit user override + gesture (highest priority after PANIC)
    if user_gesture == "lod_up":
        prev = base_lod
        base_lod = min(3, base_lod + 1)
        if base_lod != prev:
            log.triggered_rules.append("Gesture:lod_up→+1")
    elif user_gesture == "lod_down":
        prev = base_lod
        base_lod = max(1, base_lod - 1)
        if base_lod != prev:
            log.triggered_rules.append("Gesture:lod_down→-1")
    elif user_requested_detail:
        base_lod = 3
        log.triggered_rules.append("Rule7:user_requested_detail→LOD3")
        log.user_override = "detail"
    elif user_said_stop:
        base_lod = 1
        log.triggered_rules.append("Rule7:user_said_stop→LOD1")
        log.user_override = "stop"

    # ── Finalise ──────────────────────────────────────────────────────
    log.final_lod = base_lod
    if log.triggered_rules:
        log.reason = " + ".join(log.triggered_rules) + f" → LOD {base_lod}"
    else:
        log.reason = f"default → LOD {base_lod}"

    if base_lod != previous_lod:
        logger.info(
            "LOD %d → %d  (%s)",
            previous_lod,
            base_lod,
            log.reason,
        )

    return base_lod, log
