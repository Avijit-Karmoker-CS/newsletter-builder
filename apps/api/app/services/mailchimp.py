from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import Settings
from app.models import Newsletter

logger = logging.getLogger(__name__)


def render_newsletter_html(newsletter: Newsletter) -> str:
    parts = [
        "<!DOCTYPE html><html><body style='font-family:Georgia,serif;margin:0;padding:0'>",
        f"<div style='background:url({newsletter.background_url or ''}) center/cover;#0f172a;padding:40px 24px'>",
        f"<h1 style='color:#fff;margin:0'>{newsletter.headline or newsletter.title}</h1>",
        f"<p style='color:#cbd5e1'>{newsletter.issue_date or ''}</p>",
        "</div>",
    ]
    for section in sorted(newsletter.sections, key=lambda s: s.sort_order):
        imgs = "".join(
            f"<img src='{url}' alt='' style='max-width:100%;margin:8px 0' />"
            for url in (section.image_urls or [])
        )
        parts.append(
            "<div style='padding:24px;border-bottom:1px solid #e2e8f0'>"
            f"<h2>{section.title or section.section_type.value.replace('_', ' ').title()}</h2>"
            f"<p>{(section.body or '').replace(chr(10), '<br/>')}</p>"
            f"{imgs}"
            "</div>"
        )
    parts.append("</body></html>")
    return "".join(parts)


def editor_url(settings: Settings, campaign_id: str) -> str:
    return (
        f"https://{settings.mailchimp_server_prefix}.admin.mailchimp.com/"
        f"campaigns/edit?id={campaign_id}"
    )


async def sync_campaign(settings: Settings, newsletter: Newsletter) -> dict[str, Any]:
    html = render_newsletter_html(newsletter)

    if not settings.mailchimp_api_key or not settings.mailchimp_list_id:
        campaign_id = newsletter.mailchimp_campaign_id or f"demo-{newsletter.id.hex[:12]}"
        url = editor_url(settings, campaign_id)
        logger.info("Mailchimp demo sync for %s → %s", newsletter.id, campaign_id)
        return {"campaign_id": campaign_id, "editor_url": url, "demo": True}

    base = f"https://{settings.mailchimp_server_prefix}.api.mailchimp.com/3.0"
    auth = ("anystring", settings.mailchimp_api_key)

    async with httpx.AsyncClient(timeout=30, auth=auth) as client:
        if newsletter.mailchimp_campaign_id:
            campaign_id = newsletter.mailchimp_campaign_id
            await client.patch(
                f"{base}/campaigns/{campaign_id}",
                json={
                    "settings": {
                        "subject_line": newsletter.headline or newsletter.title,
                        "title": newsletter.title,
                        "from_name": settings.mailchimp_from_name,
                        "reply_to": settings.mailchimp_reply_to,
                    }
                },
            )
        else:
            create = await client.post(
                f"{base}/campaigns",
                json={
                    "type": "regular",
                    "recipients": {"list_id": settings.mailchimp_list_id},
                    "settings": {
                        "subject_line": newsletter.headline or newsletter.title,
                        "title": newsletter.title,
                        "from_name": settings.mailchimp_from_name,
                        "reply_to": settings.mailchimp_reply_to,
                    },
                },
            )
            create.raise_for_status()
            campaign_id = create.json()["id"]

        content = await client.put(
            f"{base}/campaigns/{campaign_id}/content",
            json={"html": html},
        )
        content.raise_for_status()

    return {
        "campaign_id": campaign_id,
        "editor_url": editor_url(settings, campaign_id),
        "demo": False,
    }
