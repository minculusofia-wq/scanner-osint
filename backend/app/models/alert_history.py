from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class AlertHistory(Base):
    __tablename__ = "alert_history"
    __table_args__ = (
        Index("ix_alert_created", "created_at"),
        Index("ix_alert_rule", "alert_rule_id"),
        Index("ix_alert_tracker", "escalation_tracker_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    alert_rule_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    escalation_tracker_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Content
    title: Mapped[str] = mapped_column(Text)
    message: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20))
    escalation_level: Mapped[str] = mapped_column(String(20), default="")
    region: Mapped[str] = mapped_column(String(100), default="")
    category: Mapped[str] = mapped_column(String(50), default="")

    # Trigger details
    trigger_signal_count: Mapped[int] = mapped_column(Integer, default=0)
    trigger_source_types: Mapped[str] = mapped_column(Text, default="[]")
    trigger_item_ids: Mapped[str] = mapped_column(Text, default="[]")
    matched_patterns: Mapped[str] = mapped_column(Text, default="[]")

    # Delivery
    channels_sent: Mapped[str] = mapped_column(Text, default="[]")
    delivery_status: Mapped[str] = mapped_column(String(20), default="pending")

    # Markets at time of alert
    linked_market_ids: Mapped[str] = mapped_column(Text, default="[]")
    linked_market_questions: Mapped[str] = mapped_column(Text, default="[]")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
