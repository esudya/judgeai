import unittest
from dataclasses import replace

from legal_core.entities import Category, Guilt
from legal_core.rules.art18 import CurrentOffence, PriorConviction, Recidivism, classify_recidivism


class RecidivismTest(unittest.TestCase):
    def prior(self, identity="one", category=Category.MEDIUM, **kwargs):
        return PriorConviction(
            identity, Guilt.INTENTIONAL, category, True, True, True, True, False, False, **kwargs
        )

    def classify(self, category, priors, real=True, complete=True):
        return classify_recidivism(
            CurrentOffence(Guilt.INTENTIONAL, category, real), priors, history_complete=complete
        )

    def test_incomplete_history_does_not_mean_no_recidivism(self):
        self.assertEqual(self.classify(Category.GRAVE, [], complete=False), Recidivism.UNKNOWN)

    def test_empty_complete_history(self):
        self.assertEqual(self.classify(Category.GRAVE, []), Recidivism.NONE)

    def test_small_current_crime_can_have_simple_recidivism(self):
        self.assertEqual(self.classify(Category.SMALL, [self.prior()]), Recidivism.SIMPLE)

    def test_negligent_current_offence(self):
        current = CurrentOffence(Guilt.NEGLIGENT, Category.MEDIUM, True)
        self.assertEqual(
            classify_recidivism(current, [self.prior()], history_complete=True), Recidivism.NONE
        )

    def test_part4_exclusions(self):
        prior = self.prior()
        excluded = [
            replace(prior, guilt=Guilt.NEGLIGENT),
            replace(prior, category=Category.SMALL),
            replace(prior, adult_at_offence=False),
            replace(prior, active_at_offence=False),
            replace(prior, convicted_before_offence=False),
            replace(prior, conditional_or_deferred=True),
        ]
        for item in excluded:
            with self.subTest(item=item):
                self.assertEqual(self.classify(Category.GRAVE, [item]), Recidivism.NONE)

    def test_revoked_and_sent_before_new_offence_counts(self):
        prior = replace(
            self.prior(), conditional_or_deferred=True, revoked_and_sent_before_offence=True
        )
        self.assertEqual(self.classify(Category.SMALL, [prior]), Recidivism.SIMPLE)

    def test_two_medium_prior_sentences_make_dangerous(self):
        priors = [self.prior("one"), self.prior("two")]
        self.assertEqual(self.classify(Category.GRAVE, priors), Recidivism.DANGEROUS)
        self.assertEqual(self.classify(Category.GRAVE, priors, real=False), Recidivism.SIMPLE)
        self.assertEqual(self.classify(Category.ESPECIALLY_GRAVE, priors), Recidivism.DANGEROUS)

    def test_one_grave_prior_makes_dangerous(self):
        self.assertEqual(
            self.classify(Category.GRAVE, [self.prior(category=Category.GRAVE)]),
            Recidivism.DANGEROUS,
        )
        self.assertEqual(
            self.classify(Category.ESPECIALLY_GRAVE, [self.prior(category=Category.GRAVE)]),
            Recidivism.DANGEROUS,
        )

    def test_two_serious_priors_make_especially_dangerous(self):
        priors = [self.prior("one", Category.GRAVE), self.prior("two", Category.ESPECIALLY_GRAVE)]
        self.assertEqual(self.classify(Category.GRAVE, priors), Recidivism.ESPECIALLY_DANGEROUS)

    def test_especially_grave_current_and_prior(self):
        self.assertEqual(
            self.classify(
                Category.ESPECIALLY_GRAVE, [self.prior(category=Category.ESPECIALLY_GRAVE)]
            ),
            Recidivism.ESPECIALLY_DANGEROUS,
        )

    def test_substituted_imprisonment_is_not_original_sentence(self):
        prior = replace(self.prior(category=Category.GRAVE), imprisoned_by_sentence=False)
        self.assertEqual(self.classify(Category.GRAVE, [prior]), Recidivism.SIMPLE)

    def test_duplicate_judgments_are_rejected(self):
        with self.assertRaises(ValueError):
            self.classify(Category.GRAVE, [self.prior(), self.prior()])
