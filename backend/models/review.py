import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class ReviewAction(str, enum.Enum):
    approved = "approved"
    rejected = "rejected"
    needs_edit = "needs_edit"
    deferred = "deferred"


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    example_id: Mapped[str] = mapped_column(String(36), ForeignKey("examples.id"))
    action: Mapped[ReviewAction] = mapped_column(Enum(ReviewAction))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    example = relationship("Example", back_populates="reviews")
