"""SightLine function calling tools.

Tools available to the Orchestrator agent via Gemini Function Calling:
- navigate_to / get_location_info / nearby_search / reverse_geocode: Google Maps
- google_search: Grounding search
- identify_person: Face ID matching (SILENT behavior)
"""

from __future__ import annotations

from typing import Any

from tools.face_tools import (
    MAX_FACE_SAMPLES,
    MIN_FACE_SAMPLES,
    clear_face_library,
    delete_all_faces,
    delete_face,
    list_faces,
    load_face_library,
    register_face,
)
from tools.navigation import (
    NAVIGATION_FUNCTIONS,
    NAVIGATION_TOOL_DECLARATIONS,
    bearing_between,
    bearing_to_clock,
    format_clock_direction,
    get_location_info,
    get_walking_directions,
    navigate_to,
    nearby_search,
    reverse_geocode,
)
from tools.search import (
    SEARCH_FUNCTIONS,
    SEARCH_TOOL_DECLARATIONS,
    google_search,
)
from memory.memory_tools import MEMORY_FUNCTIONS
from tools.tool_behavior import ToolBehavior, behavior_to_text, resolve_tool_behavior


def identify_person(
    description: str,
    user_id: str = "",
    image_base64: str | None = None,
    behavior: ToolBehavior = ToolBehavior.SILENT,
) -> dict[str, Any]:
    """No-op stub — face recognition runs automatically from camera frames.

    The realtime frame matching pipeline is executed in ``server.py`` via
    ``agents.face_agent.identify_persons_in_frame``.  This function exists
    only to satisfy the function-calling contract; it should rarely be called.
    """
    return {
        "status": "no_op",
        "message": (
            "Face recognition runs automatically from camera frames. "
            "Results are injected into your context as [FACE ID] entries. "
            "Do not announce this to the user."
        ),
    }

# Face tool declarations for Gemini Live API function calling
FACE_TOOL_DECLARATIONS = [
    {
        "name": "identify_person",
        "description": (
            "Acknowledge that face recognition runs automatically in the background. "
            "Do NOT call this tool — face results are injected into your context "
            "automatically as [FACE ID] entries. If called, returns a no-op confirmation."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "Brief description of the person's appearance and position",
                },
            },
            "required": ["description"],
        },
    },
]

FACE_FUNCTIONS = {
    "identify_person": identify_person,
}

# Aggregate all tool declarations and function maps
ALL_TOOL_DECLARATIONS = (
    NAVIGATION_TOOL_DECLARATIONS
    + SEARCH_TOOL_DECLARATIONS
    + FACE_TOOL_DECLARATIONS
)

ALL_FUNCTIONS = {
    **NAVIGATION_FUNCTIONS,
    **SEARCH_FUNCTIONS,
    **FACE_FUNCTIONS,
    **MEMORY_FUNCTIONS,
}

__all__ = [
    # Navigation
    "navigate_to",
    "get_location_info",
    "nearby_search",
    "reverse_geocode",
    "get_walking_directions",
    "bearing_between",
    "bearing_to_clock",
    "format_clock_direction",
    "NAVIGATION_TOOL_DECLARATIONS",
    "NAVIGATION_FUNCTIONS",
    # Search
    "google_search",
    "SEARCH_TOOL_DECLARATIONS",
    "SEARCH_FUNCTIONS",
    # Face
    "register_face",
    "delete_face",
    "delete_all_faces",
    "clear_face_library",
    "list_faces",
    "load_face_library",
    "MIN_FACE_SAMPLES",
    "MAX_FACE_SAMPLES",
    "identify_person",
    "ToolBehavior",
    "resolve_tool_behavior",
    "FACE_TOOL_DECLARATIONS",
    "FACE_FUNCTIONS",
    # Memory
    "MEMORY_FUNCTIONS",
    # Aggregated
    "ALL_TOOL_DECLARATIONS",
    "ALL_FUNCTIONS",
]
