from typing import Any, TypedDict

from app.models.schemas import (
    BriefingSection,
    CostPerformanceSummary,
    EvidenceRef,
    EvalReport,
    GovernanceDecision,
)


class GraphState(TypedDict, total=False):
    run_id: str
    condition: str
    audience: str
    include_companies: bool
    include_trials: bool
    plan: list[str]
    evidence_refs: list[EvidenceRef]
    selected_evidence_ids: list[str]
    selected_context: list[dict[str, Any]]
    executive_summary: str
    sections: list[BriefingSection]
    governance: GovernanceDecision
    evaluation: EvalReport
    performance: CostPerformanceSummary
    audit_events: list[dict[str, Any]]
    status: str
    errors: list[str]
