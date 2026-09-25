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
    ai_topic: Optional[str] = None
    ai_instructions: Optional[str] = None
    image_urls: List[str] = Field(default_factory=list)
    saved: bool
    saved_at: Optional[datetime] = None
    lead_decision: Optional[str] = None
    review_sent_at: Optional[datetime] = None
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
    lead_slack_email: Optional[str] = None
    review_token: Optional[str] = None
    last_step: Optional[str] = None
    review_requested_at: Optional[datetime] = None
    denied_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    sent_at: Optional[datetime] = None
    slack_share_url: Optional[str] = None
    sections: List[SectionOut] = Field(default_factory=list)
    review_events: List[ReviewEventOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class LeadNoteOut(BaseModel):
    section_id: UUID
    section_title: str
    body: str

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
    last_step: Optional[str] = None
    review_requested_at: Optional[datetime] = None
    denied_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    sent_at: Optional[datetime] = None
    lead_notes: List[LeadNoteOut] = Field(default_factory=list)

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
    last_step: Optional[str] = None


class SectionUpdate(BaseModel):
    layout_key: Optional[str] = None
    title: Optional[str] = None
    body: Optional[str] = None
    ai_topic: Optional[str] = None
    ai_instructions: Optional[str] = None
    image_urls: Optional[List[str]] = None
    saved: Optional[bool] = None
    sort_order: Optional[int] = None


class CommentCreate(BaseModel):
    section_id: UUID
    body: str = Field(min_length=1)


class ReviewRequestIn(BaseModel):
    lead_email: str = Field(min_length=3)


class SectionRecommendation(BaseModel):
    section_id: UUID
    body: str = Field(min_length=1)


class RecommendationsIn(BaseModel):
    comments: List[SectionRecommendation] = Field(min_length=1)


class LeadOption(BaseModel):
    id: UUID
    email: str
    name: str


class GenerateRequest(BaseModel):
    topic: Optional[str] = None
    instructions: Optional[str] = ""
    tone: Optional[str] = "friendly"


class SourceClip(BaseModel):
    title: str
    excerpt: str
    url: str
    source: str


class SearchIn(BaseModel):
    query: str = Field(min_length=1)


class SearchOut(BaseModel):
    query: str
    results: List[SourceClip] = Field(default_factory=list)


class ProfileUpdate(BaseModel):
    mailchimp_email: str = Field(min_length=3)
    slack_email: str = Field(min_length=3)
    ai_tool: str = Field(pattern="^(claude|cursor)$")


class WorkspaceOut(BaseModel):
    id: UUID
    name: str
    plan: PlanType
    brand_color: Optional[str] = None
    default_background_url: Optional[str] = None
    headline_style: Optional[str] = None
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None
    slack_connected: bool = False

    model_config = {"from_attributes": True}


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = None
    plan: Optional[PlanType] = None
    brand_color: Optional[str] = None
    default_background_url: Optional[str] = None
    headline_style: Optional[str] = None
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None
    slack_bot_token: Optional[str] = None


class UserOut(BaseModel):
    id: UUID
    email: str
    name: str
    role: UserRole
    mailchimp_email: Optional[str] = None
    slack_email: Optional[str] = None
    ai_tool: Optional[str] = None
    has_password: bool = False
    workspace: WorkspaceOut

    model_config = {"from_attributes": True}


class MailchimpSyncOut(BaseModel):
    campaign_id: str
    editor_url: str
    demo: bool = False


class MessageOut(BaseModel):
    ok: bool = True
    message: str
