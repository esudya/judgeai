"""Adapter: free-text qualification ('п. «в» ч. 2 ст. 158 УК РФ') -> ArticleReference."""

import re

from legal_core.entities import ArticleReference

# Articles 1-104 form the General Part (no sanctions); a qualification such as
# 'ч. 3 ст. 30, п. «г» ч. 4 ст. 228.1' must resolve to the Special Part article.
FIRST_SPECIAL_PART_ARTICLE = 105

_REFERENCE = re.compile(r"(?:ч\.\s*(?P<part>\d{1,2})\s+)?ст\.\s*(?P<article>\d{1,3}(?:\.\d{1,2})*)")
_OTHER_CODE = re.compile(r"\b(?:УПК|КоАП|ГК|ГПК|АПК)\b")


def parse_qualification_reference(text: str | None) -> ArticleReference | None:
    """First Special Part article of УК РФ in the text, or None when there is none."""
    if not text or _OTHER_CODE.search(text):
        return None
    for match in _REFERENCE.finditer(text):
        article = match["article"]
        if int(article.split(".")[0]) >= FIRST_SPECIAL_PART_ARTICLE:
            part = int(match["part"]) if match["part"] else None
            return ArticleReference(article=article, part=part)
    return None
