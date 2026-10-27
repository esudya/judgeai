# Domain Layer — value objects used by the rules.
from dataclasses import dataclass
from enum import Enum, StrEnum


class Guilt(StrEnum):
    INTENTIONAL = "intentional"
    NEGLIGENT = "negligent"


class Category(int, Enum):
    """Crime categories of art. 15; the value orders them by gravity."""

    SMALL = 1
    MEDIUM = 2
    GRAVE = 3
    ESPECIALLY_GRAVE = 4


@dataclass(frozen=True)
class SanctionCeiling:
    """Upper bound of the article's sanction (comes from the DB, never hardcoded).

    max_imprisonment_months is None when the sanction has no imprisonment at all.
    harsher_than_imprisonment marks life imprisonment / death penalty in the sanction.
    """

    max_imprisonment_months: int | None
    harsher_than_imprisonment: bool = False

    def __post_init__(self) -> None:
        if self.max_imprisonment_months is not None and self.max_imprisonment_months <= 0:
            raise ValueError("max_imprisonment_months must be positive or None")
        if self.harsher_than_imprisonment and self.max_imprisonment_months is None:
            raise ValueError("a sanction harsher than imprisonment must also contain imprisonment")


@dataclass(frozen=True)
class ImposedPunishment:
    """Punishment from the draft verdict. imprisonment_months None = milder than imprisonment."""

    imprisonment_months: int | None

    def __post_init__(self) -> None:
        if self.imprisonment_months is not None and self.imprisonment_months <= 0:
            raise ValueError("imprisonment_months must be positive or None")


class PunishmentKind(StrEnum):
    """Kinds of punishment named in art. 44 УК РФ as they appear in sanctions."""

    FINE = "fine"
    DEPRIVATION_OF_RIGHT = "deprivation_of_right"
    COMPULSORY_WORKS = "compulsory_works"
    CORRECTIONAL_WORKS = "correctional_works"
    MILITARY_SERVICE_RESTRICTION = "military_service_restriction"
    RESTRICTION_OF_FREEDOM = "restriction_of_freedom"
    FORCED_LABOUR = "forced_labour"
    ARREST = "arrest"
    DISCIPLINARY_MILITARY_UNIT = "disciplinary_military_unit"
    IMPRISONMENT = "imprisonment"
    LIFE_IMPRISONMENT = "life_imprisonment"
    DEATH_PENALTY = "death_penalty"


class SanctionRole(StrEnum):
    """MAIN = alternative chosen by the court; ADDITIONAL = may be added to a main one."""

    MAIN = "main"
    ADDITIONAL = "additional"


class MeasureUnit(StrEnum):
    MONTHS = "months"
    HOURS = "hours"
    RUBLES = "rubles"


@dataclass(frozen=True)
class StatutorySanction:
    """One punishment alternative of a part of an article, as written in the statute.

    Values come from the imported official text (DB), never from code. part is None for
    articles without numbered parts. Bounds are None when the statute gives none or the
    amount is not a fixed figure (e.g. a multiple of a bribe).
    """

    article: str
    part: int | None
    kind: PunishmentKind
    role: SanctionRole
    min_value: float | None
    max_value: float | None
    unit: MeasureUnit | None
    clause: str

    def __post_init__(self) -> None:
        for bound in (self.min_value, self.max_value):
            if bound is not None and bound <= 0:
                raise ValueError("sanction bounds must be positive")
        if (
            self.min_value is not None
            and self.max_value is not None
            and self.min_value > self.max_value
        ):
            raise ValueError("min_value must not exceed max_value")
        if (self.min_value is not None or self.max_value is not None) and self.unit is None:
            raise ValueError("a bounded sanction needs a unit")


@dataclass(frozen=True)
class ArticleReference:
    """Article (e.g. '228.1') and optional part of the Special Part of УК РФ."""

    article: str
    part: int | None = None

    def __str__(self) -> str:
        prefix = f"ч. {self.part} " if self.part is not None else ""
        return f"{prefix}ст. {self.article} УК РФ"
