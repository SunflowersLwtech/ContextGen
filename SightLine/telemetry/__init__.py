"""SightLine telemetry parsing and semantic conversion.

Converts raw sensor JSON from iOS into semantic text
suitable for injection into Gemini Live API context.
"""

from telemetry.telemetry_parser import parse_telemetry

__all__ = ["parse_telemetry"]
