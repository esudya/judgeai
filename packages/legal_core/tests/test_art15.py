# Domain test — ст. 15 УК РФ (категории преступлений), редакция от 04.08.2026.
import unittest

from legal_core.checks import CheckStatus
from legal_core.entities import Category, Guilt, ImposedPunishment, SanctionCeiling
from legal_core.rules.art15 import categorize, check_category_change

Y = 12  # months in a year


def ceiling(years=None, *, harsher=False):
    return SanctionCeiling(
        max_imprisonment_months=None if years is None else years * Y,
        harsher_than_imprisonment=harsher,
    )


class CategorizeTest(unittest.TestCase):
    def test_part2_small_up_to_three_years_both_forms_of_guilt(self):
        for guilt in Guilt:
            self.assertEqual(categorize(guilt, ceiling(3)), Category.SMALL)

    def test_part2_no_imprisonment_in_sanction_is_small(self):
        self.assertEqual(categorize(Guilt.INTENTIONAL, ceiling(None)), Category.SMALL)

    def test_part3_medium(self):
        self.assertEqual(categorize(Guilt.INTENTIONAL, ceiling(5)), Category.MEDIUM)
        self.assertEqual(categorize(Guilt.NEGLIGENT, ceiling(10)), Category.MEDIUM)

    def test_part4_grave(self):
        self.assertEqual(categorize(Guilt.INTENTIONAL, ceiling(10)), Category.GRAVE)
        self.assertEqual(categorize(Guilt.NEGLIGENT, ceiling(15)), Category.GRAVE)

    def test_part5_especially_grave_intentional_over_ten_or_harsher(self):
        self.assertEqual(categorize(Guilt.INTENTIONAL, ceiling(11)), Category.ESPECIALLY_GRAVE)
        self.assertEqual(
            categorize(Guilt.INTENTIONAL, ceiling(20, harsher=True)), Category.ESPECIALLY_GRAVE
        )

    def test_boundary_one_month_over_three_years(self):
        c = SanctionCeiling(max_imprisonment_months=3 * Y + 1, harsher_than_imprisonment=False)
        self.assertEqual(categorize(Guilt.INTENTIONAL, c), Category.MEDIUM)

    def test_negligent_beyond_part4_is_not_defined_by_article(self):
        with self.assertRaises(ValueError):
            categorize(Guilt.NEGLIGENT, ceiling(16))


class SanctionCeilingInvariantsTest(unittest.TestCase):
    def test_rejects_non_positive_term(self):
        with self.assertRaises(ValueError):
            SanctionCeiling(max_imprisonment_months=0, harsher_than_imprisonment=False)

    def test_harsher_requires_imprisonment_in_sanction(self):
        with self.assertRaises(ValueError):
            SanctionCeiling(max_imprisonment_months=None, harsher_than_imprisonment=True)


class CategoryChangePart6Test(unittest.TestCase):
    def _check(self, original, new, *, mitig=True, aggr=False, months=24):
        return check_category_change(
            original=original,
            claimed=new,
            has_mitigating=mitig,
            has_aggravating=aggr,
            imposed=ImposedPunishment(imprisonment_months=months),
        )

    def test_lawful_change_medium_to_small(self):
        r = self._check(Category.MEDIUM, Category.SMALL, months=36)
        self.assertEqual(r.status, CheckStatus.OK)
        self.assertEqual(r.norm, "ч. 6 ст. 15 УК РФ")

    def test_more_than_one_step_is_violation(self):
        r = self._check(Category.ESPECIALLY_GRAVE, Category.MEDIUM, months=60)
        self.assertEqual(r.status, CheckStatus.POSSIBLE_VIOLATION)

    def test_aggravating_circumstances_block_change(self):
        # Рецидив — отягчающее (п. «а» ч. 1 ст. 63) — категорию снижать нельзя.
        r = self._check(Category.GRAVE, Category.MEDIUM, aggr=True, months=48)
        self.assertEqual(r.status, CheckStatus.POSSIBLE_VIOLATION)
        self.assertIn("отягчающ", r.explanation)

    def test_no_mitigating_blocks_change(self):
        r = self._check(Category.MEDIUM, Category.SMALL, mitig=False, months=12)
        self.assertEqual(r.status, CheckStatus.POSSIBLE_VIOLATION)

    def test_imposed_term_limits_per_original_category(self):
        cases = [
            (Category.MEDIUM, Category.SMALL, 36, 37),
            (Category.GRAVE, Category.MEDIUM, 60, 61),
            (Category.ESPECIALLY_GRAVE, Category.GRAVE, 84, 85),
        ]
        for original, new, ok_months, bad_months in cases:
            with self.subTest(original=original):
                self.assertEqual(self._check(original, new, months=ok_months).status, CheckStatus.OK)
                self.assertEqual(
                    self._check(original, new, months=bad_months).status,
                    CheckStatus.POSSIBLE_VIOLATION,
                )

    def test_milder_punishment_than_imprisonment_is_within_limit(self):
        r = self._check(Category.GRAVE, Category.MEDIUM, months=None)
        self.assertEqual(r.status, CheckStatus.OK)

    def test_small_category_cannot_be_lowered(self):
        r = self._check(Category.SMALL, Category.SMALL)
        self.assertEqual(r.status, CheckStatus.POSSIBLE_VIOLATION)

    def test_raising_category_is_violation(self):
        r = self._check(Category.MEDIUM, Category.GRAVE)
        self.assertEqual(r.status, CheckStatus.POSSIBLE_VIOLATION)

    def test_every_result_flags_legal_review_and_cites_edition(self):
        r = self._check(Category.MEDIUM, Category.SMALL, months=12)
        self.assertTrue(r.needs_legal_review)
        self.assertIn("04.08.2026", r.source)


if __name__ == "__main__":
    unittest.main()
