from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock

from app.models.schemas import EvidenceDocument, EvidenceRef


@dataclass
class EvidenceStore:
    """Document store used to reduce LangGraph state to compact refs."""

    _documents: dict[str, EvidenceDocument] = field(default_factory=dict)
    _lock: RLock = field(default_factory=RLock)

    def upsert_many(self, documents: list[EvidenceDocument]) -> list[EvidenceRef]:
        refs: list[EvidenceRef] = []
        with self._lock:
            for doc in documents:
                self._documents[doc.id] = doc
                refs.append(EvidenceRef(**doc.model_dump(exclude={"condition", "text"})))
        return refs

    def get(self, evidence_id: str) -> EvidenceDocument | None:
        with self._lock:
            return self._documents.get(evidence_id)

    def get_many(self, evidence_ids: list[str]) -> list[EvidenceDocument]:
        with self._lock:
            return [self._documents[eid] for eid in evidence_ids if eid in self._documents]

    def list_refs(self, condition: str | None = None) -> list[EvidenceRef]:
        with self._lock:
            docs = list(self._documents.values())
        if condition:
            docs = [doc for doc in docs if doc.condition.lower() == condition.lower()]
        return [EvidenceRef(**doc.model_dump(exclude={"condition", "text"})) for doc in docs]


evidence_store = EvidenceStore()

