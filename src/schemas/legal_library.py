from datetime import date
from typing import Literal
from urllib.parse import urlsplit

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

OFFICIAL_HOSTS = {
    "pravo.gov.ru",
    "publication.pravo.gov.ru",
    "kremlin.ru",
    "www.kremlin.ru",
    "vsrf.ru",
    "www.vsrf.ru",
}


class ActImport(BaseModel):
    key: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,79}$")
    title: str = Field(min_length=1, max_length=2000)
    kind: Literal["constitution", "code", "federal_law", "plenum", "constitutional_court_decision"]
    number: str | None = Field(default=None, max_length=80)
    adopted_on: date | None = None


class ProvisionImport(BaseModel):
    locator: str = Field(min_length=1, max_length=160)
    title: str = Field(min_length=1, max_length=2000)
    body: str = Field(min_length=1, max_length=2_000_000)
    ordinal: int = Field(ge=0)
    start_page: int | None = Field(default=None, ge=1)
    end_page: int | None = Field(default=None, ge=1)


class SnapshotImport(BaseModel):
    act: ActImport
    source_url: str = Field(max_length=5000)
    raw_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    retrieved_at: AwareDatetime
    edition_label: str = Field(min_length=1, max_length=2000)
    full_text: str = Field(min_length=1, max_length=20_000_000)
    parser_version: str = Field(min_length=1, max_length=120)
    provisions: list[ProvisionImport] = Field(min_length=1, max_length=10000)

    @field_validator("source_url")
    @classmethod
    def official_source(cls, value):
        parts = urlsplit(value)
        if (
            parts.scheme not in ("http", "https")
            or parts.hostname not in OFFICIAL_HOSTS
            or parts.username
            or parts.password
            or parts.port not in (None, 80, 443)
        ):
            raise ValueError("only explicit official source hosts are accepted")
        return value

    @field_validator("full_text")
    @classmethod
    def nonempty_text(cls, value):
        if not value.strip():
            raise ValueError("source text is empty")
        return value

    @model_validator(mode="after")
    def unique_provisions(self):
        if len({p.locator for p in self.provisions}) != len(self.provisions):
            raise ValueError("duplicate provision locator")
        if len({p.ordinal for p in self.provisions}) != len(self.provisions):
            raise ValueError("duplicate provision order")
        return self


class ActRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    key: str
    title: str
    kind: str
    number: str | None
    adopted_on: date | None
