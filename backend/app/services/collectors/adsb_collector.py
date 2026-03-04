import logging
from datetime import datetime

import httpx

from .base_collector import BaseCollector

logger = logging.getLogger(__name__)

# OpenSky Network API (free, no key needed for basic access)
OPENSKY_URL = "https://opensky-network.org/api/states/all"

# Strategic zones to monitor
# Expanded Middle East coverage per OSINT community (FlightRadar24 + @clement_molin thread)
MONITORING_ZONES = [
    {
        "name": "Ukraine",
        "bbox": {"lamin": 44.0, "lomin": 22.0, "lamax": 52.5, "lomax": 40.5},
        "region": "europe",
    },
    {
        "name": "Taiwan Strait",
        "bbox": {"lamin": 22.0, "lomin": 117.0, "lamax": 26.0, "lomax": 122.0},
        "region": "asia",
    },
    {
        "name": "Persian Gulf / Strait of Hormuz",
        "bbox": {"lamin": 23.0, "lomin": 48.0, "lamax": 30.0, "lomax": 60.0},
        "region": "middle_east",
    },
    {
        "name": "Israel / Lebanon / Syria",
        "bbox": {"lamin": 29.0, "lomin": 33.0, "lamax": 37.5, "lomax": 42.0},
        "region": "middle_east",
    },
    {
        "name": "Iran Airspace",
        "bbox": {"lamin": 25.0, "lomin": 44.0, "lamax": 40.0, "lomax": 63.5},
        "region": "middle_east",
    },
    {
        "name": "Red Sea / Bab el-Mandeb",
        "bbox": {"lamin": 11.0, "lomin": 39.0, "lamax": 20.0, "lomax": 46.0},
        "region": "middle_east",
    },
    {
        "name": "South China Sea",
        "bbox": {"lamin": 5.0, "lomin": 108.0, "lamax": 22.0, "lomax": 121.0},
        "region": "asia",
    },
    {
        "name": "Baltic Sea",
        "bbox": {"lamin": 53.0, "lomin": 12.0, "lamax": 66.0, "lomax": 30.0},
        "region": "europe",
    },
    {
        "name": "Eastern Mediterranean",
        "bbox": {"lamin": 31.0, "lomin": 24.0, "lamax": 38.0, "lomax": 36.0},
        "region": "europe",
    },
]

# Military/government callsign prefixes and patterns
MILITARY_CALLSIGNS = [
    # US Military
    "FORTE",  # RQ-4 Global Hawk drones
    "RQ4",
    "DUKE",   # Intelligence aircraft
    "HOMER",  # P-8 Poseidon
    "JAKE",   # RC-135 Rivet Joint
    "COBRA",  # E-6B Mercury (nuclear C2)
    "IRON",   # B-52
    "DOOM",   # B-2
    "REACH",  # C-17 (military transport)
    "RCH",    # C-17
    "EVAC",   # Military evacuation
    "SAM",    # Special Air Mission (VIP)
    "EXEC",   # Executive flight
    "NAVY",
    "USAF",
    # NATO
    "NATO",
    "OTAN",
    "MMF",    # Multinational MRTT Fleet
    # Reconnaissance patterns
    "SIGINT",
    "ELINT",
    # Israeli Air Force
    "IAF",
    "ELAL",  # Sometimes used for military charters
    # Middle East military
    "RSAF",   # Royal Saudi Air Force
    "IQAF",   # Iraqi Air Force
    "IRIAF",  # Islamic Republic of Iran Air Force
    # French military
    "FAF",    # French Air Force
    "CTM",    # French military transport
    # UK military
    "RAF",
    "RRR",    # RAF transport
    # Tanker/refueling
    "LAGR",   # KC-135 tanker
    "NCHO",   # KC-46
    "PACK",   # KC-10
]

# ICAO24 hex ranges for military (partial list of known allocators)
# These are approximate ranges - military aircraft often use specific blocks
MILITARY_ICAO_PREFIXES = [
    "AE",  # US military
    "AF",  # US military
    "43",  # UK military
    "3B",  # French military
    "73",  # Israeli military
    "50",  # Saudi military
    "70",  # Iranian (some blocks)
]


class ADSBCollector(BaseCollector):
    """Collects ADS-B aircraft tracking data from OpenSky Network for military/gov activity."""

    SOURCE_NAME = "adsb"

    async def collect(self, config: dict) -> list[dict]:
        items = []

        async with httpx.AsyncClient(timeout=25) as client:
            for zone in MONITORING_ZONES:
                try:
                    resp = await client.get(OPENSKY_URL, params=zone["bbox"])

                    if resp.status_code == 429:
                        logger.warning("OpenSky rate limited, skipping remaining zones")
                        break

                    if resp.status_code != 200:
                        logger.warning(f"OpenSky {zone['name']}: HTTP {resp.status_code}")
                        continue

                    data = resp.json()
                    states = data.get("states", [])

                    if not states:
                        continue

                    # Filter for military/government aircraft
                    military_aircraft = []
                    for state in states:
                        if len(state) < 9:
                            continue

                        icao24 = (state[0] or "").strip()
                        callsign = (state[1] or "").strip().upper()
                        origin_country = (state[2] or "").strip()
                        longitude = state[5]
                        latitude = state[6]
                        altitude = state[7]  # barometric altitude in meters
                        on_ground = state[8]

                        if longitude is None or latitude is None:
                            continue
                        if on_ground:
                            continue

                        is_military = False
                        aircraft_type = "unknown"

                        # Check callsign patterns
                        for mil_cs in MILITARY_CALLSIGNS:
                            if callsign.startswith(mil_cs):
                                is_military = True
                                aircraft_type = mil_cs
                                break

                        # Check ICAO24 hex prefix
                        if not is_military:
                            for prefix in MILITARY_ICAO_PREFIXES:
                                if icao24.upper().startswith(prefix):
                                    is_military = True
                                    aircraft_type = "military_hex"
                                    break

                        if is_military:
                            military_aircraft.append({
                                "icao24": icao24,
                                "callsign": callsign,
                                "origin": origin_country,
                                "lat": latitude,
                                "lon": longitude,
                                "alt": altitude,
                                "type": aircraft_type,
                            })

                    if not military_aircraft:
                        continue

                    # Group by type for summary
                    count = len(military_aircraft)

                    # Calculate relevance
                    # More military aircraft = higher relevance
                    if count >= 5:
                        relevance = 0.9
                    elif count >= 3:
                        relevance = 0.8
                    elif count >= 2:
                        relevance = 0.7
                    else:
                        relevance = 0.6

                    # Special high-value callsigns boost relevance
                    high_value = {"FORTE", "COBRA", "JAKE", "DUKE", "DOOM", "SAM", "EXEC"}
                    for ac in military_aircraft:
                        if ac["type"] in high_value:
                            relevance = min(1.0, relevance + 0.1)
                            break

                    # Build summary
                    callsigns = [ac["callsign"] for ac in military_aircraft if ac["callsign"]]
                    origins = list(set(ac["origin"] for ac in military_aircraft if ac["origin"]))

                    title = f"ADS-B: {count} military aircraft detected over {zone['name']}"
                    summary = (
                        f"{count} military/government aircraft tracked in {zone['name']} airspace. "
                        f"Countries: {', '.join(origins[:5])}. "
                        f"Callsigns: {', '.join(callsigns[:5])}."
                    )

                    tag_type = "military"
                    for ac in military_aircraft:
                        if ac["type"] in ("SAM", "EXEC"):
                            tag_type = "government"
                            break

                    bbox = zone["bbox"]
                    center_lat = (bbox["lamin"] + bbox["lamax"]) / 2
                    center_lon = (bbox["lomin"] + bbox["lomax"]) / 2
                    now = datetime.utcnow()

                    items.append(self._make_item(
                        title=title,
                        summary=summary,
                        url=f"https://www.flightradar24.com/{center_lat:.0f},{center_lon:.0f}/6",
                        category="geopolitical",
                        region=zone["region"],
                        tags=["adsb", tag_type, zone["name"].lower().replace(" ", "_")],
                        raw_relevance=relevance,
                        published_at=now,
                        source_id=f"adsb-{zone['name']}-{count}-{now.strftime('%Y%m%d%H')}",
                    ))

                except Exception as e:
                    logger.error(f"OpenSky {zone['name']} error: {e}")

        logger.info(f"ADS-B: collected {len(items)} items")
        return items
