import logging
from datetime import datetime, timedelta

import httpx

from .base_collector import BaseCollector

logger = logging.getLogger(__name__)

FRED_API_URL = "https://api.stlouisfed.org/fred/series/observations"

# Key economic indicators to monitor
FRED_SERIES = [
    {"id": "GDP", "name": "GDP", "desc": "Gross Domestic Product", "freq": "quarterly"},
    {"id": "CPIAUCSL", "name": "CPI", "desc": "Consumer Price Index (inflation)", "freq": "monthly"},
    {"id": "UNRATE", "name": "Unemployment", "desc": "Unemployment Rate", "freq": "monthly"},
    {"id": "FEDFUNDS", "name": "Fed Funds Rate", "desc": "Federal Funds Effective Rate", "freq": "daily"},
    {"id": "T10Y2Y", "name": "Yield Curve", "desc": "10Y-2Y Treasury Spread (inversion signal)", "freq": "daily"},
    {"id": "MORTGAGE30US", "name": "Mortgage 30Y", "desc": "30-Year Fixed Mortgage Rate", "freq": "weekly"},
    {"id": "UMCSENT", "name": "Consumer Sentiment", "desc": "U of Michigan Consumer Sentiment", "freq": "monthly"},
    {"id": "BAMLH0A0HYM2", "name": "HY Spread", "desc": "High Yield Bond Spread (risk indicator)", "freq": "daily"},
]


class FREDCollector(BaseCollector):
    """Collects Federal Reserve Economic Data (FRED) macro indicators."""

    SOURCE_NAME = "fred"

    async def collect(self, config: dict) -> list[dict]:
        api_key = config.get("fred_api_key", "")
        if not api_key:
            logger.debug("FRED: no API key configured, skipping")
            return []

        items = []
        today = datetime.utcnow()
        # Dynamic lookback based on frequency (quarterly needs ~400 days)
        FREQ_LOOKBACK = {"quarterly": 400, "monthly": 120, "weekly": 60, "daily": 30}
        default_lookback = 90

        async with httpx.AsyncClient(timeout=20) as client:
            for series in FRED_SERIES:
                try:
                    lookback_days = FREQ_LOOKBACK.get(series["freq"], default_lookback)
                    lookback = today - timedelta(days=lookback_days)
                    params = {
                        "series_id": series["id"],
                        "api_key": api_key,
                        "file_type": "json",
                        "observation_start": lookback.strftime("%Y-%m-%d"),
                        "sort_order": "desc",
                        "limit": 5,
                    }

                    resp = await client.get(FRED_API_URL, params=params)

                    if resp.status_code != 200:
                        logger.warning(f"FRED {series['id']}: HTTP {resp.status_code}")
                        continue

                    data = resp.json()
                    observations = data.get("observations", [])

                    if len(observations) < 2:
                        continue

                    # Get latest and previous values
                    latest = None
                    previous = None
                    for obs in observations:
                        val = obs.get("value", ".")
                        if val == ".":
                            continue
                        try:
                            v = float(val)
                        except ValueError:
                            continue
                        if latest is None:
                            latest = {"value": v, "date": obs["date"]}
                        elif previous is None:
                            previous = {"value": v, "date": obs["date"]}
                            break

                    if latest is None or previous is None:
                        continue

                    # Calculate change
                    change = latest["value"] - previous["value"]
                    if previous["value"] != 0:
                        pct_change = abs(change / previous["value"]) * 100
                    else:
                        pct_change = 0

                    # Determine relevance based on magnitude of change
                    if pct_change > 5:
                        relevance = 0.95
                    elif pct_change > 2:
                        relevance = 0.8
                    elif pct_change > 1:
                        relevance = 0.6
                    else:
                        relevance = 0.4

                    # Special cases: yield curve inversion is always high priority
                    if series["id"] == "T10Y2Y" and latest["value"] < 0:
                        relevance = 0.95

                    # HY spread widening = risk-off
                    if series["id"] == "BAMLH0A0HYM2" and change > 0.5:
                        relevance = max(relevance, 0.85)

                    # Skip low-change items for frequent series
                    if series["freq"] == "daily" and pct_change < 0.5:
                        continue

                    direction = "up" if change > 0 else "down"
                    sentiment = -0.3 if series["id"] in ("UNRATE", "BAMLH0A0HYM2", "CPIAUCSL") and change > 0 else 0.0
                    if series["id"] == "FEDFUNDS" and change > 0:
                        sentiment = -0.2  # Rate hike = bearish
                    elif series["id"] == "FEDFUNDS" and change < 0:
                        sentiment = 0.2  # Rate cut = bullish
                    elif direction == "up" and series["id"] in ("GDP", "UMCSENT"):
                        sentiment = 0.3  # Growth/sentiment up = bullish

                    published = None
                    try:
                        published = datetime.strptime(latest["date"], "%Y-%m-%d")
                    except ValueError:
                        pass

                    title = f"FRED: {series['name']} {direction} {pct_change:.1f}% to {latest['value']:.2f}"
                    summary = (
                        f"{series['desc']}: {previous['value']:.2f} -> {latest['value']:.2f} "
                        f"({'+' if change > 0 else ''}{change:.2f}, {pct_change:.1f}% change). "
                        f"Previous: {previous['date']}, Latest: {latest['date']}."
                    )

                    items.append(self._make_item(
                        title=title,
                        summary=summary,
                        url=f"https://fred.stlouisfed.org/series/{series['id']}",
                        category="financial",
                        region="north_america",
                        country="US",
                        tags=["fed", "macro", series["name"].lower().replace(" ", "_")],
                        raw_relevance=relevance,
                        sentiment_score=sentiment,
                        published_at=published,
                        source_id=f"fred-{series['id']}-{latest['date']}",
                    ))

                except Exception as e:
                    logger.error(f"FRED {series['id']} error: {e}")

        logger.info(f"FRED: collected {len(items)} items")
        return items
