import enum
import uuid
from datetime import date, datetime
from typing import Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database import Base


class UserRole(str, enum.Enum):
    bader = "bader"
    lead = "lead"


class PlanType(str, enum.Enum):
    free = "free"
    premium = "premium"


class NewsletterStatus(str, enum.Enum):
    drafting = "drafting"
    in_review = "in_review"
    changes_requested = "changes_requested"
    review_complete = "review_complete"
    ready_to_send = "ready_to_send"
    sent = "sent"


class SectionType(str, enum.Enum):
    news = "news"
    featured_story = "featured_story"
    tips = "tips"
    events = "events"
    cta = "cta"


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(120), default="Default Workspace")
    plan: Mapped[PlanType] = mapped_column(
        Enum(PlanType, native_enum=False), default=PlanType.premium
    )
    brand_color: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    default_background_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    headline_style: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ai_provider: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ai_model: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    users: Mapped[List["User"]] = relationship(back_populates="workspace")
    newsletters: Mapped[List["Newsletter"]] = relationship(back_populates="workspace")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, native_enum=False), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    workspace: Mapped["Workspace"] = relationship(back_populates="users")


class Newsletter(Base):
    __tablename__ = "newsletters"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), default="Untitled Newsletter")
    headline: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    issue_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    background_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    status: Mapped[NewsletterStatus] = mapped_column(
        Enum(NewsletterStatus, native_enum=False),
        default=NewsletterStatus.drafting,
        index=True,
    )
    section_count: Mapped[int] = mapped_column(Integer, default=0)
    mailchimp_campaign_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    mailchimp_editor_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    slack_message_ts: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    workspace: Mapped["Workspace"] = relationship(back_populates="newsletters")
    sections: Mapped[List["Section"]] = relationship(
        back_populates="newsletter",
        cascade="all, delete-orphan",
        order_by="Section.sort_order",
    )
    review_events: Mapped[List["ReviewEvent"]] = relationship(
        back_populates="newsletter",
        cascade="all, delete-orphan",
        order_by="ReviewEvent.created_at",
    )


class Section(Base):
    __tablename__ = "sections"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    newsletter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("newsletters.id"), nullable=False)
    section_type: Mapped[SectionType] = mapped_column(
        Enum(SectionType, native_enum=False), nullable=False
    )
    layout_key: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_urls: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    saved: Mapped[bool] = mapped_column(Boolean, default=False)
    saved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    newsletter: Mapped["Newsletter"] = relationship(back_populates="sections")
    comments: Mapped[List["SectionComment"]] = relationship(
        back_populates="section",
        cascade="all, delete-orphan",
        order_by="SectionComment.created_at",
    )


class SectionComment(Base):
    __tablename__ = "section_comments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    section_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sections.id"), nullable=False)
    author_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    section: Mapped["Section"] = relationship(back_populates="comments")


class ReviewEvent(Base):
    __tablename__ = "review_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    newsletter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("newsletters.id"), nullable=False)
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    newsletter: Mapped["Newsletter"] = relationship(back_populates="review_events")


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    newsletter_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("newsletters.id"), nullable=True
    )
    section_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("sections.id"), nullable=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
