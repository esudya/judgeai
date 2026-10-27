import pytest

from src.services.legal_source_parser import extract_html, extract_mhtml, split_articles


def test_mhtml_superscript_numbers_do_not_become_different_articles():
    raw = (
        b'MIME-Version: 1.0\r\nContent-Type: multipart/related; boundary="boundary"\r\n\r\n'
        b"--boundary\r\nContent-Type: text/html; charset=utf-8\r\n\r\n"
        + '<html><body><p>Статья 228<span class="W9">1</span>. Synthetic title</p>'
        '<p>1<span class="W9">1</span>. Synthetic clause.</p></body></html>'.encode()
        + b"\r\n--boundary--\r\n"
    )
    text = extract_mhtml(raw)
    provisions = split_articles(text)
    assert provisions[0].locator == "article.228.1"
    assert "1.1. Synthetic clause." in provisions[0].body


def test_constitution_parser_excludes_page_navigation():
    html = (
        '<body><p>Navigation</p><div itemprop="articleBody">'
        "<h3>Статья 1</h3><p>Rule.</p></div><p>Footer</p></body>"
    )
    text = extract_html(html, article_body=True)
    assert "Navigation" not in text and "Footer" not in text
    assert split_articles(text)[0].body == "Статья 1\nRule."


def test_duplicate_article_numbers_fail_instead_of_picking_one():
    with pytest.raises(ValueError, match="duplicate"):
        split_articles("Статья 1. First\nA\nСтатья 1. Second\nB")


def test_missing_source_body_is_rejected():
    with pytest.raises(ValueError):
        extract_mhtml(b"Not a source document")
    with pytest.raises(ValueError):
        extract_html("<body>Only a menu</body>", article_body=True)


def test_numbered_article_with_footnote_is_not_the_parent_article():
    parts = split_articles(
        "Статья 67\nA\nСтатья 67.1*\nB\nСтатья 83\nC\nСтатья 83 дополнена новым пунктом."
    )
    assert [p.locator for p in parts] == ["article.67", "article.67.1", "article.83"]
    assert "дополнена" in parts[-1].body


def test_non_numeric_superscript_footnote_does_not_add_a_decimal_point():
    text = extract_html("<body><p>Rule.<sup>i</sup></p></body>")
    assert text == "Rule.i"
