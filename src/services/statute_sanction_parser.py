"""Adapter: official text of an УК РФ article -> structured StatutorySanction values.

Pure text processing without I/O. The result is a technical reading of an unreviewed
source; callers must keep the provenance and the review status next to it.
"""

import re

from legal_core.entities import MeasureUnit, PunishmentKind, SanctionRole, StatutorySanction

from src.services.russian_numerals import parse_russian_number

PARSER_VERSION = "statute-sanction-parser/2"

# (kind, regex that starts the alternative). Order matters: life imprisonment before imprisonment.
_KIND_PATTERNS: list[tuple[PunishmentKind, str]] = [
    (PunishmentKind.LIFE_IMPRISONMENT, r"пожизненн\w+ лишени\w+ свободы"),
    (PunishmentKind.DEATH_PENALTY, r"смертн\w+ казн\w+"),
    (PunishmentKind.IMPRISONMENT, r"лишени\w+ свободы"),
    (PunishmentKind.FINE, r"штраф\w*"),
    (PunishmentKind.DEPRIVATION_OF_RIGHT, r"лишени\w+ права"),
    (PunishmentKind.COMPULSORY_WORKS, r"обязательн\w+ работ\w*"),
    (PunishmentKind.CORRECTIONAL_WORKS, r"исправительн\w+ работ\w*"),
    (PunishmentKind.FORCED_LABOUR, r"принудительн\w+ работ\w*"),
    (PunishmentKind.MILITARY_SERVICE_RESTRICTION, r"ограничени\w+ по военной службе"),
    (PunishmentKind.RESTRICTION_OF_FREEDOM, r"ограничени\w+ свободы"),
    (PunishmentKind.ARREST, r"арест\w*"),
    (PunishmentKind.DISCIPLINARY_MILITARY_UNIT, r"содержани\w+ в дисциплинарной воинской части"),
]
_KIND_REGEX = re.compile(
    "|".join(f"(?P<k{i}>{pattern})" for i, (_, pattern) in enumerate(_KIND_PATTERNS))
)
_TIME_UNITS = {
    **dict.fromkeys(["лет", "год", "года"], (MeasureUnit.MONTHS, 12)),
    **dict.fromkeys(["месяц", "месяца", "месяцев"], (MeasureUnit.MONTHS, 1)),
    **dict.fromkeys(["час", "часа", "часов"], (MeasureUnit.HOURS, 1)),
}
_NUMBER_PHRASE = r"[0-9а-яё ]+?"
_UNIT_WORD = r"лет|года?|месяц\w*|час\w*"
_TERM_RANGE = re.compile(
    rf"\s*(?:на срок\s+)?"
    rf"(?:от\s+(?P<low>{_NUMBER_PHRASE})(?:\s+(?P<low_unit>{_UNIT_WORD}))?\s+)?"
    rf"до\s+(?P<high>{_NUMBER_PHRASE})\s+(?P<high_unit>{_UNIT_WORD})\b"
)
_TERM_START = re.compile(r"на срок\s+(?:от|до)\b")
_SAME_TERM = re.compile(r"^\s*на тот же срок")
_FINE_RANGE = re.compile(
    rf"^\s*в размере\s+(?:от\s+(?P<low>{_NUMBER_PHRASE})\s+)?до\s+(?P<high>{_NUMBER_PHRASE})\s+рубл"
)
_AMENDMENT_NOTE = re.compile(
    r"\((?:В редакции|Дополнен|Часть|Пункт|Абзац|Статья|Утратил|Наименование)[^()]*\)"
)
_PART_MARKER = re.compile(r"(?<!\d)(?<!\d\.)(\d{1,2})\.\s*(?=[А-ЯЁA-Z«(])")
_NOTES = re.compile(r"Примечани[ея]")
_SANCTION_START = re.compile(r"наказыва\w+")


def split_article_parts(body: str, title: str) -> list[tuple[int | None, str]]:
    """Split an article into numbered parts; notes ('Примечания') are cut off.

    Part numbers must increase; a lower or equal number is treated as text (e.g. a list item).
    An article without numbered parts is returned as a single (None, text) item.
    """
    text = body[len(title) :] if body.startswith(title) else body
    notes = _NOTES.search(text)
    if notes:
        text = text[: notes.start()]
    markers, last = [], 0
    for match in _PART_MARKER.finditer(text):
        number = int(match.group(1))
        if number > last and (last or number == 1):
            markers.append((number, match.start(), match.end()))
            last = number
    if not markers:
        return [(None, text.strip())]
    parts = []
    for index, (number, _, content_start) in enumerate(markers):
        end = markers[index + 1][1] if index + 1 < len(markers) else len(text)
        parts.append((number, text[content_start:end].strip()))
    return parts


def _kind_of(match: re.Match) -> PunishmentKind:
    return next(
        _KIND_PATTERNS[int(name[1:])][0] for name, value in match.groupdict().items() if value
    )


def _role_of(clause: str, start: int) -> SanctionRole:
    before = clause[max(0, start - 4) : start].lower()
    return (
        SanctionRole.ADDITIONAL if re.search(r"(?:^|\s)(?:с|со)\s$", before) else SanctionRole.MAIN
    )


def _bounds(kind: PunishmentKind, tail: str):
    if kind is PunishmentKind.FINE:
        match = _FINE_RANGE.match(tail)
        if not match:
            return None, None, None
        low = parse_russian_number(match["low"]) if match["low"] else None
        high = parse_russian_number(match["high"])
        if high is None or (match["low"] and low is None):
            return None, None, None
        return low, high, MeasureUnit.RUBLES
    term = _TERM_START.search(tail)
    match = _TERM_RANGE.match(tail, term.start()) if term else None
    if not match:
        return None, None, None
    high_unit, high_factor = _TIME_UNITS.get(match["high_unit"], (None, None))
    high = parse_russian_number(match["high"])
    if high_unit is None or high is None:
        return None, None, None
    low = None
    if match["low"]:
        low_unit, low_factor = _TIME_UNITS.get(
            match["low_unit"] or match["high_unit"], (None, None)
        )
        low_value = parse_russian_number(match["low"])
        if low_unit is not high_unit or low_value is None:
            return None, None, None
        low = low_value * low_factor
    return low, high * high_factor, high_unit


def _normalize(value):
    return int(value) if value is not None and float(value).is_integer() else value


def parse_article_sanctions(article: str, body: str, title: str) -> list[StatutorySanction]:
    """All punishment alternatives of every part of the article that has a sanction."""
    sanctions: list[StatutorySanction] = []
    for part, text in split_article_parts(body, title):
        start = _SANCTION_START.search(text)
        if not start:
            continue
        clause = _AMENDMENT_NOTE.sub("", text[start.start() :]).strip()
        matches = list(_KIND_REGEX.finditer(clause))
        previous_term = (None, None, None)
        for index, match in enumerate(matches):
            kind = _kind_of(match)
            role = _role_of(clause, match.start())
            end = matches[index + 1].start() if index + 1 < len(matches) else len(clause)
            tail = clause[match.end() : end]
            if _SAME_TERM.match(tail):
                # "либо лишением свободы на тот же срок" repeats the previous main term.
                low, high, unit = previous_term
            else:
                low, high, unit = _bounds(kind, tail)
            if role is SanctionRole.MAIN and unit is MeasureUnit.MONTHS:
                previous_term = (low, high, unit)
            sanctions.append(
                StatutorySanction(
                    article=article,
                    part=part,
                    kind=kind,
                    role=role,
                    min_value=_normalize(low),
                    max_value=_normalize(high),
                    unit=unit,
                    clause=clause,
                )
            )
    return sanctions
