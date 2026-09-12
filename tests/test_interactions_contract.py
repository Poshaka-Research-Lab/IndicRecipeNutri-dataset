from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from interactions_contract import COMPATIBLE, DECLARED, id_map, read_split


class InteractionsContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'map.txt'

    def tearDown(self):
        self.tmp.cleanup()

    def test_map_uses_final_field_and_preserves_recipe_namespace(self):
        self.path.write_text('org_id remap_id\nitem:780 0\nregion:West Bengal 1\n', encoding='utf-8')
        self.assertEqual(id_map(self.path), {0: 'item:780', 1: 'region:West Bengal'})

    def test_duplicate_original_or_remapped_ids_rejected(self):
        for body in ['item:7 0\nitem:8 0', 'item:7 0\nitem:7 1']:
            self.path.write_text('org_id remap_id\n'+body, encoding='utf-8')
            with self.assertRaises(ValueError):
                id_map(self.path)

    def test_split_ids_are_remapped_not_recipe_ids(self):
        self.path.write_text('0 1\n', encoding='utf-8')
        self.assertEqual(read_split(self.path, {0: '900'}, {1: '780'}), ({(0, 1)}, 1))
        self.path.write_text('0 780\n', encoding='utf-8')
        with self.assertRaises(ValueError):
            read_split(self.path, {0: '900'}, {1: '780'})

    def test_duplicate_interactions_are_reported_as_rows_not_unique_pairs(self):
        self.path.write_text('0 1 1\n', encoding='utf-8')
        self.assertEqual(read_split(self.path, {0: '900'}, {1: '780'}), ({(0, 1)}, 2))

    # ---- the diet table is a hard constraint, so its shape is asserted, not assumed.
    # gen.py's norm_diet() returned 'Vegetarian' for anything it did not recognise, which put
    # 731 `unknown`-diet recipes into the Vegan pool while the audit reported zero violations
    # because it re-used the same function. These two tests fail if that shape comes back.

    def test_vegan_users_may_be_served_only_vegan(self):
        self.assertEqual(COMPATIBLE['Vegan'], {'Vegan'})

    def test_no_undeclared_diet_is_servable_to_a_restricted_user(self):
        for user_diet, allowed in COMPATIBLE.items():
            self.assertTrue(allowed <= set(DECLARED),
                            f'{user_diet} may be served a diet outside {DECLARED}')
        self.assertNotIn('unknown', set().union(*COMPATIBLE.values()))


if __name__ == '__main__':
    unittest.main()
