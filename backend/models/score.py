import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class Score(Base):
    __tablename__ = "scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    example_id: Mapped[str] = mapped_column(String(36), ForeignKey("examples.id"))
    engine_name: Mapped[str] = mapped_column(String(50))
    score_type: Mapped[str] = mapped_column(String(50))
    score_value: Mapped[float] = mapped_column(Float)
    raw_value: Mapped[str] = mapped_column(Text, default="{}")  # JSON string
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    example = relationship("Example", back_populates="scores")
