"""Deterministic test embedder: hashed bag of word stems, L2-normalised."""

import math
import re
from hashlib import md5

from src.config import settings


class HashingEmbedder:
    model_name = "test-hashing-embedder"

    def __init__(self):
        self.calls = 0

    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * settings.EMBEDDING_DIM
        for word in re.findall(r"[а-яё]{4,}", text.lower()):
            stem = word[:5]
            index = int(md5(stem.encode()).hexdigest(), 16) % settings.EMBEDDING_DIM
            vector[index] += 1.0
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]

    async def embed_passages(self, texts: list[str]) -> list[list[float]]:
        self.calls += 1
        return [self._vector(t) for t in texts]

    async def embed_query(self, text: str) -> list[float] | None:
        self.calls += 1
        return self._vector(text)
