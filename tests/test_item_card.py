from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from item_card import rating_bin, render_local_card


class ItemCardTests(unittest.TestCase):
    def test_missing_zero_and_positive_are_distinct(self):
        self.assertEqual(rating_bin(None), 'unknown')
        self.assertEqual(rating_bin(float('nan')), 'unknown')
        self.assertEqual(rating_bin(-1), 'unknown')
        self.assertEqual(rating_bin(0), 'zero')
        self.assertEqual(rating_bin(9), '1_9')
        self.assertEqual(rating_bin(10), '10_99')
        self.assertEqual(rating_bin(100), '100_plus')

    def test_render_uses_allowlisted_fields_and_provenance(self):
        recipe = dict(recipe_id=1, Title_normalized='Invented example', IngredientsList='["water"]')
        attrs = dict(recipe_id=1, Region='Goa', SpiceLevel='hot', SpiceLevel_src='ingredient-rule',
                     HealthGrade='B', rating_count_bin='unknown', hidden_quality='DO_NOT_EXPORT',
                     oracle_rank='DO_NOT_EXPORT', exposure='DO_NOT_EXPORT')
        result = render_local_card(recipe, attrs)
        self.assertIn('ingredient-rule', result)
        self.assertIn('unknown', result)
        self.assertNotIn('DO_NOT_EXPORT', result)
        self.assertNotIn('recipe_id', result)
        attrs['recipe_id'] = 2
        with self.assertRaises(ValueError):
            render_local_card(recipe, attrs)


if __name__ == '__main__':
    unittest.main()
