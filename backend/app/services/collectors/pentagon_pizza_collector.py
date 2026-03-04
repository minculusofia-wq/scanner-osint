"""Pentagon Pizza Index Collector.

Monitors activity levels at restaurants near key US government buildings
(Pentagon, CIA Langley, White House) using Google Maps Popular Times.

When late-night busyness spikes above baseline, it's a behavioral OSINT
signal that something may be happening (the "Pizza Meter" indicator).

Uses a free scraping approach via Google search results.
"""

import hashlib
import json
import logging
import statistics
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

# Target locations: pizza/fast-food near government buildings
# Each entry: (name, place_id_or_query, lat, lon, zone)
MONITORED_LOCATIONS = [
    # Pentagon area (Arlington, VA)
    ("Dominos Pentagon City", "Domino's Pizza Arlington Pentagon", 38.8631, -77.0596, "pentagon"),
    ("Pizza Hut Pentagon", "Pizza Hut Arlington VA Pentagon", 38.8619, -77.0528, "pentagon"),
    ("Papa Johns Pentagon", "Papa John's Pentagon City Arlington", 38.8655, -77.0610, "pentagon"),
    # CIA / Langley area (McLean, VA)
    ("Dominos McLean", "Domino's Pizza McLean VA", 38.9342, -77.1773, "cia"),
    ("Pizza Hut McLean", "Pizza Hut McLean VA", 38.9285, -77.1792, "cia"),
    # White House / Downtown DC
    ("Dominos Downtown DC", "Domino's Pizza Washington DC downtown", 38.9012, -77.0320, "white_house"),
    ("Pizza Hut DC", "Pizza Hut Washington DC", 38.8970, -77.0264, "white_house"),
    # NSA / Fort Meade area
    ("Dominos Fort Meade", "Domino's Pizza Fort Meade MD", 39.1085, -76.7706, "nsa"),
    # State Department area (Foggy Bottom)
    ("Dominos Foggy Bottom", "Domino's Pizza Foggy Bottom DC", 38.8951, -77.0480, "state_dept"),
]

# Baseline busy levels by hour (0-23) and day type (weekday vs weekend)
# These are typical Google Popular Times percentages
# Source: aggregated from Google Maps data for DC pizza restaurants
BASELINE_WEEKDAY = {
    0: 5, 1: 3, 2: 2, 3: 1, 4: 1, 5: 2, 6: 3, 7: 5,
    8: 10, 9: 15, 10: 20, 11: 40, 12: 65, 13: 60, 14: 45,
    15: 35, 16: 40, 17: 55, 18: 70, 19: 75, 20: 65, 21: 50,
    22: 30, 23: 15,
}
BASELINE_WEEKEND = {
    0: 8, 1: 5, 2: 3, 3: 2, 4: 1, 5: 1, 6: 2, 7: 3,
    8: 5, 9: 10, 10: 15, 11: 30, 12: 55, 13: 60, 14: 50,
    15: 45, 16: 50, 17: 60, 18: 75, 19: 80, 20: 70, 21: 55,
    22: 35, 23: 20,
}

# Standard deviations by hour (rough estimates)
BASELINE_STD = {
    0: 8, 1: 6, 2: 5, 3: 4, 4: 4, 5: 5, 6: 6, 7: 8,
    8: 10, 9: 12, 10: 15, 11: 18, 12: 15, 13: 15, 14: 14,
    15: 13, 16: 14, 17: 15, 18: 15, 19: 14, 20: 14, 21: 15,
    22: 12, 23: 10,
}

# Night hours get higher weight (late-night activity is more suspicious)
NIGHT_HOURS = set(range(22, 24)) | set(range(0, 6))

# Z-score thresholds
Z_THRESHOLD_ALERT = 2.0  # Significant anomaly
Z_THRESHOLD_CRITICAL = 3.0  # Very significant


class PentagonPizzaCollector:
    """Collects Pentagon Pizza Index busyness data."""

    def __init__(self):
        self._http = httpx.AsyncClient(timeout=20, follow_redirects=True)

    async def collect(self, config: dict) -> list[dict]:
        """Collect busyness data for all monitored locations."""
        now = datetime.utcnow()
        current_hour = now.hour
        is_weekend = now.weekday() >= 5

        baseline = BASELINE_WEEKEND if is_weekend else BASELINE_WEEKDAY
        expected = baseline.get(current_hour, 20)
        std = BASELINE_STD.get(current_hour, 10)

        # Collect busyness from all locations
        results = []
        zone_scores: dict[str, list[float]] = {}

        for name, query, lat, lon, zone in MONITORED_LOCATIONS:
            try:
                busyness = await self._get_busyness(query)
                if busyness is None:
                    continue

                # Calculate Z-score
                z_score = (busyness - expected) / max(std, 1)

                zone_scores.setdefault(zone, []).append(z_score)

                logger.debug(
                    f"PentagonPizza: {name} busyness={busyness}% "
                    f"(expected={expected}%, z={z_score:.1f})"
                )

            except Exception as e:
                logger.debug(f"PentagonPizza: failed to get {name}: {e}")
                continue

        if not zone_scores:
            logger.debug("PentagonPizza: no busyness data collected")
            return []

        # Compute composite score per zone and overall
        zone_alerts = {}
        for zone, scores in zone_scores.items():
            avg_z = statistics.mean(scores) if scores else 0
            zone_alerts[zone] = avg_z

        overall_z = statistics.mean(
            z for scores in zone_scores.values() for z in scores
        )

        # Night hours amplifier
        night_multiplier = 1.5 if current_hour in NIGHT_HOURS else 1.0
        effective_z = overall_z * night_multiplier

        # Only generate items if anomaly detected
        items = []

        if effective_z >= Z_THRESHOLD_ALERT:
            severity = "critical" if effective_z >= Z_THRESHOLD_CRITICAL else "high"
            is_night = current_hour in NIGHT_HOURS

            # Build zone detail
            zone_details = []
            for zone, avg_z in sorted(zone_alerts.items(), key=lambda x: x[1], reverse=True):
                if avg_z > 1.0:
                    zone_details.append(f"{zone}: z={avg_z:.1f}")

            title = (
                f"Pentagon Pizza Alert: {'nocturne ' if is_night else ''}"
                f"activite anormale detectee (z={effective_z:.1f})"
            )
            summary = (
                f"Activite inhabituelle detectee pres des batiments gouvernementaux US. "
                f"Score composite z={effective_z:.1f} "
                f"({'NUIT' if is_night else 'jour'}). "
                f"Zones: {', '.join(zone_details) if zone_details else 'multiple'}. "
                f"Heure: {current_hour}h UTC."
            )

            content_hash = hashlib.sha256(
                f"pentagon_pizza|{now.strftime('%Y-%m-%d-%H')}|{effective_z:.0f}".encode()
            ).hexdigest()

            # Priority based on Z-score
            if effective_z >= Z_THRESHOLD_CRITICAL:
                priority = 0.9
                raw_relevance = 0.85
            elif effective_z >= 2.5:
                priority = 0.75
                raw_relevance = 0.7
            else:
                priority = 0.6
                raw_relevance = 0.55

            items.append({
                "source": "pentagon_pizza",
                "source_id": f"pizza_{now.strftime('%Y%m%d%H')}",
                "content_hash": content_hash,
                "title": title,
                "summary": summary,
                "url": "",
                "image_url": "",
                "category": "behavioral_osint",
                "region": "North America",
                "country": "United States",
                "tags": json.dumps([
                    "pentagon_pizza", "behavioral_osint", "anomaly",
                    *(["night_activity"] if is_night else []),
                    *[z for z in zone_alerts if zone_alerts[z] > 1.5],
                ]),
                "raw_relevance": raw_relevance,
                "sentiment_score": -0.3 * min(effective_z / 3.0, 1.0),
                "priority_score": priority,
                "confidence": min(0.9, effective_z / 4.0),
                "urgency": severity,
                "market_impact": "volatile",
                "published_at": now,
            })

            logger.info(
                f"PentagonPizza ALERT: z={effective_z:.1f}, "
                f"hour={current_hour}, zones={zone_details}"
            )

        return items

    async def _get_busyness(self, query: str) -> int | None:
        """Get current busyness percentage for a location.

        Uses Google search scraping as a free alternative to paid APIs.
        Returns a value 0-100 or None if unavailable.
        """
        try:
            # Try to get Popular Times from Google search
            url = "https://www.google.com/search"
            params = {"q": query, "hl": "en"}
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }

            resp = await self._http.get(url, params=params, headers=headers)
            if resp.status_code != 200:
                return None

            text = resp.text

            # Look for popular times / busyness indicators in the HTML
            # Google embeds this data in various formats
            import re

            # Pattern 1: "X% busy" or "Currently X% busy"
            match = re.search(r'(\d+)%\s*busy', text, re.IGNORECASE)
            if match:
                return int(match.group(1))

            # Pattern 2: "Busier than usual" / "Less busy than usual"
            if "busier than usual" in text.lower():
                return 80  # Approximate
            if "less busy than usual" in text.lower():
                return 20  # Approximate
            if "not too busy" in text.lower():
                return 30
            if "a little busy" in text.lower():
                return 50
            if "as busy as it gets" in text.lower():
                return 95

            # Pattern 3: Look for aria-label with percentage
            match = re.search(r'aria-label="[^"]*?(\d+)%[^"]*?busy', text)
            if match:
                return int(match.group(1))

            return None

        except Exception:
            return None
