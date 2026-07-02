from __future__ import annotations

import httpx

from app.core.settings import Settings


async def fetch(condition: str, settings: Settings, client: httpx.AsyncClient, limit: int = 3) -> list[dict]:
    """Fetch CDC clinical guidance/reports mentioning `condition` from the Content Syndication API."""
    response = await client.get(
        settings.cdc_media_api_base_url,
        params={"title": condition, "max": limit, "sort": "-datepublished"},
    )
    response.raise_for_status()
    payload = response.json()
    results = payload.get("results") or []

    items = []
    for result in results:
        title = result.get("name")
        text = result.get("description")
        url = result.get("url")
        if not title or not text:
            continue
        items.append({"title": title, "text": text, "url": url})
    return items
