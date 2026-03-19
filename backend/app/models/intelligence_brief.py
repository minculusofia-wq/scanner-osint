from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class IntelligenceBrief(Base):
    __tablename__ = "intelligence_briefs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Brief content
    title: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text, default="")
    trading_implication: Mapped[str] = mapped_column(Text, default="")

    # Scoring
    priority_score: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    urgency: Mapped[str] = mapped_column(String(20), default="medium")

    # Source items
    source_item_ids: Mapped[str] = mapped_column(Text, default="[]")
    source_count: Mapped[int] = mapped_column(Integer, default=0)

    # Market mapping
    linked_market_ids: Mapped[str] = mapped_column(Text, default="[]")
    linked_market_questions: Mapped[str] = mapped_column(Text, default="[]")
    category: Mapped[str] = mapped_column(String(50), default="general")
    region: Mapped[str] = mapped_column(String(100), default="")

    # AI Analysis (Claude Sonnet)
    ai_situation: Mapped[str] = mapped_column(Text, default="")
    ai_analysis: Mapped[str] = mapped_column(Text, default="")
    ai_trading_signal: Mapped[str] = mapped_column(Text, default="")
    ai_confidence: Mapped[int] = mapped_column(Integer, default=0)
    ai_risk_factors: Mapped[str] = mapped_column(Text, default="")
    graph_data: Mapped[str] = mapped_column(Text, default="{}")

    # Status
    is_actionable: Mapped[bool] = mapped_column(Boolean, default=False)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
