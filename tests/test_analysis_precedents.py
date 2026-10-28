"""Case analysis uses the precedent cards (T24–T27) and compares the draft with practice (T28)."""

import pytest

from src.application.precedent_cards import CARD_EXTRACTOR_VERSION
from src.application.similar_precedents import IndexPrecedents
from src.db.models import KnowledgeVerdict
from src.db.session import async_session_factory
from src.infrastructure.precedent_store import SqlPrecedentStore
from src.infrastructure.verdict_reader import RegexVerdictReader
from tests.fixtures.fake_embedder import HashingEmbedder
from tests.fixtures.synthetic_verdicts import PRACTICE_ROBBERY, PRACTICE_THEFT, SINGLE_CONDITIONAL

TERM = "на срок 1 (один) год 6 (шесть) месяцев"
# Same qualification, different terms: 6, 12, 18, 24, 30 and 36 months.
TERMS = {
    6: "на срок 6 (шесть) месяцев",
    12: "на срок 1 (один) год",
    18: TERM,
    24: "на срок 2 (два) года",
    30: "на срок 2 (два) года 6 (шесть) месяцев",
    36: "на срок 3 (три) года",
}


def _theft(months: int, n: int) -> str:
    return PRACTICE_THEFT.replace(TERM, TERMS[months]).replace(
        "ноутбук", f"ноутбук № {n}"
    )  # distinct texts, otherwise deduplicated


@pytest.fixture(autouse=True)
def embedder(monkeypatch):
    fake = HashingEmbedder()
    monkeypatch.setattr("src.services.analysis_runner.get_precedent_embedder", lambda: fake)
    return fake


async def _practice(*texts):
    async with async_session_factory() as db:
        for i, text in enumerate(texts):
            db.add(KnowledgeVerdict(raw_text=text, source_type="manual", uid=f"u{i}"))
        await db.commit()
        store = SqlPrecedentStore(db)
        await IndexPrecedents(store, RegexVerdictReader(), HashingEmbedder()).execute(
            CARD_EXTRACTOR_VERSION
        )


async def _analyse(client, use_knowledge_base=True):
    chat_id = (await client.post("/api/chats", json={"title": None})).json()["id"]
    r = await client.post(
        f"/api/chats/{chat_id}/messages",
        data={"content": "Проверь проект", "use_knowledge_base": str(use_knowledge_base).lower()},
        files=[("files", ("Проект.txt", SINGLE_CONDITIONAL.encode(), "text/plain"))],
    )
    msg_id = r.json()["assistant_message"]["id"]
    message = (await client.get(f"/api/chats/{chat_id}/messages/{msg_id}")).json()
    assert message["status"] == "completed", message["error"]
    return message["result"]


async def test_analysis_lists_comparable_precedents_and_excludes_other_articles(client):
    await _practice(PRACTICE_THEFT, PRACTICE_ROBBERY)
    result = await _analyse(client)
    assert result["precedent_source"] == "cards"
    [precedent] = result["precedents"]
    assert precedent["qualifications"] == ["п. «в» ч. 2 ст. 158 УК РФ"]
    assert precedent["punishment_months"] == 18 and precedent["conditional"] is True
    assert 0 < precedent["score"] <= 1 and precedent["breakdown"]
    assert "fabula" not in precedent
    # the old free-text list is filled from the same cards
    assert result["similar"][0]["punishment"].startswith("1 г. 6 мес.")


async def test_practice_comparison_and_scale_band(client):
    await _practice(*(_theft(m, i) for i, m in enumerate(TERMS)))
    result = await _analyse(client)
    practice = result["practice"]
    assert practice["with_term"] == 6 and practice["enough_data"] is True
    # inclusive quartiles of 6..36 step 6: 13.5, 21, 28.5
    assert (practice["p25_months"], practice["median_months"], practice["p75_months"]) == (
        13.5,
        21,
        28.5,
    )
    # the draft imposes 4 years 6 months: above every comparable term
    assert practice["draft_months"] == 54 and practice["position"] == "above"
    assert practice["draft_percentile"] == 100
    # rounded half up on both ends: Python's round() would give 14 and 28
    assert result["scale"]["practice_months"] == [14, 29]
    assert result["scale"]["avg_similar_months"] == 21


async def test_too_little_practice_gives_statistics_without_position(client):
    await _practice(PRACTICE_THEFT)
    practice = (await _analyse(client))["practice"]
    assert practice["with_term"] == 1 and practice["enough_data"] is False
    assert practice["position"] is None


async def test_empty_card_base_falls_back_to_text_search(client):
    result = await _analyse(client)
    assert result["precedent_source"] == "none"
    assert result["precedents"] == [] and result["practice"] is None


async def test_knowledge_base_off_means_no_precedent_search(client, embedder):
    await _practice(PRACTICE_THEFT)
    calls = embedder.calls
    result = await _analyse(client, use_knowledge_base=False)
    assert result["precedent_source"] is None and result["precedents"] == []
    assert embedder.calls == calls


async def test_no_cards_but_text_search_finds_verdicts(client, monkeypatch):
    found = [{"verdict_id": 7, "case_number": "1-1/2026", "court_name": "Суд", "excerpt": "кража"}]

    async def fake_search(**_kwargs):
        return found

    monkeypatch.setattr("src.services.analysis_runner.find_similar_verdicts", fake_search)
    result = await _analyse(client)
    assert result["precedent_source"] == "text"
    assert result["practice"] is None and result["precedents"] == []
    assert [s["verdict_id"] for s in result["similar"]] == [7]


async def test_question_without_documents_uses_text_search(client, monkeypatch):
    await _practice(PRACTICE_THEFT)  # cards exist, but there is no draft to read a card from
    asked = []

    async def fake_search(**kwargs):
        asked.append(kwargs["query_text"])
        return []

    monkeypatch.setattr("src.services.analysis_runner.find_similar_verdicts", fake_search)
    chat_id = (await client.post("/api/chats", json={"title": None})).json()["id"]
    r = await client.post(
        f"/api/chats/{chat_id}/messages",
        data={"content": "Кража ноутбука", "use_knowledge_base": "true"},
    )
    msg_id = r.json()["assistant_message"]["id"]
    result = (await client.get(f"/api/chats/{chat_id}/messages/{msg_id}")).json()["result"]
    assert asked == ["Кража ноутбука"] and result["precedent_source"] == "none"
