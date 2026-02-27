"""Tests for SightLine navigation tools.

All Google Maps API calls are mocked — no real API key needed.
"""

from __future__ import annotations

import math
from unittest.mock import MagicMock, patch

import pytest

from tools.navigation import (
    NAVIGATION_FUNCTIONS,
    NAVIGATION_TOOL_DECLARATIONS,
    _haversine_distance,
    _maneuver_to_description,
    _strip_html,
    bearing_between,
    bearing_to_clock,
    format_clock_direction,
    get_location_info,
    get_walking_directions,
    navigate_to,
    nearby_search,
    reverse_geocode,
)


# ---------------------------------------------------------------------------
# Clock-position unit tests
# ---------------------------------------------------------------------------


class TestBearingBetween:
    """Test compass bearing calculations."""

    def test_due_north(self):
        # NYC to a point directly north
        bearing = bearing_between(40.0, -74.0, 41.0, -74.0)
        assert abs(bearing - 0) < 1  # ~0 degrees (north)

    def test_due_east(self):
        bearing = bearing_between(0.0, 0.0, 0.0, 1.0)
        assert abs(bearing - 90) < 1

    def test_due_south(self):
        bearing = bearing_between(41.0, -74.0, 40.0, -74.0)
        assert abs(bearing - 180) < 1

    def test_due_west(self):
        bearing = bearing_between(0.0, 1.0, 0.0, 0.0)
        assert abs(bearing - 270) < 1

    def test_same_point(self):
        bearing = bearing_between(40.0, -74.0, 40.0, -74.0)
        # Should be 0 (atan2(0,0) = 0)
        assert bearing == 0.0


class TestBearingToClock:
    """Test bearing-to-clock-position conversion."""

    def test_straight_ahead(self):
        # Target is at same bearing as user heading
        assert bearing_to_clock(90, 90) == 12

    def test_right_3_oclock(self):
        # Target 90 degrees to the right
        assert bearing_to_clock(180, 90) == 3

    def test_behind_6_oclock(self):
        # Target directly behind
        assert bearing_to_clock(270, 90) == 6

    def test_left_9_oclock(self):
        # Target 90 degrees to the left
        assert bearing_to_clock(0, 90) == 9

    def test_slight_right(self):
        # Target ~60 degrees right -> 2 o'clock
        assert bearing_to_clock(150, 90) == 2

    def test_slight_left(self):
        # Target ~60 degrees left -> 10 o'clock
        assert bearing_to_clock(30, 90) == 10

    def test_wrap_around(self):
        # User heading 350, target at 20 -> 30 degrees right -> 1 o'clock
        assert bearing_to_clock(20, 350) == 1

    def test_heading_zero_target_north(self):
        # Facing north, target north -> 12
        assert bearing_to_clock(0, 0) == 12

    def test_heading_zero_target_east(self):
        # Facing north, target east -> 3
        assert bearing_to_clock(90, 0) == 3


class TestFormatClockDirection:
    """Test spoken direction formatting."""

    def test_straight_ahead(self):
        result = format_clock_direction(12, 50)
        assert result == "straight ahead, 50 meters"

    def test_behind(self):
        result = format_clock_direction(6, 30)
        assert result == "behind you, 30 meters"

    def test_clock_position(self):
        result = format_clock_direction(2, 120)
        assert result == "at 2 o'clock, 120 meters"

    def test_kilometers(self):
        result = format_clock_direction(3, 1500)
        assert result == "at 3 o'clock, 1.5 kilometers"

    def test_rounding(self):
        result = format_clock_direction(9, 47.6)
        assert result == "at 9 o'clock, 48 meters"


# ---------------------------------------------------------------------------
# Helper unit tests
# ---------------------------------------------------------------------------


class TestStripHtml:
    """Test HTML tag stripping."""

    def test_simple_tags(self):
        assert _strip_html("Go <b>north</b> on Main St") == "Go north on Main St"

    def test_nested_tags(self):
        result = _strip_html("<div>Turn <b>left</b> onto <span>Oak Ave</span></div>")
        assert result == "Turn left onto Oak Ave"

    def test_no_tags(self):
        assert _strip_html("Walk 50 meters") == "Walk 50 meters"


class TestManeuverToDescription:
    """Test maneuver string conversion."""

    def test_turn_left(self):
        assert _maneuver_to_description("turn-left") == "turn to 9 o'clock"

    def test_turn_right(self):
        assert _maneuver_to_description("turn-right") == "turn to 3 o'clock"

    def test_slight_left(self):
        assert _maneuver_to_description("turn-slight-left") == "bear to 10 o'clock"

    def test_straight(self):
        assert _maneuver_to_description("straight") == "continue straight ahead"

    def test_unknown(self):
        assert _maneuver_to_description("ferry") == ""

    def test_none(self):
        assert _maneuver_to_description(None) == ""


class TestHaversineDistance:
    """Test haversine distance calculation."""

    def test_same_point(self):
        assert _haversine_distance(40.0, -74.0, 40.0, -74.0) == 0.0

    def test_known_distance(self):
        # NYC to LA ~ 3,940 km
        dist = _haversine_distance(40.7128, -74.0060, 34.0522, -118.2437)
        assert 3_900_000 < dist < 4_000_000


# ---------------------------------------------------------------------------
# API-mocked integration tests
# ---------------------------------------------------------------------------

MOCK_DIRECTIONS_RESPONSE = [
    {
        "legs": [
            {
                "start_address": "123 Main St",
                "end_address": "456 Oak Ave",
                "start_location": {"lat": 37.7749, "lng": -122.4194},
                "end_location": {"lat": 37.7849, "lng": -122.4094},
                "distance": {"text": "1.2 km", "value": 1200},
                "duration": {"text": "15 mins", "value": 900},
                "steps": [
                    {
                        "html_instructions": "Head <b>north</b> on Main St",
                        "distance": {"text": "200 m", "value": 200},
                        "duration": {"text": "3 mins", "value": 180},
                        "start_location": {"lat": 37.7749, "lng": -122.4194},
                        "end_location": {"lat": 37.7769, "lng": -122.4194},
                        "maneuver": "straight",
                    },
                    {
                        "html_instructions": "Turn <b>right</b> onto Oak Ave",
                        "distance": {"text": "1.0 km", "value": 1000},
                        "duration": {"text": "12 mins", "value": 720},
                        "start_location": {"lat": 37.7769, "lng": -122.4194},
                        "end_location": {"lat": 37.7849, "lng": -122.4094},
                        "maneuver": "turn-right",
                    },
                ],
            }
        ]
    }
]

MOCK_GEOCODE_RESPONSE = [
    {"formatted_address": "123 Main St, San Francisco, CA 94105"}
]

MOCK_NEARBY_RESPONSE = {
    "results": [
        {
            "name": "Coffee Bean",
            "geometry": {"location": {"lat": 37.7751, "lng": -122.4190}},
            "types": ["cafe", "food"],
            "rating": 4.2,
            "vicinity": "100 Main St",
            "opening_hours": {"open_now": True},
        },
        {
            "name": "City Pharmacy",
            "geometry": {"location": {"lat": 37.7755, "lng": -122.4185}},
            "types": ["pharmacy", "health"],
            "rating": 3.8,
            "vicinity": "110 Main St",
            "opening_hours": {"open_now": False},
        },
    ]
}


@pytest.fixture
def mock_gmaps():
    """Provide a mocked Google Maps client."""
    with patch("tools.navigation._get_client") as mock_get:
        client = MagicMock()
        mock_get.return_value = client
        yield client


class TestNavigateTo:
    """Test navigate_to with mocked API."""

    def test_success(self, mock_gmaps):
        mock_gmaps.directions.return_value = MOCK_DIRECTIONS_RESPONSE

        result = navigate_to(
            destination="456 Oak Ave",
            origin_lat=37.7749,
            origin_lng=-122.4194,
            user_heading=0.0,
        )

        assert result["success"] is True
        assert result["destination"] == "456 Oak Ave"
        assert result["total_distance"] == "1.2 km"
        assert result["total_duration"] == "15 mins"
        assert len(result["steps"]) == 2
        assert "clock_direction" in result["steps"][0]
        assert "accessibility_note" in result

    def test_no_route_found(self, mock_gmaps):
        mock_gmaps.directions.return_value = []

        result = navigate_to(
            destination="Nonexistent Place",
            origin_lat=37.7749,
            origin_lng=-122.4194,
        )

        assert result["success"] is False
        assert "No walking route" in result["error"]

    def test_api_error(self, mock_gmaps):
        mock_gmaps.directions.side_effect = Exception("API quota exceeded")

        result = navigate_to(
            destination="456 Oak Ave",
            origin_lat=37.7749,
            origin_lng=-122.4194,
        )

        assert result["success"] is False
        assert "API quota exceeded" in result["error"]

    def test_step_has_maneuver_direction(self, mock_gmaps):
        mock_gmaps.directions.return_value = MOCK_DIRECTIONS_RESPONSE

        result = navigate_to(
            destination="456 Oak Ave",
            origin_lat=37.7749,
            origin_lng=-122.4194,
            user_heading=0.0,
        )

        # Second step has turn-right maneuver
        step2 = result["steps"][1]
        assert step2["direction"] == "turn to 3 o'clock"


class TestGetLocationInfo:
    """Test get_location_info with mocked API."""

    def test_success(self, mock_gmaps):
        mock_gmaps.reverse_geocode.return_value = MOCK_GEOCODE_RESPONSE
        mock_gmaps.places_nearby.return_value = MOCK_NEARBY_RESPONSE

        result = get_location_info(37.7749, -122.4194)

        assert result["success"] is True
        assert "San Francisco" in result["address"]
        assert len(result["nearby_places"]) == 2
        assert result["nearby_places"][0]["name"] == "Coffee Bean"

    def test_no_geocode_results(self, mock_gmaps):
        mock_gmaps.reverse_geocode.return_value = []
        mock_gmaps.places_nearby.return_value = {"results": []}

        result = get_location_info(0.0, 0.0)

        assert result["success"] is True
        assert result["address"] == "Unknown location"

    def test_api_error(self, mock_gmaps):
        mock_gmaps.reverse_geocode.side_effect = Exception("Network error")

        result = get_location_info(37.7749, -122.4194)

        assert result["success"] is False
        assert "Network error" in result["error"]


class TestNearbySearch:
    """Test nearby_search with mocked API."""

    def test_success(self, mock_gmaps):
        mock_gmaps.places_nearby.return_value = MOCK_NEARBY_RESPONSE

        result = nearby_search(37.7749, -122.4194, radius=200, types=["cafe"])

        assert result["success"] is True
        assert result["count"] == 2
        # Results should be sorted by distance
        places = result["places"]
        assert places[0]["distance_meters"] <= places[1]["distance_meters"]

    def test_with_keyword(self, mock_gmaps):
        mock_gmaps.places_nearby.return_value = MOCK_NEARBY_RESPONSE

        result = nearby_search(37.7749, -122.4194, keyword="coffee")

        assert result["success"] is True
        assert result["query"] == "coffee"
        mock_gmaps.places_nearby.assert_called_once()
        call_kwargs = mock_gmaps.places_nearby.call_args[1]
        assert call_kwargs["keyword"] == "coffee"

    def test_empty_results(self, mock_gmaps):
        mock_gmaps.places_nearby.return_value = {"results": []}

        result = nearby_search(37.7749, -122.4194)

        assert result["success"] is True
        assert result["count"] == 0
        assert result["places"] == []

    def test_api_error(self, mock_gmaps):
        mock_gmaps.places_nearby.side_effect = Exception("Quota exceeded")

        result = nearby_search(37.7749, -122.4194)

        assert result["success"] is False


class TestReverseGeocode:
    """Test reverse_geocode with mocked API."""

    def test_success(self, mock_gmaps):
        mock_gmaps.reverse_geocode.return_value = MOCK_GEOCODE_RESPONSE

        result = reverse_geocode(37.7749, -122.4194)

        assert result["success"] is True
        assert "San Francisco" in result["address"]

    def test_no_results(self, mock_gmaps):
        mock_gmaps.reverse_geocode.return_value = []

        result = reverse_geocode(0.0, 0.0)

        assert result["success"] is False
        assert "No address" in result["error"]

    def test_api_error(self, mock_gmaps):
        mock_gmaps.reverse_geocode.side_effect = Exception("Network error")

        result = reverse_geocode(37.7749, -122.4194)

        assert result["success"] is False
        assert "Could not determine" in result["error"]


class TestGetWalkingDirections:
    """Test get_walking_directions with mocked API."""

    def test_success(self, mock_gmaps):
        mock_gmaps.directions.return_value = MOCK_DIRECTIONS_RESPONSE

        result = get_walking_directions("123 Main St", "456 Oak Ave")

        assert result["success"] is True
        assert result["total_distance"] == "1.2 km"
        assert len(result["steps"]) == 2
        # Check maneuver descriptions
        assert result["steps"][1]["direction"] == "turn to 3 o'clock"

    def test_no_route(self, mock_gmaps):
        mock_gmaps.directions.return_value = []

        result = get_walking_directions("Mars", "Jupiter")

        assert result["success"] is False

    def test_api_error(self, mock_gmaps):
        mock_gmaps.directions.side_effect = Exception("Timeout")

        result = get_walking_directions("A", "B")

        assert result["success"] is False


# ---------------------------------------------------------------------------
# Declaration / registration tests
# ---------------------------------------------------------------------------


class TestDeclarations:
    """Verify ADK tool declarations are well-formed."""

    def test_all_functions_have_declarations(self):
        declared_names = {d["name"] for d in NAVIGATION_TOOL_DECLARATIONS}
        func_names = set(NAVIGATION_FUNCTIONS.keys())
        assert declared_names == func_names

    def test_declarations_have_required_fields(self):
        for decl in NAVIGATION_TOOL_DECLARATIONS:
            assert "name" in decl
            assert "description" in decl
            assert "parameters" in decl
            assert decl["parameters"]["type"] == "object"

    def test_functions_are_callable(self):
        for name, func in NAVIGATION_FUNCTIONS.items():
            assert callable(func), f"{name} is not callable"
