import sys
import json
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from source_recovery_contract import validate_recovered_row


class SourceRecoveryContractTests(unittest.TestCase):
    def test_known_missing_ingredient_case_is_rejected(self):
        row = {'IngredientsList': json.dumps(['ingredient'] * 8), 'Allergens_v2': 'milk;sulphites', 'allergen_tier': 'milk:derived;sulphites:derived'}
        self.assertEqual(len(validate_recovered_row(row)), 3)

    def test_label_without_source_ingredients_is_rejected(self):
        row = {'IngredientsList': json.dumps(['ingredient'] * 8), 'Allergens_v2': 'milk;sulphites;tree_nuts', 'allergen_tier': 'milk:derived;sulphites:derived;tree_nuts:direct'}
        self.assertIn('reviewed source ingredients are missing', validate_recovered_row(row))


if __name__ == '__main__':
    unittest.main()
