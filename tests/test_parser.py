from pathlib import Path

from src.services.document_parser import classify_pages, extract_document


def test_classify_pages():
    assert classify_pages([]) == "empty"
    assert classify_pages(["", "  "]) == "empty"
    assert classify_pages(["текст", "ещё"]) == "ok"
    assert classify_pages(["текст", ""]) == "partial"


async def test_txt(tmp_path: Path):
    p = tmp_path / "a.txt"
    p.write_text("Обвинительное заключение", encoding="utf-8")
    doc = await extract_document(p)
    assert (doc.text, doc.status, doc.page_count) == ("Обвинительное заключение", "ok", None)


async def test_docx(tmp_path: Path):
    import docx

    p = tmp_path / "a.docx"
    d = docx.Document()
    d.add_paragraph("Характеристика")
    d.save(str(p))
    doc = await extract_document(p)
    assert doc.status == "ok" and "Характеристика" in doc.text


async def test_unsupported_and_broken(tmp_path: Path):
    jpg = tmp_path / "scan.jpg"
    jpg.write_bytes(b"\xff\xd8\xff")
    assert (await extract_document(jpg)).status == "unsupported"

    pdf = tmp_path / "broken.pdf"
    pdf.write_bytes(b"not a pdf")
    broken = await extract_document(pdf)
    assert broken.status == "error" and broken.text == ""
