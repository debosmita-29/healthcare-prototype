from __future__ import annotations

import re

from app.models.schemas import BriefingSection, GovernanceDecision


PERSONAL_MEDICAL_PATTERNS = [
    re.compile(r"\bshould i\b", re.I),
    re.compile(r"\bmy medication\b", re.I),
    re.compile(r"\bdiagnose me\b", re.I),
    re.compile(r"\bemergency\b", re.I),
]


class HealthcareGuardrails:
    def validate_input(self, condition: str) -> GovernanceDecision:
        for pattern in PERSONAL_MEDICAL_PATTERNS:
            if pattern.search(condition):
                return GovernanceDecision(
                    approved=False,
                    reasons=["Input appears to request personal medical advice or emergency guidance."],
                    required_revisions=["Submit a medical condition or therapeutic area for strategy research."],
                )
        return GovernanceDecision(approved=True, reasons=["Input accepted for organizational strategy briefing."])

    def supervise_output(
        self,
        executive_summary: str,
        sections: list[BriefingSection],
        selected_evidence_ids: list[str],
    ) -> GovernanceDecision:
        reasons: list[str] = []
        revisions: list[str] = []
        text = " ".join([executive_summary] + [bullet for section in sections for bullet in section.bullets])
        if not selected_evidence_ids:
            revisions.append("No evidence IDs selected for grounding.")
        if "not personalized medical advice" not in text.lower():
            revisions.append("Add explicit non-personalized-medical-advice safety framing.")
        if not any("investigational" in bullet.lower() for section in sections for bullet in section.bullets):
            revisions.append("Distinguish investigational assets from approved standard of care.")
        if len(sections) < 4:
            revisions.append("Briefing is missing required sections.")
        if revisions:
            return GovernanceDecision(approved=False, reasons=reasons, required_revisions=revisions)
        reasons.extend(
            [
                "Evidence IDs are attached.",
                "Safety framing is present.",
                "Investigational versus approved distinction is present.",
                "Required briefing sections are present.",
            ]
        )
        return GovernanceDecision(approved=True, reasons=reasons)

