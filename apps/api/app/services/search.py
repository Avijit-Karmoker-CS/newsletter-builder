from __future__ import annotations

import re
from typing import List
from urllib.parse import quote

import httpx

_TAG = re.compile(r"<[^>]+>")
_USER_AGENT = "NewsletterBuilder/1.0 (local research; verified Wikipedia lookup)"


def _plain(value: str) -> str:
    return _TAG.sub("", value or "").replace("&quot;", '"').replace("&#039;", "'").strip()


async def search_verified(query: str) -> List[dict]:
    text = query.strip()
    if not text:
        raise ValueError("Enter something to search")

    headers = {"User-Agent": _USER_AGENT, "Accept": "application/json"}
    async with httpx.AsyncClient(timeout=20, headers=headers, follow_redirects=True) as client:
        found = await client.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": text,
                "srlimit": 5,
                "srnamespace": 0,
                "format": "json",
                "utf8": 1,
            },
        )
        found.raise_for_status()
        hits = found.json().get("query", {}).get("search", [])
        clips: List[dict] = []
        for hit in hits:
            title = hit.get("title") or ""
            if not title:
                continue
            slug = quote(title.replace(" ", "_"), safe="()'")
            summary = await client.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{slug}")
            excerpt = ""
            url = f"https://en.wikipedia.org/wiki/{slug}"
            if summary.status_code == 200:
                data = summary.json()
                if data.get("type") == "disambiguation":
                    continue
                excerpt = (data.get("extract") or "").strip()
                desktop = (data.get("content_urls") or {}).get("desktop") or {}
                url = desktop.get("page") or url
            if not excerpt:
                excerpt = _plain(hit.get("snippet") or "")
            if not excerpt:
                continue
            clips.append(
                {
                    "title": title,
                    "excerpt": excerpt,
                    "url": url,
                    "source": "Wikipedia",
                }
            )
        return clips
