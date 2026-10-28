"""Use case: read punishments the regex could not parse, by sending only short windows to the LLM.

Every reading is cached by (sha256 of the window, field, prompt version), including empty ones.
The model must quote the window literally; otherwise its reading is discarded.
"""

from hashlib import sha256

from legal_core.entities import MeasureUnit, PunishmentKind, PunishmentTerm
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import LlmWindowExtraction
from src.services.llm_client import LLMClient, LLMError

FIELD = "imposed_punishment"
PROMPT_VERSION = "punishment-window/1"
SYSTEM_PROMPT = """Ты читаешь фрагмент резолютивной части приговора суда РФ.
Найди назначенное наказание и верни JSON-объект:
{"kind": "imprisonment|fine|compulsory_works|correctional_works|forced_labour|
          restriction_of_freedom|arrest|life_imprisonment|null",
 "years": число или null, "months": число или null, "hours": число или null,
 "rubles": число или null, "quote": "точная цитата из фрагмента с наказанием"}
Если срок или размер во фрагменте не указан числом — верни null в соответствующих полях.
Ничего не выдумывай."""


def window_hash(window: str) -> str:
    return sha256(window.encode("utf-8")).hexdigest()


def term_from_reading(reading: dict, window: str) -> PunishmentTerm | None:
    """Domain term from a model reading; None when the reading is empty, invalid or unquoted."""
    quote = reading.get("quote")
    if not isinstance(quote, str) or not quote.strip() or quote not in window:
        return None
    try:
        kind = PunishmentKind(reading.get("kind"))
    except ValueError:
        return None
    if kind is PunishmentKind.LIFE_IMPRISONMENT:
        return PunishmentTerm(kind)

    def number(name: str) -> float:
        value = reading.get(name)
        return value if isinstance(value, int | float) and value > 0 else 0

    if kind is PunishmentKind.FINE:
        rubles = number("rubles")
        return PunishmentTerm(kind, rubles, MeasureUnit.RUBLES) if rubles else None
    if number("hours"):
        return PunishmentTerm(kind, number("hours"), MeasureUnit.HOURS)
    months = number("years") * 12 + number("months")
    return PunishmentTerm(kind, months, MeasureUnit.MONTHS) if months else None


async def resolve_windows(
    db: AsyncSession, llm: LLMClient, windows: tuple[str, ...]
) -> list[tuple[str, PunishmentTerm | None]]:
    results = []
    for window in windows:
        key = window_hash(window)
        cached = await db.scalar(
            select(LlmWindowExtraction.value).where(
                LlmWindowExtraction.input_hash == key,
                LlmWindowExtraction.field == FIELD,
                LlmWindowExtraction.prompt_version == PROMPT_VERSION,
            )
        )
        if cached is None:
            try:
                cached = await llm.complete_json(SYSTEM_PROMPT, window)
            except LLMError:
                results.append((window, None))
                continue
            await db.execute(
                insert(LlmWindowExtraction)
                .values(input_hash=key, field=FIELD, prompt_version=PROMPT_VERSION, value=cached)
                .on_conflict_do_nothing(constraint="uq_llm_window_extraction")
            )
            await db.commit()
        results.append((window, term_from_reading(cached, window)))
    return results
