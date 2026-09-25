from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_bader
from app.models import PlanType, User, Workspace
from app.schemas import UserOut, WorkspaceOut, WorkspaceUpdate

router = APIRouter(tags=["workspace"])


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.get("/workspace", response_model=WorkspaceOut)
def get_workspace(user: User = Depends(get_current_user)):
    return user.workspace


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

    for key, value in data.items():
        setattr(ws, key, value)
    db.commit()
    db.refresh(ws)
    return ws
