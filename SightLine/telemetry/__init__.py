"""SightLine telemetry parsing and semantic conversion.

Converts raw sensor JSON from iOS into semantic text
suitable for injection into Gemini Live API context.

Phase 2: Also converts raw telemetry into ``EphemeralContext``
for the LOD decision engine.
"""

from telemetry.telemetry_parser import parse_telemetry, parse_telemetry_to_ephemeral

__all__ = ["parse_telemetry", "parse_telemetry_to_ephemeral"]
