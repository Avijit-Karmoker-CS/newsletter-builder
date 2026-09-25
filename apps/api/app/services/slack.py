from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)


def build_review_blocks(
    newsletter_id: str,
    title: str,
    preview_url: str,
) -> list[dict[str, Any]]:
    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"Newsletter review: {title}"},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"Please review this draft.\n<{preview_url}|Open preview>",
            },
        },
        {
            "type": "actions",
            "block_id": f"review_{newsletter_id}",
            "elements": [
                {
                    "type": "button",
                    "action_id": "approve",
                    "text": {"type": "plain_text", "text": "Approve"},
                    "style": "primary",
                    "value": newsletter_id,
                },
                {
                    "type": "button",
                    "action_id": "request_changes",
                    "text": {"type": "plain_text", "text": "Request changes"},
                    "style": "danger",
                    "value": newsletter_id,
                },
            ],
        },
    ]


async def post_review_request(
    settings: Settings,
    *,
    newsletter_id: str,
    title: str,
) -> str | None:
    preview_url = f"{settings.web_app_url}/newsletters/{newsletter_id}/preview"
    blocks = build_review_blocks(newsletter_id, title, preview_url)

    if not settings.slack_bot_token:
        logger.info(
            "Slack demo mode — would post review for %s to %s: %s",
            newsletter_id,
            settings.slack_lead_channel,
            title,
        )
        return f"demo-ts-{newsletter_id[:8]}"

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {settings.slack_bot_token}"},
            json={
                "channel": settings.slack_lead_channel,
                "text": f"Newsletter review: {title}",
                "blocks": blocks,
            },
        )
        data = resp.json()
        if not data.get("ok"):
            logger.error("Slack post failed: %s", data)
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
