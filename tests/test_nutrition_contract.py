import sys
import unittest
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from nutrition_contract import CANONICAL, LEGACY, normalize_fraction_name, validate_fraction_frames


class NutritionContractTests(unittest.TestCase):
    def test_rename_preserves_missing_and_values(self):
        frame = pd.DataFrame({'recipe_id': [1, 2], LEGACY: [.25, None]})
        wide = normalize_fraction_name(frame)
        quality = normalize_fraction_name(frame, retain_legacy=True)
        self.assertNotIn(LEGACY, wide)
        self.assertTrue(quality[LEGACY].equals(quality[CANONICAL]))
        self.assertTrue(pd.isna(wide[CANONICAL].iloc[1]))
        self.assertEqual(validate_fraction_frames(wide, quality.iloc[::-1]), [])

    def test_conflict_does_not_overwrite(self):
        with self.assertRaises(ValueError):
            normalize_fraction_name(pd.DataFrame({LEGACY: [.2], CANONICAL: [.3]}))

    def test_domain(self):
        for value in [-.1, 1.1, float('inf')]:
            with self.assertRaises(ValueError):
                normalize_fraction_name(pd.DataFrame({LEGACY: [value]}))

    def test_id_alignment_is_required(self):
        wide = pd.DataFrame({'recipe_id': [1, 2], CANONICAL: [.2, .3]})
        quality = normalize_fraction_name(wide, retain_legacy=True)
        quality[CANONICAL] = [.3, .2]
        quality[LEGACY] = [.3, .2]
        self.assertTrue(validate_fraction_frames(wide, quality))
        self.assertTrue(validate_fraction_frames(wide, quality.iloc[:1]))


if __name__ == '__main__':
    unittest.main()
