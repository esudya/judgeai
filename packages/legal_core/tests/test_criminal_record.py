import unittest
from dataclasses import replace
from datetime import date

from legal_core.criminal_record import (
    Conviction,
    CriminalRecord,
    adult_on,
    classify_record,
    eighteenth_birthday,
)
from legal_core.entities import Category, Guilt
from legal_core.rules.art18 import CurrentOffence, Recidivism

OFFENCE = date(2026, 5, 10)


def conviction(identity="one", category=Category.MEDIUM, **kwargs):
    values = dict(
        judgment_id=identity,
        guilt=Guilt.INTENTIONAL,
        category=category,
        offence_date=date(2020, 1, 15),
        legal_force_date=date(2020, 6, 1),
        imprisoned_by_sentence=True,
        conditional_or_deferred=False,
        sent_to_prison_on=None,
        active_at_offence=True,
    )
    values.update(kwargs)
    return Conviction(**values)


def record(*convictions, birth=date(1990, 3, 3), complete=True):
    return CriminalRecord(birth_date=birth, convictions=tuple(convictions), complete=complete)


GRAVE_REAL = CurrentOffence(Guilt.INTENTIONAL, Category.GRAVE, True)


class AgeTest(unittest.TestCase):
    def test_age_is_reached_the_day_after_birthday(self):
        # Plenum 1 of 2011-02-01, para.7: from 00:00 of the day after the birthday.
        birth = date(2000, 4, 20)
        self.assertEqual(eighteenth_birthday(birth), date(2018, 4, 20))
        self.assertFalse(adult_on(birth, date(2018, 4, 20)))
        self.assertTrue(adult_on(birth, date(2018, 4, 21)))

    def test_leap_day_birth_uses_last_day_of_february(self):
        # Civil Code art.192 p.3: missing day of month -> last day of the month.
        birth = date(2004, 2, 29)
        self.assertEqual(eighteenth_birthday(birth), date(2022, 2, 28))
        self.assertFalse(adult_on(birth, date(2022, 2, 28)))
        self.assertTrue(adult_on(birth, date(2022, 3, 1)))


class ConvictionFactsTest(unittest.TestCase):
    def test_full_facts_map_to_art18_prior(self):
        prior = record(conviction()).priors_for(OFFENCE)[0]
        self.assertTrue(prior.adult_at_offence)
        self.assertTrue(prior.convicted_before_offence)
        self.assertTrue(prior.eligible)

    def test_judgment_in_force_after_new_offence_is_not_a_record(self):
        late = conviction(legal_force_date=date(2026, 6, 1))
        prior = record(late).priors_for(OFFENCE)[0]
        self.assertFalse(prior.convicted_before_offence)

    def test_minor_at_prior_offence_is_excluded(self):
        young = conviction(offence_date=date(2008, 3, 3))
        prior = record(young).priors_for(OFFENCE)[0]
        self.assertFalse(prior.adult_at_offence)

    def test_revocation_before_new_offence(self):
        cond = conviction(conditional_or_deferred=True, revocation_decision_date=date(2025, 1, 1))
        self.assertTrue(record(cond).priors_for(OFFENCE)[0].revoked_and_sent_before_offence)
        late = replace(cond, revocation_decision_date=date(2026, 7, 1))
        self.assertFalse(record(late).priors_for(OFFENCE)[0].revoked_and_sent_before_offence)

    def test_unknown_or_ambiguous_facts_give_no_priors(self):
        cases = [
            record(conviction(), birth=None),
            record(conviction(legal_force_date=None)),
            record(conviction(legal_force_date=OFFENCE)),  # same day: order unknown
            record(conviction(active_at_offence=None)),
            record(conviction(offence_date=None)),
            record(conviction(conditional_or_deferred=True, revocation_decision_date=OFFENCE)),
        ]
        for item in cases:
            with self.subTest(item=item):
                self.assertIsNone(item.priors_for(OFFENCE))

    def test_irrelevant_unknowns_do_not_block(self):
        # Age and dates do not matter for a negligent prior: it is excluded anyway.
        negligent = conviction(guilt=Guilt.NEGLIGENT, legal_force_date=None)
        self.assertIsNotNone(record(negligent).priors_for(OFFENCE))


class ClassifyRecordTest(unittest.TestCase):
    def test_reference_cases(self):
        two_medium = record(conviction("a"), conviction("b"))
        cases = [
            (record(), GRAVE_REAL, Recidivism.NONE),
            (record(complete=False), GRAVE_REAL, Recidivism.UNKNOWN),
            (record(conviction()), GRAVE_REAL, Recidivism.SIMPLE),
            (two_medium, GRAVE_REAL, Recidivism.DANGEROUS),
            (record(conviction(category=Category.GRAVE)), GRAVE_REAL, Recidivism.DANGEROUS),
            (record(conviction(legal_force_date=None)), GRAVE_REAL, Recidivism.UNKNOWN),
        ]
        for rec, current, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(classify_record(rec, current, OFFENCE), expected)

    def test_negligent_current_offence_needs_no_history(self):
        current = CurrentOffence(Guilt.NEGLIGENT, Category.MEDIUM, True)
        rec = record(conviction(legal_force_date=None), complete=False)
        self.assertEqual(classify_record(rec, current, OFFENCE), Recidivism.NONE)


if __name__ == "__main__":
    unittest.main()


class RevocationDecisionTest(unittest.TestCase):
    def test_decision_before_new_offence_counts_even_when_transfer_is_later(self):
        # The decision date is decisive; actual transfer on May 20 is irrelevant.
        prior = conviction(conditional_or_deferred=True, sent_to_prison_on=date(2026, 5, 20))
        prior = replace(prior, revocation_decision_date=date(2026, 5, 1))
        self.assertEqual(classify_record(record(prior), GRAVE_REAL, OFFENCE), Recidivism.SIMPLE)

    def test_physical_transfer_alone_does_not_prove_revocation_decision_date(self):
        prior = conviction(conditional_or_deferred=True, sent_to_prison_on=date(2026, 5, 1))
        self.assertEqual(classify_record(record(prior), GRAVE_REAL, OFFENCE), Recidivism.UNKNOWN)

    def test_missing_revocation_decision_is_unknown(self):
        prior = conviction(conditional_or_deferred=True)
        self.assertEqual(classify_record(record(prior), GRAVE_REAL, OFFENCE), Recidivism.UNKNOWN)
