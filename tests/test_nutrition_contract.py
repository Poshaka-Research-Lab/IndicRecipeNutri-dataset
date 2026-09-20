import sys
import unittest
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from nutrition_contract import CANONICAL, LEGACY, normalize_fraction_name, validate_fraction_frames
from nutrition_contract import DENSITY_UNAVAILABLE, validate_density_frame


class NutritionContractTests(unittest.TestCase):
    def density_fixture(self):
        fields = ['per100g_kcal', 'per100g_protein', 'per100g_fat', 'per100g_carb',
                  'per100g_fiber', 'per100g_sugar', 'per100g_sodium', 'per100g_salt',
                  'per100g_satfat', 'fsa_fat', 'fsa_saturates', 'fsa_sugars', 'fsa_salt']
        frame = pd.DataFrame({c:[None] for c in fields})
        frame['per100g_basis'] = DENSITY_UNAVAILABLE
        frame['per100g_available_v3'] = False
        frame['per100g_confident'] = False
        return frame

    def test_density_unavailable_has_no_values_or_labels(self):
        frame = self.density_fixture()
        self.assertEqual(validate_density_frame(frame), [])
        for field,value in [('per100g_kcal', 0), ('per100g_sugar', 0), ('fsa_sugars','green')]:
            bad = frame.copy()
            bad.loc[0,field] = value
            self.assertTrue(validate_density_frame(bad))

    def test_density_unavailable_flags_explicit_false(self):
        for flag in ['per100g_available_v3','per100g_confident']:
            for value in [True,None]:
                frame = self.density_fixture()
                frame[flag] = value
                self.assertTrue(validate_density_frame(frame))

    def test_density_contract_requires_fields(self):
        frame = self.density_fixture().drop(columns='per100g_sugar')
        self.assertTrue(validate_density_frame(frame))

    def test_stale_density_summaries_and_portion_override_rejected(self):
        for field,value in [('fsa_n_red',0),('fsa_n_green',4),('fsa_n_labelled',4),
                            ('fsa_portion_g',150),('fsa_portion_override_applied',True)]:
            frame=self.density_fixture()
            frame[field]=value
            self.assertTrue(validate_density_frame(frame),field)

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

    def test_fraction_basis_distinguishes_missing_from_zero(self):
        frame=pd.DataFrame({CANONICAL:[0.], 'nut_suppl_fct_basis':['unavailable_no_energy']})
        with self.assertRaises(ValueError):normalize_fraction_name(frame)
        frame['nut_suppl_fct_basis']='complete_computed_ingredient_energy'
        self.assertEqual(normalize_fraction_name(frame)[CANONICAL].iloc[0],0.)

    def test_fraction_basis_agrees_across_surfaces(self):
        wide=pd.DataFrame({'recipe_id':[1],CANONICAL:[.5], 'nut_suppl_fct_basis':['partial_computed_ingredient_energy']})
        quality=normalize_fraction_name(wide,retain_legacy=True)
        self.assertEqual(validate_fraction_frames(wide,quality),[])
        quality['nut_suppl_fct_basis']='complete_computed_ingredient_energy'
        self.assertTrue(validate_fraction_frames(wide,quality))

    def test_id_alignment_is_required(self):
        wide = pd.DataFrame({'recipe_id': [1, 2], CANONICAL: [.2, .3]})
        quality = normalize_fraction_name(wide, retain_legacy=True)
        quality[CANONICAL] = [.3, .2]
        quality[LEGACY] = [.3, .2]
        self.assertTrue(validate_fraction_frames(wide, quality))
        self.assertTrue(validate_fraction_frames(wide, quality.iloc[:1]))


if __name__ == '__main__':
    unittest.main()
