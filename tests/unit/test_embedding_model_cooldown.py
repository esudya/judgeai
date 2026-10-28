"""A model that failed to load is not retried on every call: fastembed's own download retries
take about 40 s, and an upload of several files would wait that long per file."""

import types

import pytest

from src.services import embeddings


@pytest.fixture
def broken_fastembed(monkeypatch):
    calls = []

    class Failing:
        def __init__(self, **kwargs):
            calls.append(kwargs)
            raise RuntimeError("download failed")

    monkeypatch.setattr(embeddings, "_model", None)
    monkeypatch.setattr(embeddings, "_failed_until", 0.0)
    monkeypatch.setattr(
        embeddings.importlib,
        "import_module",
        lambda name: types.SimpleNamespace(TextEmbedding=Failing),
    )
    return calls


async def test_failure_is_remembered_during_the_cooldown(broken_fastembed, monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(embeddings.time, "monotonic", lambda: now[0])
    with pytest.raises(RuntimeError, match="download failed"):
        await embeddings.get_embedding_model()
    with pytest.raises(RuntimeError, match="unavailable"):
        await embeddings.get_embedding_model()
    assert len(broken_fastembed) == 1
    now[0] += embeddings.LOAD_RETRY_SECONDS + 1
    with pytest.raises(RuntimeError, match="download failed"):
        await embeddings.get_embedding_model()
    assert len(broken_fastembed) == 2


async def test_successful_load_is_cached(monkeypatch):
    created = []

    class Model:
        def __init__(self, **kwargs):
            created.append(kwargs)

    monkeypatch.setattr(embeddings, "_model", None)
    monkeypatch.setattr(embeddings, "_failed_until", 0.0)
    monkeypatch.setattr(
        embeddings.importlib,
        "import_module",
        lambda name: types.SimpleNamespace(TextEmbedding=Model),
    )
    first = await embeddings.get_embedding_model()
    assert await embeddings.get_embedding_model() is first and len(created) == 1
