import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class BriefGenerator:
    """Generates intelligence briefs from clusters of related items (rule-based)."""

    # Minimum items to form a cluster
    MIN_CLUSTER_SIZE = 2

    # Keywords that indicate trading direction
    BULLISH_KEYWORDS = [
        "peace", "ceasefire", "deal", "agreement", "growth", "recovery",
        "surplus", "approval", "resolved", "breakthrough", "rally",
    ]
    BEARISH_KEYWORDS = [
        "war", "attack", "sanctions", "crisis", "recession", "default",
        "collapse", "escalation", "threat", "ban", "crash", "downturn",
    ]

    def generate_briefs(self, items: list[dict]) -> list[dict]:
        """Generate briefs from a list of scored intelligence items.

        Clusters items by (category, region) and generates one brief per cluster.
        """
        if not items:
            return []

        clusters = self._cluster_items(items)
        briefs = []

        for key, cluster_items in clusters.items():
            if len(cluster_items) < self.MIN_CLUSTER_SIZE:
                continue

            brief = self._build_brief(key, cluster_items)
            if brief:
                briefs.append(brief)

        # Sort by priority
        briefs.sort(key=lambda b: b["priority_score"], reverse=True)
        return briefs

    def _cluster_items(self, items: list[dict]) -> dict[str, list[dict]]:
        """Group items by (category, region) as cluster key."""
        clusters: dict[str, list[dict]] = defaultdict(list)

        for item in items:
            category = item.get("category", "general")
            region = item.get("region", "global") or "global"
            key = f"{category}:{region}"
            clusters[key].append(item)

        return dict(clusters)

    def _build_brief(self, cluster_key: str, items: list[dict]) -> dict | None:
        """Build a single brief from a cluster of related items."""
        if not items:
            return None

        category, region = cluster_key.split(":", 1)

        # Sort by priority, highest first
        sorted_items = sorted(items, key=lambda x: x.get("priority_score", 0), reverse=True)
        top_item = sorted_items[0]

        # Title from highest-priority item
        title = top_item.get("title", "Intelligence Brief")

        # Summary: top 3 items' summaries
        summaries = []
        for item in sorted_items[:3]:
            s = item.get("summary", "") or item.get("title", "")
            if s and s not in summaries:
                summaries.append(s)
        summary = " | ".join(summaries) if summaries else title

        # Aggregate sentiment
        sentiments = [i.get("sentiment_score", 0) for i in items]
        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0

        # Aggregate priority
        priorities = [i.get("priority_score", 0) for i in items]
        avg_priority = sum(priorities) / len(priorities) if priorities else 0
        max_priority = max(priorities) if priorities else 0

        # Trading implication (rule-based)
        trading_implication = self._infer_trading_implication(
            title, summary, avg_sentiment, category, items
        )

        # Confidence = average of item confidences, boosted by source count
        confidences = [i.get("confidence", 0.5) for i in items]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
        source_boost = min(0.2, len(items) * 0.05)  # More sources = higher confidence
        confidence = min(1.0, avg_confidence + source_boost)

        # Urgency from max priority
        if max_priority >= 80:
            urgency = "critical"
        elif max_priority >= 60:
            urgency = "high"
        elif max_priority >= 40:
            urgency = "medium"
        else:
            urgency = "low"

        # Collect all linked markets
        all_market_ids = []
        all_market_questions = []
        for item in items:
            try:
                ids = json.loads(item.get("linked_market_ids", "[]"))
                questions = json.loads(item.get("linked_market_questions", "[]"))
                for mid, mq in zip(ids, questions):
                    if mid not in all_market_ids:
                        all_market_ids.append(mid)
                        all_market_questions.append(mq)
            except (json.JSONDecodeError, TypeError):
                pass

        is_actionable = max_priority >= 60

        return {
            "title": title,
            "summary": summary[:1000],
            "trading_implication": trading_implication,
            "priority_score": round(max_priority, 1),
            "confidence": round(confidence, 2),
            "urgency": urgency,
            "source_item_ids": json.dumps([i.get("id") for i in items if i.get("id")]),
            "source_count": len(items),
            "linked_market_ids": json.dumps(all_market_ids[:5]),
            "linked_market_questions": json.dumps(all_market_questions[:5]),
            "category": category,
            "region": region,
            "is_actionable": is_actionable,
            "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
        }

    def _infer_trading_implication(
        self, title: str, summary: str, avg_sentiment: float,
        category: str, items: list[dict],
    ) -> str:
        """Infer trading implication from content + sentiment (rule-based)."""
        text = f"{title} {summary}".lower()

        bullish_count = sum(1 for kw in self.BULLISH_KEYWORDS if kw in text)
        bearish_count = sum(1 for kw in self.BEARISH_KEYWORDS if kw in text)

        if avg_sentiment > 0.3 or bullish_count > bearish_count:
            direction = "positive"
            action = "Consider YES positions on related markets"
        elif avg_sentiment < -0.3 or bearish_count > bullish_count:
            direction = "negative"
            action = "Consider NO positions or avoid YES on related markets"
        else:
            direction = "mixed"
            action = "Monitor closely — sentiment is mixed"

        source_count = len(items)
        if source_count >= 5:
            confidence_note = f"Signal confirmed by {source_count} sources."
        elif source_count >= 3:
            confidence_note = f"Moderate signal ({source_count} sources)."
        else:
            confidence_note = f"Early signal ({source_count} sources), verify before acting."

        return f"{action}. {confidence_note} Overall sentiment: {direction} ({avg_sentiment:+.2f})."
