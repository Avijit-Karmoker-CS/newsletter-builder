from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from secrets import token_urlsafe
from uuid import UUID, uuid4

import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session, joinedload, selectinload

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
    UserRole,
)
from app.routers.public_review import ensure_lead, valid_email
from app.services.lead_mail import MailDeliveryError, send_review_email
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
    ReviewRequestIn,
    SearchIn,
    SearchOut,
    SectionOut,
    SectionUpdate,
)
from app.services import ai as ai_service
from app.services.search import search_verified
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
    apply_review_defaults(nl)
    return nl


def apply_review_defaults(nl: Newsletter) -> None:
    sent_at = None
    for event in nl.review_events:
        if event.event_type in ("review_requested", "urgent_follow_up"):
            sent_at = event.created_at
    sent_at = sent_at or nl.updated_at
    for section in nl.sections:
        if section.lead_decision:
            if section.review_sent_at is None and section.lead_decision in ("pending", "changes"):
                section.review_sent_at = sent_at
            continue
        if nl.status in (NewsletterStatus.sent, NewsletterStatus.ready_to_send):
            section.lead_decision = "queued"
        elif nl.status == NewsletterStatus.review_complete:
            section.lead_decision = "approved"
        elif nl.status == NewsletterStatus.changes_requested and any(
            not comment.resolved for comment in section.comments
        ):
            section.lead_decision = "changes"
            section.review_sent_at = sent_at
        elif nl.status in (NewsletterStatus.in_review, NewsletterStatus.changes_requested):
            section.lead_decision = "pending"
            section.review_sent_at = sent_at


def lead_email_for_follow_up(db: Session, user: User, nl: Newsletter) -> str:
    if nl.lead_slack_email and not nl.lead_slack_email.endswith("@example.com"):
        return nl.lead_slack_email
    leads = (
        db.query(User)
        .filter(User.workspace_id == user.workspace_id, User.role == UserRole.lead)
        .order_by(User.created_at.desc())
        .all()
    )
    real = [lead for lead in leads if not lead.email.endswith("@example.com")]
    chosen = real or leads
    if not chosen:
        raise HTTPException(
            status_code=400,
            detail="Add the lead Slack email on Preview before the follow-up.",
        )
    return chosen[0].email


def _email_review(email: str, title: str, review_url: str, urgent: bool) -> str:
    prefix = "URGENT review request" if urgent else "Newsletter review"
    body = (
        f"{prefix}: {title}\n\n"
        "Open this link to approve or request changes:\n"
        f"{review_url}\n\n"
        "After you approve, Bader will see this newsletter under Lead approved.\n"
    )
    try:
        send_review_email(to=email, subject=f"{prefix}: {title}", body=body)
    except MailDeliveryError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not email the review to {email}. {exc}",
        ) from exc
    return "email"


def slack_ready(settings: Settings, user: User, db: Session) -> Settings:
    stored = (user.workspace.slack_bot_token or "").strip()
    token = slack_service.valid_bot_token(stored or settings.slack_bot_token)
    if stored and not token:
        user.workspace.slack_bot_token = None
        db.commit()
        raise HTTPException(
            status_code=400,
            detail=(
                "Slack rejected the saved token. Paste the Bot User OAuth Token from api.slack.com. "
                "It starts with xoxb-."
            ),
        )
    if not token:
        raise HTTPException(
            status_code=400,
            detail=(
                "Slack rejected the connection. Paste the Bot User OAuth Token that starts with xoxb- "
                "on Review, then use Urgent follow-up again."
            ),
        )
    return settings.model_copy(update={"slack_bot_token": token})


def slack_detail(exc: Exception) -> str:
    code = str(exc)
    if "users_not_found" in code:
        return "Slack has no member with that email. Use the email on their Slack profile."
    if "invalid_auth" in code or "not_authed" in code:
        return "Slack rejected the bot token. Paste the Bot User OAuth Token from your Slack app."
    if "missing_scope" in code:
        return "The Slack bot needs users:read.email, chat:write, and im:write, then reinstall it."
    if "Slack is not connected" in code:
        return "Slack is not connected. Paste the bot token, then send again."
    return f"Slack did not accept the message ({code})."


def _agent_log(message: str, data: dict, hypothesis: str) -> None:
    # #region agent log
    try:
        import json
        import time
        from pathlib import Path

        path = Path(__file__).resolve().parents[4] / ".cursor" / "debug-f3ff1c.log"
        payload = {
            "sessionId": "f3ff1c",
            "location": "newsletters.py:request_review",
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
            "hypothesisId": hypothesis,
            "runId": "slack-send",
        }
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")
    except Exception:
        pass
    # #endregion


def refresh_review_status(nl: Newsletter) -> None:
    if nl.status == NewsletterStatus.sent:
        return
    decisions = [section.lead_decision for section in nl.sections]
    if any(decision == "changes" for decision in decisions):
        nl.status = NewsletterStatus.changes_requested
    elif any(decision == "pending" for decision in decisions):
        nl.status = NewsletterStatus.in_review
    elif any(decision == "queued" for decision in decisions):
        nl.status = NewsletterStatus.ready_to_send
    elif decisions and all(decision == "approved" for decision in decisions):
        nl.status = NewsletterStatus.review_complete


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


def purge_expired_denials(db: Session, workspace_id: UUID) -> None:
    from zoneinfo import ZoneInfo

    today = datetime.now(ZoneInfo("America/Halifax")).date()
    zone = ZoneInfo("America/Halifax")
    rows = (
        db.query(Newsletter)
        .filter(
            Newsletter.workspace_id == workspace_id,
            Newsletter.status == NewsletterStatus.denied,
        )
        .all()
    )
    removed = False
    for nl in rows:
        stamp = nl.denied_at or nl.updated_at
        if stamp is None:
            continue
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        if stamp.astimezone(zone).date() < today:
            db.delete(nl)
            removed = True
    if removed:
        db.commit()


@router.get("", response_model=list[NewsletterSummary])
def list_newsletters(
    status_filter: NewsletterStatus | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    purge_expired_denials(db, user.workspace_id)
    q = db.query(Newsletter).filter(Newsletter.workspace_id == user.workspace_id)
    if status_filter:
        q = q.filter(Newsletter.status == status_filter)
    rows = (
        q.options(selectinload(Newsletter.sections).selectinload(Section.comments))
        .order_by(Newsletter.updated_at.desc())
        .all()
    )
    for nl in rows:
        notes = []
        for section in nl.sections:
            title = section.title or section.section_type.value.replace("_", " ")
            for comment in section.comments:
                if comment.resolved:
                    continue
                notes.append(
                    {
                        "section_id": section.id,
                        "section_title": title,
                        "body": comment.body,
                    }
                )
        nl.lead_notes = notes
    return rows


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
    if payload.saved is True or payload.body is not None or payload.title is not None:
        section.saved = True
        section.saved_at = datetime.now(timezone.utc)
    nl.updated_at = datetime.now(timezone.utc)
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
            instructions=payload.instructions or "",
            tone=payload.tone,
            tool=user.ai_tool or user.workspace.ai_provider,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    section.body = text
    db.commit()
    return {"body": text}


@router.post("/{newsletter_id}/sections/{section_id}/search", response_model=SearchOut)
async def search_section_sources(
    newsletter_id: UUID,
    section_id: UUID,
    payload: SearchIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_bader),
):
    nl = _load_newsletter(db, newsletter_id, user.workspace_id)
    section = next((s for s in nl.sections if s.id == section_id), None)
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    try:
        results = await search_verified(payload.query)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Verified search is unavailable right now") from exc
    return SearchOut(query=payload.query.strip(), results=results)


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
    payload: ReviewRequestIn,
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
    if not nl.sections:
        raise HTTPException(status_code=400, detail="Add at least one section before sending")
    email = valid_email(payload.lead_email)
    ensure_lead(db, nl, email)
    if not nl.review_token:
        nl.review_token = token_urlsafe(24)
    nl.lead_slack_email = email
    review_url = f"{settings.web_app_url.rstrip('/')}/r/{nl.review_token}"
    sections = [
        {
            "title": section.title or "",
            "section_type": section.section_type.value,
            "body": section.body or "",
        }
        for section in sorted(nl.sections, key=lambda s: s.sort_order)
    ]
    token = slack_service.valid_bot_token(user.workspace.slack_bot_token or settings.slack_bot_token)
    share_url = None
    if not token:
        ts = _email_review(email, nl.headline or nl.title, review_url, urgent=False)
        _agent_log("review emailed", {"delivered": True, "channel": "email"}, "D")
    else:
        try:
            send_settings = settings.model_copy(update={"slack_bot_token": token})
            ts = await slack_service.post_review_request(
                send_settings,
                newsletter_id=str(nl.id),
                title=nl.headline or nl.title,
                review_url=review_url,
                lead_email=email,
                sections=sections,
            )
        except RuntimeError as exc:
            if "invalid_auth" in str(exc) or "not_authed" in str(exc):
                user.workspace.slack_bot_token = None
                db.commit()
            _agent_log("slack send failed", {"delivered": False, "reason": str(exc)[:80]}, "C")
            raise HTTPException(status_code=502, detail=slack_detail(exc)) from exc
        _agent_log("slack send posted", {"delivered": True, "demo": str(ts).startswith("demo-")}, "B")
    sent_at = datetime.now(timezone.utc)
    nl.review_requested_at = sent_at
    for section in nl.sections:
        if section.lead_decision == "queued":
            continue
        if section.lead_decision != "approved":
            section.lead_decision = "pending"
            section.review_sent_at = sent_at
    nl.status = NewsletterStatus.in_review
    nl.slack_message_ts = ts
    _add_event(
        db,
        nl,
        user,
        "review_requested",
        f"Sent the full newsletter ({len(sections)} sections) to {email}: {review_url}",
        meta={"lead_email": email, "review_url": review_url, "demo": False},
    )
    db.commit()
    saved = _load_newsletter(db, newsletter_id, user.workspace_id)
    saved.slack_share_url = share_url
    return saved


@router.post("/{newsletter_id}/review/release", response_model=NewsletterOut)
def release_for_community(
    newsletter_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_bader),
):
    nl = _load_newsletter(db, newsletter_id, user.workspace_id)
    if nl.status not in (NewsletterStatus.review_complete, NewsletterStatus.ready_to_send):
        raise HTTPException(status_code=400, detail="The lead has not approved this newsletter")
    for section in nl.sections:
        section.lead_decision = "queued"
    nl.status = NewsletterStatus.ready_to_send
    _add_event(db, nl, user, "released", "Bader sent this approved newsletter to the final community copy")
    db.commit()
    return _load_newsletter(db, newsletter_id, user.workspace_id)


@router.post("/{newsletter_id}/review/urgent", response_model=NewsletterOut)
async def urgent_review(
    newsletter_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_bader),
    settings: Settings = Depends(get_settings),
):
    nl = _load_newsletter(db, newsletter_id, user.workspace_id)
    waiting = [s for s in nl.sections if s.lead_decision in ("pending", "changes")]
    if not waiting:
        _agent_log("urgent blocked", {"delivered": False, "reason": "nothing_waiting"}, "A")
        raise HTTPException(status_code=400, detail="Nothing is waiting on the lead")
    email = lead_email_for_follow_up(db, user, nl)
    ensure_lead(db, nl, email)
    if not nl.review_token:
        nl.review_token = token_urlsafe(24)
    nl.lead_slack_email = email
    review_url = f"{settings.web_app_url.rstrip('/')}/r/{nl.review_token}"
    sections = [
        {
            "title": section.title or "",
            "section_type": section.section_type.value,
            "body": section.body or "",
        }
        for section in sorted(nl.sections, key=lambda s: s.sort_order)
    ]
    token = slack_service.valid_bot_token(user.workspace.slack_bot_token or settings.slack_bot_token)
    share_url = None
    if not token:
        ts = _email_review(email, nl.headline or nl.title, review_url, urgent=True)
        _agent_log("urgent emailed", {"delivered": True, "channel": "email"}, "D")
    else:
        try:
            send_settings = settings.model_copy(update={"slack_bot_token": token})
            ts = await slack_service.post_review_request(
                send_settings,
                newsletter_id=str(nl.id),
                title=nl.headline or nl.title,
                review_url=review_url,
                lead_email=email,
                sections=sections,
                urgent=True,
            )
        except RuntimeError as exc:
            if "invalid_auth" in str(exc) or "not_authed" in str(exc):
                user.workspace.slack_bot_token = None
                db.commit()
            _agent_log("urgent failed", {"delivered": False, "reason": str(exc)[:80]}, "C")
            raise HTTPException(status_code=502, detail=slack_detail(exc)) from exc
        _agent_log("urgent posted", {"delivered": True, "demo": str(ts).startswith("demo-")}, "D")
    now = datetime.now(timezone.utc)
    for section in waiting:
        section.review_sent_at = now
    nl.slack_message_ts = ts
    _add_event(
        db,
        nl,
        user,
        "urgent_follow_up",
        f"Urgent follow-up sent to {nl.lead_slack_email}: {review_url}",
        meta={"lead_email": nl.lead_slack_email, "review_url": review_url, "urgent": True},
    )
    db.commit()
    saved = _load_newsletter(db, newsletter_id, user.workspace_id)
    saved.slack_share_url = share_url
    return saved


@router.post("/{newsletter_id}/sections/{section_id}/queue", response_model=NewsletterOut)
def queue_section_for_send(
    newsletter_id: UUID,
    section_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_bader),
):
    nl = _load_newsletter(db, newsletter_id, user.workspace_id)
    section = next((s for s in nl.sections if s.id == section_id), None)
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    if section.lead_decision != "approved":
        raise HTTPException(status_code=400, detail="Only a lead-approved section can be sent")
    section.lead_decision = "queued"
    refresh_review_status(nl)
    _add_event(
        db,
        nl,
        user,
        "section_queued",
        f"Sent {(section.title or section.section_type.value)} to the final newsletter",
    )
    db.commit()
    return _load_newsletter(db, newsletter_id, user.workspace_id)


@router.post("/{newsletter_id}/review/resubmit", response_model=NewsletterOut)
async def resubmit_for_approval(
    newsletter_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_bader),
    settings: Settings = Depends(get_settings),
):
    nl = _load_newsletter(db, newsletter_id, user.workspace_id)
    open_count = 0
    now = datetime.now(timezone.utc)
    for section in nl.sections:
        unresolved = [comment for comment in section.comments if not comment.resolved]
        if section.lead_decision != "changes" and not unresolved:
            continue
        for comment in unresolved:
            comment.resolved = True
            open_count += 1
        if section.lead_decision == "changes":
            section.lead_decision = "pending"
            section.review_sent_at = now
    if open_count == 0:
        raise HTTPException(status_code=400, detail="There are no lead recommendations to send back")
    email = lead_email_for_follow_up(db, user, nl)
    ensure_lead(db, nl, email)
    if not nl.review_token:
        nl.review_token = token_urlsafe(24)
    nl.lead_slack_email = email
    review_url = f"{settings.web_app_url.rstrip('/')}/r/{nl.review_token}"
    refresh_review_status(nl)
    sections = [
        {
            "title": section.title or "",
            "section_type": section.section_type.value,
            "body": section.body or "",
        }
        for section in sorted(nl.sections, key=lambda s: s.sort_order)
    ]
    token = slack_service.valid_bot_token(user.workspace.slack_bot_token or settings.slack_bot_token)
    if not token:
        ts = _email_review(email, nl.headline or nl.title, review_url, urgent=False)
    else:
        try:
            send_settings = settings.model_copy(update={"slack_bot_token": token})
            ts = await slack_service.post_review_request(
                send_settings,
                newsletter_id=str(nl.id),
                title=nl.headline or nl.title,
                review_url=review_url,
                lead_email=email,
                sections=sections,
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=slack_detail(exc)) from exc
    nl.review_requested_at = now
    nl.slack_message_ts = ts
    _add_event(
        db,
        nl,
        user,
        "review_requested",
        f"Bader sent the updated newsletter back to {email} for approval: {review_url}",
        meta={"lead_email": email, "review_url": review_url},
    )
    db.commit()
    return _load_newsletter(db, newsletter_id, user.workspace_id)


@router.post("/{newsletter_id}/review/confirm-changes", response_model=NewsletterOut)
def confirm_changes(
    newsletter_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_bader),
):
    nl = _load_newsletter(db, newsletter_id, user.workspace_id)
    open_count = 0
    now = datetime.now(timezone.utc)
    for section in nl.sections:
        if section.lead_decision != "changes":
            continue
        for comment in section.comments:
            if not comment.resolved:
                comment.resolved = True
                open_count += 1
        section.lead_decision = "pending"
        section.review_sent_at = now
    if open_count == 0:
        raise HTTPException(status_code=400, detail="There are no lead recommendations to confirm")
    refresh_review_status(nl)
    _add_event(
        db,
        nl,
        user,
        "changes_confirmed",
        f"Bader confirmed edits for {open_count} lead recommendation(s). Those sections are waiting on the lead again.",
    )
    db.commit()
    return _load_newsletter(db, newsletter_id, user.workspace_id)


@router.post("/{newsletter_id}/review/approve", response_model=NewsletterOut)
def approve_review(
    newsletter_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    nl = _load_newsletter(db, newsletter_id, user.workspace_id)
    for section in nl.sections:
        if section.lead_decision != "queued":
            section.lead_decision = "approved"
    refresh_review_status(nl)
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
    ) and not any(section.lead_decision == "queued" for section in nl.sections):
        raise HTTPException(status_code=400, detail="Lead approval is required before Mailchimp sync")
    result = await mailchimp_service.sync_campaign(
        settings, nl, reply_to=user.mailchimp_email
    )
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
