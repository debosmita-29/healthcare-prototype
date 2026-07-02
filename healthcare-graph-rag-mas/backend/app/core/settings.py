from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    app_name: str = "Healthcare Graph RAG MAS"
    database_url: str = "postgresql://health:health@localhost:5432/healthrag"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: str = "healthgraph"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    embedding_model: str = "BAAI/bge-m3"
    phoenix_collector_endpoint: Optional[str] = None
    nemo_guardrails_config: Optional[str] = None
    mem0_enabled: bool = False
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
