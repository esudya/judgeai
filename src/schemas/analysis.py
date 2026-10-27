"""Structured case analysis — the contract between the backend and the cabinet UI.

Stored in `Message.analysis` (with `schema_version`) and served as `MessageRead.result`.
Field names are snake_case like the rest of the API; the frontend adapter maps them to the
camelCase `CaseAnalysis` in its src/api/types.ts.
"""

from typing import Literal

from pydantic import BaseModel, Field, StrictBool, StrictInt, StrictStr

SCHEMA_VERSION = 1


class ApiModel(BaseModel):
    pass


class AnalysisStats(ApiModel):
    documents: int
    pages: int
    seconds: int


class Qualification(ApiModel):
    article: str = Field(description="e.g. 'п. «в» ч. 2 ст. 158 УК РФ'")
    title: str


class Circumstance(ApiModel):
    name: str
    norm: str


class PunishmentVariant(ApiModel):
    label: str
    title: str
    details: str
    rationale: str


class SimilarVerdictRef(ApiModel):
    verdict_id: int | None = None
    punishment: str
    court: str
    match: str
    score: int = Field(ge=0, le=100)


class SentenceScale(ApiModel):
    """All terms in months; the UI draws them on a 0..sanction_max_months axis."""

    sanction_max_months: int = Field(gt=0)
    limit_months: int | None = None
    limit_norm: str | None = None
    practice_months: tuple[int, int] | None = None
    avg_similar_months: int | None = None
    recommended_months: int | None = Field(default=None, ge=0)
    within_sanction: bool | None = None
    extra_notes: list[str] = []


class DraftDocument(ApiModel):
    filename: str
    note: str


class CaseAnalysis(ApiModel):
    legal_checks: list["LegalCheck"] = Field(default_factory=list)
    schema_version: Literal[1] = SCHEMA_VERSION
    stats: AnalysisStats
    prompt: str
    fabula: str
    qualification: Qualification | None = None
    draft: DraftDocument | None = None
    scale: SentenceScale | None = None
    mitigating: list[Circumstance] = []
    aggravating: str | None = None
    personality: str | None = None
    variants: list[PunishmentVariant] = []
    similar: list[SimilarVerdictRef] = []
    # Human-readable caveats the UI must show (e.g. unverified sanction, partial OCR).
    warnings: list[str] = []


class LlmCaseFacts(BaseModel):
    """What the LLM is asked to extract. Legal arithmetic is done in code, not by the model."""

    fabula: str
    legal_facts: "LegalFacts | None" = None
    qualification: Qualification | None = None
    sanction_max_months: int | None = Field(
        default=None, gt=0, description="Max term of imprisonment in the article's sanction, months"
    )
    mitigating: list[Circumstance] = []
    aggravating: list[Circumstance] = []
    personality: str | None = None
    recommended_months: int | None = Field(default=None, ge=0)
    variants: list[PunishmentVariant] = []


class CitedFact(BaseModel):
    value: StrictStr | StrictInt | StrictBool
    quote: str = Field(min_length=6, max_length=2000)


class LegalFacts(BaseModel):
    guilt: CitedFact | None = None
    category: CitedFact | None = None
    sanction_max_months: CitedFact | None = None
    harsher_than_imprisonment: CitedFact | None = None
    real_imprisonment: CitedFact | None = None
    history_complete: CitedFact | None = None
    # Each dictionary describes ONE distinct prior judgment and cites every supplied field.
    prior_convictions: list[dict[str, CitedFact]] = Field(default_factory=list, max_length=100)


class LegalCheck(BaseModel):
    norm: str
    status: Literal["ok", "possible_violation", "insufficient_data"]
    explanation: str
    source: str
    value: str | None = None
    evidence: list[str] = Field(default_factory=list)
    needs_legal_review: bool = True


# Resolve references declared below the backwards-compatible result classes.
CaseAnalysis.model_rebuild()
LlmCaseFacts.model_rebuild()
