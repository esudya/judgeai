import pytest
from legal_core.entities import ArticleReference

from src.services.qualification_reference import parse_qualification_reference


@pytest.mark.parametrize(
    "text,expected",
    [
        ("п. «в» ч. 2 ст. 158 УК РФ", ArticleReference("158", 2)),
        ("ч. 3 ст. 30, п. «г» ч. 4 ст. 228.1 УК РФ", ArticleReference("228.1", 4)),
        ("ст. 264.1 УК РФ", ArticleReference("264.1", None)),
        ("ч.1 ст.105 УК РФ", ArticleReference("105", 1)),
    ],
)
def test_special_part_reference_is_found(text, expected):
    assert parse_qualification_reference(text) == expected


@pytest.mark.parametrize("text", [None, "", "ч. 1 ст. 62 УК РФ", "ст. 307 УПК РФ", "кража"])
def test_no_special_part_reference(text):
    assert parse_qualification_reference(text) is None


def test_reference_renders_for_reports():
    assert str(ArticleReference("158", 2)) == "ч. 2 ст. 158 УК РФ"
    assert str(ArticleReference("264.1")) == "ст. 264.1 УК РФ"
