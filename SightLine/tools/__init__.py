"""SightLine function calling tools.

Tools available to the Orchestrator agent via Gemini Function Calling:
- navigate_to / get_location_info / nearby_search / reverse_geocode: Google Maps
- google_search: Grounding search
- identify_person: Face ID matching (SILENT behavior)
"""

from tools.face_tools import (
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

# Face tool declarations for Gemini Live API function calling
FACE_TOOL_DECLARATIONS = [
    {
        "name": "identify_person",
        "description": (
            "Identify a person detected in the camera frame by matching their face "
            "against the user's face library. Behavior: SILENT — results are injected "
            "into context without interrupting dialogue. Only call this when you detect "
            "a face in the scene that might be someone the user knows."
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
    "identify_person": None,  # Handled directly in server.py via face_agent
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
    "list_faces",
    "load_face_library",
    "FACE_TOOL_DECLARATIONS",
    "FACE_FUNCTIONS",
    # Aggregated
    "ALL_TOOL_DECLARATIONS",
    "ALL_FUNCTIONS",
]
