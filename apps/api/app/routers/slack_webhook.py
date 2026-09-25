from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy.orm import Session, joinedload

from app.config import Settings, get_settings
from app.database import get_db
from app.models import Newsletter, NewsletterStatus, ReviewEvent, SectionComment, User, UserRole
from app.services import slack as slack_service

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _lead_user(db: Session) -> User | None:
    return db.query(User).filter(User.role == UserRole.lead).first()


@router.post("/slack")
async def slack_interactions(
    request: Request,
    payload: str | None = Form(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    if payload is None:
        body = await request.body()
        raw = body.decode()
        if raw.startswith("payload="):
            from urllib.parse import parse_qs

            payload = parse_qs(raw).get("payload", [None])[0]
        else:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise HTTPException(status_code=400, detail="Invalid payload") from exc
            if data.get("type") == "url_verification":
                return {"challenge": data.get("challenge")}
            raise HTTPException(status_code=400, detail="Expected form payload")
    data = json.loads(payload)

    lead = _lead_user(db)
    event_type = data.get("type")

    if event_type == "block_actions":
        action = data["actions"][0]
        newsletter_id = UUID(action["value"])
        nl = (
            db.query(Newsletter)
            .options(joinedload(Newsletter.sections))
            .filter(Newsletter.id == newsletter_id)
            .first()
        )
        if not nl:
            return {"ok": False}

        if action["action_id"] == "approve":
            nl.status = NewsletterStatus.review_complete
            db.add(
                ReviewEvent(
                    newsletter_id=nl.id,
                    actor_id=lead.id if lead else None,
                    event_type="approved",
                    message="Approved via Slack",
                )
            )
            db.commit()
            return {"ok": True}

        if action["action_id"] == "request_changes":
            trigger_id = data.get("trigger_id")
            if trigger_id:
                await slack_service.open_changes_modal(
                    settings, trigger_id=trigger_id, newsletter_id=str(nl.id)
                )
            else:
                nl.status = NewsletterStatus.changes_requested
                db.add(
                    ReviewEvent(
                        newsletter_id=nl.id,
                        actor_id=lead.id if lead else None,
                        event_type="changes_requested",
                        message="Lead requested changes via Slack",
                    )
                )
                db.commit()
            return {"ok": True}

    if event_type == "view_submission" and data.get("view", {}).get("callback_id") == "request_changes_modal":
        view = data["view"]
        newsletter_id = UUID(view["private_metadata"])
        values = view["state"]["values"]
        section_raw = values["section_index"]["section_index_value"]["value"]
        comment_body = values["comment"]["comment_value"]["value"]
        try:
            section_index = int(section_raw)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Section number must be an integer") from exc

        nl = (
            db.query(Newsletter)
            .options(joinedload(Newsletter.sections))
            .filter(Newsletter.id == newsletter_id)
            .first()
        )
        if not nl:
            return {"response_action": "errors", "errors": {"section_index": "Not found"}}
        sections = sorted(nl.sections, key=lambda s: s.sort_order)
        if section_index < 1 or section_index > len(sections):
            return {
                "response_action": "errors",
                "errors": {"section_index": f"Use 1–{len(sections)}"},
            }
        section = sections[section_index - 1]
        db.add(
            SectionComment(
                section_id=section.id,
                author_id=lead.id if lead else None,
                body=comment_body,
            )
        )
        nl.status = NewsletterStatus.changes_requested
        db.add(
            ReviewEvent(
                newsletter_id=nl.id,
                actor_id=lead.id if lead else None,
                event_type="changes_requested",
                message=f"Section {section_index}: {comment_body}",
            )
        )
        db.commit()
        return {"response_action": "clear"}

    return {"ok": True}
