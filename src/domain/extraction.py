"""Registry of extracted fields: every value keeps how it was read and from what.

The idempotency key is (field, extractor version, sha256 of the input): the same input read by
the same extractor version never produces a second record.
"""

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from typing import Any


class ExtractionMethod(StrEnum):
    REGEX = "regex"
    LLM = "llm"
    NONE = "none"


def input_hash(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ExtractedField:
    name: str
    value: Any
    method: ExtractionMethod
    quote: str
    extractor_version: str
    input_hash: str

    def __post_init__(self) -> None:
        if self.method is ExtractionMethod.NONE:
            if self.value is not None or self.quote:
                raise ValueError("an absent field has neither a value nor a quote")
            return
        if self.value is None:
            raise ValueError("a found field needs a value")
        if not self.quote.strip():
            raise ValueError("a found field needs a quote from the source text")

    @classmethod
    def absent(cls, name: str, extractor_version: str, source_hash: str) -> "ExtractedField":
        return cls(name, None, ExtractionMethod.NONE, "", extractor_version, source_hash)

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.name, self.extractor_version, self.input_hash)
