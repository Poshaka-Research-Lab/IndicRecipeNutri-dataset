import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from allergen_evidence import parse_ingredients, evidence_for_class, decide_status, decide_constraint


class AllergenEvidenceTests(unittest.TestCase):
    def test_ambiguous_oil_fails_closed(self):
        kind, _ = evidence_for_class('peanut', ('2 tbsp oil',), True)
        self.assertEqual(kind, 'ambiguous_carrier')
        self.assertEqual(decide_status('absent', kind, False, True)[0], 'unknown')

    def test_named_oil_does_not_infer_an_allergen(self):
        kind, _ = evidence_for_class('peanut', ('olive oil',), True)
        self.assertEqual(kind, 'text_silent')
        self.assertEqual(decide_status('absent', kind, False, True)[0], 'absent')
        self.assertEqual(decide_constraint('absent'), 'PASS_SILVER_ONLY')

    def test_mixed_alternative_is_not_masked_by_named_oil(self):
        kind, _ = evidence_for_class('peanut', ('olive oil or vegetable oil',), True)
        self.assertEqual(kind, 'ambiguous_carrier')

    def test_conflict_is_review_not_automatic_correction(self):
        kind, _ = evidence_for_class('milk', ('paneer',), True)
        self.assertEqual(kind, 'implicit_name')
        self.assertEqual(decide_status('absent', kind, False, True)[0], 'unknown')

    def test_explicit_precedes_implicit_and_ambiguity(self):
        kind, _ = evidence_for_class('peanut', ('peanuts', 'moongphali', 'oil'), True)
        self.assertEqual(kind, 'explicit')

    def test_coconut_milk_does_not_become_dairy(self):
        self.assertEqual(evidence_for_class('milk', ('coconut milk',), True)[0], 'text_silent')

    def test_negated_name_is_not_asserted_present(self):
        kind, _ = evidence_for_class('peanut', ('peanut-free oil',), True)
        self.assertEqual(kind, 'ambiguous_carrier')
        self.assertEqual(decide_status('absent', kind, False, True)[0], 'unknown')

    def test_legacy_positive_and_incomplete_are_handled_asymmetrically(self):
        self.assertEqual(decide_status('present', 'unassessed', True, False)[0], 'present')
        self.assertEqual(decide_status('absent', 'text_silent', True, True)[0], 'unknown')
        self.assertEqual(decide_status('unassessed', 'explicit', False, True)[0], 'unknown')

    def test_unreadable_or_empty_arrays_are_unassessed(self):
        for raw in [None, 'invalid', '{}', '[]', '[3]', '[""]']:
            self.assertFalse(parse_ingredients(raw)[1])
        self.assertEqual(decide_status('absent', 'unassessed', False, False)[0], 'unknown')

    def test_unknown_class_or_status_rejected(self):
        with self.assertRaises(ValueError):
            evidence_for_class('fictional', ('oil',), True)
        with self.assertRaises(ValueError):
            decide_constraint('safe')


if __name__ == '__main__':
    unittest.main()
