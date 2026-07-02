# Engineering Principles

## Execution Model

- LangGraph owns the graph lifecycle and node ordering.
- Retrieval agents are asynchronous because external APIs are network-bound.
- `sync_join` is the deterministic aggregation point that normalizes retrieved evidence into compact references.
- The RAG, synthesis, supervisor, and eval path is synchronous to make quality gates ordered and auditable.
- FastAPI exposes both SSE and WebSocket channels for external API progress and UI updates.
- Researcher source routing is section-specific: NIH for current standard of care, PubMed plus ClinicalTrials.gov for emerging treatments, and PubMed plus ClinicalTrials.gov for companies/institutions.
- Writer output includes a `neo4j-briefing-v1` JSON graph with `nodes` and `relationships` arrays.
- The evaluator applies a citation-aware LLM-as-judge rubric for groundedness, relevance, citation-source alignment, citation coverage, and confidence. It falls back to deterministic scoring when the local judge model is unavailable.

## Performance

- Async fan-out reduces retrieval wall-clock time.
- State reduction passes `EvidenceRef` objects through graph state instead of raw source payloads.
- On-demand context fetching limits RAG prompt size to selected evidence only.
- Bounded `rag_top_k`, `max_evidence_refs`, and token estimates provide cost controls.
- The Ollama client centralizes LLM calls so budgets, model routing, and retries can be enforced in one place.

## Governance and Security

- Healthcare guardrails block personal medical advice and emergency prompts.
- Supervisor approval is required before RAGAS evaluation.
- Every graph node emits an audit event with compact payloads.
- NeMo Guardrails, mem0, Phoenix, PostgreSQL/pgvector, and Neo4j are integrated behind adapters so production policies can be applied without changing graph semantics.
- Production hardening should add RBAC, PHI redaction, tenant isolation, append-only audit storage, source allowlists, prompt/model versioning, and CI golden-set eval gates.
