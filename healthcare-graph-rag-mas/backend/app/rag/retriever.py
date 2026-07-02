from __future__ import annotations

import re

import numpy as np

from app.models.schemas import EvidenceDocument, EvidenceRef
from app.rag.embedder import BgeM3Embedder
from app.retrieval.evidence_store import EvidenceStore

_CHUNK_TARGET_CHARS = 900  # sentence-boundary chunk target (~225 tokens at 4 chars/token)
_MAX_CONTEXT_TOKENS = 400  # hard ceiling per selected chunk; only clipped if a chunk exceeds this


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


class RagRetriever:
    def __init__(self, evidence_store: EvidenceStore, embedder: BgeM3Embedder) -> None:
        self.evidence_store = evidence_store
        self.embedder = embedder

    def select_context(self, condition: str, refs: list[EvidenceRef], top_k: int) -> tuple[list[str], list[dict]]:
        documents = self.evidence_store.get_many([ref.id for ref in refs])
        ref_by_id = {ref.id: ref for ref in refs}
        chunks: list[dict] = [
            {"doc": doc, "ref": ref_by_id.get(doc.id), "text": chunk_text}
            for doc in documents
            for chunk_text in self._chunk(doc.text)
        ]
        if not chunks:
            return [], []

        query_vec = np.array(self.embedder.embed([condition])[0])
        chunk_vecs = np.array(self.embedder.embed([chunk["text"] for chunk in chunks]))
        similarities = self._cosine_similarity(query_vec, chunk_vecs)

        for chunk, similarity in zip(chunks, similarities):
            trust_bonus = 0.05 if chunk["ref"] and chunk["ref"].trust_tier.value == "high" else 0.0
            chunk["score"] = float(similarity) + trust_bonus

        ranked = sorted(chunks, key=lambda chunk: chunk["score"], reverse=True)[:top_k]
        context = [self._to_context(chunk) for chunk in ranked]
        selected_ids = list(dict.fromkeys(item["evidence_id"] for item in context))
        return selected_ids, context

    @staticmethod
    def _cosine_similarity(query_vec: np.ndarray, matrix: np.ndarray) -> np.ndarray:
        query_norm = np.linalg.norm(query_vec)
        matrix_norms = np.linalg.norm(matrix, axis=1)
        denom = matrix_norms * query_norm
        denom[denom == 0] = 1e-9
        return (matrix @ query_vec) / denom

    @staticmethod
    def _chunk(text: str, target_chars: int = _CHUNK_TARGET_CHARS) -> list[str]:
        normalized = " ".join(text.split())
        if len(normalized) <= target_chars:
            return [normalized]
        sentences = re.split(r"(?<=[.!?])\s+", normalized)
        chunks: list[str] = []
        current = ""
        for sentence in sentences:
            candidate = f"{current} {sentence}".strip()
            if current and len(candidate) > target_chars:
                chunks.append(current)
                current = sentence
            else:
                current = candidate
        if current:
            chunks.append(current)
        return chunks or [normalized]

    @staticmethod
    def _to_context(chunk: dict) -> dict:
        doc: EvidenceDocument = chunk["doc"]
        text = chunk["text"]
        if _estimate_tokens(text) > _MAX_CONTEXT_TOKENS:
            allowed_chars = _MAX_CONTEXT_TOKENS * 4
            text = text[:allowed_chars].rsplit(" ", 1)[0] + "…"
        return {
            "evidence_id": doc.id,
            "title": doc.title,
            "source_type": doc.source_type.value,
            "trust_tier": doc.trust_tier.value,
            "url": doc.url,
            "excerpt": text,
            "metadata": doc.metadata,
            "similarity": round(chunk["score"], 4),
        }
