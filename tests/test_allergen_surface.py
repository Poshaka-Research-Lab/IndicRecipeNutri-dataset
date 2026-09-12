import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import allergen_surface as surface


class AllergenSurfaceTests(unittest.TestCase):
    def frame(self):
        return pd.DataFrame([(rid, token, status) for rid, status in
                             [(1, 'absent'), (2, 'unassessed')]
                             for token in surface._AT.TOKENS],
                            columns=['recipe_id', 'allergen', 'status'])

    def load(self, frame):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / surface.LONG_PATH
            path.parent.mkdir(parents=True)
            frame.to_parquet(path, index=False)
            return surface.load_wide(root).set_index('recipe_id')

    def test_absent_and_unassessed_remain_distinct(self):
        wide = self.load(self.frame())
        self.assertFalse(wide.loc[1, 'allergen_unassessed'])
        self.assertTrue(wide.loc[2, 'allergen_unassessed'])
        self.assertEqual(wide.n_allergens.tolist(), [0, 0])

    def test_partial_uncertainty_preserves_positive_evidence(self):
        frame = self.frame()
        frame.loc[(frame.recipe_id == 2) & (frame.allergen == 'milk'), 'status'] = 'present'
        wide = self.load(frame)
        self.assertTrue(wide.loc[2, 'has_milk'])
        self.assertTrue(wide.loc[2, 'allergen_unassessed'])

    def test_missing_class_is_not_absence(self):
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            self.load(self.frame().iloc[1:])

    def test_invalid_status_is_not_absence(self):
        for status in ['unknown', 'not-assessed', '', None]:
            with self.subTest(status=status):
                frame = self.frame()
                frame.loc[0, 'status'] = status
                with self.assertRaises(ValueError):
                    self.load(frame)

    def test_duplicate_assessment_rejected_even_when_identical(self):
        frame = self.frame()
        for status in ['absent', 'present']:
            duplicate = frame.iloc[:1].copy()
            duplicate['status'] = status
            with self.subTest(status=status), self.assertRaisesRegex(ValueError, 'duplicate'):
                self.load(pd.concat([frame, duplicate], ignore_index=True))

    def test_unknown_class_cannot_replace_required_class(self):
        frame = self.frame()
        frame.loc[0, 'allergen'] = 'unrecognized'
        with self.assertRaisesRegex(ValueError, 'undeclared'):
            self.load(frame)

    def test_null_identifier_rejected(self):
        frame = self.frame()
        frame.loc[0, 'recipe_id'] = None
        with self.assertRaisesRegex(ValueError, 'null'):
            self.load(frame)

    def test_missing_schema_rejected(self):
        with self.assertRaisesRegex(ValueError, 'missing columns'):
            self.load(self.frame().drop(columns='status'))


if __name__ == '__main__':
    unittest.main()
