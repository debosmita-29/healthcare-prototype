from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    guideline = "guideline"
    literature = "literature"
    trial = "trial"
    company = "company"
    institution = "institution"
    knowledge_graph = "knowledge_graph"
    drug_label = "drug_label"


class TrustTier(str, Enum):
    high = "high"
    medium = "medium"
    exploratory = "exploratory"


class EvidenceRef(BaseModel):
    id: str
    source_type: SourceType
    title: str
    url: Optional[str] = None
    trust_tier: TrustTier = TrustTier.medium
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    published_at: Optional[datetime] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceDocument(EvidenceRef):
    condition: str
    text: str


class BriefingRequest(BaseModel):
    condition: str = Field(min_length=2, max_length=120)
    audience: str = "health system strategy team"
    include_companies: bool = True
    include_trials: bool = True
    max_wait_seconds: int = Field(default=90, ge=20, le=240)


class BriefingSection(BaseModel):
    title: str
    bullets: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class EvalReport(BaseModel):
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    safety: float
    notes: list[str] = Field(default_factory=list)


class GovernanceDecision(BaseModel):
    approved: bool
    reasons: list[str] = Field(default_factory=list)
    required_revisions: list[str] = Field(default_factory=list)


class CostPerformanceSummary(BaseModel):
    async_retrieval_ms: int = 0
    rag_ms: int = 0
    llm_ms: int = 0
    eval_ms: int = 0
    estimated_prompt_tokens: int = 0
    estimated_completion_tokens: int = 0
    llm_calls: int = 0
    evidence_refs_count: int = 0
    selected_context_count: int = 0


class BriefingResponse(BaseModel):
    run_id: str
    condition: str
    status: str
    executive_summary: str = ""
    sections: list[BriefingSection] = Field(default_factory=list)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    governance: Optional[GovernanceDecision] = None
    evaluation: Optional[EvalReport] = None
    performance: CostPerformanceSummary = Field(default_factory=CostPerformanceSummary)
    audit_events: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
