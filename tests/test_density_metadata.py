import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import json
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import stamp_units
from nutrition_contract import DENSITY_BASIS_CONTRACT, DENSITY_UNAVAILABLE, FRACTION_BASIS_CONTRACT, WEIGHT_CONFIDENCE_CONTRACT


class DensityMetadataTests(unittest.TestCase):
    def test_basis_document_uses_checkout_stable_line_endings(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'docs').mkdir()
            with patch.object(stamp_units,'REPO_ROOT',root):stamp_units.write_nutrition_basis()
            raw=(root/'docs/NUTRITION_BASIS.json').read_bytes()
            self.assertNotIn(b'\r',raw)
            self.assertTrue(raw.endswith(b'\n'))
            self.assertEqual(json.loads(raw),{'density':DENSITY_BASIS_CONTRACT,'supplemental_fraction':FRACTION_BASIS_CONTRACT,'weight_confidence':WEIGHT_CONFIDENCE_CONTRACT})

    def test_stamping_preserves_values_and_adds_basis_semantics(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            target=root/'fixture.parquet'
            source=pa.table({'recipe_id':[1,2], 'per100g_basis':[DENSITY_UNAVAILABLE,'ingredient_density'],
                             'per100g_kcal':[None,100.], 'ing_weight_confident_frac':[None,.5],
                             'nut_suppl_fct_basis':['unavailable_no_energy','partial_computed_ingredient_energy']})
            pq.write_table(source,target)
            with patch.object(stamp_units,'REPO_ROOT',root):stamp_units.stamp(target)
            actual=pq.read_table(target)
            self.assertTrue(source.equals(actual,check_metadata=False))
            metadata=actual.schema.field('per100g_basis').metadata
            self.assertEqual(json.loads(metadata[b'value_semantics']),DENSITY_BASIS_CONTRACT)
            self.assertEqual(json.loads(actual.schema.field('nut_suppl_fct_basis').metadata[b'value_semantics']),FRACTION_BASIS_CONTRACT)
            self.assertEqual(actual.schema.field('per100g_kcal').metadata[b'unit'],b'kcal')
            self.assertEqual(json.loads(actual.schema.field('ing_weight_confident_frac').metadata[b'value_semantics']),WEIGHT_CONFIDENCE_CONTRACT)


if __name__=='__main__':unittest.main()
