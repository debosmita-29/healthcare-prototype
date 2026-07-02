from __future__ import annotations


class LongTermMemory:
    """mem0 facade for reusable organizational preferences and prior strategy context."""

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled
        self._client = None
        self._fallback: dict[str, list[str]] = {}

    def connect(self) -> None:
        if self._client is not None or not self.enabled:
            return
        try:
            from mem0 import Memory

            self._client = Memory.from_config({"vector_store": {"provider": "qdrant"}})
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

