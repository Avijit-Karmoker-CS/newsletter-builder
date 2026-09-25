from __future__ import annotations

import shutil
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import ROOT, get_settings

settings = get_settings()


def _stable_database_url() -> str:
    """Always use one on-disk database so a restart does not open an empty file."""
    configured = settings.database_url
    if not configured.startswith("sqlite"):
        return configured
    relative = configured in {
        "sqlite:///./newsletter_builder.db",
        "sqlite:///newsletter_builder.db",
    } or configured.startswith("sqlite:///./")
    if not relative:
        return configured
    target = ROOT / "data" / "newsletter_builder.db"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        for source in (
            ROOT / "apps" / "api" / "newsletter_builder.db",
            ROOT / "newsletter_builder.db",
        ):
            if source.exists() and source.stat().st_size > 0:
                shutil.copy2(source, target)
                break
    return "sqlite:///" + target.as_posix()


DATABASE_URL = _stable_database_url()

_connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=not DATABASE_URL.startswith("sqlite"),
    connect_args=_connect_args,
)


if DATABASE_URL.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _sqlite_durable(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_schema() -> None:
    """Create tables and add columns introduced after the first SQLite file."""
    from sqlalchemy import text

    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    if not DATABASE_URL.startswith("sqlite"):
        return
    with engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(newsletters)")).fetchall()
        cols = {row[1] for row in rows}
        if "review_token" not in cols:
            conn.execute(text("ALTER TABLE newsletters ADD COLUMN review_token VARCHAR(64)"))
        if "lead_slack_email" not in cols:
            conn.execute(text("ALTER TABLE newsletters ADD COLUMN lead_slack_email VARCHAR(255)"))
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_newsletters_review_token "
                "ON newsletters (review_token)"
            )
        )
        user_rows = conn.execute(text("PRAGMA table_info(users)")).fetchall()
        user_cols = {row[1] for row in user_rows}
        if "mailchimp_email" not in user_cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN mailchimp_email VARCHAR(255)"))
        if "slack_email" not in user_cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN slack_email VARCHAR(255)"))
        if "ai_tool" not in user_cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN ai_tool VARCHAR(32)"))
        if "password_hash" not in user_cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)"))
        section_rows = conn.execute(text("PRAGMA table_info(sections)")).fetchall()
        section_cols = {row[1] for row in section_rows}
        if "ai_topic" not in section_cols:
            conn.execute(text("ALTER TABLE sections ADD COLUMN ai_topic VARCHAR(255)"))
        if "ai_instructions" not in section_cols:
            conn.execute(text("ALTER TABLE sections ADD COLUMN ai_instructions TEXT"))
        if "lead_decision" not in section_cols:
            conn.execute(text("ALTER TABLE sections ADD COLUMN lead_decision VARCHAR(32)"))
        if "review_sent_at" not in section_cols:
            conn.execute(text("ALTER TABLE sections ADD COLUMN review_sent_at DATETIME"))
        nl_rows = conn.execute(text("PRAGMA table_info(newsletters)")).fetchall()
        nl_cols = {row[1] for row in nl_rows}
        if "last_step" not in nl_cols:
            conn.execute(text("ALTER TABLE newsletters ADD COLUMN last_step VARCHAR(32)"))
        if "review_requested_at" not in nl_cols:
            conn.execute(text("ALTER TABLE newsletters ADD COLUMN review_requested_at DATETIME"))
        if "denied_at" not in nl_cols:
            conn.execute(text("ALTER TABLE newsletters ADD COLUMN denied_at DATETIME"))
        ws_rows = conn.execute(text("PRAGMA table_info(workspaces)")).fetchall()
        ws_cols = {row[1] for row in ws_rows}
        if "slack_bot_token" not in ws_cols:
            conn.execute(text("ALTER TABLE workspaces ADD COLUMN slack_bot_token VARCHAR(255)"))
