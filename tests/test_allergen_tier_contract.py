import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from allergen_tier_contract import validate_row, parse_tiers, REINSTATED, DECLARED_ADDITIONS, COMBINED_READDITIONS

# batch I-5 (D16M, I5-R10-1): the 30 rows of the 401 reconciliation set the batch moved, as (reconciliation prior, current tiers,
# before_d16m_v1 prior). 29 carry DECLARED_ADDITIONS entries; 184699 carries the one COMBINED_READDITIONS entry. Values read from the
# rebuilt release and the pre-install master (contract_draft_d16m/make_contract_draft_d16m.py).
D16M = {
    28021: ('asafoetida:direct;gluten:blend;milk:inherited;mustard:blend;soy:direct', 'asafoetida:direct;ghee:inherited;gluten:blend;milk:inherited;soy:direct', 'asafoetida:direct;gluten:blend;milk:inherited;soy:direct'),
    30758: ('milk:inherited;mustard:blend', 'asafoetida:inherited;ghee:inherited;milk:inherited', 'milk:inherited'),
    40775: ('fenugreek:direct;gluten:inherited;mustard:blend', 'asafoetida:inherited;fenugreek:direct;gluten:inherited', 'fenugreek:direct;gluten:inherited'),
    45836: ('gluten:direct;milk:derived;mustard:blend', 'ghee:inherited;gluten:direct;milk:derived', 'gluten:direct;milk:derived'),
    47525: ('fenugreek:direct;ghee:direct;gluten:derived;milk:derived;mustard:blend', 'fenugreek:direct;ghee:direct;gluten:derived;milk:derived;sulphites:inherited', 'fenugreek:direct;ghee:direct;gluten:derived;milk:derived'),
    52510: ('gluten:direct;milk:derived;mustard:blend;tamarind:direct', 'asafoetida:inherited;gluten:direct;milk:derived;tamarind:direct', 'gluten:direct;milk:derived;tamarind:direct'),
    54385: ('ghee:direct;milk:derived;mustard:blend', 'asafoetida:inherited;ghee:direct;milk:derived', 'ghee:direct;milk:derived'),
    81354: ('asafoetida:direct;gluten:direct;mustard:blend', 'asafoetida:direct;gluten:direct;sulphites:inherited', 'asafoetida:direct;gluten:direct'),
    85282: ('mustard:blend;tamarind:direct', 'ghee:inherited;milk:inherited;tamarind:direct', 'tamarind:direct'),
    117104: ('milk:derived;mustard:blend;tree_nuts:direct', 'ghee:inherited;milk:derived;tree_nuts:direct', 'milk:derived;tree_nuts:direct'),
    119584: ('mustard:blend', 'sulphites:inherited', ''),
    126908: ('asafoetida:direct;fenugreek:direct;ghee:direct;milk:derived;mustard:blend', 'asafoetida:direct;fenugreek:direct;ghee:direct;milk:derived;sulphites:inherited', 'asafoetida:direct;fenugreek:direct;ghee:direct;milk:derived'),
    126913: ('asafoetida:direct;milk:inherited;mustard:blend', 'asafoetida:direct;ghee:inherited;milk:inherited', 'asafoetida:direct;milk:inherited'),
    127710: ('ghee:direct;gluten:direct;milk:derived;mustard:blend;sulphites:derived', 'asafoetida:inherited;ghee:direct;gluten:direct;milk:derived;sulphites:derived', 'ghee:direct;gluten:direct;milk:derived;sulphites:derived'),
    127968: ('gluten:inherited;mustard:blend;sulphites:derived', 'asafoetida:inherited;gluten:inherited;sulphites:derived', 'gluten:inherited;sulphites:derived'),
    129964: ('asafoetida:direct;fenugreek:direct;milk:derived;mustard:blend;peanut:direct', 'asafoetida:direct;fenugreek:direct;gluten:derived;milk:derived;peanut:direct', 'asafoetida:direct;fenugreek:direct;milk:derived;peanut:direct'),
    130331: ('ghee:direct;milk:derived;mustard:blend', 'ghee:direct;gluten:derived;milk:derived', 'ghee:direct;milk:derived'),
    139708: ('coconut:direct;ghee:direct;milk:derived;mustard:blend;tree_nuts:direct', 'coconut:direct;ghee:direct;milk:derived;sulphites:inherited;tree_nuts:direct', 'coconut:direct;ghee:direct;milk:derived;tree_nuts:direct'),
    144079: ('mustard:blend;tamarind:direct', 'ghee:inherited;milk:inherited;tamarind:direct', 'tamarind:direct'),
    155636: ('milk:derived;mustard:blend', 'ghee:inherited;milk:derived', 'milk:derived'),
    175159: ('asafoetida:direct;gluten:blend;milk:derived;mustard:blend;sulphites:derived', 'asafoetida:direct;ghee:inherited;gluten:blend;milk:derived;sulphites:derived', 'asafoetida:direct;gluten:blend;milk:derived;sulphites:derived'),
    184581: ('asafoetida:direct;mustard:blend', 'asafoetida:direct;sulphites:inherited', 'asafoetida:direct'),
    184699: ('coconut:direct;milk:inherited;sulphites:derived', 'coconut:direct;ghee:inherited;milk:inherited;sulphites:derived;tree_nuts:inherited', 'coconut:direct;sulphites:derived'),
    184793: ('asafoetida:direct;gluten:direct;mustard:blend', 'asafoetida:direct;ghee:inherited;gluten:direct;milk:inherited', 'asafoetida:direct;gluten:direct'),
    185104: ('gluten:direct;milk:derived;mustard:blend', 'asafoetida:inherited;gluten:direct;milk:derived', 'gluten:direct;milk:derived'),
    202905: ('coconut:direct;mustard:blend', 'coconut:direct;ghee:inherited;milk:inherited', 'coconut:direct'),
    203067: ('milk:inherited;mustard:blend', 'gluten:derived;milk:inherited', 'milk:inherited'),
    209602: ('ghee:direct;milk:derived;mustard:blend', 'asafoetida:inherited;ghee:direct;milk:derived', 'ghee:direct;milk:derived'),
    210667: ('milk:derived;mustard:blend', 'asafoetida:inherited;milk:derived', 'milk:derived'),
    210679: ('coconut:direct;mustard:blend;sulphites:derived;tree_nuts:inherited', 'coconut:direct;ghee:inherited;milk:inherited;sulphites:derived;tree_nuts:inherited', 'coconut:direct;sulphites:derived;tree_nuts:inherited'),
}
D16M_ADDITIONS = {
    (28021, 'ghee'): 'inherited',
    (30758, 'asafoetida'): 'inherited',
    (30758, 'ghee'): 'inherited',
    (40775, 'asafoetida'): 'inherited',
    (45836, 'ghee'): 'inherited',
    (47525, 'sulphites'): 'inherited',
    (52510, 'asafoetida'): 'inherited',
    (54385, 'asafoetida'): 'inherited',
    (81354, 'sulphites'): 'inherited',
    (85282, 'ghee'): 'inherited',
    (85282, 'milk'): 'inherited',
    (117104, 'ghee'): 'inherited',
    (119584, 'sulphites'): 'inherited',
    (126908, 'sulphites'): 'inherited',
    (126913, 'ghee'): 'inherited',
    (127710, 'asafoetida'): 'inherited',
    (127968, 'asafoetida'): 'inherited',
    (129964, 'gluten'): 'derived',
    (130331, 'gluten'): 'derived',
    (139708, 'sulphites'): 'inherited',
    (144079, 'ghee'): 'inherited',
    (144079, 'milk'): 'inherited',
    (155636, 'ghee'): 'inherited',
    (175159, 'ghee'): 'inherited',
    (184581, 'sulphites'): 'inherited',
    (184793, 'ghee'): 'inherited',
    (184793, 'milk'): 'inherited',
    (185104, 'asafoetida'): 'inherited',
    (202905, 'ghee'): 'inherited',
    (202905, 'milk'): 'inherited',
    (203067, 'gluten'): 'derived',
    (209602, 'asafoetida'): 'inherited',
    (210667, 'asafoetida'): 'inherited',
    (210679, 'ghee'): 'inherited',
    (210679, 'milk'): 'inherited',
}


def d16m_rows(gen):
    """(ids, current tiers, history rows) for the 30 D16M rows in their declared forms."""
    hist = [(r, gen, v[0]) for r, v in D16M.items()] + [(r, 'before_d16m_v1', v[2]) for r, v in D16M.items()]
    return sorted(D16M), {r: v[1] for r, v in D16M.items()}, hist


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
        self.assertEqual(set(DECLARED_ADDITIONS), {(15690, 'gluten')} | set(D16M_ADDITIONS))
        self.assertEqual({k: DECLARED_ADDITIONS[k][1] for k in D16M_ADDITIONS}, D16M_ADDITIONS)
        self.assertTrue(all(DECLARED_ADDITIONS[k][0] == 'before_d16m_v1' for k in D16M_ADDITIONS))
        self.assertFalse(set(rid for rid, _ in DECLARED_ADDITIONS) & set(rid for rid, _ in REINSTATED))
        for (rid, cls), (gen, literal, record) in DECLARED_ADDITIONS.items():
            self.assertIsInstance(rid, int)
            self.assertEqual(parse_tiers(cls + ':' + literal), {cls: literal})
            self.assertTrue(gen.startswith('before_') and record)

    def test_combined_readditions_is_one_pinned_row(self):
        self.assertEqual(COMBINED_READDITIONS, {184699: ('before_d16m_v1', {'milk': 'inherited'}, {'ghee': 'inherited', 'tree_nuts': 'inherited'},
                                                         'coconut:direct;sulphites:derived', COMBINED_READDITIONS[184699][4])})
        self.assertTrue(COMBINED_READDITIONS[184699][4])
        self.assertFalse(set(COMBINED_READDITIONS) & ({r for r, _ in DECLARED_ADDITIONS} | {r for r, _ in REINSTATED}))


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
            # the batch I-1 rows 15690 / 99213 and the 30 D16M rows are present in their declared forms; 368 fillers keep 401
            i1 = D16IExemptionTests
            m_ids, m_cur, m_hist = d16m_rows(c.GENERATION)
            ids = [99336, 15690, 99213] + m_ids + list(range(1, 369))
            tiers = {99336: current, 15690: i1.CURRENT[15690], 99213: i1.CURRENT[99213], **m_cur}
            tiers.update({i: 'milk:derived' for i in range(1, 369)})
            labels = {i: ';'.join(sorted(parse_tiers(t))) or 'none_detected' for i, t in tiers.items()}
            wide = pd.DataFrame({'recipe_id': ids, 'Allergens_v2': [labels[i] for i in ids], 'allergen_tier': [tiers[i] for i in ids]})
            wide.to_parquet(root / 'data/corpus/recipes_structured.parquet')
            wide[['recipe_id', 'allergen_tier']].to_parquet(root / 'data/corpus/recipes.parquet')
            hist = [(99336, c.GENERATION, 'gluten:inherited;milk:derived;sulphites:inherited')]
            hist += [(i, c.GENERATION, 'milk:derived;sesame:direct') for i in range(1, 369)] + m_hist
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

    def _run(self, current=None, recon=None, prior=None, filler_current=None, d16m_hist=None, n_filler=368, recon_extra=()):
        import tempfile
        import pandas as pd
        import allergen_tier_contract as c
        m_ids, m_cur, m_hist = d16m_rows(c.GENERATION)
        cur = {**self.CURRENT, **m_cur, **(current or {})}
        rec = {**self.RECON, **{r: v[0] for r, v in D16M.items()}, **(recon or {})}
        hist_prior = self.PRIOR if prior is None else prior
        m_prior = [h for h in m_hist if h[1] == 'before_d16m_v1'] if d16m_hist is None else d16m_hist
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'data/corpus').mkdir(parents=True)
            (root / 'data/provenance').mkdir(parents=True)
            filler = list(range(1, n_filler + 1))
            ids = sorted(cur) + filler
            tiers = dict(cur)
            tiers.update({i: 'milk:derived' for i in filler})
            tiers.update(filler_current or {})
            labels = {i: ';'.join(sorted(parse_tiers(t))) or 'none_detected' for i, t in tiers.items()}
            wide = pd.DataFrame({'recipe_id': ids, 'Allergens_v2': [labels[i] for i in ids], 'allergen_tier': [tiers[i] for i in ids]})
            wide.to_parquet(root / 'data/corpus/recipes_structured.parquet')
            wide[['recipe_id', 'allergen_tier']].to_parquet(root / 'data/corpus/recipes.parquet')
            hist = [(i, c.GENERATION, rec[i]) for i in sorted(rec)] + [(i, c.GENERATION, 'milk:derived;sesame:direct') for i in filler]
            hist += list(recon_extra) + list(hist_prior) + list(m_prior)
            # an optional 4th element names the field (default allergen_tier)
            pd.DataFrame({'recipe_id': [h[0] for h in hist], 'field': [h[3] if len(h) > 3 else 'allergen_tier' for h in hist],
                          'generation': [h[1] for h in hist],
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


class D16MExemptionTests(unittest.TestCase):
    """I5-R10-1: the 29 D16M DECLARED_ADDITIONS rows and the one COMBINED_READDITIONS row (184699) are admitted only in their exact declared forms."""
    P = [(r, 'before_d16m_v1', v[2]) for r, v in D16M.items()]

    def _r(self, **kw):
        return D16IExemptionTests._run(D16IExemptionTests(), **kw)

    def _p(self, rid, value=None, gen='before_d16m_v1'):
        p = [x for x in self.P if x[0] != rid]
        return p if value is None else p + [(rid, gen, value)]

    def test_declared_forms_admitted(self):
        self.assertEqual(self._r(), [])

    def test_184699_readd_plus_removal_refused(self):
        # milk re-added and ghee / tree_nuts added as declared, but sulphites REMOVED: refused, whether or not the prior record agrees
        cur = {184699: 'coconut:direct;ghee:inherited;milk:inherited;tree_nuts:inherited'}
        self.assertNotEqual(self._r(current=cur), [])
        self.assertNotEqual(self._r(current=cur, d16m_hist=self._p(184699, 'coconut:direct')), [])

    def test_184699_variants_refused(self):
        for name, kw in [
            ('re-added literal changed', {'current': {184699: 'coconut:direct;ghee:inherited;milk:direct;sulphites:derived;tree_nuts:inherited'}}),
            ('added literal changed', {'current': {184699: 'coconut:direct;ghee:direct;milk:inherited;sulphites:derived;tree_nuts:inherited'}}),
            ('extra class', {'current': {184699: 'coconut:direct;ghee:inherited;milk:inherited;peanut:direct;sulphites:derived;tree_nuts:inherited'},
                             'd16m_hist': self._p(184699, 'coconut:direct;peanut:direct;sulphites:derived')}),
            ('an added class missing', {'current': {184699: 'coconut:direct;ghee:inherited;milk:inherited;sulphites:derived'}}),
            ('prior record missing', {'d16m_hist': self._p(184699)}),
            ('prior value altered', {'d16m_hist': self._p(184699, 'coconut:direct')}),
            ('prior under another generation', {'d16m_hist': self._p(184699, 'coconut:direct;sulphites:derived', 'before_d16l_v1')}),
            ('duplicated prior record', {'d16m_hist': self.P + [(184699, 'before_d16m_v1', 'coconut:direct;sulphites:derived')]}),
            ('re-added class not in the reconciliation prior', {'recon': {184699: 'coconut:direct;sulphites:derived;tree_nuts:direct'}}),
            ('added class was in the reconciliation prior', {'recon': {184699: 'coconut:direct;ghee:inherited;milk:inherited;sulphites:derived'}}),
            ('combined with a later-generation record',
             {'prior': D16IExemptionTests.PRIOR + [(184699, 'before_diet_repair_v1', D16M[184699][1])]}),
        ]:
            with self.subTest(name):
                self.assertNotEqual(self._r(**kw), [])

    def test_declared_addition_variants_refused(self):
        rid, (rec, cur, pri) = min((r, v) for r, v in D16M.items() if r != 184699)
        cls = sorted(set(parse_tiers(cur)) - set(parse_tiers(rec)))[0]
        changed = ';'.join(f'{k}:{"direct" if k == cls and v != "direct" else ("derived" if k == cls else v)}' for k, v in sorted(parse_tiers(cur).items()))
        for name, kw in [
            ('literal changed', {'current': {rid: changed}}),
            ('prior record missing', {'d16m_hist': self._p(rid)}),
            ('duplicated prior record', {'d16m_hist': self.P + [(rid, 'before_d16m_v1', pri)]}),
        ]:
            with self.subTest(name, rid=rid):
                self.assertNotEqual(self._r(**kw), [])

    def test_combined_shape_on_an_undeclared_row_refused(self):
        self.assertNotEqual(self._r(filler_current={7: 'ghee:inherited;milk:derived;sesame:direct;tree_nuts:inherited'}), [])


class ReconciliationCountTests(unittest.TestCase):
    """REVIEW_I5_CONTRACT N1: the reconciliation generation must carry exactly 401 unique allergen_tier rows; any other count is refused."""
    MSG = ['401 unique prior tier values missing from correction history']

    def _r(self, **kw):
        return D16IExemptionTests._run(D16IExemptionTests(), **kw)

    def test_401_admitted(self):
        self.assertEqual(self._r(), [])

    def test_wrong_count_refused(self):
        import allergen_tier_contract as c
        for name, kw in [
            ('400 rows', {'n_filler': 367}),
            ('402 rows', {'n_filler': 369}),
            ('401 rows with one recipe duplicated', {'n_filler': 367, 'recon_extra': [(1, c.GENERATION, 'milk:derived;sesame:direct')]}),
            ('401 unique rows, one off-field', {'n_filler': 367, 'recon_extra': [(368, c.GENERATION, 'milk;sesame', 'Allergens_v2')]}),
        ]:
            with self.subTest(name):
                self.assertEqual(self._r(**kw), self.MSG)
