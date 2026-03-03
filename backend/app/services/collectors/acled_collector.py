import logging
from datetime import datetime, timedelta

import httpx

from app.services.collectors.base_collector import BaseCollector

logger = logging.getLogger(__name__)


class ACLEDCollector(BaseCollector):
    """Collects armed conflict events from ACLED API (free with registration)."""

    SOURCE_NAME = "acled"
    BASE_URL = "https://api.acleddata.com/acled/read"

    EVENT_TYPE_CATEGORY = {
        "Battles": "conflict",
        "Violence against civilians": "conflict",
        "Explosions/Remote violence": "conflict",
        "Riots": "geopolitical",
        "Protests": "political",
        "Strategic developments": "geopolitical",
    }

    REGION_MAP = {
        "Western Africa": "Africa",
        "Middle Africa": "Africa",
        "Eastern Africa": "Africa",
        "Southern Africa": "Africa",
        "Northern Africa": "Africa",
        "Western Europe": "Europe",
        "Eastern Europe": "Europe",
        "Middle East": "Middle East",
        "South Asia": "Asia",
        "Southeast Asia": "Asia",
        "East Asia": "Asia",
        "Central Asia": "Asia",
        "Caucasus and Central Asia": "Asia",
        "South America": "Americas",
        "Central America": "Americas",
        "Caribbean": "Americas",
        "North America": "North America",
        "Oceania": "Oceania",
    }

    async def collect(self, config: dict) -> list[dict]:
        api_key = config.get("acled_api_key", "")
        email = config.get("acled_email", "")
        if not api_key or not email:
            logger.debug("ACLED: no API key or email, skipping")
            return []

        items = []
        today = datetime.utcnow()
        week_ago = today - timedelta(days=7)

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    self.BASE_URL,
                    params={
                        "key": api_key,
                        "email": email,
                        "event_date": f"{week_ago:%Y-%m-%d}|{today:%Y-%m-%d}",
                        "event_date_where": "BETWEEN",
                        "limit": 100,
                        "fields": "event_id_cnty|event_date|event_type|sub_event_type|actor1|actor2|country|region|fatalities|notes|source",
                    },
                )
                response.raise_for_status()
                data = response.json()

            events = data.get("data", [])
            logger.info(f"ACLED: fetched {len(events)} conflict events")

            for event in events:
                event_type = event.get("event_type", "")
                sub_type = event.get("sub_event_type", "")
                country = event.get("country", "")
                acled_region = event.get("region", "")
                try:
                    fatalities = int(float(event.get("fatalities", 0) or 0))
                except (ValueError, TypeError):
                    fatalities = 0
                notes = event.get("notes", "") or ""
                actor1 = event.get("actor1", "") or ""
                actor2 = event.get("actor2", "") or ""
                event_date = event.get("event_date", "")

                title = f"{event_type}: {actor1}"
                if actor2:
                    title += f" vs {actor2}"
                title += f" ({country})"

                published_at = None
                if event_date:
                    try:
                        published_at = datetime.strptime(event_date, "%Y-%m-%d")
                    except ValueError:
                        pass

                category = self.EVENT_TYPE_CATEGORY.get(event_type, "geopolitical")
                region = self.REGION_MAP.get(acled_region, "")

                # More fatalities = higher relevance
                if fatalities >= 50:
                    raw_relevance = 1.0
                elif fatalities >= 10:
                    raw_relevance = 0.8
                elif fatalities >= 1:
                    raw_relevance = 0.6
                else:
                    raw_relevance = 0.4

                # Conflict events are inherently negative sentiment
                sentiment = -0.3 if fatalities == 0 else max(-1.0, min(-0.5, -fatalities / 100.0))

                tags = [event_type.lower(), sub_type.lower()] if sub_type else [event_type.lower()]

                items.append(self._make_item(
                    title=title,
                    summary=notes[:500],
                    category=category,
                    region=region,
                    country=country,
                    tags=tags,
                    raw_relevance=raw_relevance,
                    sentiment_score=max(-1.0, sentiment),
                    published_at=published_at,
                    source_id=event.get("event_id_cnty", ""),
                ))

        except httpx.HTTPStatusError as e:
            logger.error(f"ACLED HTTP error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"ACLED collection error: {e}")

        return items
