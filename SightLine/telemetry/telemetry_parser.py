"""Telemetry data parser for SightLine.

Converts raw sensor JSON from the iOS client into semantic text
suitable for injection into the Gemini Live context.

Phase 2 additions:
- ``parse_telemetry_to_ephemeral()`` — converts raw JSON into
  ``EphemeralContext`` for the LOD decision engine.
"""

import json
import logging

from lod.models import EphemeralContext, GPSData

logger = logging.getLogger(__name__)


def _noise_bucket(noise_db: float) -> str:
    """Classify ambient noise level into a bucket label."""
    if noise_db < 40:
        return "quiet"
    elif noise_db < 65:
        return "moderate"
    elif noise_db < 80:
        return "loud"
    else:
        return "very_loud"


def _hr_bucket(hr: float) -> str:
    """Classify heart rate into a bucket label."""
    if hr > 120:
        return "high"
    elif hr > 100:
        return "elevated"
    else:
        return "normal"


def parse_telemetry(data: dict) -> str:
    """Convert raw telemetry JSON to structured KV text for Gemini context injection.

    Args:
        data: Raw telemetry dict from iOS client containing fields like
              motion_state, step_cadence, ambient_noise_db, heart_rate, gps.

    Returns:
        Structured key=value string with ``[TELEMETRY UPDATE]`` prefix.
    """
    pairs: list[str] = []

    # Motion state
    motion_state = data.get("motion_state")
    if motion_state:
        pairs.append(f"motion={motion_state}")

    # Step cadence
    step_cadence = data.get("step_cadence")
    if step_cadence is not None:
        try:
            cadence = float(step_cadence)
            if cadence > 0:
                pairs.append(f"cadence={cadence:.0f}spm")
        except (ValueError, TypeError):
            pass

    # Ambient noise
    ambient_noise_db = data.get("ambient_noise_db")
    if ambient_noise_db is not None:
        try:
            noise = float(ambient_noise_db)
            bucket = _noise_bucket(noise)
            pairs.append(f"noise={noise:.0f}dB/{bucket}")
        except (ValueError, TypeError):
            pass

    # Heart rate
    heart_rate = data.get("heart_rate")
    if heart_rate is not None:
        try:
            hr = float(heart_rate)
            if hr > 0:
                bucket = _hr_bucket(hr)
                pairs.append(f"hr={hr:.0f}/{bucket}")
        except (ValueError, TypeError):
            pass

    # GPS
    gps = data.get("gps")
    if gps and isinstance(gps, dict):
        lat = gps.get("latitude")
        lon = gps.get("longitude")
        accuracy = gps.get("accuracy")
        speed = gps.get("speed")

        if lat is not None and lon is not None:
            loc = f"loc={lat:.6f},{lon:.6f}"
            if accuracy is not None:
                loc += f"/acc={accuracy:.0f}m"
            pairs.append(loc)

        if speed is not None:
            try:
                spd = float(speed)
                if spd > 0:
                    pairs.append(f"speed={spd:.1f}m/s")
            except (ValueError, TypeError):
                pass

    # Heading
    heading = data.get("heading")
    if heading is not None:
        try:
            h = float(heading)
            cardinal = _degrees_to_cardinal(h)
            pairs.append(f"heading={cardinal}/{h:.0f}deg")
        except (ValueError, TypeError):
            pass

    if not pairs:
        logger.debug("Telemetry data had no parseable fields: %s", json.dumps(data))
        return "[TELEMETRY UPDATE] No sensor data available."

    return "[TELEMETRY UPDATE] " + " ".join(pairs)


def _degrees_to_cardinal(degrees: float) -> str:
    """Convert compass degrees to cardinal direction."""
    directions = [
        "North", "North-Northeast", "Northeast", "East-Northeast",
        "East", "East-Southeast", "Southeast", "South-Southeast",
        "South", "South-Southwest", "Southwest", "West-Southwest",
        "West", "West-Northwest", "Northwest", "North-Northwest",
    ]
    idx = round(degrees / 22.5) % 16
    return directions[idx]


# ---------------------------------------------------------------------------
# Phase 2: Raw telemetry → EphemeralContext (for LOD engine)
# ---------------------------------------------------------------------------

# iOS CMMotionActivity types → normalised motion states
_MOTION_STATE_MAP: dict[str, str] = {
    "stationary": "stationary",
    "walking": "walking",
    "running": "running",
    "automotive": "in_vehicle",
    "cycling": "cycling",
    "unknown": "stationary",
}


def parse_telemetry_to_ephemeral(data: dict) -> EphemeralContext:
    """Convert raw telemetry JSON from iOS into an ``EphemeralContext``.

    This is the LOD engine's input — a structured snapshot of the user's
    physical state, used alongside ``SessionContext`` and ``UserProfile``
    by ``decide_lod()``.

    Args:
        data: Raw telemetry dict from iOS TelemetryData.toJSON().

    Returns:
        Populated EphemeralContext dataclass.
    """
    ctx = EphemeralContext()

    # Motion state
    raw_motion = data.get("motion_state", "stationary")
    ctx.motion_state = _MOTION_STATE_MAP.get(raw_motion, "stationary")

    # Step cadence
    try:
        ctx.step_cadence = float(data.get("step_cadence", 0.0))
    except (ValueError, TypeError):
        ctx.step_cadence = 0.0

    # Ambient noise
    try:
        ctx.ambient_noise_db = float(data.get("ambient_noise_db", 50.0))
    except (ValueError, TypeError):
        ctx.ambient_noise_db = 50.0

    # GPS
    gps_raw = data.get("gps")
    if gps_raw and isinstance(gps_raw, dict):
        try:
            ctx.gps = GPSData(
                lat=float(gps_raw.get("latitude", 0.0)),
                lng=float(gps_raw.get("longitude", 0.0)),
                accuracy=float(gps_raw.get("accuracy", 0.0)),
                speed=float(gps_raw.get("speed", 0.0)),
                altitude=float(gps_raw.get("altitude", 0.0)),
            )
        except (ValueError, TypeError):
            ctx.gps = None

    # Heading
    try:
        ctx.heading = float(data.get("heading", 0.0))
    except (ValueError, TypeError):
        ctx.heading = 0.0

    # Time context
    ctx.time_context = data.get("time_context", "unknown")

    # Heart rate (None when watch not connected)
    hr = data.get("heart_rate")
    if hr is not None:
        try:
            ctx.heart_rate = float(hr)
        except (ValueError, TypeError):
            ctx.heart_rate = None

    # User gesture (lod_up, lod_down, tap, shake)
    ctx.user_gesture = data.get("user_gesture")

    # Panic flag
    ctx.panic = bool(data.get("panic", False))

    # Device type
    ctx.device_type = data.get("device_type", "phone_only")

    return ctx
