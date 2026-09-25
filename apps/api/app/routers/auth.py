from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user
from app.models import PlanType, User, UserRole, Workspace
from app.routers.public_review import valid_email
from app.schemas import UserOut
from app.services.passwords import (
    COOKIE_NAME,
    SESSION_DAYS,
    create_session,
    hash_password,
    revoke_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class AuthStatus(BaseModel):
    password_set: bool


class RegisterIn(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=8, max_length=128)
    mailchimp_email: str = Field(min_length=3)
    slack_email: str = Field(min_length=3)
    ai_tool: str = Field(pattern="^(claude|cursor)$")


class LoginIn(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=1, max_length=128)


def _cookie_secure() -> bool:
    return get_settings().web_app_url.startswith("https://")


def _set_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=_cookie_secure(),
        max_age=SESSION_DAYS * 24 * 60 * 60,
        path="/",
    )


@router.get("/status", response_model=AuthStatus)
def auth_status(db: Session = Depends(get_db)):
    ready = (
        db.query(User)
        .filter(User.role == UserRole.bader, User.password_hash.isnot(None))
        .first()
    )
    return AuthStatus(password_set=bool(ready and ready.password_hash))


@router.post("/register", response_model=UserOut)
def register(payload: RegisterIn, response: Response, db: Session = Depends(get_db)):
    email = valid_email(payload.email)
    existing = db.query(User).filter(User.email == email).first()
    if existing and existing.password_hash:
        raise HTTPException(status_code=409, detail="That email already has an account. Log in instead.")
    if existing and existing.role != UserRole.bader:
        raise HTTPException(status_code=400, detail="That email is already used")

    settings = get_settings()
    plan = PlanType.premium if settings.default_workspace_plan == "premium" else PlanType.free
    if existing:
        user = existing
        if user.workspace is None:
            user.workspace = db.query(Workspace).filter(Workspace.id == user.workspace_id).first()
    else:
        workspace = Workspace(
            name="Newsletter Builder",
            plan=plan,
            brand_color="#0f766e",
            headline_style="classic",
            ai_provider=payload.ai_tool,
            ai_model=payload.ai_tool,
        )
        db.add(workspace)
        db.flush()
        user = User(
            workspace_id=workspace.id,
            email=email,
            name=email.split("@", 1)[0],
            role=UserRole.bader,
        )
        db.add(user)
        db.flush()

    user.email = email
    user.name = email.split("@", 1)[0]
    user.password_hash = hash_password(payload.password)
    user.mailchimp_email = valid_email(payload.mailchimp_email)
    user.slack_email = valid_email(payload.slack_email)
    user.ai_tool = payload.ai_tool
    if user.workspace:
        user.workspace.ai_provider = payload.ai_tool
        user.workspace.ai_model = payload.ai_tool
    token = create_session(db, user)
    _set_cookie(response, token)
    return (
        db.query(User)
        .options(joinedload(User.workspace))
        .filter(User.id == user.id)
        .one()
    )


@router.post("/login", response_model=UserOut)
def login(payload: LoginIn, response: Response, db: Session = Depends(get_db)):
    email = valid_email(payload.email)
    user = (
        db.query(User)
        .options(joinedload(User.workspace))
        .filter(User.email == email, User.role == UserRole.bader)
        .first()
    )
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email or password is incorrect")
    token = create_session(db, user)
    _set_cookie(response, token)
    return user


@router.post("/logout")
def logout(
    response: Response,
    db: Session = Depends(get_db),
    nb_session: str | None = Cookie(default=None),
    user: User = Depends(get_current_user),
):
    revoke_token(db, nb_session)
    response.delete_cookie(COOKIE_NAME, path="/", secure=_cookie_secure(), samesite="lax")
    return {"ok": True}
