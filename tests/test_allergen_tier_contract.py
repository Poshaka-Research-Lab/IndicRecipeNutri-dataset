import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from allergen_tier_contract import validate_row, parse_tiers, REINSTATED, DECLARED_ADDITIONS


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
        self.assertEqual(set(REINSTATED), {(99336, 'gluten'), (99213, 'gluten')})
        for (rid, cls), (gen, record) in REINSTATED.items():
            self.assertIsInstance(rid, int)
            self.assertIn(cls, parse_tiers(cls + ':inherited'))
            self.assertTrue(gen.startswith('before_') and record)

    def test_declared_additions_is_narrow_and_documented(self):
        self.assertEqual(set(DECLARED_ADDITIONS), {(15690, 'gluten')})
        self.assertFalse(set(rid for rid, _ in DECLARED_ADDITIONS) & set(rid for rid, _ in REINSTATED))
        for (rid, cls), (gen, literal, record) in DECLARED_ADDITIONS.items():
            self.assertIsInstance(rid, int)
            self.assertEqual(parse_tiers(cls + ':' + literal), {cls: literal})
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
            # the batch I-1 rows 15690 / 99213 are present in their declared forms (D16IExemptionTests varies them); 398 fillers keep 401
            i1 = D16IExemptionTests
            ids = [99336, 15690, 99213] + list(range(1, 399))
            tiers = {99336: current, 15690: i1.CURRENT[15690], 99213: i1.CURRENT[99213]}
            tiers.update({i: 'milk:derived' for i in range(1, 399)})
            labels = {i: ';'.join(sorted(parse_tiers(t))) or 'none_detected' for i, t in tiers.items()}
            wide = pd.DataFrame({'recipe_id': ids, 'Allergens_v2': [labels[i] for i in ids], 'allergen_tier': [tiers[i] for i in ids]})
            wide.to_parquet(root / 'data/corpus/recipes_structured.parquet')
            wide[['recipe_id', 'allergen_tier']].to_parquet(root / 'data/corpus/recipes.parquet')
            hist = [(99336, c.GENERATION, 'gluten:inherited;milk:derived;sulphites:inherited')]
            hist += [(i, c.GENERATION, 'milk:derived;sesame:direct') for i in range(1, 399)]
            hist += [(i, c.GENERATION, i1.RECON[i]) for i in (15690, 99213)] + [x for x in i1.PRIOR if x[0] in (15690, 99213)]
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


class D16IExemptionTests(unittest.TestCase):
    """validate_release_tiers on a synthetic release carrying the batch I-1 rows: (99213, gluten) as a REINSTATED re-addition and (15690, gluten)
    as the one DECLARED_ADDITIONS first addition (owner round 2 point 1; BATCH_I review C3). Each is admitted only in its exact declared form,
    and the addition branch admits nothing on any other row."""
    RECON = {15690: 'mustard:blend;soy:inherited;sulphites:derived', 99213: 'gluten:inherited;soy:inherited;sulphites:derived',
             99336: 'gluten:inherited;milk:derived;sulphites:inherited'}
    CURRENT = {15690: 'gluten:inherited;soy:inherited;sulphites:derived', 99213: 'gluten:inherited;soy:inherited;sulphites:derived',
               99336: 'gluten:inherited;milk:derived;sulphites:inherited'}
    PRIOR = [(15690, 'before_d16i_v1', 'soy:inherited;sulphites:derived'), (99213, 'before_d16i_v1', 'soy:inherited;sulphites:derived'),
             (99336, 'before_d16e_v1', 'milk:derived;sulphites:inherited')]

    def _run(self, current=None, recon=None, prior=None, filler_current=None):
        import tempfile
        import pandas as pd
        import allergen_tier_contract as c
        cur = {**self.CURRENT, **(current or {})}
        rec = {**self.RECON, **(recon or {})}
        hist_prior = self.PRIOR if prior is None else prior
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'data/corpus').mkdir(parents=True)
            (root / 'data/provenance').mkdir(parents=True)
            filler = list(range(1, 399))
            ids = sorted(cur) + filler
            tiers = dict(cur)
            tiers.update({i: 'milk:derived' for i in filler})
            tiers.update(filler_current or {})
            labels = {i: ';'.join(sorted(parse_tiers(t))) or 'none_detected' for i, t in tiers.items()}
            wide = pd.DataFrame({'recipe_id': ids, 'Allergens_v2': [labels[i] for i in ids], 'allergen_tier': [tiers[i] for i in ids]})
            wide.to_parquet(root / 'data/corpus/recipes_structured.parquet')
            wide[['recipe_id', 'allergen_tier']].to_parquet(root / 'data/corpus/recipes.parquet')
            hist = [(i, c.GENERATION, rec[i]) for i in sorted(rec)] + [(i, c.GENERATION, 'milk:derived;sesame:direct') for i in filler]
            hist += list(hist_prior)
            pd.DataFrame({'recipe_id': [h[0] for h in hist], 'field': 'allergen_tier', 'generation': [h[1] for h in hist],
                          'value_num': float('nan'), 'value_str': pd.array([h[2] for h in hist], dtype='string'),
                          'build_id': 'test'}).to_parquet(root / 'data/provenance/field_history.parquet')
            return c.validate_release_tiers(root)

    def test_declared_forms_admitted(self):
        self.assertEqual(self._run(), [])

    def test_15690_variants_rejected(self):
        p = [x for x in self.PRIOR if x[0] != 15690]
        for name, kw in [
            ('literal changed', {'current': {15690: 'gluten:derived;soy:inherited;sulphites:derived'}}),
            ('prior record missing', {'prior': p}),
            ('prior value altered', {'prior': p + [(15690, 'before_d16i_v1', 'soy:inherited')]}),
            ('prior under another generation', {'prior': p + [(15690, 'before_d16h_v1', 'soy:inherited;sulphites:derived')]}),
            ('duplicated prior record', {'prior': self.PRIOR + [(15690, 'before_d16i_v1', 'soy:inherited;sulphites:derived')]}),
            ('extra class', {'current': {15690: 'gluten:inherited;peanut:direct;soy:inherited;sulphites:derived'},
                             'prior': p + [(15690, 'before_d16i_v1', 'peanut:direct;soy:inherited;sulphites:derived')]}),
            ('class was in the reconciliation prior', {'recon': {15690: 'gluten:inherited;mustard:blend;soy:inherited;sulphites:derived'}}),
            ('remaining classes not a strict removal', {'recon': {15690: 'soy:inherited;sulphites:derived'}}),
            ('combined with a later-generation record',
             {'prior': self.PRIOR + [(15690, 'before_diet_repair_v1', 'gluten:inherited;soy:inherited;sulphites:derived')]}),
        ]:
            with self.subTest(name):
                self.assertNotEqual(self._run(**kw), [])

    def test_99213_variants_rejected(self):
        p = [x for x in self.PRIOR if x[0] != 99213]
        for name, kw in [
            ('literal changed', {'current': {99213: 'gluten:derived;soy:inherited;sulphites:derived'}}),
            ('prior record missing', {'prior': p}),
            ('prior value altered', {'prior': p + [(99213, 'before_d16i_v1', 'sulphites:derived')]}),
        ]:
            with self.subTest(name):
                self.assertNotEqual(self._run(**kw), [])

    def test_addition_on_an_undeclared_row_rejected(self):
        # the shape of 15690 (class absent from the reconciliation prior, prior recorded under before_d16i_v1) on a row with no entry
        self.assertNotEqual(self._run(filler_current={7: 'gluten:inherited;milk:derived'}), [])
        self.assertNotEqual(self._run(filler_current={7: 'gluten:inherited;milk:derived'},
                                      prior=self.PRIOR + [(7, 'before_d16i_v1', 'milk:derived')]), [])
