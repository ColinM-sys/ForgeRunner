import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class ReviewStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    needs_edit = "needs_edit"


class Example(Base):
    __tablename__ = "examples"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id: Mapped[str] = mapped_column(String(36), ForeignKey("datasets.id"))
    line_number: Mapped[int] = mapped_column(Integer)
    system_prompt: Mapped[str] = mapped_column(Text, default="")
    user_content: Mapped[str] = mapped_column(Text, default="")
    assistant_content: Mapped[str] = mapped_column(Text, default="")
    raw_json: Mapped[str] = mapped_column(Text)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    char_count: Mapped[int] = mapped_column(Integer, default=0)
    bucket_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("buckets.id"), nullable=True)
    review_status: Mapped[ReviewStatus] = mapped_column(Enum(ReviewStatus), default=ReviewStatus.pending)
    aggregate_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    dataset = relationship("Dataset", back_populates="examples")
    bucket = relationship("Bucket", back_populates="examples")
    scores = relationship("Score", back_populates="example", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="example", cascade="all, delete-orphan")
