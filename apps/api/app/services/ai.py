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


async def generate_section_text(
    settings: Settings,
    workspace: Workspace,
    *,
    section_type: SectionType,
    topic: str | None,
    tone: str | None,
) -> str:
    if workspace.plan != PlanType.premium:
        raise PermissionError("AI generation requires a premium plan")

    prompt = SECTION_PROMPTS.get(section_type, "Write newsletter section copy.")
    topic_line = topic or section_type.value.replace("_", " ")
    tone_line = tone or "friendly"

    if not settings.openai_api_key:
        return (
            f"[Demo AI · {workspace.ai_provider or 'mock'} / "
            f"{workspace.ai_model or settings.openai_model}]\n\n"
            f"{prompt}\n\n"
            f"Topic: {topic_line}. Tone: {tone_line}. "
            f"This is placeholder copy for the {section_type.value.replace('_', ' ')} section. "
            "Edit freely, then save before moving on."
        )

    model = workspace.ai_model or settings.openai_model
    async with httpx.AsyncClient(timeout=45) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You write concise newsletter copy. No markdown headings.",
                    },
                    {
                        "role": "user",
                        "content": f"{prompt}\nTopic: {topic_line}\nTone: {tone_line}",
                    },
                ],
                "temperature": 0.7,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
