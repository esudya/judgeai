"""Sanction parser over official УК РФ text (short public-law excerpts as fixtures)."""

import pytest

from src.services.statute_sanction_parser import (
    parse_article_sanctions,
    parse_russian_number,
    split_article_parts,
)

ART158 = (
    "Статья 158. Кража1. Кража, то есть тайное хищение чужого имущества, -наказывается штрафом в "
    "размере до восьмидесяти тысяч рублей или в размере заработной платы или иного дохода "
    "осужденного за период до шести месяцев, либо обязательными работами на срок до трехсот "
    "шестидесяти часов, либо исправительными работами на срок до одного года, либо ограничением "
    "свободы на срок до двух лет, либо принудительными работами на срок до двух лет, либо арестом "
    "на срок до четырех месяцев, либо лишением свободы на срок до двух лет. (В редакции "
    "Федерального закона от 07.12.2011 № 420-ФЗ)2. Кража, совершенная:а) группой лиц по "
    "предварительному сговору;в) с причинением значительного ущерба гражданину, -наказывается "
    "штрафом в размере до двухсот тысяч рублей, либо принудительными работами на срок до пяти лет "
    "с ограничением свободы на срок до одного года или без такового, либо лишением свободы на срок "
    "до пяти лет с ограничением свободы на срок до одного года или без такового.3. Кража, "
    "совершенная:г) с банковского счета (при отсутствии признаков преступления, предусмотренного "
    "статьей 159.3 настоящего Кодекса), -наказывается штрафом в размере от ста тысяч до пятисот "
    "тысяч рублей, либо лишением свободы на срок до шести лет со штрафом в размере до "
    "восьмидесяти тысяч рублей и с ограничением свободы на срок до полутора лет либо без такового."
    "Примечания. 1. Под хищением в статьях настоящего Кодекса понимаются..."
)

ART2281 = (
    "Статья 228.1. Незаконные производство, сбыт1. Незаконные производство, сбыт -наказываются "
    "лишением свободы на срок от четырех до восьми лет с ограничением свободы на срок до одного "
    "года либо без такового.2. Сбыт, совершенный:а) в следственном изоляторе, -наказывается "
    "лишением свободы на срок от пяти до двенадцати лет со штрафом в размере до пятисот тысяч "
    "рублей либо без такового.5. Деяния, совершенные в особо крупном размере, -наказываются "
    "лишением свободы на срок от пятнадцати до двадцати лет или пожизненным лишением свободы."
)


def _find(items, part, kind, role="main"):
    found = [s for s in items if s.part == part and s.kind.value == kind and s.role.value == role]
    assert len(found) == 1, (part, kind, role, items)
    return found[0]


@pytest.mark.parametrize(
    "words,value",
    [
        ("одного", 1),
        ("трехсот шестидесяти", 360),
        ("восьмидесяти тысяч", 80_000),
        ("пятисот тысяч", 500_000),
        ("одного миллиона", 1_000_000),
        ("полутора", 1.5),
        ("двадцати", 20),
        ("2", 2),
    ],
)
def test_parse_russian_number(words, value):
    assert parse_russian_number(words) == value


@pytest.mark.parametrize("words", ["", "много", "двадцатикратной"])
def test_parse_russian_number_rejects_unknown(words):
    assert parse_russian_number(words) is None


def test_split_article_parts_is_sequential_and_ignores_notes_and_decimals():
    parts = split_article_parts(ART158, title="Статья 158. Кража")
    assert [n for n, _ in parts] == [1, 2, 3]
    assert "159.3" in parts[2][1]
    assert "Примечани" not in parts[2][1]


def test_split_article_parts_skips_missing_numbers_only_forward():
    assert [n for n, _ in split_article_parts(ART2281, title="Статья 228.1. Незаконные")] == [
        1,
        2,
        5,
    ]


def test_article_158_part_1_main_alternatives():
    items = parse_article_sanctions("158", ART158, title="Статья 158. Кража")
    assert (
        _find(items, 1, "imprisonment").min_value,
        _find(items, 1, "imprisonment").max_value,
    ) == (
        None,
        24,
    )
    assert _find(items, 1, "imprisonment").unit.value == "months"
    assert _find(items, 1, "arrest").max_value == 4
    assert _find(items, 1, "compulsory_works").max_value == 360
    assert _find(items, 1, "compulsory_works").unit.value == "hours"
    assert _find(items, 1, "correctional_works").max_value == 12
    assert _find(items, 1, "fine").max_value == 80_000
    assert _find(items, 1, "fine").unit.value == "rubles"


def test_article_158_additional_punishments_are_marked():
    items = parse_article_sanctions("158", ART158, title="Статья 158. Кража")
    assert _find(items, 2, "imprisonment").max_value == 60
    extra = [s for s in items if s.part == 2 and s.role.value == "additional"]
    assert {s.kind.value for s in extra} == {"restriction_of_freedom"}
    assert all(s.max_value == 12 for s in extra)
    assert _find(items, 3, "fine").min_value == 100_000
    assert _find(items, 3, "fine").max_value == 500_000
    assert _find(items, 3, "restriction_of_freedom", role="additional").max_value == 18
    assert _find(items, 3, "fine", role="additional").max_value == 80_000


def test_article_228_1_minimums_and_life_imprisonment():
    items = parse_article_sanctions("228.1", ART2281, title="Статья 228.1. Незаконные")
    first = _find(items, 1, "imprisonment")
    assert (first.min_value, first.max_value) == (48, 96)
    assert (
        _find(items, 2, "imprisonment").min_value,
        _find(items, 2, "imprisonment").max_value,
    ) == (
        60,
        144,
    )
    life = _find(items, 5, "life_imprisonment")
    assert life.min_value is None and life.max_value is None
    assert "наказыва" in first.clause


def test_mixed_units_in_one_range():
    text = "Статья 999. Тест1. Деяние -наказывается арестом на срок от двух месяцев до одного года."
    item = _find(parse_article_sanctions("999", text, title="Статья 999. Тест"), 1, "arrest")
    assert (item.min_value, item.max_value) == (2, 12)


def test_single_paragraph_article_has_no_part_number():
    text = "Статья 998. Тест Деяние -наказывается лишением свободы на срок до трех лет."
    item = _find(
        parse_article_sanctions("998", text, title="Статья 998. Тест"), None, "imprisonment"
    )
    assert item.max_value == 36


def test_unparseable_amount_keeps_kind_without_bounds():
    text = (
        "Статья 997. Тест1. Деяние -наказывается штрафом в размере от двадцатикратной до "
        "сорокакратной суммы взятки."
    )
    item = _find(parse_article_sanctions("997", text, title="Статья 997. Тест"), 1, "fine")
    assert item.min_value is None and item.max_value is None and item.unit is None


def test_part_without_sanction_and_repealed_part_yield_nothing():
    text = "Статья 996. Тест1. Определение без наказания.2. Утратила силу."
    assert parse_article_sanctions("996", text, title="Статья 996. Тест") == []


def test_deprivation_of_right_term_follows_its_description():
    text = (
        "Статья 995. Тест1. Деяние -наказывается лишением свободы на срок до двух лет с лишением "
        "права занимать определенные должности или заниматься определенной деятельностью на срок "
        "до трех лет или без такового."
    )
    items = parse_article_sanctions("995", text, title="Статья 995. Тест")
    assert _find(items, 1, "deprivation_of_right", role="additional").max_value == 36


def test_same_term_reuses_previous_main_alternative():
    text = (
        "Статья 994. Тест1. Деяние -наказывается принудительными работами на срок от одного года "
        "до трех лет, либо лишением свободы на тот же срок."
    )
    item = _find(parse_article_sanctions("994", text, title="Статья 994. Тест"), 1, "imprisonment")
    assert (item.min_value, item.max_value) == (12, 36)
