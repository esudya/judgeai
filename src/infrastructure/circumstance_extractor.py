"""Adapter: circumstances, recidivism and applied General Part rules from a verdict, by regex.

Only text after the words «смягчающ…» / «отягчающ…» is read for circumstances, so a mention
in the description of the crime is not mistaken for the court's finding. Sentences that deny
something ("оснований для применения ст. 64 не усматривает") are skipped.
Every code keeps the sentence it was read from.
"""

import re
from dataclasses import dataclass, field

from legal_core.precedents import Recidivism

EXTRACTOR_VERSION = "circumstances/1"

_SENTENCE_SPLIT = re.compile(r"(?<=[.;])\s+(?=[А-ЯЁ])|\n\s*\n")
_NEGATION = re.compile(
    r"\bне\s+(?:усматрива|находит|име[её]т|имеется|установлен|применя|подлеж|признаёт|признает)"
    r"|отсутству|нет\s+оснований|оснований\s+для[^.]{0,120}\bнет\b|не\s+установил",
    re.IGNORECASE,
)
_MARKER = re.compile(r"(?P<kind>смягчающ|отягчающ)\w*", re.IGNORECASE)
_EXPLICIT = re.compile(
    r"(?:п\.\s*(?:п\.\s*)?«(?P<points>[а-яё,\s]{1,20})»\s*)?ч\.\s*(?P<part>\d(?:\.\d)?)\s*"
    r"ст\.\s*(?P<article>6[13])(?!\d)",
    re.IGNORECASE,
)
_MITIGATING_WORDS: list[tuple[str, re.Pattern]] = [
    ("61.1.и", re.compile(r"явк\w*\s+с\s+повинной|активн\w+\s+способствовани", re.I)),
    ("61.1.г", re.compile(r"малолетн\w+\s+(?:ребенка|ребёнка|детей|дочер|сын)", re.I)),
    ("61.1.в", re.compile(r"беременност", re.I)),
    (
        "61.1.к",
        re.compile(r"возмещени\w+\s+(?:\w+\s+)?(?:ущерба|вреда)|возместил|заглаживани", re.I),
    ),
    ("61.2", re.compile(r"признани\w+\s+вины|раскаяни|состояни\w+\s+здоровья", re.I)),
]
_AGGRAVATING_WORDS: list[tuple[str, re.Pattern]] = [
    ("63.1.а", re.compile(r"рецидив", re.I)),
    ("63.1.в", re.compile(r"групп\w+\s+лиц", re.I)),
    ("63.1.1", re.compile(r"состояни\w+\s+(?:алкогольного\s+)?опьянени", re.I)),
]
_GENERAL_RULES = re.compile(
    r"(?:ч\.\s*(?P<part>\d)\s*)?ст\.\s*(?P<article>62|64|68|73)(?!\d)", re.IGNORECASE
)
_RECIDIVISM: list[tuple[Recidivism, re.Pattern]] = [
    (Recidivism.ESPECIALLY_DANGEROUS, re.compile(r"особо\s+опасн\w*\s+рецидив", re.I)),
    (Recidivism.DANGEROUS, re.compile(r"(?<!особо\s)опасн\w*\s+рецидив", re.I)),
    (Recidivism.SIMPLE, re.compile(r"рецидив", re.I)),
]
_NOT_CONVICTED = re.compile(r"ранее\s+не\s+суд[иі]м|не\s+имеющ\w+\s+судимост", re.IGNORECASE)


@dataclass
class CircumstanceReading:
    mitigating: dict[str, str] = field(default_factory=dict)
    aggravating: dict[str, str] = field(default_factory=dict)
    applied_general: dict[str, str] = field(default_factory=dict)
    recidivism: Recidivism | None = None
    recidivism_quote: str = ""


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT.split(text) if s and s.strip()]


def _explicit_codes(segment: str, article: str) -> list[str]:
    codes = []
    for match in _EXPLICIT.finditer(segment):
        if match["article"] != article:
            continue
        points = re.findall(r"[а-яё]", (match["points"] or "").lower())
        base = f"{article}.{match['part']}"
        if points:
            codes.extend(f"{base}.{p}" for p in points)
        else:
            codes.append(base)
    return codes


def _read_circumstances(sentence: str, reading: CircumstanceReading) -> None:
    markers = list(_MARKER.finditer(sentence))
    for index, marker in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(sentence)
        segment = sentence[marker.start() : end]
        mitigating = marker["kind"].lower().startswith("смягч")
        article = "61" if mitigating else "63"
        target = reading.mitigating if mitigating else reading.aggravating
        words = _MITIGATING_WORDS if mitigating else _AGGRAVATING_WORDS
        codes = _explicit_codes(segment, article)
        codes += [code for code, pattern in words if pattern.search(segment)]
        for code in codes:
            target.setdefault(code, sentence)


def extract_circumstances(
    description: str, operative: str = "", introduction: str = ""
) -> CircumstanceReading:
    reading = CircumstanceReading()
    for sentence in _sentences(description):
        if _NEGATION.search(sentence):
            continue
        _read_circumstances(sentence, reading)
    for sentence in _sentences(f"{description}\n\n{operative}"):
        if _NEGATION.search(sentence):
            continue
        for match in _GENERAL_RULES.finditer(sentence):
            article, part = match["article"], match["part"]
            if article in ("62", "68") and part is None:
                continue
            code = f"{article}.{part}" if article in ("62", "68") else article
            reading.applied_general.setdefault(code, sentence)
        if reading.recidivism is None:
            for kind, pattern in _RECIDIVISM:
                if pattern.search(sentence):
                    reading.recidivism, reading.recidivism_quote = kind, sentence
                    break
    if reading.recidivism is None:
        person = f"{introduction}\n\n{description}"
        sentence = next((s for s in _sentences(person) if _NOT_CONVICTED.search(s)), None)
        if sentence is not None:
            reading.recidivism, reading.recidivism_quote = Recidivism.NONE, sentence
    return reading
