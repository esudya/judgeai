"""Russian cardinal numbers in words ('восьмидесяти тысяч', 'полутора') -> numbers.

Shared by the statute parser and the verdict punishment extractor.
"""

_NUMBER_WORDS: dict[str, float] = {
    **dict.fromkeys(["один", "одна", "одного", "одной", "одну", "одному"], 1),
    **dict.fromkeys(["два", "две", "двух", "двум"], 2),
    **dict.fromkeys(["три", "трех", "трёх", "трем", "трём"], 3),
    **dict.fromkeys(["четыре", "четырех", "четырёх", "четырем", "четырём"], 4),
    **dict.fromkeys(["пять", "пяти"], 5),
    **dict.fromkeys(["шесть", "шести"], 6),
    **dict.fromkeys(["семь", "семи"], 7),
    **dict.fromkeys(["восемь", "восьми"], 8),
    **dict.fromkeys(["девять", "девяти"], 9),
    **dict.fromkeys(["десять", "десяти"], 10),
    "одиннадцати": 11,
    "двенадцати": 12,
    "тринадцати": 13,
    "четырнадцати": 14,
    "пятнадцати": 15,
    "шестнадцати": 16,
    "семнадцати": 17,
    "восемнадцати": 18,
    "девятнадцати": 19,
    **dict.fromkeys(["двадцать", "двадцати"], 20),
    **dict.fromkeys(["тридцать", "тридцати"], 30),
    **dict.fromkeys(["сорок", "сорока"], 40),
    **dict.fromkeys(["пятьдесят", "пятидесяти"], 50),
    **dict.fromkeys(["шестьдесят", "шестидесяти"], 60),
    **dict.fromkeys(["семьдесят", "семидесяти"], 70),
    **dict.fromkeys(["восемьдесят", "восьмидесяти"], 80),
    **dict.fromkeys(["девяносто", "девяноста"], 90),
    **dict.fromkeys(["сто", "ста"], 100),
    "двухсот": 200,
    **dict.fromkeys(["трехсот", "трёхсот"], 300),
    **dict.fromkeys(["четырехсот", "четырёхсот"], 400),
    "пятисот": 500,
    "шестисот": 600,
    "семисот": 700,
    "восьмисот": 800,
    "девятисот": 900,
    "полутора": 1.5,
}
_MULTIPLIERS = {
    **dict.fromkeys(["тысяча", "тысячи", "тысяч", "тысячу"], 1_000),
    **dict.fromkeys(["миллион", "миллиона", "миллионов"], 1_000_000),
}


def parse_russian_number(words: str) -> float | None:
    """'восьмидесяти тысяч' -> 80000; returns None for anything outside the vocabulary."""
    tokens = words.lower().split()
    if not tokens:
        return None
    total, current = 0.0, 0.0
    for token in tokens:
        if token.isdigit():
            current += int(token)
        elif token in _NUMBER_WORDS:
            current += _NUMBER_WORDS[token]
        elif token in _MULTIPLIERS:
            total += (current or 1) * _MULTIPLIERS[token]
            current = 0
        else:
            return None
    value = total + current
    return int(value) if float(value).is_integer() else value
