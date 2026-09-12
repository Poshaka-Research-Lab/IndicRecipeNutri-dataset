from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from synthetic_history_contract import id_map, read_split


class HistoricalSyntheticTests(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()
