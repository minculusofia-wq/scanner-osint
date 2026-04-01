import logging
from datetime import datetime

import httpx

from .base_collector import BaseCollector

logger = logging.getLogger(__name__)

# NOAA Weather Alerts API — free, no key needed
# Docs: https://www.weather.gov/documentation/services-web-api
NOAA_ALERTS_URL = "https://api.weather.gov/alerts/active"

# Also monitor international severe weather via WMO
WMO_SEVERE_URL = "https://severeweather.wmo.int/v2/json/alerts.json"

# Categories that have geopolitical/market impact
IMPACTFUL_EVENT_TYPES = [
    "Tsunami Warning", "Tsunami Watch",
    "Hurricane Warning", "Hurricane Watch",
    "Typhoon Warning", "Typhoon Watch",
    "Extreme Wind Warning", "Storm Surge Warning",
    "Nuclear Power Plant Warning",
    "Radiological Hazard Warning",
    "Volcano Warning", "Volcanic Ash Advisory",
    "Earthquake Warning",
    "Fire Weather Watch", "Red Flag Warning",
    "Blizzard Warning", "Ice Storm Warning",
    "Flood Warning", "Flash Flood Warning",
    "Severe Thunderstorm Warning",
    "Tornado Warning",
]

# Strategic areas where weather disrupts markets/logistics
STRATEGIC_WEATHER_ZONES = {
    "Gulf of Mexico": {"region": "north_america", "impact": "oil_gas", "boost": 0.2},
    "Persian Gulf": {"region": "middle_east", "impact": "oil_gas", "boost": 0.2},
    "South China Sea": {"region": "asia", "impact": "shipping", "boost": 0.15},
    "Panama": {"region": "central_america", "impact": "shipping", "boost": 0.15},
    "Suez": {"region": "middle_east", "impact": "shipping", "boost": 0.15},
}


class NOAACollector(BaseCollector):
    """Collects severe weather alerts from NOAA — free, no API key."""

    SOURCE_NAME = "noaa_weather"

    async def collect(self, config: dict) -> list[dict]:
        items = []

        async with httpx.AsyncClient(
            timeout=20,
            headers={
                "User-Agent": "ScannerOSINT/1.0 (contact@scanner-osint.dev)",
                "Accept": "application/geo+json",
            },
        ) as client:
            try:
                resp = await client.get(NOAA_ALERTS_URL, params={"status": "actual"})
                resp.raise_for_status()
                data = resp.json()

                features = data.get("features", [])
                logger.info(f"NOAA: fetched {len(features)} active alerts")

                for feature in features:
                    props = feature.get("properties", {})
                    event = props.get("event", "")

                    # Only keep high-impact weather events
                    if not any(evt.lower() in event.lower() for evt in IMPACTFUL_EVENT_TYPES):
                        continue

                    headline = props.get("headline", "")
                    description = props.get("description", "")
                    severity = props.get("severity", "")  # Extreme, Severe, Moderate, Minor
                    urgency = props.get("urgency", "")  # Immediate, Expected, Future
                    certainty = props.get("certainty", "")
                    area_desc = props.get("areaDesc", "")
                    effective = props.get("effective", "")
                    sender = props.get("senderName", "")

                    # Relevance based on severity
                    if severity == "Extreme":
                        relevance = 0.95
                    elif severity == "Severe":
                        relevance = 0.8
                    elif severity == "Moderate":
                        relevance = 0.6
                    else:
                        relevance = 0.4

                    # Boost for tsunami/nuclear/volcano
                    event_lower = event.lower()
                    if "tsunami" in event_lower or "nuclear" in event_lower:
                        relevance = 1.0
                    elif "hurricane" in event_lower or "typhoon" in event_lower:
                        relevance = min(1.0, relevance + 0.1)
                    elif "volcano" in event_lower:
                        relevance = min(1.0, relevance + 0.1)

                    # Check if in strategic zone
                    area_lower = area_desc.lower()
                    region = "north_america"  # NOAA is US-focused
                    for zone_name, zone_info in STRATEGIC_WEATHER_ZONES.items():
                        if zone_name.lower() in area_lower:
                            region = zone_info["region"]
                            relevance = min(1.0, relevance + zone_info["boost"])
                            break

                    # Parse date
                    published_at = None
                    if effective:
                        try:
                            published_at = datetime.fromisoformat(effective.replace("Z", "+00:00")).replace(tzinfo=None)
                        except (ValueError, TypeError):
                            pass

                    # Sentiment
                    sentiment = -0.5 if severity in ("Extreme", "Severe") else -0.3

                    tags = ["weather", event.lower().replace(" ", "_")]
                    if "tsunami" in event_lower:
                        tags.append("tsunami")
                    if "hurricane" in event_lower or "typhoon" in event_lower:
                        tags.append("tropical_cyclone")

                    title = f"Weather Alert: {event} — {area_desc[:80]}"
                    summary = headline[:300] if headline else description[:300]

                    items.append(self._make_item(
                        title=title,
                        summary=summary,
                        url=f"https://alerts.weather.gov",
                        category="weather",
                        region=region,
                        tags=tags,
                        raw_relevance=relevance,
                        sentiment_score=sentiment,
                        published_at=published_at,
                        source_id=props.get("id", ""),
                    ))

            except httpx.HTTPStatusError as e:
                logger.error(f"NOAA HTTP error: {e.response.status_code}")
            except Exception as e:
                logger.error(f"NOAA collection error: {e}")

        logger.info(f"NOAA: collected {len(items)} weather alert items")
        return items
