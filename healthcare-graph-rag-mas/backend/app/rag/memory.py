from __future__ import annotations

from app.core.settings import Settings


class LongTermMemory:
    """mem0 facade for reusable organizational preferences and prior strategy context."""

    def __init__(self, settings: Settings | bool) -> None:
        if isinstance(settings, bool):
            self.enabled = settings
            self.settings = None
        else:
            self.enabled = settings.mem0_enabled
            self.settings = settings
        self._client = None
        self._fallback: dict[str, list[str]] = {}

    def connect(self) -> None:
        if self._client is not None or not self.enabled:
            return
        try:
            from mem0 import Memory

            self._client = Memory.from_config(self._config())
        except Exception:
            self._client = False

    def remember(self, user_id: str, text: str) -> None:
        self.connect()
        if self._client:
            self._client.add(text, user_id=user_id)
            return
        self._fallback.setdefault(user_id, []).append(text)

    def recall(self, user_id: str, query: str) -> list[str]:
        self.connect()
        if self._client:
            result = self._client.search(query, user_id=user_id)
            return [item.get("memory", "") for item in result]
        return self._fallback.get(user_id, [])[-5:]

    def _config(self) -> dict:
        if self.settings is None:
            return {"vector_store": {"provider": "qdrant"}}

        vector_config: dict = {"provider": self.settings.mem0_vector_store_provider}
        if self.settings.mem0_vector_store_provider == "qdrant":
            qdrant_config: dict = {}
            if self.settings.mem0_qdrant_url:
                qdrant_config["url"] = self.settings.mem0_qdrant_url
            else:
                qdrant_config["host"] = self.settings.mem0_qdrant_host
                qdrant_config["port"] = self.settings.mem0_qdrant_port
            vector_config["config"] = qdrant_config

        return {
            "vector_store": vector_config,
            "llm": {
                "provider": "ollama",
                "config": {
                    "model": self.settings.ollama_model,
                    "ollama_base_url": self.settings.effective_ollama_base_url,
                },
            },
        }
