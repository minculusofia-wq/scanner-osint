import logging
from datetime import datetime

import httpx

from app.services.collectors.base_collector import BaseCollector

logger = logging.getLogger(__name__)


class RedditCollector(BaseCollector):
    """Collects top/hot posts from relevant subreddits (public JSON API, no auth)."""

    SOURCE_NAME = "reddit"

    SUBREDDITS = {
        "polymarket": "financial",
        "geopolitics": "geopolitical",
        "worldnews": "geopolitical",
        "economics": "financial",
        "CryptoCurrency": "crypto",
        "finance": "financial",
    }

    USER_AGENT = "python:ScannerOSINT:v1.0 (by /u/scanner_osint_bot)"

    async def collect(self, config: dict) -> list[dict]:
        items = []
        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(
            timeout=15,
            headers=headers,
            follow_redirects=True,
        ) as client:
            for subreddit, category in self.SUBREDDITS.items():
                try:
                    # Use old.reddit.com to avoid 403 blocks
                    response = await client.get(
                        f"https://old.reddit.com/r/{subreddit}/hot.json",
                        params={"limit": 10},
                    )
                    if response.status_code == 429:
                        logger.warning(f"Reddit rate limited on r/{subreddit}")
                        continue
                    response.raise_for_status()
                    data = response.json()

                    posts = data.get("data", {}).get("children", [])
                    logger.info(f"Reddit: fetched {len(posts)} posts from r/{subreddit}")

                    for post in posts:
                        post_data = post.get("data", {})
                        title = post_data.get("title", "").strip()
                        if not title:
                            continue

                        # Skip stickied/pinned posts
                        if post_data.get("stickied", False):
                            continue

                        selftext = post_data.get("selftext", "") or ""
                        # Skip deleted/removed content
                        if selftext in ("[deleted]", "[removed]"):
                            selftext = ""
                        permalink = post_data.get("permalink", "")
                        url = f"https://reddit.com{permalink}" if permalink else ""
                        created_utc = post_data.get("created_utc", 0)
                        score = post_data.get("score", 0)
                        num_comments = post_data.get("num_comments", 0)

                        published_at = datetime.utcfromtimestamp(created_utc) if created_utc else None

                        # Reddit engagement as relevance proxy
                        engagement = score + num_comments * 2
                        if engagement >= 500:
                            raw_relevance = 0.9
                        elif engagement >= 100:
                            raw_relevance = 0.7
                        elif engagement >= 20:
                            raw_relevance = 0.5
                        else:
                            raw_relevance = 0.3

                        items.append(self._make_item(
                            title=f"[r/{subreddit}] {title}",
                            summary=selftext[:300],
                            url=url,
                            category=category,
                            tags=[subreddit],
                            raw_relevance=raw_relevance,
                            published_at=published_at,
                            source_id=post_data.get("id", ""),
                        ))

                except httpx.HTTPStatusError as e:
                    logger.error(f"Reddit r/{subreddit} HTTP error: {e.response.status_code}")
                except Exception as e:
                    logger.error(f"Reddit r/{subreddit} error: {e}")

        return items
