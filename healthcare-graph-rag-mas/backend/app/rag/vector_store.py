from __future__ import annotations

import json
from typing import Iterable

from app.models.schemas import EvidenceDocument
from app.rag.embedder import BgeM3Embedder


class PgVectorRepository:
    """PostgreSQL + pgvector adapter for durable evidence retrieval."""

    def __init__(self, database_url: str, embedder: BgeM3Embedder) -> None:
        self.database_url = database_url
        self.embedder = embedder
        self._pool = None

    async def connect(self) -> None:
        if self._pool is not None:
            return
        try:
            import asyncpg

            self._pool = await asyncpg.create_pool(self.database_url)
        except Exception:
            self._pool = False

    async def upsert_documents(self, documents: Iterable[EvidenceDocument]) -> None:
        await self.connect()
        if not self._pool:
            return
        try:
            async with self._pool.acquire() as conn:
                for doc in documents:
                    await conn.execute(
                        """
                        INSERT INTO evidence_documents
                        (id, condition, source_type, title, url, published_at, text, metadata)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb)
                        ON CONFLICT (id) DO UPDATE SET
                          title = EXCLUDED.title,
                          text = EXCLUDED.text,
                          metadata = EXCLUDED.metadata
                        """,
                        doc.id,
                        doc.condition,
                        doc.source_type.value,
                        doc.title,
                        doc.url,
                        doc.published_at,
                        doc.text,
                        json.dumps(doc.metadata),
                    )
                    chunks = self._chunk(doc.text)
                    embeddings = self.embedder.embed(chunks)
                    for index, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                        chunk_id = f"{doc.id}_{index}"
                        embedding_value = self._vector_literal(embedding)
                        await conn.execute(
                            """
                            INSERT INTO evidence_chunks
                            (id, document_id, chunk_index, text, embedding, metadata)
                            VALUES ($1, $2, $3, $4, $5::vector, $6::jsonb)
                            ON CONFLICT (id) DO UPDATE SET
                              text = EXCLUDED.text,
                              embedding = EXCLUDED.embedding,
                              metadata = EXCLUDED.metadata
                            """,
                            chunk_id,
                            doc.id,
                            index,
                            chunk,
                            embedding_value,
                            json.dumps({"source_type": doc.source_type.value, "trust_tier": doc.trust_tier.value}),
                        )
        except Exception:
            self._pool = False
            return

    async def search(self, query: str, condition: str, top_k: int = 10) -> list[dict]:
        await self.connect()
        if not self._pool:
            return []
        embedding = self._vector_literal(self.embedder.embed([query])[0])
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT c.id, c.document_id, c.text, d.title, d.url, d.source_type,
                           1 - (c.embedding <=> $1::vector) AS score
                    FROM evidence_chunks c
                    JOIN evidence_documents d ON d.id = c.document_id
                    WHERE d.condition ILIKE $2
                    ORDER BY c.embedding <=> $1::vector
                    LIMIT $3
                    """,
                    embedding,
                    condition,
                    top_k,
                )
            return [dict(row) for row in rows]
        except Exception:
            self._pool = False
            return []

    @staticmethod
    def _chunk(text: str, chunk_size: int = 900) -> list[str]:
        normalized = " ".join(text.split())
        return [normalized[i : i + chunk_size] for i in range(0, len(normalized), chunk_size)] or [normalized]

    @staticmethod
    def _vector_literal(values: list[float]) -> str:
        return "[" + ",".join(f"{value:.8f}" for value in values) + "]"
