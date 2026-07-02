from __future__ import annotations

import httpx

from app.core.settings import Settings


async def fetch(condition: str, settings: Settings, client: httpx.AsyncClient, limit: int = 5) -> list[dict]:
    """Fetch active clinical trials for `condition` from the ClinicalTrials.gov API v2."""
    response = await client.get(
        f"{settings.clinicaltrials_base_url}/studies",
        params={
            "query.cond": condition,
            "pageSize": limit,
            "format": "json",
            "fields": (
                "NCTId,BriefTitle,BriefSummary,OverallStatus,"
                "Phase,StartDate,CompletionDate,LeadSponsorName"
            ),
        },
    )
    response.raise_for_status()
    data = response.json()
    studies = data.get("studies", [])

    items = []
    for study in studies:
        protocol = study.get("protocolSection", {})
        identification = protocol.get("identificationModule", {})
        description = protocol.get("descriptionModule", {})
        status_module = protocol.get("statusModule", {})
        design_module = protocol.get("designModule", {})
        sponsor_module = protocol.get("sponsorCollaboratorsModule", {})

        nct_id = identification.get("nctId")
        title = identification.get("briefTitle")
        summary = description.get("briefSummary", "").strip()
        overall_status = status_module.get("overallStatus", "")
        phases = design_module.get("phases", [])
        phase_text = ", ".join(phases) if phases else "Phase Not Specified"
        sponsor = sponsor_module.get("leadSponsor", {}).get("name", "")

        if not nct_id or not title or not summary:
            continue

        parts = []
        if overall_status:
            parts.append(f"Status: {overall_status}")
        if phase_text:
            parts.append(f"Phase: {phase_text}")
        if sponsor:
            parts.append(f"Lead Sponsor: {sponsor}")
        prefix = ". ".join(parts)
        text = f"{prefix}. {summary}" if prefix else summary

        items.append(
            {
                "title": title,
                "text": text,
                "url": f"https://clinicaltrials.gov/study/{nct_id}",
                "nct_id": nct_id,
                "sponsor": sponsor,
                "phase": phase_text,
                "status": overall_status,
            }
        )
    return items
