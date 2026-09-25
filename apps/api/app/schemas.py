from datetime import date, datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models import NewsletterStatus, PlanType, SectionType, UserRole


class CommentOut(BaseModel):
    id: UUID
    section_id: UUID
    body: str
    resolved: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SectionOut(BaseModel):
    id: UUID
    section_type: SectionType
    layout_key: Optional[str] = None
    sort_order: int
    title: Optional[str] = None
    body: Optional[str] = None
    image_urls: List[str] = Field(default_factory=list)
    saved: bool
    saved_at: Optional[datetime] = None
    comments: List[CommentOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ReviewEventOut(BaseModel):
    id: UUID
    event_type: str
    message: str
    meta: Optional[Dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NewsletterOut(BaseModel):
    id: UUID
    title: str
    headline: Optional[str] = None
    issue_date: Optional[date] = None
    background_url: Optional[str] = None
    status: NewsletterStatus
    section_count: int
    mailchimp_campaign_id: Optional[str] = None
    mailchimp_editor_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    sent_at: Optional[datetime] = None
    sections: List[SectionOut] = Field(default_factory=list)
    review_events: List[ReviewEventOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class NewsletterSummary(BaseModel):
    id: UUID
    title: str
    headline: Optional[str] = None
    issue_date: Optional[date] = None
    status: NewsletterStatus
    section_count: int
    mailchimp_campaign_id: Optional[str] = None
    mailchimp_editor_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    sent_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class IntakeSection(BaseModel):
    section_type: SectionType


class NewsletterCreate(BaseModel):
    title: str = "Untitled Newsletter"
    sections: List[IntakeSection] = Field(min_length=1, max_length=12)


class NewsletterUpdate(BaseModel):
    title: Optional[str] = None
    headline: Optional[str] = None
    issue_date: Optional[date] = None
    background_url: Optional[str] = None
    status: Optional[NewsletterStatus] = None


class SectionUpdate(BaseModel):
    layout_key: Optional[str] = None
    title: Optional[str] = None
    body: Optional[str] = None
    image_urls: Optional[List[str]] = None
    saved: Optional[bool] = None
    sort_order: Optional[int] = None


class CommentCreate(BaseModel):
    section_id: UUID
    body: str = Field(min_length=1)


class GenerateRequest(BaseModel):
    topic: Optional[str] = None
    tone: Optional[str] = "friendly"


class WorkspaceOut(BaseModel):
    id: UUID
    name: str
    plan: PlanType
    brand_color: Optional[str] = None
    default_background_url: Optional[str] = None
    headline_style: Optional[str] = None
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None

    model_config = {"from_attributes": True}


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = None
    plan: Optional[PlanType] = None
    brand_color: Optional[str] = None
    default_background_url: Optional[str] = None
    headline_style: Optional[str] = None
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None


class UserOut(BaseModel):
    id: UUID
    email: str
    name: str
    role: UserRole
    workspace: WorkspaceOut

    model_config = {"from_attributes": True}


class MailchimpSyncOut(BaseModel):
    campaign_id: str
    editor_url: str
    demo: bool = False


class MessageOut(BaseModel):
    ok: bool = True
    message: str
