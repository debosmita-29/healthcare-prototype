# Healthcare Graph RAG Multi-Agent System

An end-to-end prototype for a health system strategy team that generates a structured medical-condition briefing covering:

- Current standard of care
- Emerging treatments in development
- Key companies and institutions
- Evidence quality, governance checks, audit trail, and RAGAS-style evaluation

The system uses a hybrid graph architecture: external retrieval runs asynchronously, then a synchronous join node aggregates compact evidence references into a deterministic RAG and supervision pipeline.

## Stack

- Graph orchestrator: LangGraph
- API and streaming: FastAPI with SSE and WebSocket
- RAG: BAAI/bge-m3 embeddings, PostgreSQL, pgvector
- Relational knowledge graph: Neo4j
- LLM: Ollama llama3.2
- Long-term memory: mem0 integration point
- Guardrails: NVIDIA NeMo Guardrails integration point plus local healthcare policy checks
- Eval: RAGAS-style LLM-as-judge harness with golden annotations
- Observability: Phoenix/OpenTelemetry integration point plus local audit events
- Deployment: Docker Compose
- UI: React

## Quick Start

```bash
cd /Users/debosmitaroy/Documents/Prototype/healthcare-graph-rag-mas
docker compose up --build
```

Open:

- UI: http://localhost:5173
- API: http://localhost:8000/docs
- Phoenix: http://localhost:6006
- Neo4j: internal Docker service `bolt://neo4j:7687` (host ports left unmapped to avoid local DB conflicts)
- Ollama host port: http://localhost:11435

If Ollama has not pulled the model yet:

```bash
docker compose exec ollama ollama pull llama3.2
```

## Local Backend Development

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

For full ML/governance integrations in an environment that can install the heavier model stack:

```bash
pip install -r requirements-full.txt
```

## Design Notes

The orchestration state intentionally avoids passing raw retrieved documents between nodes. Retrieval adapters persist raw payloads into an evidence store and return compact `EvidenceRef` objects. Downstream synthesis fetches only the selected source text on demand.

The supervisor node gates output before evaluation. Only approved briefings run through the RAGAS-style evaluator against golden annotations, reflecting regulated healthcare workflows where quality gates precede broad distribution.
