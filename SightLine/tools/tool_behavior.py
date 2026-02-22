"""Tool behavior policy for downstream delivery modes.

Phase 3 contract:
- INTERRUPT: stop current playback and deliver now.
- WHEN_IDLE: queue until playback is idle.
- SILENT: inject context/update without forced speech.
"""

from __future__ import annotations

from enum import Enum


class ToolBehavior(str, Enum):
    """Delivery policy used by cloud and edge runtimes."""

    INTERRUPT = "INTERRUPT"
    WHEN_IDLE = "WHEN_IDLE"
    SILENT = "SILENT"


def resolve_tool_behavior(
    tool_name: str,
    lod: int = 2,
    is_user_speaking: bool = False,
) -> ToolBehavior:
    """Resolve behavior mode for a tool call.

    Rules:
    - identify_person is always SILENT to avoid hard interruption.
    - Navigation/search default to WHEN_IDLE during active speech.
    - LOD1 safety mode can escalate navigation to INTERRUPT.
    """
    name = (tool_name or "").strip().lower()

    if name == "identify_person":
        return ToolBehavior.SILENT

    if name in {"navigate_to", "navigate_location"} and lod <= 1:
        return ToolBehavior.INTERRUPT

    if name in {
        "navigate_to",
        "navigate_location",
        "get_location_info",
        "nearby_search",
        "reverse_geocode",
        "get_walking_directions",
        "google_search",
    }:
        return ToolBehavior.WHEN_IDLE if is_user_speaking else ToolBehavior.INTERRUPT

    return ToolBehavior.WHEN_IDLE if is_user_speaking else ToolBehavior.INTERRUPT


def behavior_to_text(behavior: ToolBehavior | str) -> str:
    """Convert behavior enum/value into canonical uppercase text."""
    if isinstance(behavior, ToolBehavior):
        return behavior.value
    return str(behavior).strip().upper()
