"""Builds a structured CaseAnalysis from case documents.

The LLM only extracts facts (LlmCaseFacts). Everything that is arithmetic over the law
(ч. 1 ст. 62 limit, "within sanction") is computed here.
"""

import json
import logging

from pydantic import ValidationError

from src.schemas.analysis import (
    AnalysisStats,
    CaseAnalysis,
    LlmCaseFacts,
    SentenceScale,
    SimilarVerdictRef,
)
from src.services.llm_client import LLMClient, LLMError
from src.services.sentencing import art62_part1_limit

logger = logging.getLogger(__name__)

DOCUMENT_CHARS_LIMIT = 5000
DEFAULT_QUESTION = "Подготовь проект приговора: квалификация, обстоятельства, варианты наказания."

SYSTEM_PROMPT = """Ты — ассистент судьи по уголовным делам (УК РФ).
По материалам дела извлеки факты.
Отвечай ТОЛЬКО JSON-объектом без пояснений, строго по схеме:
{schema}
Правила:
- Сроки — целые месяцы.
- sanction_max_months — максимальный срок лишения свободы по санкции квалифицирующей части статьи.
- В norm указывай норму в виде «п. «и» ч. 1 ст. 61».
- Если сведений нет — null или пустой список, ничего не выдумывай."""


def build_user_prompt(
    question: str | None, document_texts: list[str], similar_items: list[dict]
) -> str:
    documents = "\n\n---\n\n".join(t[:DOCUMENT_CHARS_LIMIT] for t in document_texts if t.strip())
    similar = "\n".join(
        f"- {item.get('case_number') or 'без номера'}: {item.get('excerpt')}"
        for item in similar_items
    )
    return (
        f"Вопрос:\n{question or DEFAULT_QUESTION}\n\n"
        f"Материалы дела:\n{documents or 'Материалы не переданы.'}\n\n"
        f"Похожие приговоры из базы знаний:\n{similar or 'Не найдены.'}"
    )


def _similar_refs(similar_items: list[dict]) -> list[SimilarVerdictRef]:
    refs = []
    for item in similar_items:
        score = item.get("score")
        refs.append(
            SimilarVerdictRef(
                verdict_id=item.get("verdict_id"),
                # Punishment is not extracted from knowledge-base verdicts yet (next iteration).
                punishment=item.get("case_number") or "Приговор без номера",
                court=" · ".join(x for x in [item.get("court_name"), item.get("verdict_date")] if x)
                or "Суд не указан",
                match=(item.get("excerpt") or "")[:160],
                score=round(score * 100) if isinstance(score, int | float) else 0,
            )
        )
    return refs


def assemble_analysis(
    facts: LlmCaseFacts,
    *,
    prompt: str,
    documents: int,
    pages: int,
    seconds: int,
    similar_items: list[dict],
    extra_warnings: list[str],
) -> CaseAnalysis:
    warnings = list(extra_warnings)
    scale = None
    if facts.sanction_max_months:
        limit = art62_part1_limit(facts.sanction_max_months, facts.mitigating, facts.aggravating)
        rec = facts.recommended_months
        cap = limit if limit is not None else facts.sanction_max_months
        scale = SentenceScale(
            sanction_max_months=facts.sanction_max_months,
            limit_months=limit,
            limit_norm="ч. 1 ст. 62" if limit is not None else None,
            recommended_months=rec,
            within_sanction=(rec <= cap) if rec is not None else None,
        )
        warnings.append(
            "Максимум санкции определён моделью и пока не сверен со справочником УК РФ."
        )
        if rec is not None and rec > cap:
            warnings.append("Рекомендованный срок выходит за допустимый предел — проверьте.")

    return CaseAnalysis(
        stats=AnalysisStats(documents=documents, pages=pages, seconds=seconds),
        prompt=prompt,
        fabula=facts.fabula,
        qualification=facts.qualification,
        scale=scale,
        mitigating=facts.mitigating,
        aggravating="; ".join(f"{c.name} — {c.norm}" for c in facts.aggravating)
        or "Не установлены (ст. 63 УК РФ).",
        personality=facts.personality,
        variants=facts.variants,
        similar=_similar_refs(similar_items),
        warnings=warnings,
    )


async def extract_facts(
    llm: LLMClient,
    question: str | None,
    document_texts: list[str],
    similar_items: list[dict],
) -> LlmCaseFacts:
    system = SYSTEM_PROMPT.format(
        schema=json.dumps(LlmCaseFacts.model_json_schema(), ensure_ascii=False)
    )
    user = build_user_prompt(question, document_texts, similar_items)

    last_error: Exception | None = None
    for attempt in (1, 2):  # one retry for malformed output
        data = await llm.complete_json(system, user)
        try:
            return LlmCaseFacts.model_validate(data)
        except ValidationError as exc:
            last_error = exc
            logger.warning(
                "LLM output failed validation (attempt %s): %s", attempt, exc.error_count()
            )
    raise LLMError("Ответ модели не соответствует схеме анализа") from last_error
