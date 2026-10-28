"""Use case: a verdict text -> precedent card plus the registry of its extracted fields.

The same code reads the user's draft (the query) and every verdict of the practice base, so
both sides of a comparison are extracted identically. Reading the text is delegated to a
VerdictReader port; this module only assembles the domain card and its provenance.
"""

from dataclasses import dataclass
from typing import Protocol

from legal_core.entities import ImposedSentence, PunishmentTerm
from legal_core.precedents import (
    PrecedentCard,
    PrecedentEpisode,
    Recidivism,
    parse_qualifications,
)

from src.domain.extraction import ExtractedField, ExtractionMethod, input_hash

CARD_EXTRACTOR_VERSION = "precedent-card/1"


@dataclass(frozen=True)
class VerdictReading:
    """What a reader found in one verdict text; quotes are literal fragments of that text."""

    introduction: str
    description: str
    operative: str
    sentence: ImposedSentence
    fabula: str
    mitigating: dict[str, str]
    aggravating: dict[str, str]
    applied_general: dict[str, str]
    recidivism: Recidivism | None
    recidivism_quote: str


class VerdictReader(Protocol):
    def read(self, text: str) -> VerdictReading: ...


@dataclass(frozen=True)
class CardExtraction:
    card: PrecedentCard
    fields: tuple[ExtractedField, ...]
    text_hash: str


def _term_json(term: PunishmentTerm | None) -> dict | None:
    if term is None:
        return None
    return {
        "kind": term.kind.value,
        "amount": term.amount,
        "unit": term.unit.value if term.unit else None,
    }


def _episodes(reading: VerdictReading) -> tuple[PrecedentEpisode, ...]:
    episodes: list[PrecedentEpisode] = []
    for count in reading.sentence.counts:
        found = parse_qualifications(count.qualification) or parse_qualifications(count.quote)
        if found:
            episodes.append(PrecedentEpisode(found[0], count.main))
    if episodes:
        return tuple(episodes)
    qualifications = parse_qualifications(reading.operative) or parse_qualifications(
        reading.introduction
    )
    return tuple(PrecedentEpisode(q) for q in qualifications)


def build_card(reader: VerdictReader, text: str) -> CardExtraction:
    reading = reader.read(text)
    episodes = _episodes(reading)
    sentence = reading.sentence
    card = PrecedentCard(
        episodes=episodes,
        mitigating=frozenset(reading.mitigating),
        aggravating=frozenset(reading.aggravating),
        recidivism=reading.recidivism,
        applied_general=frozenset(reading.applied_general),
        final=sentence.final,
        conditional=sentence.conditional,
        fabula=reading.fabula,
    )
    source = input_hash(text)
    version = CARD_EXTRACTOR_VERSION

    def found(name: str, value, quote: str) -> ExtractedField:
        if value in (None, [], {}, "") or not quote.strip():
            return ExtractedField.absent(name, version, source)
        return ExtractedField(name, value, ExtractionMethod.REGEX, quote, version, source)

    count_quotes = " … ".join(c.quote for c in sentence.counts if c.quote)
    fields = (
        found(
            "qualifications",
            [e.qualification.key for e in episodes],
            count_quotes or reading.operative[:300] or reading.introduction[:300],
        ),
        found(
            "counts",
            [
                {"qualification": e.qualification.key, "punishment": _term_json(e.punishment)}
                for e in episodes
                if e.punishment is not None
            ],
            count_quotes,
        ),
        found("final_sentence", _term_json(sentence.final), sentence.final_quote),
        found("conditional", True if sentence.conditional else None, reading.operative[:300]),
        found("mitigating", sorted(reading.mitigating), " … ".join(reading.mitigating.values())),
        found("aggravating", sorted(reading.aggravating), " … ".join(reading.aggravating.values())),
        found(
            "applied_general",
            sorted(reading.applied_general),
            " … ".join(dict.fromkeys(reading.applied_general.values())),
        ),
        found(
            "recidivism",
            reading.recidivism.value if reading.recidivism else None,
            reading.recidivism_quote,
        ),
        found("fabula", reading.fabula or None, reading.fabula[:300]),
    )
    return CardExtraction(card, fields, source)
