from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session, joinedload

from app.config import Settings, get_settings
from app.database import get_db
from app.deps import get_current_user, require_bader
from app.models import (
    Asset,
    Newsletter,
    NewsletterStatus,
    ReviewEvent,
    Section,
    SectionComment,
    User,
)
from app.schemas import (
    CommentCreate,
    CommentOut,
    GenerateRequest,
    MailchimpSyncOut,
    MessageOut,
    NewsletterCreate,
    NewsletterOut,
    NewsletterSummary,
    NewsletterUpdate,
    SectionOut,
    SectionUpdate,
)
from app.services import ai as ai_service
from app.services import mailchimp as mailchimp_service
from app.services import slack as slack_service

router = APIRouter(prefix="/newsletters", tags=["newsletters"])


def _load_newsletter(db: Session, newsletter_id: UUID, workspace_id: UUID) -> Newsletter:
    nl = (
        db.query(Newsletter)
        .options(
            joinedload(Newsletter.sections).joinedload(Section.comments),
            joinedload(Newsletter.review_events),
        )
        .filter(Newsletter.id == newsletter_id, Newsletter.workspace_id == workspace_id)
        .first()
    )
    if not nl:
        raise HTTPException(status_code=404, detail="Newsletter not found")
    return nl


def _add_event(db: Session, newsletter: Newsletter, actor: User | None, event_type: str, message: str, meta: dict | None = None) -> None:
    db.add(
        ReviewEvent(
            newsletter_id=newsletter.id,
            actor_id=actor.id if actor else None,
            event_type=event_type,
            message=message,
            meta=meta,
        )
    )


@router.get("", response_model=list[NewsletterSummary])
def list_newsletters(
    status_filter: NewsletterStatus | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(Newsletter).filter(Newsletter.workspace_id == user.workspace_id)
    if status_filter:
        q = q.filter(Newsletter.status == status_filter)
    return q.order_by(Newsletter.updated_at.desc()).all()


@router.get("/archive", response_model=list[NewsletterSummary])
def archive(
    months: int = Query(default=12, ge=1, le=24),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cutoff = datetime.now(timezone.utc) - timedelta(days=30 * months)
    return (
        db.query(Newsletter)
        .filter(
            Newsletter.workspace_id == user.workspace_id,
            Newsletter.status.in_([NewsletterStatus.sent, NewsletterStatus.review_complete]),
            Newsletter.created_at >= cutoff,
        )
        .order_by(Newsletter.created_at.desc())
        .all()
    )


@router.post("", response_model=NewsletterOut, status_code=201)
def create_newsletter(
    payload: NewsletterCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_bader),
):
    nl = Newsletter(
        workspace_id=user.workspace_id,
        created_by_id=user.id,
        title=payload.title,
        section_count=len(payload.sections),
        headline=payload.title,
        issue_date=date.today(),
        status=NewsletterStatus.drafting,
    )
    db.add(nl)
    db.flush()
    for i, item in enumerate(payload.sections):
        db.add(
            Section(
                newsletter_id=nl.id,
                section_type=item.section_type,
                sort_order=i,
                title=item.section_type.value.replace("_", " ").title(),
                image_urls=[],
            )
        )
    _add_event(db, nl, user, "created", f"Created draft with {len(payload.sections)} sections")
    db.commit()
    return _load_newsletter(db, nl.id, user.workspace_id)


@router.get("/{newsletter_id}", response_model=NewsletterOut)
def get_newsletter(
    newsletter_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _load_newsletter(db, newsletter_id, user.workspace_id)


@router.patch("/{newsletter_id}", response_model=NewsletterOut)
def update_newsletter(
    newsletter_id: UUID,
    payload: NewsletterUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_bader),
):
    nl = _load_newsletter(db, newsletter_id, user.workspace_id)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(nl, key, value)
    db.commit()
    return _load_newsletter(db, newsletter_id, user.workspace_id)


@router.patch("/{newsletter_id}/sections/{section_id}", response_model=SectionOut)
def update_section(
    newsletter_id: UUID,
    section_id: UUID,
    payload: SectionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_bader),
):
    nl = _load_newsletter(db, newsletter_id, user.workspace_id)
    section = next((s for s in nl.sections if s.id == section_id), None)
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(section, key, value)
    if payload.saved is True:
        section.saved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(section)
    return section


@router.post("/{newsletter_id}/sections/{section_id}/generate")
async def generate_section(
    newsletter_id: UUID,
    section_id: UUID,
    payload: GenerateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_bader),
    settings: Settings = Depends(get_settings),
):
    nl = _load_newsletter(db, newsletter_id, user.workspace_id)
    section = next((s for s in nl.sections if s.id == section_id), None)
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    try:
        text = await ai_service.generate_section_text(
            settings,
            user.workspace,
            section_type=section.section_type,
            topic=payload.topic or section.title,
            tone=payload.tone,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    section.body = text
    db.commit()
    return {"body": text}


@router.post("/{newsletter_id}/sections/{section_id}/images")
async def upload_section_image(
    newsletter_id: UUID,
    section_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_bader),
    settings: Settings = Depends(get_settings),
):
    nl = _load_newsletter(db, newsletter_id, user.workspace_id)
    section = next((s for s in nl.sections if s.id == section_id), None)
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    ext = Path(file.filename or "upload.bin").suffix or ".bin"
    name = f"{uuid4().hex}{ext}"
    dest = settings.upload_path / name
    async with aiofiles.open(dest, "wb") as out:
        while chunk := await file.read(1024 * 1024):
            await out.write(chunk)

    url = f"/uploads/{name}"
    urls = list(section.image_urls or [])
    urls.append(url)
    section.image_urls = urls
    db.add(
        Asset(
            workspace_id=user.workspace_id,
            newsletter_id=nl.id,
            section_id=section.id,
            filename=file.filename or name,
            url=url,
            content_type=file.content_type,
        )
    )
    db.commit()
    return {"url": url, "image_urls": urls}


@router.post("/{newsletter_id}/chrome/background")
async def upload_background(
    newsletter_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_bader),
    settings: Settings = Depends(get_settings),
):
    nl = _load_newsletter(db, newsletter_id, user.workspace_id)
    ext = Path(file.filename or "bg.bin").suffix or ".bin"
    name = f"bg-{uuid4().hex}{ext}"
    dest = settings.upload_path / name
    async with aiofiles.open(dest, "wb") as out:
        while chunk := await file.read(1024 * 1024):
            await out.write(chunk)
    url = f"/uploads/{name}"
    nl.background_url = url
    if not nl.headline:
        nl.headline = nl.title
    if not nl.issue_date:
        nl.issue_date = date.today()
    db.add(
        Asset(
            workspace_id=user.workspace_id,
            newsletter_id=nl.id,
            filename=file.filename or name,
            url=url,
            content_type=file.content_type,
        )
    )
    db.commit()
    return {"background_url": url, "headline": nl.headline, "issue_date": nl.issue_date}


@router.post("/{newsletter_id}/comments", response_model=CommentOut, status_code=201)
def add_comment(
    newsletter_id: UUID,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    nl = _load_newsletter(db, newsletter_id, user.workspace_id)
    section = next((s for s in nl.sections if s.id == payload.section_id), None)
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    comment = SectionComment(section_id=section.id, author_id=user.id, body=payload.body)
    db.add(comment)
    nl.status = NewsletterStatus.changes_requested
    _add_event(db, nl, user, "comment", f"Comment on section {section.sort_order + 1}: {payload.body}")
    db.commit()
    db.refresh(comment)
    return comment


@router.post("/{newsletter_id}/comments/{comment_id}/resolve", response_model=CommentOut)
def resolve_comment(
    newsletter_id: UUID,
    comment_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_bader),
):
    nl = _load_newsletter(db, newsletter_id, user.workspace_id)
    comment = None
    for section in nl.sections:
        for c in section.comments:
            if c.id == comment_id:
                comment = c
                break
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    comment.resolved = True
    db.commit()
    db.refresh(comment)
    return comment


@router.post("/{newsletter_id}/review/request", response_model=NewsletterOut)
async def request_review(
    newsletter_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_bader),
    settings: Settings = Depends(get_settings),
):
    nl = _load_newsletter(db, newsletter_id, user.workspace_id)
    unsaved = [s for s in nl.sections if not s.saved]
    if unsaved:
        raise HTTPException(
            status_code=400,
            detail=f"{len(unsaved)} section(s) not saved yet",
        )
    ts = await slack_service.post_review_request(
        settings, newsletter_id=str(nl.id), title=nl.title
    )
    nl.status = NewsletterStatus.in_review
    nl.slack_message_ts = ts
    _add_event(db, nl, user, "review_requested", "Sent to lead for Slack review")
    db.commit()
    return _load_newsletter(db, newsletter_id, user.workspace_id)


@router.post("/{newsletter_id}/review/approve", response_model=NewsletterOut)
def approve_review(
    newsletter_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    nl = _load_newsletter(db, newsletter_id, user.workspace_id)
    nl.status = NewsletterStatus.review_complete
    _add_event(db, nl, user, "approved", "Lead approved the newsletter")
    db.commit()
    return _load_newsletter(db, newsletter_id, user.workspace_id)


@router.post("/{newsletter_id}/mailchimp/sync", response_model=MailchimpSyncOut)
async def sync_mailchimp(
    newsletter_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_bader),
    settings: Settings = Depends(get_settings),
):
    nl = _load_newsletter(db, newsletter_id, user.workspace_id)
    if nl.status not in (
        NewsletterStatus.review_complete,
        NewsletterStatus.ready_to_send,
        NewsletterStatus.sent,
    ):
        raise HTTPException(status_code=400, detail="Lead approval required before Mailchimp sync")
    result = await mailchimp_service.sync_campaign(settings, nl)
    nl.mailchimp_campaign_id = result["campaign_id"]
    nl.mailchimp_editor_url = result["editor_url"]
    nl.status = NewsletterStatus.ready_to_send
    _add_event(db, nl, user, "mailchimp_sync", f"Synced campaign {result['campaign_id']}")
    db.commit()
    return MailchimpSyncOut(**result)


@router.post("/{newsletter_id}/mailchimp/confirm-sent", response_model=NewsletterOut)
def confirm_sent(
    newsletter_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_bader),
):
    nl = _load_newsletter(db, newsletter_id, user.workspace_id)
    if not nl.mailchimp_campaign_id:
        raise HTTPException(status_code=400, detail="Sync to Mailchimp first")
    nl.status = NewsletterStatus.sent
    nl.sent_at = datetime.now(timezone.utc)
    _add_event(db, nl, user, "sent", "Confirmed community send via Mailchimp")
    db.commit()
    return _load_newsletter(db, newsletter_id, user.workspace_id)


@router.post("/{newsletter_id}/demo/request-changes", response_model=MessageOut)
def demo_request_changes(
    newsletter_id: UUID,
    section_index: int = Query(ge=1),
    body: str = Query(min_length=1),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Simulate Slack request-changes when Slack is not configured."""
    nl = _load_newsletter(db, newsletter_id, user.workspace_id)
    if section_index > len(nl.sections):
        raise HTTPException(status_code=400, detail="Invalid section index")
    section = sorted(nl.sections, key=lambda s: s.sort_order)[section_index - 1]
    db.add(SectionComment(section_id=section.id, author_id=user.id, body=body))
    nl.status = NewsletterStatus.changes_requested
    _add_event(db, nl, user, "changes_requested", f"Section {section_index}: {body}")
    db.commit()
    return MessageOut(message="Changes requested")
