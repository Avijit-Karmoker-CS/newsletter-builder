from __future__ import annotations

"""Seed default workspace, Bader, and Lead users."""

from app.config import get_settings
from app.database import SessionLocal, engine, Base
from app.models import PlanType, User, UserRole, Workspace


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    settings = get_settings()
    db = SessionLocal()
    try:
        ws = db.query(Workspace).first()
        if not ws:
            plan = PlanType.premium if settings.default_workspace_plan == "premium" else PlanType.free
            ws = Workspace(
                name="Volta Newsletter",
                plan=plan,
                brand_color="#0f766e",
                headline_style="classic",
                ai_provider="openai",
                ai_model=settings.openai_model,
            )
            db.add(ws)
            db.flush()

        if not db.query(User).filter(User.email == "bader@example.com").first():
            db.add(
                User(
                    workspace_id=ws.id,
                    email="bader@example.com",
                    name="Bader",
                    role=UserRole.bader,
                )
            )
        if not db.query(User).filter(User.email == "lead@example.com").first():
            db.add(
                User(
                    workspace_id=ws.id,
                    email="lead@example.com",
                    name="Lead Approver",
                    role=UserRole.lead,
                )
            )
        db.commit()
        print("Seed complete: workspace + bader@example.com + lead@example.com")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
