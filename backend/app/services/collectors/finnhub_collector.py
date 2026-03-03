import logging
from datetime import datetime, timedelta

import httpx

from app.services.collectors.base_collector import BaseCollector

logger = logging.getLogger(__name__)


class FinnhubCollector(BaseCollector):
    """Collects market news + economic calendar from Finnhub (free: 60 calls/min)."""

    SOURCE_NAME = "finnhub"
    BASE_URL = "https://finnhub.io/api/v1"

    NEWS_CATEGORIES = ["general", "forex", "crypto"]

    IMPACT_RELEVANCE = {
        "high": 1.0,
        "medium": 0.7,
        "low": 0.4,
    }

    def __init__(self):
        self._cycle_count = 0

    async def collect(self, config: dict) -> list[dict]:
        api_key = config.get("finnhub_api_key", "")
        if not api_key:
            logger.debug("Finnhub: no API key, skipping")
            return []

        items = []
        headers = {"X-Finnhub-Token": api_key}

        try:
            async with httpx.AsyncClient(timeout=30, headers=headers) as client:
                # 1. Market news (rotate category)
                cat_idx = self._cycle_count % len(self.NEWS_CATEGORIES)
                news_cat = self.NEWS_CATEGORIES[cat_idx]
                self._cycle_count += 1

                news_resp = await client.get(
                    f"{self.BASE_URL}/news",
                    params={"category": news_cat},
                )
                news_resp.raise_for_status()
                news_articles = news_resp.json()

                logger.info(f"Finnhub: fetched {len(news_articles)} {news_cat} news articles")

                for article in news_articles[:30]:
                    title = article.get("headline", "").strip()
                    if not title:
                        continue

                    ts = article.get("datetime", 0)
                    published_at = datetime.utcfromtimestamp(ts) if ts else None

                    category = "crypto" if news_cat == "crypto" else "financial"

                    items.append(self._make_item(
                        title=title,
                        summary=(article.get("summary") or "")[:500],
                        url=article.get("url") or "",
                        image_url=article.get("image") or "",
                        category=category,
                        tags=[news_cat],
                        raw_relevance=0.5,
                        published_at=published_at,
                        source_id=str(article.get("id", "")),
                    ))

                # 2. Economic calendar
                today = datetime.utcnow()
                econ_resp = await client.get(
                    f"{self.BASE_URL}/calendar/economic",
                    params={
                        "from": (today - timedelta(days=1)).strftime("%Y-%m-%d"),
                        "to": (today + timedelta(days=3)).strftime("%Y-%m-%d"),
                    },
                )
                econ_resp.raise_for_status()
                econ_data = econ_resp.json()

                events = econ_data.get("economicCalendar", [])
                logger.info(f"Finnhub: fetched {len(events)} economic calendar events")

                for event in events:
                    event_name = event.get("event", "").strip()
                    if not event_name:
                        continue

                    country = event.get("country", "")
                    impact = event.get("impact", "low")
                    actual = event.get("actual")
                    estimate = event.get("estimate")
                    prev = event.get("prev")

                    summary_parts = []
                    if actual is not None:
                        summary_parts.append(f"Actual: {actual}")
                    if estimate is not None:
                        summary_parts.append(f"Estimate: {estimate}")
                    if prev is not None:
                        summary_parts.append(f"Previous: {prev}")
                    summary = " | ".join(summary_parts)

                    # Surprise factor
                    sentiment = 0.0
                    if actual is not None and estimate is not None:
                        try:
                            diff = float(actual) - float(estimate)
                            sentiment = max(-1.0, min(1.0, diff / max(abs(float(estimate)), 0.01)))
                        except (ValueError, TypeError):
                            pass

                    raw_relevance = self.IMPACT_RELEVANCE.get(impact, 0.4)

                    items.append(self._make_item(
                        title=f"[{country}] {event_name}",
                        summary=summary,
                        category="financial",
                        country=country,
                        tags=["economic calendar", impact],
                        raw_relevance=raw_relevance,
                        sentiment_score=sentiment,
                        source_id=f"econ_{country}_{event_name}_{today:%Y%m%d}",
                    ))

        except httpx.HTTPStatusError as e:
            logger.error(f"Finnhub HTTP error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Finnhub collection error: {e}")

        return items
