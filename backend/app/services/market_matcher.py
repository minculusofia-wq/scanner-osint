import logging
import re
import time
from collections import defaultdict

import httpx

logger = logging.getLogger(__name__)

GAMMA_HOST = "https://gamma-api.polymarket.com"

# Polymarket tag IDs for event categories
TAG_IDS = {
    "political": 2,
    "financial": 120,
    "crypto": 21,
    "geopolitical": 100265,
    "tech": 1401,
    "culture": 596,
}

# Category aliases
CATEGORY_TAG_MAP = {
    "conflict": "geopolitical",
    "general": "political",
}


class MarketMatcher:
    """Matches intelligence items to open Polymarket markets via Gamma API."""

    CACHE_TTL = 300  # 5 minutes

    def __init__(self):
        self._cache: dict[int, tuple[float, list[dict]]] = {}

    async def find_matching_markets(self, item: dict, top_n: int = 3) -> list[dict]:
        """Find Polymarket markets matching an intelligence item.

        Returns list of {condition_id, question, token_id, price_yes} dicts.
        """
        category = item.get("category", "general")
        tag_name = CATEGORY_TAG_MAP.get(category, category)
        tag_id = TAG_IDS.get(tag_name)

        if not tag_id:
            return []

        markets = await self._fetch_markets(tag_id)
        if not markets:
            return []

        # Extract keywords from item
        title = item.get("title", "").lower()
        summary = item.get("summary", "").lower()
        text = f"{title} {summary}"
        keywords = self._extract_keywords(text)

        if not keywords:
            return []

        # Score each market by keyword overlap
        scored = []
        for market in markets:
            question = market.get("question", "").lower()
            group_title = market.get("group_title", "").lower()
            match_text = f"{question} {group_title}"

            score = sum(1 for kw in keywords if kw in match_text)
            if score > 0:
                scored.append((score, market))

        scored.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, market in scored[:top_n]:
            results.append({
                "condition_id": market.get("condition_id", ""),
                "question": market.get("question", ""),
                "token_id": market.get("token_id_yes", ""),
                "price_yes": market.get("price_yes", 0),
            })

        return results

    async def _fetch_markets(self, tag_id: int) -> list[dict]:
        """Fetch open Polymarket events by tag. Cached 5 min."""
        now = time.time()
        if tag_id in self._cache:
            cached_time, cached_data = self._cache[tag_id]
            if now - cached_time < self.CACHE_TTL:
                return cached_data

        markets = []
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                offset = 0
                while True:
                    resp = await client.get(
                        f"{GAMMA_HOST}/events",
                        params={
                            "tag_id": tag_id,
                            "closed": "false",
                            "limit": 100,
                            "offset": offset,
                            "order": "volume24hr",
                            "ascending": "false",
                        },
                    )
                    resp.raise_for_status()
                    events = resp.json()
                    if not events:
                        break

                    for event in events:
                        event_title = event.get("title", "")
                        for market in event.get("markets", []):
                            question = market.get("question", "")
                            condition_id = market.get("condition_id", "")
                            if not condition_id:
                                continue

                            tokens = market.get("clobTokenIds", "")
                            token_ids = []
                            if isinstance(tokens, str) and tokens.startswith("["):
                                try:
                                    import json
                                    token_ids = json.loads(tokens)
                                except Exception:
                                    pass
                            elif isinstance(tokens, list):
                                token_ids = tokens

                            outcomes = market.get("outcomes", "")
                            if isinstance(outcomes, str):
                                try:
                                    import json
                                    outcomes = json.loads(outcomes)
                                except Exception:
                                    outcomes = []

                            prices = market.get("outcomePrices", "")
                            if isinstance(prices, str):
                                try:
                                    import json
                                    prices = json.loads(prices)
                                except Exception:
                                    prices = []

                            price_yes = float(prices[0]) if prices else 0
                            token_id_yes = token_ids[0] if token_ids else ""

                            markets.append({
                                "condition_id": condition_id,
                                "question": question,
                                "group_title": event_title,
                                "token_id_yes": token_id_yes,
                                "price_yes": price_yes,
                            })

                    offset += 100
                    if len(events) < 100:
                        break

            self._cache[tag_id] = (now, markets)
            logger.info(f"MarketMatcher: cached {len(markets)} markets for tag_id={tag_id}")

        except Exception as e:
            logger.error(f"MarketMatcher fetch error for tag {tag_id}: {e}")

        return markets

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract meaningful keywords from text for matching."""
        # Remove common stop words and short words
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "shall", "can", "to", "of", "in", "for",
            "on", "with", "at", "by", "from", "as", "into", "about", "after",
            "before", "between", "under", "over", "than", "that", "this", "these",
            "those", "it", "its", "or", "and", "but", "not", "no", "nor", "so",
            "if", "then", "else", "when", "where", "how", "what", "which", "who",
            "whom", "why", "all", "each", "every", "both", "few", "more", "most",
            "other", "some", "such", "only", "own", "same", "too", "very",
        }

        words = re.findall(r"[a-z]{3,}", text)
        keywords = [w for w in words if w not in stop_words]

        # Also extract multi-word phrases
        bigrams = []
        for i in range(len(words) - 1):
            if words[i] not in stop_words and words[i + 1] not in stop_words:
                bigrams.append(f"{words[i]} {words[i+1]}")

        return keywords + bigrams
