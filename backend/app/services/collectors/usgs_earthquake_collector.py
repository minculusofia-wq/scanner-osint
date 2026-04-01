import logging
from datetime import datetime

import httpx

from .base_collector import BaseCollector

logger = logging.getLogger(__name__)

# USGS Earthquake Hazards API — free, no key needed
# Docs: https://earthquake.usgs.gov/fdsnws/event/1/
USGS_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson"

# Strategic regions where earthquakes have geopolitical/market impact
STRATEGIC_ZONES = [
    {
        "name": "Iran/Middle East",
        "bbox": {"min_lat": 24, "max_lat": 40, "min_lon": 44, "max_lon": 64},
        "region": "middle_east",
        "boost": 0.2,
    },
    {
        "name": "Turkey/Aegean",
        "bbox": {"min_lat": 36, "max_lat": 42, "min_lon": 26, "max_lon": 45},
        "region": "europe",
        "boost": 0.15,
    },
    {
        "name": "Japan/Pacific",
        "bbox": {"min_lat": 30, "max_lat": 46, "min_lon": 128, "max_lon": 146},
        "region": "asia",
        "boost": 0.15,
    },
    {
        "name": "Taiwan",
        "bbox": {"min_lat": 21, "max_lat": 26, "min_lon": 119, "max_lon": 123},
        "region": "asia",
        "boost": 0.2,
    },
    {
        "name": "US West Coast",
        "bbox": {"min_lat": 32, "max_lat": 49, "min_lon": -125, "max_lon": -114},
        "region": "north_america",
        "boost": 0.1,
    },
    {
        "name": "Mediterranean",
        "bbox": {"min_lat": 34, "max_lat": 44, "min_lon": -6, "max_lon": 36},
        "region": "europe",
        "boost": 0.1,
    },
]


def _match_zone(lat: float, lon: float) -> dict | None:
    for zone in STRATEGIC_ZONES:
        bb = zone["bbox"]
        if bb["min_lat"] <= lat <= bb["max_lat"] and bb["min_lon"] <= lon <= bb["max_lon"]:
            return zone
    return None


class USGSEarthquakeCollector(BaseCollector):
    """Collects earthquake data from USGS — free API, no key needed."""

    SOURCE_NAME = "usgs_earthquake"

    async def collect(self, config: dict) -> list[dict]:
        items = []

        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.get(USGS_URL)
                resp.raise_for_status()
                data = resp.json()

            features = data.get("features", [])
            logger.info(f"USGS: fetched {len(features)} earthquakes (M2.5+ last 24h)")

            for feature in features:
                props = feature.get("properties", {})
                geom = feature.get("geometry", {})
                coords = geom.get("coordinates", [0, 0, 0])

                lon, lat, depth = coords[0], coords[1], coords[2] if len(coords) > 2 else 0
                magnitude = props.get("mag", 0)
                place = props.get("place", "Unknown location")
                time_ms = props.get("time")
                url = props.get("url", "")
                tsunami = props.get("tsunami", 0)
                felt = props.get("felt")  # number of "Did You Feel It?" reports
                alert = props.get("alert")  # green, yellow, orange, red
                sig = props.get("sig", 0)  # significance 0-1000

                if magnitude is None:
                    continue

                # Relevance based on magnitude
                if magnitude >= 7.0:
                    relevance = 1.0
                elif magnitude >= 6.0:
                    relevance = 0.9
                elif magnitude >= 5.0:
                    relevance = 0.75
                elif magnitude >= 4.0:
                    relevance = 0.55
                else:
                    relevance = 0.35

                # Boost if in strategic zone
                zone = _match_zone(lat, lon)
                if zone:
                    relevance = min(1.0, relevance + zone["boost"])
                    region = zone["region"]
                else:
                    region = ""

                # Tsunami warning boosts
                if tsunami:
                    relevance = min(1.0, relevance + 0.15)

                # Alert level boosts
                if alert == "red":
                    relevance = 1.0
                elif alert == "orange":
                    relevance = min(1.0, relevance + 0.1)

                # Skip low-significance quakes outside strategic zones
                if not zone and magnitude < 4.5:
                    continue

                # Parse timestamp
                published_at = None
                if time_ms:
                    try:
                        published_at = datetime.utcfromtimestamp(time_ms / 1000)
                    except (ValueError, OSError):
                        pass

                # Sentiment: earthquakes are inherently negative
                sentiment = -0.3 if magnitude < 5 else -0.6 if magnitude < 6 else -0.9

                tags = ["earthquake", f"M{magnitude:.1f}"]
                if tsunami:
                    tags.append("tsunami")
                if alert:
                    tags.append(f"alert_{alert}")
                if zone:
                    tags.append(zone["name"].lower().replace("/", "_").replace(" ", "_"))

                title = f"Earthquake M{magnitude:.1f} — {place}"
                summary = (
                    f"M{magnitude:.1f} earthquake at depth {depth:.0f}km near {place}. "
                    f"Significance: {sig}/1000."
                )
                if tsunami:
                    summary += " TSUNAMI WARNING ISSUED."
                if felt:
                    summary += f" Felt by {felt} people."
                if alert:
                    summary += f" PAGER alert: {alert.upper()}."

                items.append(self._make_item(
                    title=title,
                    summary=summary,
                    url=url,
                    category="natural_disaster",
                    region=region,
                    tags=tags,
                    raw_relevance=relevance,
                    sentiment_score=sentiment,
                    published_at=published_at,
                    source_id=feature.get("id", ""),
                ))

        except httpx.HTTPStatusError as e:
            logger.error(f"USGS HTTP error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"USGS collection error: {e}")

        logger.info(f"USGS: collected {len(items)} earthquake items")
        return items
