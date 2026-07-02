from __future__ import annotations

import json
import time
from pathlib import Path

from app.models.schemas import BriefingSection, EvalReport


class RagasEvaluator:
    def __init__(self, golden_dataset_path: Path) -> None:
        self.golden_dataset_path = golden_dataset_path

    async def evaluate(
        self,
        condition: str,
        executive_summary: str,
        sections: list[BriefingSection],
        evidence_context: list[dict],
    ) -> tuple[EvalReport, int]:
        started = time.perf_counter()
        golden = self._load_golden(condition)
        text = " ".join([executive_summary] + [bullet for section in sections for bullet in section.bullets]).lower()
        evidence_text = " ".join(item.get("excerpt", "") for item in evidence_context).lower()
        required_topics = golden.get("required_topics", ["standard of care", "emerging treatments", "companies"])
        topic_hits = sum(1 for topic in required_topics if topic.lower() in text)
        companies = golden.get("ground_truth_companies", [])
        company_hits = sum(1 for company in companies if company.lower() in text or company.lower() in evidence_text)
        safety_notes = golden.get("must_have_safety_notes", [])
        safety_hits = sum(1 for note in safety_notes if any(word in text for word in note.lower().split()[:3]))
        report = EvalReport(
            faithfulness=min(1.0, 0.65 + 0.05 * len(evidence_context)),
            answer_relevancy=topic_hits / max(1, len(required_topics)),
            context_precision=min(1.0, 0.7 + 0.06 * len({item["source_type"] for item in evidence_context})),
            safety=min(1.0, 0.5 + 0.25 * safety_hits),
            notes=[
                "Prototype uses deterministic RAGAS-style scoring when a judge model is unavailable.",
                f"Matched {topic_hits}/{len(required_topics)} required topics.",
                f"Matched {company_hits}/{len(companies)} expected companies in briefing or evidence.",
            ],
        )
        return report, int((time.perf_counter() - started) * 1000)

    def _load_golden(self, condition: str) -> dict:
        if not self.golden_dataset_path.exists():
            return {}
        condition_lower = condition.lower()
        with self.golden_dataset_path.open() as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("condition", "").lower() in condition_lower or condition_lower in row.get("condition", "").lower():
                    return row
        return {}
