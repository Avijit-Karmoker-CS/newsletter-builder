from __future__ import annotations

from fastapi import Cookie, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import User, UserRole
from app.services.passwords import user_for_token


def get_current_user(
    authorization: str | None = Header(default=None),
    nb_session: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> User:
    token = nb_session
    if not token and authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    user = user_for_token(db, token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in required")
    loaded = (
        db.query(User)
        .options(joinedload(User.workspace))
        .filter(User.id == user.id)
        .first()
    )
    if not loaded:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in required")
    return loaded


def require_bader(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.bader:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bader role required")
    return user


def require_lead(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.lead:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Lead role required")
    return user
