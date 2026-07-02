from __future__ import annotations

import httpx

from app.core.settings import Settings


async def fetch(condition: str, settings: Settings, client: httpx.AsyncClient, limit: int = 2) -> list[dict]:
    """Fetch FDA-approved drug label information indicated for `condition` via openFDA."""
    params = {"search": f'indications_and_usage:"{condition}"', "limit": limit}
    if settings.openfda_api_key:
        params["api_key"] = settings.openfda_api_key

    response = await client.get(settings.openfda_label_base_url, params=params)
    if response.status_code == 404:
        return []
    response.raise_for_status()
    payload = response.json()
    results = payload.get("results") or []

    items = []
    for result in results:
        openfda = result.get("openfda", {})
        name = (openfda.get("brand_name") or openfda.get("generic_name") or ["Unnamed drug"])[0]
        indications = result.get("indications_and_usage") or []
        if not indications:
            continue
        warnings = result.get("boxed_warning") or result.get("warnings") or []
        text = " ".join(indications[:1] + warnings[:1])

        set_id = (openfda.get("spl_set_id") or [None])[0]
        url = (
            f"https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid={set_id}"
            if set_id
            else "https://labels.fda.gov/"
        )
        items.append({"title": f"FDA label: {name} — indicated for {condition}", "text": text, "url": url})
    return items
