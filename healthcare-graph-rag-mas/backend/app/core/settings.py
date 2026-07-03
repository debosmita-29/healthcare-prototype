from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    app_name: str = "Healthcare Graph RAG MAS"
    database_url: str = "postgresql://health:health@localhost:5432/healthrag"
    postgres_host: Optional[str] = None
    postgres_port: int = 5432
    postgres_user: str = "health"
    postgres_password: str = "health"
    postgres_db: str = "healthrag"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_host: Optional[str] = None
    neo4j_port: int = 7687
    neo4j_username: str = "neo4j"
    neo4j_password: str = "healthgraph"
    ollama_base_url: str = "http://localhost:11434"
    ollama_host: Optional[str] = None
    ollama_port: int = 11434
    ollama_model: str = "llama3.2"
    embedding_model: str = "BAAI/bge-m3"
    phoenix_collector_endpoint: Optional[str] = None
    phoenix_host: Optional[str] = None
    phoenix_port: int = 6006
    nemo_guardrails_config: Optional[str] = None
    mem0_enabled: bool = False
    mem0_vector_store_provider: str = "qdrant"
    mem0_qdrant_host: str = "localhost"
    mem0_qdrant_port: int = 6333
    mem0_qdrant_url: Optional[str] = None
    max_evidence_refs: int = Field(default=24, ge=4, le=100)
    rag_top_k: int = Field(default=10, ge=3, le=30)
    llm_timeout_seconds: float = 60.0
    golden_dataset_path: Path = Path("/app/data/golden/condition_briefings.jsonl")

    use_live_external_apis: bool = True
    external_api_timeout_seconds: float = 10.0
    medlineplus_base_url: str = "https://wsearch.nlm.nih.gov/ws/query"
    cdc_media_api_base_url: str = "https://tools.cdc.gov/api/v2/resources/media.json"
    openfda_label_base_url: str = "https://api.fda.gov/drug/label.json"
    pubmed_eutils_base_url: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    clinicaltrials_base_url: str = "https://clinicaltrials.gov/api/v2"
    ncbi_api_key: Optional[str] = None
    openfda_api_key: Optional[str] = None

    @property
    def effective_database_url(self) -> str:
        if not self.postgres_host:
            return self.database_url
        user = quote(self.postgres_user, safe="")
        password = quote(self.postgres_password, safe="")
        return f"postgresql://{user}:{password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def effective_neo4j_uri(self) -> str:
        if not self.neo4j_host:
            return self.neo4j_uri
        return f"bolt://{self.neo4j_host}:{self.neo4j_port}"

    @property
    def effective_ollama_base_url(self) -> str:
        if not self.ollama_host:
            return self.ollama_base_url
        return f"http://{self.ollama_host}:{self.ollama_port}"

    @property
    def effective_phoenix_collector_endpoint(self) -> Optional[str]:
        if not self.phoenix_host:
            return self.phoenix_collector_endpoint
        return f"http://{self.phoenix_host}:{self.phoenix_port}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
