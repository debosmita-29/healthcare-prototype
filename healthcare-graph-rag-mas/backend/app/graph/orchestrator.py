from __future__ import annotations

import time
import uuid
from copy import deepcopy

from app.core.settings import Settings
from app.eval.ragas_runner import RagasEvaluator
from app.governance.guardrails import HealthcareGuardrails
from app.graph.state import GraphState
from app.models.schemas import (
    BriefingResponse,
    CostPerformanceSummary,
    EvidenceRef,
)
from app.observability.audit import audit_sink
from app.observability.phoenix import get_tracer, node_span
from app.rag.embedder import BgeM3Embedder
from app.rag.knowledge_graph import Neo4jKnowledgeGraph
from app.rag.llm import OllamaClient
from app.rag.memory import LongTermMemory
from app.rag.retriever import RagRetriever
from app.rag.vector_store import PgVectorRepository
from app.retrieval.evidence_store import evidence_store
from app.retrieval.external import ExternalRetrievalService


class BriefingGraphOrchestrator:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.guardrails = HealthcareGuardrails()
        self.external_retrieval = ExternalRetrievalService(settings)
        self.embedder = BgeM3Embedder(settings.embedding_model)
        self.rag = RagRetriever(evidence_store, self.embedder)
        self.vector_store = PgVectorRepository(settings.database_url, self.embedder)
        self.knowledge_graph = Neo4jKnowledgeGraph(settings.neo4j_uri, settings.neo4j_username, settings.neo4j_password)
        self.memory = LongTermMemory(settings.mem0_enabled)
        self.llm = OllamaClient(settings)
        self.evaluator = RagasEvaluator(settings.golden_dataset_path)
        self._compiled_graph = self._compile_graph()

    async def run(
        self,
        condition: str,
        audience: str,
        include_companies: bool,
        include_trials: bool,
        run_id: str | None = None,
    ) -> BriefingResponse:
        run_id = run_id or f"run_{uuid.uuid4().hex[:12]}"
        initial: GraphState = {
            "run_id": run_id,
            "condition": condition.strip(),
            "audience": audience,
            "include_companies": include_companies,
            "include_trials": include_trials,
            "evidence_refs": [],
            "selected_evidence_ids": [],
            "selected_context": [],
            "sections": [],
            "audit_events": [],
            "performance": CostPerformanceSummary(),
            "status": "running",
            "errors": [],
        }
        if self._compiled_graph:
            final_state = await self._compiled_graph.ainvoke(initial)
        else:
            final_state = await self._fallback_run(initial)
        final_state["audit_events"] = audit_sink.list(run_id)
        return self._to_response(final_state)

    def _compile_graph(self):
        try:
            from langgraph.graph import END, StateGraph

            graph = StateGraph(GraphState)
            graph.add_node("input_guardrails", self.input_guardrails)
            graph.add_node("planner", self.planner)
            graph.add_node("async_retrieval_fanout", self.async_retrieval_fanout)
            graph.add_node("sync_join", self.sync_join)
            graph.add_node("rag_select", self.rag_select)
            graph.add_node("synthesize", self.synthesize)
            graph.add_node("supervisor", self.supervisor)
            graph.add_node("evaluate", self.evaluate)
            graph.add_node("cost_performance", self.cost_performance)

            graph.set_entry_point("input_guardrails")
            graph.add_conditional_edges(
                "input_guardrails",
                self._input_route,
                {"continue": "planner", "blocked": END},
            )
            graph.add_edge("planner", "async_retrieval_fanout")
            graph.add_edge("async_retrieval_fanout", "sync_join")
            graph.add_edge("sync_join", "rag_select")
            graph.add_edge("rag_select", "synthesize")
            graph.add_edge("synthesize", "supervisor")
            graph.add_edge("supervisor", "evaluate")
            graph.add_edge("evaluate", "cost_performance")
            graph.add_edge("cost_performance", END)
            return graph.compile()
        except Exception:
            return None

    async def _fallback_run(self, state: GraphState) -> GraphState:
        for node in [
            self.input_guardrails,
            self.planner,
            self.async_retrieval_fanout,
            self.sync_join,
            self.rag_select,
            self.synthesize,
            self.supervisor,
        ]:
            state = await node(state)
            if state.get("status") == "blocked":
                return await self.cost_performance(state)
        if state.get("status") not in {"blocked"}:
            state = await self.evaluate(state)
        return await self.cost_performance(state)

    async def input_guardrails(self, state: GraphState) -> GraphState:
        state = deepcopy(state)
        decision = self.guardrails.validate_input(state["condition"])
        state["governance"] = decision
        if not decision.approved:
            state["status"] = "blocked"
        self._audit(state, "input_guardrails", "decision", decision.model_dump())
        return state

    async def planner(self, state: GraphState) -> GraphState:
        state = deepcopy(state)
        plan = [
            "Fetch standard-of-care sources",
            "Fetch emerging treatment literature",
            "Fetch clinical development activity",
            "Fetch company and institution ecosystem",
            "Join compact evidence references",
            "Run synchronous RAG and governance review",
        ]
        state["plan"] = plan
        self._audit(state, "planner", "plan_created", {"steps": plan})
        return state

    async def async_retrieval_fanout(self, state: GraphState) -> GraphState:
        state = deepcopy(state)
        started = time.perf_counter()
        with node_span("async_retrieval_fanout", {"condition": state["condition"]}):
            documents = await self.external_retrieval.fetch_all(
                state["condition"],
                include_trials=state.get("include_trials", True),
                include_companies=state.get("include_companies", True),
            )
            refs = evidence_store.upsert_many(documents)
            await self.vector_store.upsert_documents(documents)
            self.knowledge_graph.upsert_evidence_graph(documents)
            self.memory.remember("strategy-team", f"Generated evidence set for {state['condition']} with {len(refs)} refs.")
        performance = state["performance"]
        performance.async_retrieval_ms = int((time.perf_counter() - started) * 1000)
        state["performance"] = performance
        state["evidence_refs"] = refs
        self._audit(
            state,
            "async_retrieval_fanout",
            "retrieval_complete",
            {
                "documents_persisted": len(documents),
                "state_payload": "EvidenceRef only; raw text persisted in evidence store",
                "sources": sorted({ref.source_type.value for ref in refs}),
            },
        )
        fallback_providers = sorted(
            {
                doc.metadata.get("provider")
                for doc in documents
                if doc.metadata.get("retrieval_mode") == "offline_fallback"
            }
        )
        if fallback_providers:
            self._audit(
                state,
                "async_retrieval_fanout",
                "live_fetch_fallback",
                {"providers": fallback_providers, "reason": "live API call failed or returned no results"},
            )
        return state

    async def sync_join(self, state: GraphState) -> GraphState:
        state = deepcopy(state)
        refs = sorted(
            state.get("evidence_refs", []),
            key=lambda ref: (ref.trust_tier.value == "high", ref.score),
            reverse=True,
        )[: self.settings.max_evidence_refs]
        state["evidence_refs"] = refs
        self._audit(
            state,
            "sync_join",
            "joined",
            {"evidence_refs": len(refs), "raw_payload_bytes_in_state": 0},
        )
        return state

    async def rag_select(self, state: GraphState) -> GraphState:
        state = deepcopy(state)
        started = time.perf_counter()
        with node_span("rag_select", {"condition": state["condition"]}) as span:
            span.set_attribute("openinference.span.kind", "RETRIEVER")
            selected_ids, context = self.rag.select_context(
                state["condition"],
                state.get("evidence_refs", []),
                top_k=self.settings.rag_top_k,
            )
            span.set_attribute("retriever.selected_count", len(context))
        performance = state["performance"]
        performance.rag_ms = int((time.perf_counter() - started) * 1000)
        performance.selected_context_count = len(context)
        state["performance"] = performance
        state["selected_evidence_ids"] = selected_ids
        state["selected_context"] = context
        self._audit(
            state,
            "rag_select",
            "context_selected",
            {"selected_evidence_ids": selected_ids, "selected_context_count": len(context)},
        )
        return state

    async def synthesize(self, state: GraphState) -> GraphState:
        state = deepcopy(state)
        with node_span("synthesize", {"condition": state["condition"], "audience": state["audience"]}) as span:
            span.set_attribute("openinference.span.kind", "LLM")
            span.set_attribute("llm.model_name", self.settings.ollama_model)
            span.set_attribute("input.value", state["condition"])
            summary, sections, llm_ms = await self.llm.generate_briefing(
                state["condition"],
                state["audience"],
                state.get("selected_context", []),
            )
            span.set_attribute("llm.token_count.prompt", self.llm.prompt_tokens)
            span.set_attribute("llm.token_count.completion", self.llm.completion_tokens)
            span.set_attribute("output.value", summary[:500] if summary else "")
        performance = state["performance"]
        performance.llm_ms = llm_ms
        performance.llm_calls = self.llm.calls
        performance.estimated_prompt_tokens = self.llm.prompt_tokens
        performance.estimated_completion_tokens = self.llm.completion_tokens
        state["performance"] = performance
        state["executive_summary"] = summary
        state["sections"] = sections
        self._audit(
            state,
            "synthesize",
            "briefing_drafted",
            {"sections": [section.title for section in sections], "llm_ms": llm_ms},
        )
        return state

    async def supervisor(self, state: GraphState) -> GraphState:
        state = deepcopy(state)
        decision = self.guardrails.supervise_output(
            state.get("executive_summary", ""),
            state.get("sections", []),
            state.get("selected_evidence_ids", []),
        )
        state["governance"] = decision
        state["status"] = "approved" if decision.approved else "needs_revision"
        self._audit(state, "supervisor", "decision", decision.model_dump())
        return state

    async def evaluate(self, state: GraphState) -> GraphState:
        state = deepcopy(state)
        with node_span("evaluate", {"condition": state["condition"]}) as span:
            span.set_attribute("openinference.span.kind", "EVALUATOR")
            report, eval_ms = await self.evaluator.evaluate(
                state["condition"],
                state.get("executive_summary", ""),
                state.get("sections", []),
                state.get("selected_context", []),
            )
            span.set_attribute("eval.faithfulness", report.faithfulness)
            span.set_attribute("eval.answer_relevancy", report.answer_relevancy)
            span.set_attribute("eval.context_precision", report.context_precision)
            span.set_attribute("eval.safety", report.safety)
        performance = state["performance"]
        performance.eval_ms = eval_ms
        state["performance"] = performance
        state["evaluation"] = report
        self._audit(state, "evaluate", "ragas_report", report.model_dump())
        return state

    async def cost_performance(self, state: GraphState) -> GraphState:
        state = deepcopy(state)
        performance = state["performance"]
        performance.evidence_refs_count = len(state.get("evidence_refs", []))
        state["performance"] = performance
        if state.get("status") not in {"blocked", "needs_revision"}:
            state["status"] = "complete"
        self._audit(
            state,
            "cost_performance",
            "summary",
            performance.model_dump(),
        )
        return state

    @staticmethod
    def _input_route(state: GraphState) -> str:
        return "blocked" if state.get("status") == "blocked" else "continue"

    @staticmethod
    def _audit(state: GraphState, node: str, event_type: str, payload: dict) -> None:
        audit_sink.emit(state["run_id"], node, event_type, payload)

    @staticmethod
    def _to_response(state: GraphState) -> BriefingResponse:
        return BriefingResponse(
            run_id=state["run_id"],
            condition=state["condition"],
            status=state.get("status", "unknown"),
            executive_summary=state.get("executive_summary", ""),
            sections=state.get("sections", []),
            evidence=state.get("evidence_refs", []),
            governance=state.get("governance"),
            evaluation=state.get("evaluation"),
            performance=state.get("performance", CostPerformanceSummary()),
            audit_events=state.get("audit_events", []),
        )
