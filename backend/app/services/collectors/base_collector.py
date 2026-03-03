import logging
from abc import ABC, abstractmethod
from datetime import datetime

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """Base class for all OSINT intelligence collectors."""

    SOURCE_NAME: str = "unknown"

    @abstractmethod
    async def collect(self, config: dict) -> list[dict]:
        """Fetch intelligence items from source. Returns list of raw item dicts."""
        ...

    def _make_item(
        self,
        title: str,
        summary: str = "",
        url: str = "",
        image_url: str = "",
        category: str = "general",
        region: str = "",
        country: str = "",
        tags: list[str] | None = None,
        raw_relevance: float = 0.5,
        sentiment_score: float = 0.0,
        goldstein_scale: float = 0.0,
        published_at: datetime | None = None,
        source_id: str = "",
    ) -> dict:
        """Build a standardized item dict."""
        return {
            "source": self.SOURCE_NAME,
            "source_id": source_id,
            "title": title,
            "summary": summary,
            "url": url,
            "image_url": image_url,
            "category": category,
            "region": region,
            "country": country,
            "tags": tags or [],
            "raw_relevance": raw_relevance,
            "sentiment_score": sentiment_score,
            "goldstein_scale": goldstein_scale,
            "published_at": published_at,
        }
