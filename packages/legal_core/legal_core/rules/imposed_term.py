# Domain Layer — is the imposed term of imprisonment within the statutory limits?
# Limits: the sanction of the article part (min/max), ч. 1 ст. 62 УК РФ (two thirds) and
# ст. 64 УК РФ (going below the minimum). Not checked here: ч. 5 ст. 62, ст. 65, 66, 68.
from legal_core.checks import CheckResult, CheckStatus
from legal_core.entities import (
    ImposedPunishment,
    MeasureUnit,
    PunishmentKind,
    SanctionRole,
    StatutorySanction,
)

NORM = "Назначенное наказание: пределы санкции и ч. 1 ст. 62 УК РФ"
NOT_COVERED = "Не проверены ч. 5 ст. 62, ст. 65, 66, 68 УК РФ."


def main_imprisonment(sanctions: list[StatutorySanction]) -> StatutorySanction | None:
    return next(
        (
            s
            for s in sanctions
            if s.kind is PunishmentKind.IMPRISONMENT
            and s.role is SanctionRole.MAIN
            and s.unit is MeasureUnit.MONTHS
        ),
        None,
    )


def check_imposed_imprisonment(
    imposed: ImposedPunishment,
    sanctions: list[StatutorySanction],
    *,
    source: str,
    art62_limit_months: int | None = None,
    art64_applied: bool = False,
) -> CheckResult:
    """Candidate check of the imposed imprisonment term against the statutory limits."""

    def result(status: CheckStatus, why: str) -> CheckResult:
        return CheckResult(NORM, status, f"{why} {NOT_COVERED}", source)

    months = imposed.imprisonment_months
    if months is None:
        return result(CheckStatus.INSUFFICIENT_DATA, "Проверяется только лишение свободы.")
    term = main_imprisonment(sanctions)
    if term is None or term.max_value is None:
        return result(
            CheckStatus.POSSIBLE_VIOLATION,
            "Санкция этой части статьи не предусматривает лишения свободы.",
        )
    if months > term.max_value:
        return result(
            CheckStatus.POSSIBLE_VIOLATION,
            f"Назначено {months} мес. при максимуме санкции {int(term.max_value)} мес.",
        )
    if term.min_value is not None and months < term.min_value and not art64_applied:
        return result(
            CheckStatus.POSSIBLE_VIOLATION,
            f"Назначено {months} мес. ниже минимума санкции {int(term.min_value)} мес. "
            "без применения ст. 64 УК РФ.",
        )
    if art62_limit_months is not None and months > art62_limit_months:
        return result(
            CheckStatus.POSSIBLE_VIOLATION,
            f"Назначено {months} мес. при пределе {art62_limit_months} мес. "
            "(две трети максимума, ч. 1 ст. 62 УК РФ).",
        )
    return result(CheckStatus.OK, f"Назначено {months} мес.: в пределах проверенных ограничений.")
