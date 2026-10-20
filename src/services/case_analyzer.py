from src.services.llm_client import generate_answer


def build_prompt(
    question: str | None,
    document_texts: list[str],
    similar_items: list[dict],
) -> str:
    documents = "\n\n---\n\n".join(
        text[:5000] for text in document_texts if text
    )

    similar = "\n".join(
        f"- {item.get('case_number') or 'без номера'}: {item.get('excerpt')}"
        for item in similar_items
    )

    return f"""
Ты — ассистент судьи по уголовным делам.
Проанализируй материалы дела и ответь на вопрос.

Вопрос:
{question or "Проанализируй дело, определи рецидив, коридор наказания и похожие приговоры."}

Материалы дела:
{documents or "Материалы не переданы."}

Похожие приговоры из базы знаний:
{similar or "Не найдены."}

Дай ответ структурно и кратко.
"""


async def analyze_case(
    question: str | None,
    document_texts: list[str],
    similar_items: list[dict],
) -> tuple[str, dict]:
    prompt = build_prompt(question, document_texts, similar_items)

    try:
        answer = await generate_answer(prompt)
        error = None
    except Exception as exc:
        answer = "Не удалось получить ответ от нейросети. Проверьте настройки LLM_API_KEY и LLM_API_BASE."
        error = str(exc)

    analysis = {
        "documents_count": len(document_texts),
        "non_empty_documents_count": sum(1 for text in document_texts if text.strip()),
        "similar_items_count": len(similar_items),
        "similar_items": similar_items,
    }

    if error:
        analysis["error"] = error

    return answer, analysis
