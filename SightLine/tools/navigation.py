"""SightLine navigation tools using Google Maps APIs.

Provides walking directions, reverse geocoding, nearby search, and
location info — all formatted for blind/low-vision users with
clock-position directional cues.

Clock-position system: Instead of "turn right", we say
"destination at 2 o'clock, 50 meters". This converts absolute
compass bearings to positions relative to the user's current heading.
"""

from __future__ import annotations

import logging
import math
import os
from typing import Any

import googlemaps

logger = logging.getLogger("sightline.tools.navigation")

# ---------------------------------------------------------------------------
# Client singleton
# ---------------------------------------------------------------------------

_client: googlemaps.Client | None = None


def _get_client() -> googlemaps.Client:
    """Return a lazily-initialised Google Maps client."""
    global _client
    if _client is None:
        api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
        if not api_key:
            raise RuntimeError("GOOGLE_MAPS_API_KEY environment variable not set")
        _client = googlemaps.Client(key=api_key)
    return _client


# ---------------------------------------------------------------------------
# Clock-position helpers
# ---------------------------------------------------------------------------


def bearing_between(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Compute initial compass bearing (0-360) from point 1 to point 2."""
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    d_lng = lng2 - lng1
    x = math.sin(d_lng) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(d_lng)
    bearing = math.degrees(math.atan2(x, y))
    return bearing % 360


def bearing_to_clock(absolute_bearing: float, user_heading: float) -> int:
    """Convert an absolute bearing to a clock position (1-12).

    Args:
        absolute_bearing: Compass bearing to the target (0-360, 0=N).
        user_heading: User's current compass heading (0-360, 0=N).

    Returns:
        Clock position 1-12 (12 = straight ahead, 6 = behind).
    """
    relative = (absolute_bearing - user_heading) % 360
    # Each clock position spans 30 degrees, with 12 o'clock centered at 0.
    clock = round(relative / 30) % 12
    return clock if clock != 0 else 12


def format_clock_direction(clock: int, distance_m: float) -> str:
    """Format a clock position and distance into a spoken direction.

    Examples:
        "straight ahead, 50 meters"
        "at 2 o'clock, 120 meters"
        "behind you, 30 meters"
    """
    if distance_m >= 1000:
        dist_str = f"{distance_m / 1000:.1f} kilometers"
    else:
        dist_str = f"{int(round(distance_m))} meters"

    if clock == 12:
        return f"straight ahead, {dist_str}"
    if clock == 6:
        return f"behind you, {dist_str}"
    return f"at {clock} o'clock, {dist_str}"


def _extract_distance_meters(step: dict) -> float:
    """Extract distance in meters from a directions API step."""
    return step.get("distance", {}).get("value", 0)


def _maneuver_to_description(maneuver: str | None) -> str:
    """Convert a Google Maps maneuver string to accessible language."""
    mapping = {
        "turn-left": "turn to 9 o'clock",
        "turn-right": "turn to 3 o'clock",
        "turn-slight-left": "bear to 10 o'clock",
        "turn-slight-right": "bear to 2 o'clock",
        "turn-sharp-left": "turn to 8 o'clock",
        "turn-sharp-right": "turn to 4 o'clock",
        "uturn-left": "make a U-turn to the left",
        "uturn-right": "make a U-turn to the right",
        "straight": "continue straight ahead",
        "roundabout-left": "take the roundabout to the left",
        "roundabout-right": "take the roundabout to the right",
    }
    if maneuver and maneuver in mapping:
        return mapping[maneuver]
    return ""


def _strip_html(text: str) -> str:
    """Remove HTML tags from Google Maps instruction text."""
    import re
    clean = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", clean).strip()


# ---------------------------------------------------------------------------
# Public tool functions
# ---------------------------------------------------------------------------


def navigate_to(
    destination: str,
    origin_lat: float,
    origin_lng: float,
    user_heading: float = 0.0,
) -> dict[str, Any]:
    """Get step-by-step walking directions to a destination.

    Uses clock-position format for directional cues.

    Args:
        destination: Place name or address to navigate to.
        origin_lat: User's current latitude.
        origin_lng: User's current longitude.
        user_heading: User's current compass heading (0-360, 0=N).

    Returns:
        Dict with route summary and accessible step-by-step directions.
    """
    try:
        client = _get_client()
        result = client.directions(
            origin=(origin_lat, origin_lng),
            destination=destination,
            mode="walking",
        )

        if not result:
            return {
                "success": False,
                "error": "No walking route found to that destination.",
            }

        leg = result[0]["legs"][0]
        steps = leg["steps"]

        # Compute clock position to destination
        dest_lat = leg["end_location"]["lat"]
        dest_lng = leg["end_location"]["lng"]
        dest_bearing = bearing_between(origin_lat, origin_lng, dest_lat, dest_lng)
        dest_clock = bearing_to_clock(dest_bearing, user_heading)
        total_distance = leg["distance"]["text"]
        total_duration = leg["duration"]["text"]

        accessible_steps = []
        for i, step in enumerate(steps, 1):
            instruction = _strip_html(step.get("html_instructions", ""))
            distance = step["distance"]["text"]
            maneuver = step.get("maneuver")
            maneuver_desc = _maneuver_to_description(maneuver)

            step_info: dict[str, Any] = {
                "step": i,
                "instruction": instruction,
                "distance": distance,
            }
            if maneuver_desc:
                step_info["direction"] = maneuver_desc

            # Clock position for the start of each step
            step_lat = step["start_location"]["lat"]
            step_lng = step["start_location"]["lng"]
            end_lat = step["end_location"]["lat"]
            end_lng = step["end_location"]["lng"]
            step_bearing = bearing_between(step_lat, step_lng, end_lat, end_lng)
            step_dist_m = _extract_distance_meters(step)
            step_clock = bearing_to_clock(step_bearing, user_heading)
            step_info["clock_direction"] = format_clock_direction(step_clock, step_dist_m)

            accessible_steps.append(step_info)

        return {
            "success": True,
            "destination": leg["end_address"],
            "total_distance": total_distance,
            "total_duration": total_duration,
            "destination_direction": format_clock_direction(dest_clock, leg["distance"]["value"]),
            "steps": accessible_steps,
            "accessibility_note": (
                "Walking route. Watch for crosswalks and intersections. "
                "Listen for traffic signals at crossings."
            ),
        }

    except Exception as e:
        logger.exception("navigate_to failed: %s", e)
        return {
            "success": False,
            "error": f"Navigation request failed: {e}",
        }


def get_location_info(lat: float, lng: float) -> dict[str, Any]:
    """Get information about the user's current location.

    Combines reverse geocoding with nearby places of interest.

    Args:
        lat: Latitude.
        lng: Longitude.

    Returns:
        Dict with address and nearby points of interest.
    """
    try:
        client = _get_client()

        # Reverse geocode
        geocode_results = client.reverse_geocode((lat, lng))
        address = "Unknown location"
        if geocode_results:
            address = geocode_results[0].get("formatted_address", "Unknown location")

        # Nearby POIs
        nearby = client.places_nearby(
            location=(lat, lng),
            radius=100,
            type="point_of_interest",
        )

        pois = []
        for place in nearby.get("results", [])[:5]:
            poi_lat = place["geometry"]["location"]["lat"]
            poi_lng = place["geometry"]["location"]["lng"]
            dist = _haversine_distance(lat, lng, poi_lat, poi_lng)
            pois.append({
                "name": place.get("name", "Unknown"),
                "types": place.get("types", []),
                "distance_meters": round(dist),
                "open_now": place.get("opening_hours", {}).get("open_now"),
            })

        return {
            "success": True,
            "address": address,
            "nearby_places": pois,
        }

    except Exception as e:
        logger.exception("get_location_info failed: %s", e)
        return {
            "success": False,
            "error": f"Could not get location info: {e}",
        }


def nearby_search(
    lat: float,
    lng: float,
    radius: int = 200,
    types: list[str] | None = None,
    keyword: str | None = None,
) -> dict[str, Any]:
    """Search for nearby places matching given criteria.

    Args:
        lat: Latitude.
        lng: Longitude.
        radius: Search radius in meters (default 200).
        types: Place types to filter by (e.g. ["restaurant", "cafe"]).
        keyword: Optional keyword to search for.

    Returns:
        Dict with list of matching places and their distances.
    """
    try:
        client = _get_client()

        kwargs: dict[str, Any] = {
            "location": (lat, lng),
            "radius": radius,
        }
        if types:
            kwargs["type"] = types[0]  # API accepts single type
        if keyword:
            kwargs["keyword"] = keyword

        results = client.places_nearby(**kwargs)

        places = []
        for place in results.get("results", [])[:10]:
            p_lat = place["geometry"]["location"]["lat"]
            p_lng = place["geometry"]["location"]["lng"]
            dist = _haversine_distance(lat, lng, p_lat, p_lng)
            places.append({
                "name": place.get("name", "Unknown"),
                "address": place.get("vicinity", ""),
                "types": place.get("types", []),
                "rating": place.get("rating"),
                "distance_meters": round(dist),
                "open_now": place.get("opening_hours", {}).get("open_now"),
            })

        # Sort by distance
        places.sort(key=lambda p: p["distance_meters"])

        return {
            "success": True,
            "query": keyword or (types[0] if types else "nearby places"),
            "count": len(places),
            "places": places,
        }

    except Exception as e:
        logger.exception("nearby_search failed: %s", e)
        return {
            "success": False,
            "error": f"Nearby search failed: {e}",
        }


def reverse_geocode(lat: float, lng: float) -> str:
    """Get a human-readable address from coordinates.

    Args:
        lat: Latitude.
        lng: Longitude.

    Returns:
        Formatted address string, or error message.
    """
    try:
        client = _get_client()
        results = client.reverse_geocode((lat, lng))
        if results:
            return results[0].get("formatted_address", "Unknown location")
        return "No address found for this location."
    except Exception as e:
        logger.exception("reverse_geocode failed: %s", e)
        return f"Could not determine address: {e}"


def get_walking_directions(origin: str, destination: str) -> dict[str, Any]:
    """Get text-based walking directions between two addresses.

    For use when GPS coordinates are not available — uses
    address/place names instead.

    Args:
        origin: Starting address or place name.
        destination: Destination address or place name.

    Returns:
        Dict with walking directions summary and steps.
    """
    try:
        client = _get_client()
        result = client.directions(
            origin=origin,
            destination=destination,
            mode="walking",
        )

        if not result:
            return {
                "success": False,
                "error": "No walking route found between those locations.",
            }

        leg = result[0]["legs"][0]
        steps = []
        for i, step in enumerate(leg["steps"], 1):
            instruction = _strip_html(step.get("html_instructions", ""))
            maneuver = step.get("maneuver")
            maneuver_desc = _maneuver_to_description(maneuver)
            step_info: dict[str, Any] = {
                "step": i,
                "instruction": instruction,
                "distance": step["distance"]["text"],
                "duration": step["duration"]["text"],
            }
            if maneuver_desc:
                step_info["direction"] = maneuver_desc
            steps.append(step_info)

        return {
            "success": True,
            "origin": leg["start_address"],
            "destination": leg["end_address"],
            "total_distance": leg["distance"]["text"],
            "total_duration": leg["duration"]["text"],
            "steps": steps,
        }

    except Exception as e:
        logger.exception("get_walking_directions failed: %s", e)
        return {
            "success": False,
            "error": f"Could not get directions: {e}",
        }


# ---------------------------------------------------------------------------
# Haversine helper
# ---------------------------------------------------------------------------


def _haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Compute distance in meters between two GPS points."""
    R = 6_371_000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------------------------------------------
# ADK FunctionDeclaration wrappers for Gemini Live API
# ---------------------------------------------------------------------------

NAVIGATION_TOOL_DECLARATIONS = [
    {
        "name": "navigate_to",
        "description": (
            "Get step-by-step walking directions to a destination using clock-position "
            "directional cues (e.g. 'at 2 o'clock, 50 meters'). Always use this when "
            "the user asks how to get somewhere."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "destination": {
                    "type": "string",
                    "description": "Place name or address to navigate to",
                },
                "origin_lat": {
                    "type": "number",
                    "description": "User's current latitude",
                },
                "origin_lng": {
                    "type": "number",
                    "description": "User's current longitude",
                },
                "user_heading": {
                    "type": "number",
                    "description": "User's current compass heading (0-360, 0=North)",
                },
            },
            "required": ["destination", "origin_lat", "origin_lng"],
        },
    },
    {
        "name": "get_location_info",
        "description": (
            "Get information about the user's current location including address and "
            "nearby points of interest. Use when the user asks 'where am I?' or wants "
            "to know what's around them."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "lat": {
                    "type": "number",
                    "description": "Latitude",
                },
                "lng": {
                    "type": "number",
                    "description": "Longitude",
                },
            },
            "required": ["lat", "lng"],
        },
    },
    {
        "name": "nearby_search",
        "description": (
            "Search for nearby places like restaurants, cafes, pharmacies, bus stops, etc. "
            "Use when the user asks to find a specific type of place nearby."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "lat": {
                    "type": "number",
                    "description": "Latitude",
                },
                "lng": {
                    "type": "number",
                    "description": "Longitude",
                },
                "radius": {
                    "type": "integer",
                    "description": "Search radius in meters (default 200)",
                },
                "types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Place types to filter (e.g. ['restaurant', 'cafe'])",
                },
                "keyword": {
                    "type": "string",
                    "description": "Optional keyword to search for",
                },
            },
            "required": ["lat", "lng"],
        },
    },
    {
        "name": "reverse_geocode",
        "description": (
            "Get a human-readable address from GPS coordinates. "
            "Use when you need to describe the user's location."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "lat": {
                    "type": "number",
                    "description": "Latitude",
                },
                "lng": {
                    "type": "number",
                    "description": "Longitude",
                },
            },
            "required": ["lat", "lng"],
        },
    },
    {
        "name": "get_walking_directions",
        "description": (
            "Get walking directions between two named locations (addresses or place names). "
            "Use when GPS coordinates are not available."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "origin": {
                    "type": "string",
                    "description": "Starting address or place name",
                },
                "destination": {
                    "type": "string",
                    "description": "Destination address or place name",
                },
            },
            "required": ["origin", "destination"],
        },
    },
]

# Map function names to callables for the tool dispatcher
NAVIGATION_FUNCTIONS = {
    "navigate_to": navigate_to,
    "get_location_info": get_location_info,
    "nearby_search": nearby_search,
    "reverse_geocode": reverse_geocode,
    "get_walking_directions": get_walking_directions,
}
