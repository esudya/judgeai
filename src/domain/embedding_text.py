"""Text that goes into the embedding of a case: the anonymised plot (fabula) only.

The signature accepts nothing but the fabula on purpose: court, region, dates, names and
article numbers are compared by filters and score axes, never by the vector. Whatever of them
is still written inside the fabula is removed here.
"""

import re

_MONTHS = "января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря"
_PATTERNS: list[tuple[re.Pattern, str]] = [
    # Courts: "Условный районный суд г. Примерска"
    (
        re.compile(
            r"[А-ЯЁ][\w\-]*\s+(?:[\w\-]+\s+){0,3}"
            r"(?:районн|городск|областн|краев|гарнизонн|мирово)\w*\s+суд\w*"
            r"(?:\s+(?:г\.|города)\s*[А-ЯЁ][\w\-]*)?"
        ),
        "суд",
    ),
    # Procedural roles with numbers: "Потерпевший №1", "Свидетель № 2"
    (re.compile(r"(?:Потерпевш|Свидетел|Представител)\w*\s*№\s*\d+"), "лицо"),
    # Surname with initials in either order: "Иванов И.И.", "И.И. Иванов"
    (re.compile(r"[А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)?\s+[А-ЯЁ]\.\s*(?:[А-ЯЁ]\.)?"), "лицо"),
    (re.compile(r"[А-ЯЁ]\.\s*(?:[А-ЯЁ]\.)?\s*[А-ЯЁ][а-яё]+"), "лицо"),
    # Anonymised initial alone: "К." (not a sentence-final capital word)
    (re.compile(r"(?<![\w.])[А-ЯЁ]\.(?=[\s,;:)]|$)"), "лицо"),
    # Dates and times
    (re.compile(rf"\d{{1,2}}\s+(?:{_MONTHS})(?:\s+\d{{4}}\s*(?:года|г\.)?)?"), "дата"),
    (re.compile(r"\d{1,2}\.\d{1,2}\.\d{2,4}(?:\s*(?:года|г\.))?"), "дата"),
    (re.compile(r"(?<!\d)(?:19|20)\d{2}\s*(?:года|г\.)"), "дата"),
    (re.compile(r"(?:около|примерно|в|до|с)?\s*\d{1,2}[:.]\d{2}(?:\s*час\w*)?(?=\D|$)"), ""),
    # Addresses: "ул. Ленина", "г. Примерска", "дома 5", "кв. 7"
    (re.compile(r"(?:ул|пр|пр-т|пер|пл|наб|пос|с|г|д|кв|корп|стр)\.\s*[А-ЯЁ0-9][\w\-]*"), "адрес"),
    (re.compile(r"(?:у\s+)?дом\w*\s+\d+\w*(?:\s+по)?"), "у дома"),
    # Article references: "п. «в» ч. 2 ст. 158 УК РФ"
    (
        re.compile(
            r"(?:п\.\s*(?:п\.\s*)?«[^»]{1,20}»\s*)?(?:ч\.\s*\d+(?:\.\d)?\s*)?"
            r"ст\.\s*\d+(?:\.\d+)?(?:\s*(?:УК|УПК)\s*РФ)?"
        ),
        "",
    ),
]


def build_embedding_text(fabula: str) -> str:
    text = fabula
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    text = re.sub(r"\b(лицо|дата|адрес)(?:\s*,?\s*\1)+", r"\1", text)
    text = re.sub(r"\s+([,.;:])", r"\1", text)
    return " ".join(text.split())
