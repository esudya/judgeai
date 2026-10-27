"""Extract source text without assigning legal validity or interpreting a statute."""

import re
from email import policy
from email.parser import BytesParser
from html.parser import HTMLParser

from src.schemas.legal_library import ProvisionImport

PARSER_VERSION = "official-source-v1"


class _VisibleText(HTMLParser):
    def __init__(self, article_body: bool):
        super().__init__()
        self.article_body = article_body
        self.root = "div" if article_body else "body"
        self.depth = 0
        self.skip = 0
        self.parts = []
        self.raised = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if not self.depth:
            if tag == self.root and (
                not self.article_body or attrs.get("itemprop") == "articleBody"
            ):
                self.depth = 1
            return
        if tag == self.root:
            self.depth += 1
        if tag in ("script", "style"):
            self.skip += 1
        if self.skip:
            return
        if tag in ("p", "h1", "h2", "h3", "h4", "li", "br"):
            self.parts.append("\n")
        if tag == "sup" or (tag == "span" and "W9" in attrs.get("class", "").split()):
            self.raised += 1

    def handle_endtag(self, tag):
        if not self.depth:
            return
        if tag in ("sup", "span"):
            self.raised = max(0, self.raised - 1)
        if tag in ("script", "style"):
            self.skip = max(0, self.skip - 1)
        if not self.skip and tag in ("p", "h1", "h2", "h3", "h4", "li"):
            self.parts.append("\n")
        if tag == self.root:
            self.depth -= 1

    def handle_data(self, text):
        if self.depth and not self.skip:
            previous = next(
                (piece.rstrip()[-1] for piece in reversed(self.parts) if piece.rstrip()), ""
            )
            if self.raised and text.strip().isdigit() and previous.isdigit():
                self.parts.append(".")
            self.parts.append(text)


def extract_html(html: str, *, article_body: bool = False) -> str:
    parser = _VisibleText(article_body)
    parser.feed(html)
    lines = [re.sub(r"[^\S\n]+", " ", line).strip() for line in "".join(parser.parts).splitlines()]
    text = "\n".join(line for line in lines if line)
    if not text:
        raise ValueError("official document body was not found")
    return text


def extract_mhtml(raw: bytes) -> str:
    message = BytesParser(policy=policy.default).parsebytes(raw)
    parts = [p for p in message.walk() if p.get_content_type() == "text/html"]
    if len(parts) != 1:
        raise ValueError("expected one HTML part in the official export")
    part = parts[0]
    payload = part.get_payload(decode=True)
    if payload is None:
        raise ValueError("empty HTML payload")
    return extract_html(payload.decode(part.get_content_charset() or "windows-1251"))


def split_articles(text: str) -> list[ProvisionImport]:
    matches = [
        (m.start(), m.group().strip(), "article." + m.group(1))
        for m in re.finditer(r"(?m)^Статья[ \t]+(\d+(?:\.\d+)*)(?:\.(?!\d)[^\n]*|\*?[ \t]*$)", text)
    ]
    matches += [
        (m.start(), m.group().strip(), "transitional")
        for m in re.finditer(r"(?mi)^Раздел второй[^\n]*", text)
    ]
    matches.sort()
    if not matches:
        raise ValueError("no article headings found; manual source review required")
    if len({locator for _, _, locator in matches}) != len(matches):
        raise ValueError("duplicate article identifiers; source review required")
    if text[: matches[0][0]].strip():
        matches.insert(0, (0, "Preamble and source notes", "preamble"))
    provisions = []
    for index, (start, title, locator) in enumerate(matches):
        end = matches[index + 1][0] if index + 1 < len(matches) else len(text)
        provisions.append(
            ProvisionImport(
                locator=locator, title=title, body=text[start:end].strip(), ordinal=index
            )
        )
    return provisions
