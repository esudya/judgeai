from legal_core.entities import ArticleReference, MeasureUnit, PunishmentKind, PunishmentTerm

from src.services.verdict_structure import read_verdict_structure
from tests.fixtures.synthetic_verdicts import AMBIGUOUS, MULTI_COUNT, NO_HEADINGS


def test_structure_reads_counts_and_keeps_operative_in_model_text():
    structure = read_verdict_structure([NO_HEADINGS, MULTI_COUNT], chars_limit=2400)
    assert structure.model_texts[0] == NO_HEADINGS
    assert "окончательно назначить" in structure.model_texts[1]
    assert len(structure.sentence.counts) == 2
    assert structure.ambiguous_windows == ()


def test_resolved_window_becomes_a_count():
    structure = read_verdict_structure([AMBIGUOUS], chars_limit=10_000)
    window = structure.ambiguous_windows[0]
    term = PunishmentTerm(PunishmentKind.IMPRISONMENT, 12, MeasureUnit.MONTHS)
    sentence = structure.with_resolved_windows([(window, term), ("other", None)])
    assert len(sentence.counts) == 1
    assert sentence.counts[0].reference == ArticleReference("158", 1)
    assert sentence.counts[0].main == term


def test_no_documents():
    structure = read_verdict_structure([], chars_limit=1000)
    assert structure.sentence.is_empty and structure.model_texts == []
