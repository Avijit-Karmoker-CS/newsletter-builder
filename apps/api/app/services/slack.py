from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)


def desktop_share_url(title: str, review_url: str, lead_email: str, urgent: bool = False) -> str:
    # slack.com/share now 301s to a help article. app.slack.com opens the signed-in client.
    del title, review_url, lead_email, urgent
    return "https://app.slack.com"


def valid_bot_token(value: str | None) -> str:
    token = (value or "").strip()
    if token.startswith("xoxb-") and len(token) >= 20:
        return token
    return ""


def build_review_blocks(
    title: str,
    review_url: str,
    sections: list[dict[str, str]],
    lead_email: str,
    urgent: bool = False,
) -> list[dict[str, Any]]:
    lines = [
        "Urgent follow-up. Please review this newsletter." if urgent else f"Full draft for <mailto:{lead_email}|{lead_email}>.",
        f"<{review_url}|Open the newsletter and approve or request changes>",
        "",
    ]
    for index, section in enumerate(sections, start=1):
        heading = section.get("title") or section.get("section_type") or f"Section {index}"
        body = (section.get("body") or "").strip()
        if len(body) > 400:
            body = body[:400].rstrip() + "…"
        lines.append(f"*{index}. {heading}*")
        if body:
            lines.append(body)
        lines.append("")
    text = "\n".join(lines).strip()
    if len(text) > 2900:
        text = text[:2900].rstrip() + "…"
    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": ("URGENT review request: " if urgent else "Newsletter review: ") + title[:120]},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": text},
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Open and approve"},
                    "url": review_url,
                    "style": "primary",
                    "action_id": "open_review",
                }
            ],
        },
    ]


async def _dm_channel(client: httpx.AsyncClient, settings: Settings, lead_email: str) -> str:
    lookup = await client.get(
        "https://slack.com/api/users.lookupByEmail",
        headers={"Authorization": f"Bearer {settings.slack_bot_token}"},
        params={"email": lead_email},
    )
    found = lookup.json()
    if not found.get("ok"):
        raise RuntimeError(
            f"No Slack user for {lead_email} ({found.get('error', 'lookup_failed')})"
        )
    opened = await client.post(
        "https://slack.com/api/conversations.open",
        headers={"Authorization": f"Bearer {settings.slack_bot_token}"},
        json={"users": found["user"]["id"]},
    )
    data = opened.json()
    if not data.get("ok"):
        raise RuntimeError(data.get("error", "slack_dm_failed"))
    return data["channel"]["id"]


async def post_review_request(
    settings: Settings,
    *,
    newsletter_id: str,
    title: str,
    review_url: str,
    lead_email: str,
    sections: list[dict[str, str]],
    urgent: bool = False,
) -> str | None:
    blocks = build_review_blocks(title, review_url, sections, lead_email, urgent=urgent)
    fallback = f"{'URGENT ' if urgent else ''}Newsletter review: {title} — {review_url}"

    if not settings.slack_bot_token:
        raise RuntimeError("Slack is not connected")

    async with httpx.AsyncClient(timeout=20) as client:
        channel = await _dm_channel(client, settings, lead_email)
        payload = {
            "channel": channel,
            "text": fallback,
            "blocks": blocks,
        }
        resp = await client.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {settings.slack_bot_token}"},
            json=payload,
        )
        data = resp.json()
        if not data.get("ok") and data.get("error") == "invalid_blocks":
            payload.pop("blocks")
            resp = await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={"Authorization": f"Bearer {settings.slack_bot_token}"},
                json=payload,
            )
            data = resp.json()
        if not data.get("ok"):
            logger.error("Slack post failed: %s", data.get("error"))
            raise RuntimeError(data.get("error", "slack_post_failed"))
        return data.get("ts")


async def open_changes_modal(
    settings: Settings,
    *,
    trigger_id: str,
    newsletter_id: str,
) -> None:
    if not settings.slack_bot_token:
        logger.info("Slack demo modal for newsletter %s", newsletter_id)
        return

    view = {
        "type": "modal",
        "callback_id": "request_changes_modal",
        "private_metadata": newsletter_id,
        "title": {"type": "plain_text", "text": "Request changes"},
        "submit": {"type": "plain_text", "text": "Submit"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "input",
                "block_id": "section_index",
                "label": {"type": "plain_text", "text": "Section number (1-based)"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "section_index_value",
                    "placeholder": {"type": "plain_text", "text": "e.g. 2"},
                },
            },
            {
                "type": "input",
                "block_id": "comment",
                "label": {"type": "plain_text", "text": "What should change?"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "comment_value",
                    "multiline": True,
                },
            },
        ],
    }

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            "https://slack.com/api/views.open",
            headers={"Authorization": f"Bearer {settings.slack_bot_token}"},
            json={"trigger_id": trigger_id, "view": view},
        )
        data = resp.json()
        if not data.get("ok"):
            logger.error("Slack modal failed: %s", data)
            raise RuntimeError(data.get("error", "slack_modal_failed"))
