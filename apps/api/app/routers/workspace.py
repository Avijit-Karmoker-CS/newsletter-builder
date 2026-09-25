from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_bader
from app.models import PlanType, User, UserRole, Workspace
from app.routers.public_review import valid_email
from app.schemas import LeadOption, ProfileUpdate, UserOut, WorkspaceOut, WorkspaceUpdate
from app.services.slack import valid_bot_token

router = APIRouter(tags=["workspace"])


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserOut)
def update_profile(
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_bader),
):
    user.mailchimp_email = valid_email(payload.mailchimp_email)
    user.slack_email = valid_email(payload.slack_email)
    user.ai_tool = payload.ai_tool
    user.workspace.ai_provider = payload.ai_tool
    if payload.ai_tool == "claude":
        user.workspace.ai_model = "claude"
    else:
        user.workspace.ai_model = "cursor"
    db.commit()
    db.refresh(user)
    return user


@router.get("/workspace", response_model=WorkspaceOut)
def get_workspace(user: User = Depends(get_current_user)):
    return user.workspace


@router.get("/leads", response_model=list[LeadOption])
def list_leads(
    db: Session = Depends(get_db),
    user: User = Depends(require_bader),
):
    leads = (
        db.query(User)
        .filter(User.workspace_id == user.workspace_id, User.role == UserRole.lead)
        .order_by(User.name)
        .all()
    )
    return leads


@router.patch("/workspace", response_model=WorkspaceOut)
def update_workspace(
    payload: WorkspaceUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_bader),
):
    ws: Workspace = user.workspace
    data = payload.model_dump(exclude_unset=True)

    premium_fields = {
        "brand_color",
        "default_background_url",
        "headline_style",
        "ai_provider",
        "ai_model",
    }
    touching_premium = premium_fields.intersection(data.keys())
    if touching_premium and ws.plan != PlanType.premium and data.get("plan") != PlanType.premium:
        raise HTTPException(
            status_code=402,
            detail="Customization and AI settings require a premium plan",
        )

    if "slack_bot_token" in data:
        raw = (data.get("slack_bot_token") or "").strip()
        token = valid_bot_token(raw)
        if raw and not token:
            raise HTTPException(
                status_code=400,
                detail="That is not a Slack bot token. Copy the Bot User OAuth Token from api.slack.com. It starts with xoxb-.",
            )
        data["slack_bot_token"] = token or None

    for key, value in data.items():
        setattr(ws, key, value)
    db.commit()
    db.refresh(ws)
    return ws
