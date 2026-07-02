# Governance and Security Controls

## Safety Controls

- Input guardrails reject personal medical advice, emergency, and treatment-decision prompts.
- Output supervision requires evidence IDs, safety framing, investigational/approved distinction, and all required sections.
- The UI labels the artifact as organizational strategy intelligence, not patient advice.

## Auditability

Each graph node emits:

- `run_id`
- `node`
- `event_type`
- compact payload
- timestamp

Raw retrieved text is not passed through state. Evidence payloads are persisted and fetched on demand, which supports audit review without bloating the LLM context.

## Regulated Healthcare Posture

For production, add:

- SSO and RBAC
- tenant-scoped data partitions
- PHI redaction before persistence
- immutable audit log storage
- approved source allowlists
- model and prompt version pinning
- release validation against golden datasets

