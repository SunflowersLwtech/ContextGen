# Location APIs & Navigation Research for SightLine

> **Research Date**: 2026-02-21
> **Source**: Parallel research agent - Google Maps and Navigation APIs

---

## 1. Google Maps Platform APIs

### 1.1 Places API (New) -- Nearby Search

```python
def nearby_search(lat, lng, radius=200, place_types=None, max_results=10):
    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.types,places.accessibilityOptions"
    }
    body = {
        "includedTypes": place_types or ["restaurant", "cafe", "pharmacy", "transit_station"],
        "maxResultCount": max_results,
        "locationRestriction": {"circle": {"center": {"latitude": lat, "longitude": lng}, "radius": radius}}
    }
    return requests.post(url, headers=headers, json=body).json()
```

### 1.2 Geocoding API

```python
def reverse_geocode(lat, lng):
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"latlng": f"{lat},{lng}", "key": API_KEY, "result_type": "street_address|point_of_interest"}
    data = requests.get(url, params=params).json()
    if data["status"] == "OK":
        return data["results"][0]["formatted_address"]
```

### 1.3 Routes API (Walking Directions)

```python
def get_walking_directions(origin_lat, origin_lng, dest_lat, dest_lng):
    url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    headers = {"X-Goog-Api-Key": API_KEY, "X-Goog-FieldMask": "routes.legs.steps.navigationInstruction,routes.legs.steps.distanceMeters"}
    body = {
        "origin": {"location": {"latLng": {"latitude": origin_lat, "longitude": origin_lng}}},
        "destination": {"location": {"latLng": {"latitude": dest_lat, "longitude": dest_lng}}},
        "travelMode": "WALK"
    }
    return requests.post(url, headers=headers, json=body).json()
```

### 1.4 Pricing (Post-March 2025)

| API | Free Tier | Per 1K requests |
|-----|-----------|----------------|
| Places Nearby (Basic) | 10,000/month | ~$32 |
| Place Details (Basic) | 10,000/month | ~$17 |
| Geocoding | 10,000/month | $5 |
| Routes | 10,000/month | ~$5 |
| Street View Metadata | Unlimited | **FREE** |

**Hackathon cost: ~$0-$5** (well within free tiers)

---

## 2. Accessibility Features

- `accessibilityOptions` field in Places API: wheelchair entrance, parking, restroom, seating
- No dedicated "wheelchair-accessible walking route" in API
- Indoor mapping limited to consumer app (no standalone API)

---

## 3. Geolocation in PWA

| Source | Accuracy |
|--------|----------|
| GPS | 3-10 meters (outdoor) |
| WiFi | 15-40 meters |
| Cell tower | 100-300 meters |

- `watchPosition` for continuous tracking
- **Background GPS stops when PWA minimized** -- use Wake Lock
- Indoor/outdoor detection: use **Gemini Vision** analysis (more reliable than GPS heuristics)

### Compass Heading

```javascript
// DeviceOrientationEvent (requires permission on iOS)
window.addEventListener('deviceorientationabsolute', (event) => {
    heading = (360 - event.alpha) % 360;
});
// Safari fallback: event.webkitCompassHeading
```

---

## 4. Clock-Position Directional System

```python
import math

def calculate_bearing(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360) % 360

def bearing_to_clock(bearing, user_heading):
    relative = (bearing - user_heading + 360) % 360
    clock = round(relative / 30) % 12
    if clock == 0: clock = 12
    return clock  # "Starbucks at 2 o'clock"

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
```

---

## 5. Gemini Integration

### Option A: Gemini Maps Grounding (Native)

```python
response = client.models.generate_content(
    model="gemini-3-flash-preview",  # Gemini 3 Flash (FREE during preview)
    contents=prompt,
    config=types.GenerateContentConfig(
        tools=[types.Tool(google_maps=types.GoogleMaps())],
        tool_config=types.ToolConfig(
            retrieval_config=types.RetrievalConfig(
                lat_lng=types.LatLng(latitude=lat, longitude=lng)
            )
        ),
    ),
)
# $25/1K grounded prompts
```

### Option B: Function Calling (RECOMMENDED for navigation)

Direct Maps API calls give control over clock-position formatting, distance calculations, and accessibility fields.

### Hybrid Strategy

- **Function Calling**: Navigation, distances, directions (we control formatting)
- **Maps Grounding**: Exploratory queries ("tell me about this area")
- **OpenStreetMap**: Accessibility data (tactile paving, audible signals)

---

## 6. OpenStreetMap for Accessibility

```python
def overpass_accessibility_features(lat, lng, radius=100):
    query = f"""[out:json][timeout:10];(
        node["kerb"](around:{radius},{lat},{lng});
        node["tactile_paving"](around:{radius},{lat},{lng});
        node["traffic_signals:sound"](around:{radius},{lat},{lng});
        node["crossing"](around:{radius},{lat},{lng});
    );out body;"""
    return requests.post("https://overpass-api.de/api/interpreter", data={"data": query}).json()
```

| Data | Google Maps | OpenStreetMap |
|------|------------|---------------|
| Business hours | Excellent | Inconsistent |
| Reviews | Best | None |
| **Tactile paving** | None | **Rich** |
| **Audible signals** | None | **Rich** |
| **Kerb types** | None | **Rich** |
| Price | $5-32/1K | **Free** |

---

## Sources

- [Google Maps Platform Pricing](https://developers.google.com/maps/billing-and-pricing/pricing)
- [Places API (New)](https://developers.google.com/maps/documentation/places/web-service)
- [Gemini Maps Grounding](https://ai.google.dev/gemini-api/docs/maps-grounding)
- [OpenStreetMap Overpass](https://wiki.openstreetmap.org/wiki/Overpass_API)
- [DeviceOrientationEvent (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/DeviceOrientationEvent)
