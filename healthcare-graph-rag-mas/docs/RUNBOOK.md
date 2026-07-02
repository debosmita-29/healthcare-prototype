# Runbook

## Generate a Briefing

1. Start Docker Compose.
2. Pull `llama3.2` in Ollama if needed.
3. Open the UI.
4. Enter a condition, such as `atopic dermatitis`.
5. Review graph progress, governance decision, RAGAS scores, evidence, and performance.

## Operate the Pipeline

- Use Phoenix to inspect traces when OpenTelemetry instrumentation is enabled.
- Use PostgreSQL to inspect persisted documents and chunks.
- Use Neo4j Browser to inspect condition-to-organization relationships.
- Use audit events for review packets and release gates.

## Production Hardening

- Replace offline fixtures with allowlisted API adapters for PubMed, ClinicalTrials.gov, FDA labels, CMS, and company filings.
- Enforce RBAC and tenant isolation.
- Add PHI redaction and DLP checks before persistence.
- Persist audit logs to append-only storage.
- Run the golden dataset in CI before model, prompt, or retrieval changes are released.
- Install `backend/requirements-full.txt` in ML-capable runners to enable FlagEmbedding BGE-M3, RAGAS, NeMo Guardrails, mem0, and Phoenix client packages.
