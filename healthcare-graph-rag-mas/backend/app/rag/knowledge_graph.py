from __future__ import annotations

from app.models.schemas import EvidenceDocument


class Neo4jKnowledgeGraph:
    """Relational knowledge graph writer for company, asset, and evidence links."""

    def __init__(self, uri: str, username: str, password: str) -> None:
        self.uri = uri
        self.username = username
        self.password = password
        self._driver = None

    def connect(self) -> None:
        if self._driver is not None:
            return
        try:
            from neo4j import GraphDatabase

            self._driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))
        except Exception:
            self._driver = False

    def upsert_evidence_graph(self, documents: list[EvidenceDocument]) -> None:
        self.connect()
        if not self._driver:
            return
        try:
            with self._driver.session() as session:
                for doc in documents:
                    session.execute_write(self._merge_document, doc)
        except Exception:
            self._driver = False
            return

    @staticmethod
    def _merge_document(tx, doc: EvidenceDocument) -> None:
        tx.run(
            """
            MERGE (c:Condition {name: $condition})
            MERGE (e:Evidence {id: $evidence_id})
            SET e.title = $title, e.source_type = $source_type, e.url = $url, e.trust_tier = $trust_tier
            MERGE (c)-[:SUPPORTED_BY]->(e)
            """,
            condition=doc.condition,
            evidence_id=doc.id,
            title=doc.title,
            source_type=doc.source_type.value,
            url=doc.url,
            trust_tier=doc.trust_tier.value,
        )
        for company in doc.metadata.get("companies", []):
            tx.run(
                """
                MATCH (c:Condition {name: $condition})
                MERGE (org:Organization {name: $company})
                MERGE (org)-[:ACTIVE_IN]->(c)
                """,
                condition=doc.condition,
                company=company,
            )
