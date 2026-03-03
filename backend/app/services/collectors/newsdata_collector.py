import logging
from datetime import datetime

import httpx

from app.services.collectors.base_collector import BaseCollector

logger = logging.getLogger(__name__)


class NewsDataCollector(BaseCollector):
    """Collects news from NewsData.io (free tier: 200 credits/day)."""

    SOURCE_NAME = "newsdata"
    BASE_URL = "https://newsdata.io/api/1/latest"

    CATEGORY_QUERIES = [
        ("geopolitical", "geopolitics OR sanctions OR military OR NATO OR diplomacy"),
        ("financial", "interest rate OR GDP OR inflation OR stock market OR fed"),
        ("conflict", "war OR ceasefire OR bombing OR military operation"),
        ("political", "election OR president OR congress OR referendum OR vote"),
        ("crypto", "bitcoin regulation OR crypto policy OR SEC crypto"),
    ]

    def __init__(self):
        self._cycle_count = 0

    async def collect(self, config: dict) -> list[dict]:
        api_key = config.get("newsdata_api_key", "")
        if not api_key:
            logger.debug("NewsData: no API key, skipping")
            return []

        items = []
        cat_idx = self._cycle_count % len(self.CATEGORY_QUERIES)
        category, query = self.CATEGORY_QUERIES[cat_idx]
        self._cycle_count += 1

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    self.BASE_URL,
                    params={
                        "apikey": api_key,
                        "q": query,
                        "language": "en",
                        "timeframe": 48,  # last 48 hours (API max)
                    },
                )
                response.raise_for_status()
                data = response.json()

            results = data.get("results", [])
            logger.info(f"NewsData: fetched {len(results)} articles for '{category}'")

            for article in results:
                title = article.get("title", "").strip()
                if not title:
                    continue

                description = article.get("description", "") or ""
                link = article.get("link", "")
                image_url = article.get("image_url", "") or ""
                pub_date = article.get("pubDate", "")
                countries = article.get("country", []) or []
                categories = article.get("category", []) or []

                published_at = None
                if pub_date:
                    try:
                        published_at = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        pass

                country = countries[0] if countries else ""
                tags = [t.strip() for t in (categories if isinstance(categories, list) else [])]

                items.append(self._make_item(
                    title=title,
                    summary=description[:500],
                    url=link,
                    image_url=image_url,
                    category=category,
                    region="",
                    country=country,
                    tags=tags,
                    raw_relevance=0.6,
                    published_at=published_at,
                    source_id=article.get("article_id", link),
                ))

        except httpx.HTTPStatusError as e:
            logger.error(f"NewsData HTTP error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"NewsData collection error: {e}")

        return items
