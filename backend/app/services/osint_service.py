import asyncio
import hashlib
import json
import logging
from datetime import datetime, timedelta

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.intelligence_brief import IntelligenceBrief
from app.models.intelligence_item import IntelligenceItem
from app.schemas.intelligence import OSINTConfig
from app.services.brief_generator import BriefGenerator
from app.services.collectors.acled_collector import ACLEDCollector
from app.services.collectors.adsb_collector import ADSBCollector
from app.services.collectors.finnhub_collector import FinnhubCollector
from app.services.collectors.fred_collector import FREDCollector
from app.services.collectors.gdelt_collector import GDELTCollector
from app.services.collectors.gov_rss_collector import GovRSSCollector
from app.services.collectors.nasa_firms_collector import NASAFirmsCollector
from app.services.collectors.newsdata_collector import NewsDataCollector
from app.services.collectors.reddit_collector import RedditCollector
from app.services.collectors.sec_edgar_collector import SECEdgarCollector
from app.services.collectors.ship_tracker_collector import ShipTrackerCollector
from app.services.collectors.telegram_collector import TelegramCollector
from app.services.collectors.whale_crypto_collector import WhaleCryptoCollector
from app.services.intelligence_scorer import IntelligenceScorer
from app.services.market_matcher import MarketMatcher
from app.services.sentiment_analyzer import SentimentAnalyzer

logger = logging.getLogger(__name__)


class OSINTService:
    """Main OSINT intelligence orchestrator."""

    def __init__(self):
        self.sentiment = SentimentAnalyzer()
        self.scorer = IntelligenceScorer()
        self.matcher = MarketMatcher()
        self.brief_gen = BriefGenerator()

        self._collectors = {
            # News/Data
            "gdelt": GDELTCollector(),
            "newsdata": NewsDataCollector(),
            "acled": ACLEDCollector(),
            "finnhub": FinnhubCollector(),
            "reddit": RedditCollector(),
            # FININT
            "sec_edgar": SECEdgarCollector(),
            "whale_crypto": WhaleCryptoCollector(),
            "fred": FREDCollector(),
            # GEOINT
            "adsb": ADSBCollector(),
            "nasa_firms": NASAFirmsCollector(),
            "ship_tracker": ShipTrackerCollector(),
            # Social OSINT
            "telegram": TelegramCollector(),
            "gov_rss": GovRSSCollector(),
        }

        self._last_collection_at: datetime | None = None

    async def collect_cycle(self, db: AsyncSession, config: OSINTConfig) -> dict:
        """Run one full collection cycle."""
        stats = {"collected": 0, "new": 0, "duplicates": 0, "scored": 0, "briefs_generated": 0}

        # 1. Collect from all enabled sources concurrently
        config_dict = config.model_dump()
        tasks = []
        source_names = []

        if config.gdelt_enabled:
            tasks.append(self._collectors["gdelt"].collect(config_dict))
            source_names.append("gdelt")
        if config.newsdata_enabled and config.newsdata_api_key:
            tasks.append(self._collectors["newsdata"].collect(config_dict))
            source_names.append("newsdata")
        if config.acled_enabled and config.acled_api_key:
            tasks.append(self._collectors["acled"].collect(config_dict))
            source_names.append("acled")
        if config.finnhub_enabled and config.finnhub_api_key:
            tasks.append(self._collectors["finnhub"].collect(config_dict))
            source_names.append("finnhub")
        if config.reddit_enabled:
            tasks.append(self._collectors["reddit"].collect(config_dict))
            source_names.append("reddit")

        # FININT
        if config.sec_edgar_enabled:
            tasks.append(self._collectors["sec_edgar"].collect(config_dict))
            source_names.append("sec_edgar")
        if config.whale_crypto_enabled and config.etherscan_api_key:
            tasks.append(self._collectors["whale_crypto"].collect(config_dict))
            source_names.append("whale_crypto")
        if config.fred_enabled and config.fred_api_key:
            tasks.append(self._collectors["fred"].collect(config_dict))
            source_names.append("fred")

        # GEOINT
        if config.adsb_enabled:
            tasks.append(self._collectors["adsb"].collect(config_dict))
            source_names.append("adsb")
        if config.nasa_firms_enabled:
            tasks.append(self._collectors["nasa_firms"].collect(config_dict))
            source_names.append("nasa_firms")
        if config.ship_tracker_enabled:
            tasks.append(self._collectors["ship_tracker"].collect(config_dict))
            source_names.append("ship_tracker")

        # Social OSINT
        if config.telegram_enabled:
            tasks.append(self._collectors["telegram"].collect(config_dict))
            source_names.append("telegram")
        if config.gov_rss_enabled:
            tasks.append(self._collectors["gov_rss"].collect(config_dict))
            source_names.append("gov_rss")

        if not tasks:
            logger.warning("No collectors enabled or configured")
            return stats

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_items = []
        for name, result in zip(source_names, results):
            if isinstance(result, Exception):
                logger.error(f"Collector {name} failed: {result}")
                continue
            all_items.extend(result)

        stats["collected"] = len(all_items)
        if not all_items:
            return stats

        # 2. Deduplicate
        new_items = await self._deduplicate(db, all_items)
        stats["duplicates"] = stats["collected"] - len(new_items)
        stats["new"] = len(new_items)

        if not new_items:
            logger.info("No new items after deduplication")
            self._last_collection_at = datetime.utcnow()
            return stats

        # 3. Enrich with VADER sentiment (for items that don't have it from source)
        for item in new_items:
            if item.get("sentiment_score", 0) == 0:
                item["sentiment_score"] = self.sentiment.score_item(
                    item.get("title", ""),
                    item.get("summary", ""),
                )

        # 4. Match to Polymarket markets + score
        for item in new_items:
            markets = await self.matcher.find_matching_markets(item)
            item["linked_market_ids"] = json.dumps([m["condition_id"] for m in markets])
            item["linked_market_questions"] = json.dumps([m["question"] for m in markets])

            scoring = self.scorer.score_item(item, has_market_match=len(markets) > 0)
            item.update(scoring)

        stats["scored"] = len(new_items)

        # 5. Filter by min priority
        if config.min_priority_score > 0:
            new_items = [i for i in new_items if i.get("priority_score", 0) >= config.min_priority_score]

        # 6. Persist items to SQLite
        for item in new_items:
            db_item = IntelligenceItem(
                source=item["source"],
                source_id=item.get("source_id", ""),
                content_hash=item["content_hash"],
                title=item["title"],
                summary=item.get("summary", ""),
                url=item.get("url", ""),
                image_url=item.get("image_url", ""),
                category=item.get("category", "general"),
                region=item.get("region", ""),
                country=item.get("country", ""),
                tags=json.dumps(item.get("tags", [])),
                raw_relevance=item.get("raw_relevance", 0),
                sentiment_score=item.get("sentiment_score", 0),
                goldstein_scale=item.get("goldstein_scale", 0),
                priority_score=item.get("priority_score", 0),
                confidence=item.get("confidence", 0),
                urgency=item.get("urgency", "low"),
                market_impact=item.get("market_impact", "neutral"),
                linked_market_ids=item.get("linked_market_ids", "[]"),
                linked_market_questions=item.get("linked_market_questions", "[]"),
                published_at=item.get("published_at"),
                collected_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
            )
            db.add(db_item)

        await db.commit()

        # 7. Generate briefs from new items
        # Reload persisted items to get their IDs
        recent_stmt = (
            select(IntelligenceItem)
            .where(IntelligenceItem.is_stale == False)
            .order_by(IntelligenceItem.created_at.desc())
            .limit(200)
        )
        result = await db.execute(recent_stmt)
        recent_items = result.scalars().all()

        item_dicts = []
        for ri in recent_items:
            item_dicts.append({
                "id": ri.id,
                "title": ri.title,
                "summary": ri.summary,
                "category": ri.category,
                "region": ri.region,
                "priority_score": ri.priority_score,
                "confidence": ri.confidence,
                "sentiment_score": ri.sentiment_score,
                "linked_market_ids": ri.linked_market_ids,
                "linked_market_questions": ri.linked_market_questions,
                "source": ri.source,
            })

        briefs = self.brief_gen.generate_briefs(item_dicts)

        # Delete dismissed briefs and regenerate active ones
        await db.execute(delete(IntelligenceBrief).where(IntelligenceBrief.is_dismissed == True))
        await db.execute(delete(IntelligenceBrief).where(IntelligenceBrief.is_dismissed == False))

        for brief_data in briefs:
            expires_at = None
            if brief_data.get("expires_at"):
                try:
                    expires_at = datetime.fromisoformat(brief_data["expires_at"])
                except (ValueError, TypeError):
                    pass

            db_brief = IntelligenceBrief(
                title=brief_data["title"],
                summary=brief_data.get("summary", ""),
                trading_implication=brief_data.get("trading_implication", ""),
                priority_score=brief_data.get("priority_score", 0),
                confidence=brief_data.get("confidence", 0),
                urgency=brief_data.get("urgency", "low"),
                source_item_ids=brief_data.get("source_item_ids", "[]"),
                source_count=brief_data.get("source_count", 0),
                linked_market_ids=brief_data.get("linked_market_ids", "[]"),
                linked_market_questions=brief_data.get("linked_market_questions", "[]"),
                category=brief_data.get("category", "general"),
                region=brief_data.get("region", ""),
                is_actionable=brief_data.get("is_actionable", False),
                created_at=datetime.utcnow(),
                expires_at=expires_at,
            )
            db.add(db_brief)

        await db.commit()
        stats["briefs_generated"] = len(briefs)

        # 8. Mark stale items
        await self._mark_stale(db, config.stale_after_hours)

        self._last_collection_at = datetime.utcnow()
        return stats

    async def get_items(
        self,
        db: AsyncSession,
        limit: int = 50,
        offset: int = 0,
        category: str | None = None,
        urgency: str | None = None,
        source: str | None = None,
        include_stale: bool = False,
    ) -> list[dict]:
        stmt = select(IntelligenceItem).order_by(IntelligenceItem.priority_score.desc())

        if not include_stale:
            stmt = stmt.where(IntelligenceItem.is_stale == False)
        if category:
            stmt = stmt.where(IntelligenceItem.category == category)
        if urgency:
            stmt = stmt.where(IntelligenceItem.urgency == urgency)
        if source:
            stmt = stmt.where(IntelligenceItem.source == source)

        stmt = stmt.offset(offset).limit(limit)
        result = await db.execute(stmt)
        items = result.scalars().all()

        return [self._item_to_dict(item) for item in items]

    async def get_briefs(
        self,
        db: AsyncSession,
        limit: int = 20,
        actionable_only: bool = False,
    ) -> list[dict]:
        stmt = select(IntelligenceBrief).where(IntelligenceBrief.is_dismissed == False)
        if actionable_only:
            stmt = stmt.where(IntelligenceBrief.is_actionable == True)
        stmt = stmt.order_by(IntelligenceBrief.priority_score.desc()).limit(limit)

        result = await db.execute(stmt)
        briefs = result.scalars().all()

        return [self._brief_to_dict(b) for b in briefs]

    async def get_stats(self, db: AsyncSession) -> dict:
        # Total items
        total = await db.execute(select(func.count(IntelligenceItem.id)))
        total_items = total.scalar() or 0

        # Items last 24h
        cutoff = datetime.utcnow() - timedelta(hours=24)
        recent = await db.execute(
            select(func.count(IntelligenceItem.id)).where(IntelligenceItem.created_at >= cutoff)
        )
        items_24h = recent.scalar() or 0

        # Briefs
        briefs_total = await db.execute(
            select(func.count(IntelligenceBrief.id)).where(IntelligenceBrief.is_dismissed == False)
        )
        briefs_count = briefs_total.scalar() or 0

        actionable = await db.execute(
            select(func.count(IntelligenceBrief.id)).where(
                IntelligenceBrief.is_dismissed == False,
                IntelligenceBrief.is_actionable == True,
            )
        )
        actionable_briefs = actionable.scalar() or 0

        # Active sources
        sources = await db.execute(
            select(IntelligenceItem.source).where(IntelligenceItem.created_at >= cutoff).distinct()
        )
        sources_active = [row[0] for row in sources.all()]

        # Markets linked
        market_count = await db.execute(
            select(func.count(IntelligenceItem.id)).where(
                IntelligenceItem.linked_market_ids != "[]",
                IntelligenceItem.is_stale == False,
            )
        )
        linked_markets = market_count.scalar() or 0

        return {
            "total_items": total_items,
            "items_last_24h": items_24h,
            "briefs_count": briefs_count,
            "actionable_briefs": actionable_briefs,
            "sources_active": sources_active,
            "last_collection_at": self._last_collection_at.isoformat() if self._last_collection_at else None,
            "linked_markets_count": linked_markets,
        }

    async def dismiss_brief(self, db: AsyncSession, brief_id: int) -> bool:
        stmt = select(IntelligenceBrief).where(IntelligenceBrief.id == brief_id)
        result = await db.execute(stmt)
        brief = result.scalar_one_or_none()
        if not brief:
            return False
        brief.is_dismissed = True
        await db.commit()
        return True

    # --- Private helpers ---

    def _compute_hash(self, title: str, url: str, source: str = "") -> str:
        content = f"{source}|{title.strip().lower()}|{url.strip().lower()}"
        return hashlib.sha256(content.encode()).hexdigest()

    async def _deduplicate(self, db: AsyncSession, items: list[dict]) -> list[dict]:
        hashes = [self._compute_hash(i.get("title", ""), i.get("url", ""), i.get("source", "")) for i in items]

        existing_stmt = select(IntelligenceItem.content_hash).where(
            IntelligenceItem.content_hash.in_(hashes)
        )
        result = await db.execute(existing_stmt)
        existing = {row[0] for row in result.all()}

        # Also dedup within the batch
        seen = set()
        new_items = []
        for item, h in zip(items, hashes):
            if h not in existing and h not in seen:
                item["content_hash"] = h
                new_items.append(item)
                seen.add(h)

        return new_items

    async def _mark_stale(self, db: AsyncSession, hours: int):
        if hours <= 0:
            return
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        stmt = (
            update(IntelligenceItem)
            .where(IntelligenceItem.created_at < cutoff, IntelligenceItem.is_stale == False)
            .values(is_stale=True)
        )
        await db.execute(stmt)
        await db.commit()

    def _item_to_dict(self, item: IntelligenceItem) -> dict:
        try:
            tags = json.loads(item.tags) if item.tags else []
        except json.JSONDecodeError:
            tags = []

        try:
            market_ids = json.loads(item.linked_market_ids) if item.linked_market_ids else []
            market_qs = json.loads(item.linked_market_questions) if item.linked_market_questions else []
        except json.JSONDecodeError:
            market_ids = []
            market_qs = []

        linked_markets = [
            {"condition_id": mid, "question": mq}
            for mid, mq in zip(market_ids, market_qs)
        ]

        return {
            "id": item.id,
            "source": item.source,
            "title": item.title,
            "summary": item.summary,
            "url": item.url,
            "image_url": item.image_url,
            "category": item.category,
            "region": item.region,
            "country": item.country,
            "tags": tags,
            "sentiment_score": item.sentiment_score,
            "priority_score": item.priority_score,
            "confidence": item.confidence,
            "urgency": item.urgency,
            "market_impact": item.market_impact,
            "linked_markets": linked_markets,
            "published_at": item.published_at.isoformat() if item.published_at else None,
            "collected_at": item.collected_at.isoformat() if item.collected_at else None,
        }

    def _brief_to_dict(self, brief: IntelligenceBrief) -> dict:
        try:
            market_ids = json.loads(brief.linked_market_ids) if brief.linked_market_ids else []
            market_qs = json.loads(brief.linked_market_questions) if brief.linked_market_questions else []
        except json.JSONDecodeError:
            market_ids = []
            market_qs = []

        linked_markets = [
            {"condition_id": mid, "question": mq}
            for mid, mq in zip(market_ids, market_qs)
        ]

        return {
            "id": brief.id,
            "title": brief.title,
            "summary": brief.summary,
            "trading_implication": brief.trading_implication,
            "priority_score": brief.priority_score,
            "confidence": brief.confidence,
            "urgency": brief.urgency,
            "source_count": brief.source_count,
            "linked_markets": linked_markets,
            "category": brief.category,
            "region": brief.region,
            "is_actionable": brief.is_actionable,
            "is_dismissed": brief.is_dismissed,
            "created_at": brief.created_at.isoformat() if brief.created_at else None,
            "expires_at": brief.expires_at.isoformat() if brief.expires_at else None,
        }
