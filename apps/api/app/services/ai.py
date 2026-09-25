from __future__ import annotations

import logging

import httpx

from app.config import Settings
from app.models import PlanType, SectionType, Workspace

logger = logging.getLogger(__name__)

SECTION_PROMPTS = {
    SectionType.news: "Write a short community news blurb (80-120 words).",
    SectionType.featured_story: "Write a featured founder/community story (120-180 words).",
    SectionType.tips: "Write 3 practical tips as short paragraphs.",
    SectionType.events: "Write an upcoming events teaser with dates placeholders.",
    SectionType.cta: "Write a clear call-to-action paragraph ending with a soft invite.",
}


def _writing_brief(
    section_type: SectionType,
    topic: str | None,
    instructions: str,
    tone: str | None,
) -> str:
    guide = SECTION_PROMPTS.get(section_type, "Write newsletter section copy.")
    topic_line = (topic or "").strip() or section_type.value.replace("_", " ")
    tone_line = tone or "friendly"
    return (
        f"{guide}\n"
        f"Topic: {topic_line}\n"
        f"Tone: {tone_line}\n"
        f"Write exactly the kind of text requested here:\n{instructions.strip()}"
    )


async def generate_section_text(
    settings: Settings,
    workspace: Workspace,
    *,
    section_type: SectionType,
    topic: str | None,
    instructions: str,
    tone: str | None,
    tool: str | None,
) -> str:
    if workspace.plan != PlanType.premium:
        raise PermissionError("AI generation requires a premium plan")

    chosen = tool if tool in ("claude", "cursor") else "claude"
    brief = _writing_brief(section_type, topic, instructions, tone)

    if chosen == "claude" and settings.anthropic_api_key:
        async with httpx.AsyncClient(timeout=45) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": settings.claude_model,
                    "max_tokens": 600,
                    "system": "You write concise newsletter copy. No markdown headings.",
                    "messages": [{"role": "user", "content": brief}],
                },
            )
            resp.raise_for_status()
            data = resp.json()
            parts = data.get("content") or []
            text = "".join(part.get("text", "") for part in parts if part.get("type") == "text")
            return text.strip()

    topic_line = (topic or "").strip() or section_type.value.replace("_", " ")
    kind = instructions.strip()
    label = "Claude" if chosen == "claude" else "Cursor"
    return (
        f"{kind}\n\n"
        f"This {section_type.value.replace('_', ' ')} is about {topic_line}. "
        f"{label} followed your direction: {kind}"
    )
