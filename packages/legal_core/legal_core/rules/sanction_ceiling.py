"""Derive the art. 15 input (SanctionCeiling) from structured statutory sanctions.

Art. 15 УК РФ classifies a crime by the maximum punishment of the article (part), so the
ceiling is the longest MAIN imprisonment; life imprisonment or death penalty as a MAIN
alternative makes the sanction harsher than imprisonment.
"""

from legal_core.entities import (
    MeasureUnit,
    PunishmentKind,
    SanctionCeiling,
    SanctionRole,
    StatutorySanction,
)

_HARSHER_THAN_IMPRISONMENT = {PunishmentKind.LIFE_IMPRISONMENT, PunishmentKind.DEATH_PENALTY}


def sanction_ceiling_for_part(
    sanctions: list[StatutorySanction], part: int | None
) -> SanctionCeiling | None:
    """Ceiling of the given part, or None when the part has no parsed sanction at all."""
    main = [s for s in sanctions if s.part == part and s.role is SanctionRole.MAIN]
    if not main:
        return None
    terms = [
        s.max_value
        for s in main
        if s.kind is PunishmentKind.IMPRISONMENT
        and s.unit is MeasureUnit.MONTHS
        and s.max_value is not None
    ]
    harsher = any(s.kind in _HARSHER_THAN_IMPRISONMENT for s in main)
    longest = int(max(terms)) if terms else None
    if harsher and longest is None:
        # Inconsistent statute reading: refuse rather than guess a category.
        return None
    return SanctionCeiling(longest, harsher)
