"""Deterministic sentencing arithmetic (no LLM).

Only rules that follow directly from the text of the Criminal Code live here.
"""

import math
import re

from src.schemas.analysis import Circumstance

# ч. 1 ст. 62 УК РФ: with mitigating circumstances under п. «и» и (или) «к» ч. 1 ст. 61 and no
# aggravating circumstances, the term cannot exceed two thirds of the maximum of the most severe
# punishment in the sanction.
_PART1_ART61 = re.compile(r"ч\.?\s*1\s*ст\.?\s*61(?!\d)(?!\.\d)", re.IGNORECASE)
_ITEM_LETTER = re.compile(r"«\s*([а-яё])\s*»", re.IGNORECASE)
_ART62_LETTERS = {"и", "к"}


def _cites_art61_part1_items(norm: str) -> set[str]:
    """Item letters of ч. 1 ст. 61 cited in a norm, e.g. 'п. «г», «и» ч. 1 ст. 61' -> {'г','и'}."""
    match = _PART1_ART61.search(norm)
    if not match:
        return set()
    return {letter.lower() for letter in _ITEM_LETTER.findall(norm[: match.start()])}


def has_art62_part1_mitigation(mitigating: list[Circumstance]) -> bool:
    return any(_cites_art61_part1_items(c.norm or "") & _ART62_LETTERS for c in mitigating)


def art62_part1_limit(
    sanction_max_months: int,
    mitigating: list[Circumstance],
    aggravating: list[Circumstance],
) -> int | None:
    """Upper limit in whole months, or None when ч. 1 ст. 62 does not apply.

    Rounded down: rounding up could produce a term above the statutory two thirds.
    """
    if sanction_max_months <= 0 or aggravating or not has_art62_part1_mitigation(mitigating):
        return None
    return math.floor(sanction_max_months * 2 / 3)
