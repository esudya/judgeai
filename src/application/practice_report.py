"""Use case: precedents comparable to a draft and the draft's place among their terms (T28).

The search decides comparability (channels, filters, axes); the comparison only counts terms
of what the search kept. A wider pool than the list shown is used for the statistics, so the
distribution is not limited to the first screen of results.
"""

from dataclasses import dataclass

from legal_core.precedents import PrecedentCard
from legal_core.rules.practice_comparison import PracticeComparison, compare_with_practice

from src.application.similar_precedents import (
    EmbeddingPort,
    FindSimilarPrecedents,
    PrecedentStore,
    SimilarPrecedent,
)

SHOWN = 10
STATISTICS_POOL = 50


@dataclass(frozen=True)
class PracticeReport:
    query: PrecedentCard
    shown: list[SimilarPrecedent]
    candidates: int
    excluded: int
    vector_used: bool
    comparison: PracticeComparison


async def compare_draft_with_practice(
    store: PrecedentStore, embedder: EmbeddingPort, query: PrecedentCard
) -> PracticeReport:
    found = await FindSimilarPrecedents(store, embedder).execute(query, STATISTICS_POOL)
    comparison = compare_with_practice(
        [item.stored.card for item in found.items], query.imprisonment_months
    )
    return PracticeReport(
        query, found.items[:SHOWN], found.candidates, found.excluded, found.vector_used, comparison
    )
