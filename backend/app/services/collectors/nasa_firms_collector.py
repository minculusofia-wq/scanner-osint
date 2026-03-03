import csv
import io
import logging
from collections import defaultdict
from datetime import datetime

import httpx

from .base_collector import BaseCollector

logger = logging.getLogger(__name__)

# NASA FIRMS API - VIIRS active fire data (free, no key for small requests)
# For larger requests, a MAP_KEY is needed (free registration)
FIRMS_BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"

# Zones of interest for OSINT (conflict areas, strategic locations)
MONITORING_ZONES = [
    {
        "name": "Ukraine",
        "bbox": "22.0,44.0,40.5,52.5",  # west,south,east,north
        "region": "europe",
        "country": "Ukraine",
        "conflict": True,
    },
    {
        "name": "Middle East",
        "bbox": "34.0,29.0,50.0,38.0",
        "region": "middle_east",
        "country": "",
        "conflict": True,
    },
    {
        "name": "Taiwan Strait",
        "bbox": "117.0,22.0,122.0,26.0",
        "region": "asia",
        "country": "Taiwan",
        "conflict": False,
    },
    {
        "name": "Sahel",
        "bbox": "-5.0,10.0,15.0,20.0",
        "region": "africa",
        "country": "",
        "conflict": True,
    },
    {
        "name": "Korean Peninsula",
        "bbox": "124.0,33.0,131.0,43.0",
        "region": "asia",
        "country": "",
        "conflict": False,
    },
]


class NASAFirmsCollector(BaseCollector):
    """Collects NASA FIRMS satellite fire/thermal data for conflict zone monitoring."""

    SOURCE_NAME = "nasa_firms"

    async def collect(self, config: dict) -> list[dict]:
        items = []

        async with httpx.AsyncClient(timeout=30) as client:
            for zone in MONITORING_ZONES:
                try:
                    # Use the open FIRMS CSV endpoint (no key needed for small areas)
                    # Format: /api/area/csv/{source}/{area}/{day_range}
                    # We use VIIRS_SNPP for best coverage
                    bbox = zone["bbox"]
                    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/VIIRS_SNPP_NRT/{bbox}/1"

                    resp = await client.get(url)

                    if resp.status_code == 403:
                        # Try alternative: use world fire data endpoint
                        url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/MODIS_NRT/{bbox}/1"
                        resp = await client.get(url)

                    if resp.status_code != 200:
                        logger.warning(f"NASA FIRMS {zone['name']}: HTTP {resp.status_code}")
                        continue

                    # Parse CSV response
                    text = resp.text.strip()
                    if not text or "latitude" not in text.lower():
                        continue

                    reader = csv.DictReader(io.StringIO(text))
                    fires = []
                    for row in reader:
                        try:
                            confidence = row.get("confidence", "0")
                            # VIIRS confidence can be "nominal", "high", "low" or numeric
                            if confidence in ("high", "h"):
                                conf_val = 90
                            elif confidence in ("nominal", "n"):
                                conf_val = 70
                            elif confidence in ("low", "l"):
                                conf_val = 40
                            else:
                                try:
                                    conf_val = int(float(confidence))
                                except (ValueError, TypeError):
                                    conf_val = 50

                            if conf_val < 70:
                                continue

                            lat = float(row.get("latitude", 0))
                            lon = float(row.get("longitude", 0))
                            brightness = float(row.get("bright_ti4", row.get("brightness", 0)))
                            frp = float(row.get("frp", 0))  # Fire Radiative Power

                            fires.append({
                                "lat": lat,
                                "lon": lon,
                                "confidence": conf_val,
                                "brightness": brightness,
                                "frp": frp,
                                "acq_date": row.get("acq_date", ""),
                                "acq_time": row.get("acq_time", ""),
                            })
                        except (ValueError, KeyError):
                            continue

                    if not fires:
                        continue

                    # Cluster nearby fires (within ~10km = 0.1 degrees)
                    clusters = _cluster_fires(fires)

                    for cluster in clusters:
                        fire_count = len(cluster)
                        avg_lat = sum(f["lat"] for f in cluster) / fire_count
                        avg_lon = sum(f["lon"] for f in cluster) / fire_count
                        max_frp = max(f["frp"] for f in cluster)
                        avg_brightness = sum(f["brightness"] for f in cluster) / fire_count

                        # Relevance: clusters > single fires, conflict zones boosted
                        if fire_count >= 5:
                            relevance = 0.9
                        elif fire_count >= 3:
                            relevance = 0.75
                        else:
                            relevance = 0.55

                        if zone["conflict"]:
                            relevance = min(1.0, relevance + 0.1)

                        # High FRP suggests explosions/industrial fires
                        if max_frp > 100:
                            relevance = min(1.0, relevance + 0.1)

                        category = "conflict" if zone["conflict"] else "geopolitical"

                        acq_date = cluster[0].get("acq_date", "")
                        published = None
                        if acq_date:
                            try:
                                published = datetime.strptime(acq_date, "%Y-%m-%d")
                            except ValueError:
                                pass

                        title = f"Satellite: {fire_count} thermal anomalies detected in {zone['name']}"
                        summary = (
                            f"{fire_count} fire/thermal detections near "
                            f"{avg_lat:.2f}N, {avg_lon:.2f}E. "
                            f"Max FRP: {max_frp:.1f} MW. "
                            f"Avg brightness: {avg_brightness:.1f}K. "
                            f"Zone: {zone['name']}."
                        )

                        items.append(self._make_item(
                            title=title,
                            summary=summary,
                            url=f"https://firms.modaps.eosdis.nasa.gov/map/#d:24hrs;@{avg_lon:.1f},{avg_lat:.1f},8z",
                            category=category,
                            region=zone["region"],
                            country=zone["country"],
                            tags=["satellite", "fire", zone["name"].lower().replace(" ", "_")],
                            raw_relevance=relevance,
                            published_at=published,
                            source_id=f"firms-{zone['name']}-{fire_count}-{avg_lat:.1f}-{avg_lon:.1f}",
                        ))

                except Exception as e:
                    logger.error(f"NASA FIRMS {zone['name']} error: {e}")

        logger.info(f"NASA FIRMS: collected {len(items)} items")
        return items


def _cluster_fires(fires: list[dict], threshold: float = 0.1) -> list[list[dict]]:
    """Simple grid-based clustering of fire detections."""
    grid = defaultdict(list)
    for fire in fires:
        # Grid cell of ~10km
        key = (round(fire["lat"] / threshold), round(fire["lon"] / threshold))
        grid[key].append(fire)
    return list(grid.values())
