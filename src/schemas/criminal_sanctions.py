from pydantic import BaseModel


class SanctionProvenance(BaseModel):
    edition_id: int
    edition_label: str
    source_url: str
    source_sha256: str
    verification_status: str
    provision_locator: str
    parser_version: str


class CriminalSanctionRead(BaseModel):
    article: str
    part: int | None
    kind: str
    role: str
    min_value: float | None
    max_value: float | None
    unit: str | None
    clause: str
    provenance: SanctionProvenance
