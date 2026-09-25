from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.routers import newsletters, slack_webhook, workspace

settings = get_settings()

app = FastAPI(title="Newsletter Builder API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(workspace.router)
app.include_router(newsletters.router)
app.include_router(slack_webhook.router)

app.mount("/uploads", StaticFiles(directory=str(settings.upload_path)), name="uploads")


@app.get("/health")
def health():
    return {"ok": True}
