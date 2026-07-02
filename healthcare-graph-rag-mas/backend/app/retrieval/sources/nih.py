from __future__ import annotations

import re
from xml.etree import ElementTree

import httpx

from app.core.settings import Settings

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return " ".join(_TAG_RE.sub(" ", text).split())


async def fetch(condition: str, settings: Settings, client: httpx.AsyncClient) -> dict | None:
    """Fetch a treatment/diagnosis overview for `condition` from NIH MedlinePlus."""
    response = await client.get(
        settings.medlineplus_base_url,
        params={"db": "healthTopics", "term": condition, "retmax": 1},
    )
    response.raise_for_status()
    root = ElementTree.fromstring(response.text)
    document = root.find("./list/document")
    if document is None:
        return None

    title = None
    full_summary = None
    snippet = None
    for content in document.findall("content"):
        name = content.get("name")
        if name == "title" and title is None:
            title = _strip_html(content.text or "")
        elif name == "FullSummary" and full_summary is None:
            full_summary = _strip_html(content.text or "")
        elif name == "snippet" and snippet is None:
            snippet = _strip_html(content.text or "")

    summary = full_summary or snippet
    if not title or not summary:
        return None

    return {
        "title": title,
        "text": summary,
        "url": document.get("url"),
    }
