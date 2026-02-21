"""SightLine PANIC interrupt handler (SL-34).

Detects PANIC conditions and enforces immediate LOD 1 with
TTS queue flush.  PANIC sources:

- ``heart_rate > 120`` (from Apple Watch via WCSession)
- ``panic: true`` flag in telemetry (iOS shake gesture / SOS)
- ``heart_rate_spike``: sudden jump > 30 bpm in < 5 s

PANIC takes absolute priority over all other LOD rules.
"""

from __future__ import annotations

import logging
import time

logger = logging.getLogger("sightline.panic")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HR_PANIC_THRESHOLD = 120  # bpm
HR_SPIKE_DELTA = 30  # bpm increase within SPIKE_WINDOW_SEC
SPIKE_WINDOW_SEC = 5.0
PANIC_COOLDOWN_SEC = 15.0  # suppress repeated PANIC within cooldown


class PanicHandler:
    """Stateful PANIC detector.

    Call :meth:`evaluate` on every telemetry tick.  When a PANIC
    condition is detected the first time (or after cooldown), it
    returns ``True`` so the caller can flush TTS and force LOD 1.
    """

    def __init__(self) -> None:
        self._prev_hr: float | None = None
        self._prev_hr_time: float = 0.0
        self._last_panic_time: float = 0.0
        self._active: bool = False

    @property
    def is_active(self) -> bool:
        """Whether PANIC is currently active (within cooldown)."""
        return self._active

    def evaluate(
        self,
        heart_rate: float | None,
        panic_flag: bool = False,
    ) -> bool:
        """Evaluate PANIC conditions.

        Returns ``True`` when a *new* PANIC event should be raised
        (i.e. first detection or cooldown has elapsed).
        """
        now = time.monotonic()

        triggered = False
        reason = ""

        # Check explicit panic flag
        if panic_flag:
            triggered = True
            reason = "explicit PANIC flag"

        # Check absolute heart-rate threshold
        if not triggered and heart_rate is not None and heart_rate > HR_PANIC_THRESHOLD:
            triggered = True
            reason = f"heart_rate={heart_rate:.0f} > {HR_PANIC_THRESHOLD}"

        # Check heart-rate spike (sudden jump)
        if (
            not triggered
            and heart_rate is not None
            and self._prev_hr is not None
            and (now - self._prev_hr_time) < SPIKE_WINDOW_SEC
        ):
            delta = heart_rate - self._prev_hr
            if delta > HR_SPIKE_DELTA:
                triggered = True
                reason = f"HR spike +{delta:.0f} bpm in {now - self._prev_hr_time:.1f}s"

        # Update heart-rate history
        if heart_rate is not None:
            self._prev_hr = heart_rate
            self._prev_hr_time = now

        if not triggered:
            # Reset active state if cooldown elapsed
            if self._active and (now - self._last_panic_time) > PANIC_COOLDOWN_SEC:
                self._active = False
                logger.info("PANIC cooldown elapsed, returning to normal")
            return False

        # Suppress duplicate triggers within cooldown
        if self._active and (now - self._last_panic_time) < PANIC_COOLDOWN_SEC:
            return False

        # New PANIC event
        self._active = True
        self._last_panic_time = now
        logger.warning("PANIC triggered: %s", reason)
        return True

    def reset(self) -> None:
        """Manually clear PANIC state (e.g. user calms down)."""
        self._active = False
        self._prev_hr = None
        logger.info("PANIC state manually reset")
