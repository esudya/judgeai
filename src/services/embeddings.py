import asyncio
import importlib
from typing import Any

from src.config import settings

_model: Any = None
_lock = asyncio.Lock()


def _clean_text(text: str, limit: int = 8000) -> str:
    return " ".join(text.split())[:limit]


def _requires_prefix() -> bool:
    return "e5" in settings.EMBEDDING_MODEL.lower()


async def get_embedding_model() -> Any:
    global _model

    if _model is None:
        async with _lock:
            if _model is None:
                try:
                    fastembed = importlib.import_module("fastembed")
                    text_embedding_cls = getattr(fastembed, "TextEmbedding")
                    _model = await asyncio.to_thread(
                        text_embedding_cls,
                        model_name=settings.EMBEDDING_MODEL,
                        cache_dir=settings.EMBEDDING_CACHE_DIR,
                    )
                except ModuleNotFoundError:
                    raise RuntimeError(
                        "Пакет fastembed не установлен. "
                        "Выполни: uv pip install fastembed"
                    )

    return _model


async def embed_texts(texts: list[str], prefix: str = "") -> list[list[float]]:
    if not texts:
        return []

    cleaned = [_clean_text(text) for text in texts]

    if prefix:
        cleaned = [f"{prefix} {text}" for text in cleaned]

    model = await get_embedding_model()

    def _embed() -> list[list[float]]:
        vectors = list(model.embed(cleaned))

        return [
            vector.tolist() if hasattr(vector, "tolist") else list(vector)
            for vector in vectors
        ]

    return await asyncio.to_thread(_embed)


async def embed_query(text: str) -> list[float] | None:
    if not text.strip():
        return None

    prefix = "query:" if _requires_prefix() else ""
    vectors = await embed_texts([text], prefix=prefix)

    return vectors[0] if vectors else None


async def embed_passages(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    prefix = "passage:" if _requires_prefix() else ""
    return await embed_texts(texts, prefix=prefix)
