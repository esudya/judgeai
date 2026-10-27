"""LLM access behind a small interface.

- `openai`: any OpenAI-compatible `/chat/completions` endpoint (OpenAI, vLLM, Ollama, proxies).
- `fake`:   deterministic stub for local development and tests. It is only used when
            LLM_PROVIDER=fake is set explicitly — never as a silent fallback.
"""

import json
from typing import Protocol

import httpx

from src.config import settings


class LLMError(RuntimeError):
    """The model could not be reached or returned something unusable."""


class LLMClient(Protocol):
    async def complete_json(self, system: str, user: str) -> dict: ...


class OpenAICompatibleClient:
    async def complete_json(self, system: str, user: str) -> dict:
        if not settings.LLM_API_KEY:
            raise LLMError(
                "LLM не настроен: задайте LLM_API_KEY (или LLM_PROVIDER=fake для разработки)."
            )

        payload = {
            "model": settings.LLM_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {settings.LLM_API_KEY}"}

        try:
            async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    f"{settings.LLM_API_BASE.rstrip('/')}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as exc:
            # Never include request headers in the message: they carry the API key.
            raise LLMError(f"LLM ответил {exc.response.status_code}") from exc
        except (httpx.HTTPError, KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"Ошибка обращения к LLM: {type(exc).__name__}") from exc

        try:
            data = json.loads(content)
        except (json.JSONDecodeError, TypeError) as exc:
            raise LLMError("LLM вернул не JSON") from exc
        if not isinstance(data, dict):
            raise LLMError("LLM вернул JSON не в виде объекта")
        return data


class FakeLLMClient:
    """Returns the design's sample case regardless of input. Development and tests only."""

    async def complete_json(self, system: str, user: str) -> dict:
        return {
            "fabula": (
                "Подсудимый тайно похитил ноутбук стоимостью 64 000 ₽ из квартиры потерпевшей. "
                "С учётом её дохода ущерб значительный. Похищенное возвращено, ущерб возмещён "
                "полностью (т. 1 л. д. 87)."
            ),
            "qualification": {
                "article": "п. «в» ч. 2 ст. 158 УК РФ",
                "title": "Кража с причинением значительного ущерба гражданину. Средней тяжести.",
            },
            "sanction_max_months": 60,
            "mitigating": [
                {"name": "Явка с повинной", "norm": "п. «и» ч. 1 ст. 61"},
                {"name": "Возмещение ущерба", "norm": "п. «к» ч. 1 ст. 61"},
                {"name": "Признание вины", "norm": "ч. 2 ст. 61"},
            ],
            "aggravating": [],
            "personality": "Ранее не судим, характеризуется положительно, трудоустроен.",
            "recommended_months": 18,
            "variants": [
                {
                    "label": "Основной",
                    "title": "Лишение свободы 1 год 6 месяцев условно",
                    "details": "Испытательный срок 2 года.",
                    "rationale": "Учтены п. «и», «к» ч. 1 ст. 61, отягчающих обстоятельств нет.",
                },
                {
                    "label": "Штраф",
                    "title": "Штраф 100 000 ₽",
                    "details": "В пределах санкции.",
                    "rationale": "С учётом полного возмещения ущерба (ч. 3 ст. 46 УК РФ).",
                },
            ],
        }


def get_llm_client() -> LLMClient:
    if settings.LLM_PROVIDER == "fake":
        return FakeLLMClient()
    return OpenAICompatibleClient()
