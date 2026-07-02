import pytest

from app.core.settings import Settings
from app.graph.orchestrator import BriefingGraphOrchestrator
from app.models.schemas import CostPerformanceSummary


@pytest.mark.asyncio
async def test_async_retrieval_stores_raw_text_outside_graph_state():
    orchestrator = BriefingGraphOrchestrator(Settings())
    state = {
        "run_id": "test_run",
        "condition": "atopic dermatitis",
        "audience": "strategy team",
        "include_companies": True,
        "include_trials": True,
        "evidence_refs": [],
        "selected_evidence_ids": [],
        "selected_context": [],
        "sections": [],
        "audit_events": [],
        "performance": CostPerformanceSummary(),
        "status": "running",
        "errors": [],
    }
    updated = await orchestrator.async_retrieval_fanout(state)
    assert updated["evidence_refs"]
    assert all(not hasattr(ref, "text") for ref in updated["evidence_refs"])

