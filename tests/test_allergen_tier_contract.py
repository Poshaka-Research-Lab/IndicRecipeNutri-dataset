import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from allergen_tier_contract import validate_row, parse_tiers, REINSTATED


class TierContractTests(unittest.TestCase):
    def test_stale_and_missing_tiers_rejected(self):
        for labels, tiers in [('none_detected', 'mustard:blend'), ('milk', ''),
                              ('unknown', 'milk:inherited')]:
            with self.subTest(labels=labels), self.assertRaises(ValueError):
                validate_row(labels, tiers)

    def test_valid_tiers_and_sentinels(self):
        for labels, tiers in [('unknown', None), ('none_detected', ''),
                              ('milk;ghee', 'ghee:direct;milk:derived')]:
            validate_row(labels, tiers)

    def test_invalid_or_duplicate_tier_rejected(self):
        for text in ['milk:direct;milk:inherited', 'milk:made_up', 'made_up:direct', 'milk']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_tiers(text)

    def test_reinstated_is_narrow_and_documented(self):
        self.assertEqual(set(REINSTATED), {(99336, 'gluten')})
        for (rid, cls), (gen, record) in REINSTATED.items():
            self.assertIsInstance(rid, int)
            self.assertIn(cls, parse_tiers(cls + ':inherited'))
            self.assertTrue(gen.startswith('before_') and record)


class ReinstatedExemptionTests(unittest.TestCase):
    """validate_release_tiers on a synthetic release: the (99336, gluten) re-addition is admitted only in its exact declared form."""

    def _run(self, current, d16e_prior, extra_history=()):
        import tempfile
        import pandas as pd
        import allergen_tier_contract as c
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'data/corpus').mkdir(parents=True)
            (root / 'data/provenance').mkdir(parents=True)
            ids = [99336] + list(range(1, 401))
            tiers = {99336: current}
            tiers.update({i: 'milk:derived' for i in range(1, 401)})
            labels = {i: ';'.join(sorted(parse_tiers(t))) or 'none_detected' for i, t in tiers.items()}
            wide = pd.DataFrame({'recipe_id': ids, 'Allergens_v2': [labels[i] for i in ids], 'allergen_tier': [tiers[i] for i in ids]})
            wide.to_parquet(root / 'data/corpus/recipes_structured.parquet')
            wide[['recipe_id', 'allergen_tier']].to_parquet(root / 'data/corpus/recipes.parquet')
            hist = [(99336, c.GENERATION, 'gluten:inherited;milk:derived;sulphites:inherited')]
            hist += [(i, c.GENERATION, 'milk:derived;sesame:direct') for i in range(1, 401)]
            if d16e_prior is not None:
                hist.append((99336, 'before_d16e_v1', d16e_prior))
            hist += list(extra_history)
            pd.DataFrame({'recipe_id': [h[0] for h in hist], 'field': 'allergen_tier', 'generation': [h[1] for h in hist],
                          'value_num': float('nan'), 'value_str': pd.array([h[2] for h in hist], dtype='string'),
                          'build_id': 'test'}).to_parquet(root / 'data/provenance/field_history.parquet')
            return c.validate_release_tiers(root)

    def test_declared_readdition_admitted(self):
        self.assertEqual(self._run('gluten:inherited;milk:derived;sulphites:inherited', 'milk:derived;sulphites:inherited'), [])

    def test_variants_rejected(self):
        for current, prior, extra in [
            ('gluten:direct;milk:derived;sulphites:inherited', 'milk:derived;sulphites:inherited', ()),        # literal changed
            ('gluten:inherited;milk:derived;sulphites:inherited', None, ()),                                   # prior record missing
            ('gluten:inherited;milk:derived;sulphites:inherited', 'milk:derived', ()),                         # prior value altered
            ('gluten:inherited;milk:derived;peanut:direct;sulphites:inherited', 'milk:derived;sulphites:inherited', ()),  # extra class
            ('gluten:inherited;milk:derived;sulphites:inherited', 'milk:derived;sulphites:inherited',
             [(99336, 'before_d16e_v1', 'milk:derived;sulphites:inherited')]),                                  # duplicated prior record
        ]:
            with self.subTest(current=current, prior=prior, extra=bool(extra)):
                self.assertNotEqual(self._run(current, prior, extra), [])
