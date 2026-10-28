from src.domain.embedding_text import build_embedding_text


def test_removes_persons_dates_courts_addresses_and_articles():
    fabula = (
        "Иванов И.И. 10 января 2026 года около 14:30 у дома 5 по ул. Ленина г. Примерска "
        "тайно похитил у Потерпевший №1 телефон, причинив ущерб 40 000 рублей; "
        "Петрова А.Б. и К. 29.01.2026 действовали группой. Квалифицировано по п. «в» ч. 2 "
        "ст. 158 УК РФ. Условный районный суд г. Примерска установил вину."
    )
    text = build_embedding_text(fabula)
    for leaked in (
        "Иванов",
        "Петрова",
        "И.И.",
        "К.",
        "января",
        "2026",
        "14:30",
        "Ленина",
        "Примерска",
        "Потерпевший №1",
        "158",
        "районный суд",
    ):
        assert leaked not in text, leaked
    assert "тайно похитил" in text and "телефон" in text and "40 000 рублей" in text


def test_empty_and_whitespace():
    assert build_embedding_text("") == ""
    assert build_embedding_text("  кража \n\n телефона ") == "кража телефона"
