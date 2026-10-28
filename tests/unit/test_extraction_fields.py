import pytest

from src.domain.extraction import ExtractedField, ExtractionMethod, input_hash


def test_field_idempotency_key_and_hash():
    field = ExtractedField(
        "recidivism", "none", ExtractionMethod.REGEX, "ранее не судим", "v/1", "h"
    )
    assert field.key == ("recidivism", "v/1", "h")
    assert input_hash("текст") == input_hash("текст") != input_hash("другой")
    assert len(input_hash("x")) == 64


def test_absent_field_has_no_quote():
    field = ExtractedField.absent("final_sentence", "v/1", "h")
    assert field.method is ExtractionMethod.NONE and field.value is None and field.quote == ""


def test_found_value_needs_a_quote():
    with pytest.raises(ValueError):
        ExtractedField("fabula", "x", ExtractionMethod.REGEX, "", "v/1", "h")
    with pytest.raises(ValueError):
        ExtractedField("fabula", None, ExtractionMethod.REGEX, "q", "v/1", "h")
