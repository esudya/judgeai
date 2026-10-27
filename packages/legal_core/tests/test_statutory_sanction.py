import pytest

from legal_core.entities import (
    MeasureUnit,
    PunishmentKind,
    SanctionCeiling,
    SanctionRole,
    StatutorySanction,
)
from legal_core.rules.sanction_ceiling import sanction_ceiling_for_part


def _sanction(kind, role=SanctionRole.MAIN, part=2, min_value=None, max_value=None, unit=None):
    return StatutorySanction(
        article="158",
        part=part,
        kind=kind,
        role=role,
        min_value=min_value,
        max_value=max_value,
        unit=unit,
        clause="наказывается ...",
    )


def test_bounds_must_be_ordered_and_positive():
    with pytest.raises(ValueError):
        _sanction(PunishmentKind.IMPRISONMENT, min_value=10, max_value=5, unit=MeasureUnit.MONTHS)
    with pytest.raises(ValueError):
        _sanction(PunishmentKind.IMPRISONMENT, max_value=0, unit=MeasureUnit.MONTHS)


def test_bounded_sanction_requires_unit():
    with pytest.raises(ValueError):
        _sanction(PunishmentKind.IMPRISONMENT, max_value=24)


def test_ceiling_uses_main_imprisonment_of_the_part():
    sanctions = [
        _sanction(PunishmentKind.FINE, max_value=200_000, unit=MeasureUnit.RUBLES),
        _sanction(PunishmentKind.IMPRISONMENT, max_value=60, unit=MeasureUnit.MONTHS),
        _sanction(
            PunishmentKind.RESTRICTION_OF_FREEDOM,
            role=SanctionRole.ADDITIONAL,
            max_value=12,
            unit=MeasureUnit.MONTHS,
        ),
        _sanction(PunishmentKind.IMPRISONMENT, part=1, max_value=24, unit=MeasureUnit.MONTHS),
    ]
    assert sanction_ceiling_for_part(sanctions, part=2) == SanctionCeiling(60, False)


def test_ceiling_marks_life_imprisonment_as_harsher():
    sanctions = [
        _sanction(
            PunishmentKind.IMPRISONMENT,
            part=5,
            min_value=180,
            max_value=240,
            unit=MeasureUnit.MONTHS,
        ),
        _sanction(PunishmentKind.LIFE_IMPRISONMENT, part=5),
    ]
    assert sanction_ceiling_for_part(sanctions, part=5) == SanctionCeiling(240, True)


def test_ceiling_without_imprisonment_is_none_bound():
    sanctions = [_sanction(PunishmentKind.FINE, max_value=80_000, unit=MeasureUnit.RUBLES)]
    assert sanction_ceiling_for_part(sanctions, part=2) == SanctionCeiling(None, False)


def test_ceiling_for_missing_part_is_none():
    assert sanction_ceiling_for_part([], part=3) is None


def test_ceiling_refuses_life_imprisonment_without_any_term():
    assert sanction_ceiling_for_part([_sanction(PunishmentKind.LIFE_IMPRISONMENT)], part=2) is None
