from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.config import Settings, get_settings
from app.database import get_db
from app.models import User, UserRole


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    email = None
    if token == settings.demo_bader_token:
        email = "bader@example.com"
    elif token == settings.demo_lead_token:
        email = "lead@example.com"
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = (
        db.query(User)
        .options(joinedload(User.workspace))
        .filter(User.email == email)
        .first()
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not seeded")
    return user


def require_bader(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.bader:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bader role required")
    return user


def require_lead(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.lead:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Lead role required")
    return user
