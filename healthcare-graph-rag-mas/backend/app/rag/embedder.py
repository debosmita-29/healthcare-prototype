from __future__ import annotations

import hashlib

import numpy as np


class BgeM3Embedder:
    def __init__(self, model_name: str = "BAAI/bge-m3") -> None:
        self.model_name = model_name
        self._model = None

    def _load(self) -> None:
        if self._model is not None:
            return
        try:
            from FlagEmbedding import BGEM3FlagModel

            self._model = BGEM3FlagModel(self.model_name, use_fp16=True)
        except Exception:
            self._model = False

    def embed(self, texts: list[str]) -> list[list[float]]:
        self._load()
        if self._model:
            output = self._model.encode(texts, return_dense=True)
            return output["dense_vecs"].tolist()
        return [self._fallback_embedding(text) for text in texts]

    @staticmethod
    def _fallback_embedding(text: str, dim: int = 1024) -> list[float]:
        vector = np.zeros(dim, dtype=np.float32)
        for token in text.lower().split():
            idx = int(hashlib.sha256(token.encode()).hexdigest(), 16) % dim
            vector[idx] += 1.0
        norm = np.linalg.norm(vector)
        if norm:
            vector = vector / norm
        return vector.tolist()

