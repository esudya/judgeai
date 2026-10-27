import pytest

from legal_core.checks import CheckStatus
from legal_core.entities import (
    ImposedPunishment,
    MeasureUnit,
    PunishmentKind,
    SanctionRole,
    StatutorySanction,
)
from legal_core.rules.imposed_term import check_imposed_imprisonment


def _sanction(kind=PunishmentKind.IMPRISONMENT, min_value=None, max_value=60):
    unit = MeasureUnit.MONTHS if max_value else None
    return StatutorySanction("158", 2, kind, SanctionRole.MAIN, min_value, max_value, unit, "...")


def _check(months, sanctions, **kwargs):
    return check_imposed_imprisonment(ImposedPunishment(months), sanctions, source="src", **kwargs)


@pytest.mark.parametrize(
    "months,sanctions,kwargs,status,fragment",
    [
        (36, [_sanction()], {}, CheckStatus.OK, "в пределах"),
        (61, [_sanction()], {}, CheckStatus.POSSIBLE_VIOLATION, "максимуме санкции 60"),
        (
            54,
            [_sanction()],
            {"art62_limit_months": 40},
            CheckStatus.POSSIBLE_VIOLATION,
            "ч. 1 ст. 62",
        ),
        (40, [_sanction()], {"art62_limit_months": 40}, CheckStatus.OK, "в пределах"),
        (24, [_sanction(min_value=36)], {}, CheckStatus.POSSIBLE_VIOLATION, "ниже минимума"),
        (24, [_sanction(min_value=36)], {"art64_applied": True}, CheckStatus.OK, "в пределах"),
        (
            12,
            [_sanction(kind=PunishmentKind.FINE, max_value=None)],
            {},
            CheckStatus.POSSIBLE_VIOLATION,
            "не предусматривает",
        ),
        (None, [_sanction()], {}, CheckStatus.INSUFFICIENT_DATA, "только лишение свободы"),
    ],
)
def test_imposed_imprisonment(months, sanctions, kwargs, status, fragment):
    result = _check(months, sanctions, **kwargs)
    assert result.status is status
    assert fragment in result.explanation
    assert "Не проверены" in result.explanation and result.needs_legal_review
