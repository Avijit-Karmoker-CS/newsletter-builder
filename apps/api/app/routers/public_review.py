from __future__ import annotations

import re
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import (
    Newsletter,
    NewsletterStatus,
    Section,
    SectionComment,
    User,
    UserRole,
)
from app.schemas import NewsletterOut, RecommendationsIn

router = APIRouter(prefix="/public/reviews", tags=["public-review"])

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def valid_email(value: str) -> str:
    email = value.strip().lower()
    if not _EMAIL.match(email):
        raise HTTPException(status_code=400, detail="Enter a valid lead email")
    return email


def load_by_token(db: Session, token: str) -> Newsletter:
    nl = (
        db.query(Newsletter)
        .options(
            joinedload(Newsletter.sections).joinedload(Section.comments),
            joinedload(Newsletter.review_events),
        )
        .filter(Newsletter.review_token == token)
        .first()
    )
    if not nl:
        raise HTTPException(status_code=404, detail="Review link not found")
    from app.routers.newsletters import apply_review_defaults

    apply_review_defaults(nl)
    return nl


def lead_author(db: Session, nl: Newsletter) -> User | None:
    if nl.lead_slack_email:
        user = db.query(User).filter(User.email == nl.lead_slack_email).first()
        if user:
            return user
    return (
        db.query(User)
        .filter(User.workspace_id == nl.workspace_id, User.role == UserRole.lead)
        .first()
    )


def ensure_lead(db: Session, nl: Newsletter, email: str) -> User:
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        if existing.workspace_id != nl.workspace_id:
            raise HTTPException(status_code=400, detail="That email belongs to another workspace")
        if existing.role != UserRole.lead:
            raise HTTPException(status_code=400, detail="Choose a lead Slack email, not Bader's")
        return existing
    user = User(
        workspace_id=nl.workspace_id,
        email=email,
        name=email.split("@", 1)[0],
        role=UserRole.lead,
    )
    db.add(user)
    db.flush()
    return user


@router.get("/{token}", response_model=NewsletterOut)
def get_public_review(token: str, db: Session = Depends(get_db)):
    return load_by_token(db, token)


@router.post("/{token}/sections/{section_id}/approve", response_model=NewsletterOut)
def approve_public_section(token: str, section_id: UUID, db: Session = Depends(get_db)):
    nl = load_by_token(db, token)
    section = next((item for item in nl.sections if item.id == section_id), None)
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    if section.lead_decision == "queued":
        raise HTTPException(status_code=400, detail="That section is already in the final newsletter")
    section.lead_decision = "approved"
    for comment in section.comments:
        comment.resolved = True
    from app.routers.newsletters import _add_event, refresh_review_status

    refresh_review_status(nl)
    lead = lead_author(db, nl)
    name = section.title or section.section_type.value.replace("_", " ")
    _add_event(db, nl, lead, "section_approved", f"Lead approved {name}")
    db.commit()
    return load_by_token(db, token)


@router.post("/{token}/deny", response_model=NewsletterOut)
def deny_public_review(token: str, db: Session = Depends(get_db)):
    nl = load_by_token(db, token)
    lead = lead_author(db, nl)
    from datetime import datetime, timezone

    from app.routers.newsletters import _add_event

    nl.status = NewsletterStatus.denied
    nl.denied_at = datetime.now(timezone.utc)
    _add_event(
        db,
        nl,
        lead,
        "denied",
        f"Lead denied the newsletter ({nl.lead_slack_email or 'lead'})",
    )
    db.commit()
    return load_by_token(db, token)


@router.post("/{token}/approve", response_model=NewsletterOut)
def approve_public_review(token: str, db: Session = Depends(get_db)):
    nl = load_by_token(db, token)
    lead = lead_author(db, nl)
    from app.routers.newsletters import _add_event, refresh_review_status

    approved = 0
    for section in nl.sections:
        if section.lead_decision == "queued":
            continue
        if any(not comment.resolved for comment in section.comments):
            section.lead_decision = "changes"
            continue
        section.lead_decision = "approved"
        approved += 1
    refresh_review_status(nl)
    _add_event(
        db,
        nl,
        lead,
        "approved",
        f"Lead approved {approved} section(s) via the Slack review link ({nl.lead_slack_email or 'lead'})",
    )
    db.commit()
    return load_by_token(db, token)


@router.post("/{token}/recommendations", response_model=NewsletterOut)
def submit_recommendations(
    token: str,
    payload: RecommendationsIn,
    db: Session = Depends(get_db),
):
    nl = load_by_token(db, token)
    lead = lead_author(db, nl)
    by_id = {section.id: section for section in nl.sections}
    notes: list[str] = []
    for item in payload.comments:
        section = by_id.get(item.section_id)
        if not section:
            raise HTTPException(status_code=400, detail="Unknown section in recommendations")
        body = item.body.strip()
        if not body:
            continue
        db.add(
            SectionComment(
                section_id=section.id,
                author_id=lead.id if lead else None,
                body=body,
            )
        )
        section.lead_decision = "changes"
        notes.append(f"Section {section.sort_order + 1}: {body}")
    if not notes:
        raise HTTPException(status_code=400, detail="Add a comment on at least one section")
    from app.routers.newsletters import _add_event, refresh_review_status

    refresh_review_status(nl)

    _add_event(
        db,
        nl,
        lead,
        "changes_requested",
        "Lead sent recommendations:\n" + "\n".join(notes),
    )
    db.commit()
    return load_by_token(db, token)
