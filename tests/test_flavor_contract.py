import json
from pathlib import Path
import sys
import unittest
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from flavor_view import make_view
from flavor_contract import merge_flavor_tables, resolve_legacy_compound


class FlavorContractTests(unittest.TestCase):
    def setUp(self):
        self.nodes = pd.DataFrame([
            ('ingredient::a', 'ingredient', 'a', None),
            ('ingredient::b', 'ingredient', 'b', None),
            ('compound::1', 'compound', 'same name', '1'),
            ('compound::2', 'compound', 'same name', '2'),
        ], columns=['node_id', 'type', 'name', 'pubchem_id'])
        self.edges = pd.DataFrame([
            ('ingredient::a', 'has_compound', 'compound::1'),
            ('ingredient::a', 'has_compound', 'compound::2'),
            ('ingredient::a', 'pairs_with', 'ingredient::b'),
        ], columns=['head', 'rel', 'tail'])
        self.evidence = self.edges.iloc[2:].assign(attributes_json=json.dumps(
            {'also_shares_flavor': True, 'shared_compounds': 2, 'jaccard': 0.5}))

    def test_same_name_different_cids_survive(self):
        nodes, edges = make_view(self.nodes, self.edges, self.evidence)
        self.assertEqual(set(nodes.node_id), {'compound::1', 'compound::2'})
        self.assertEqual(int(edges.rel.eq('has_compound').sum()), 2)

    def test_attached_molecular_evidence_becomes_independent_relation(self):
        nodes, edges = make_view(self.nodes, self.edges, self.evidence)
        self.assertEqual(edges.loc[edges.rel.eq('shares_flavor'), 'shared_compounds'].tolist(), [2])
        n, e = merge_flavor_tables(self.nodes, self.edges, nodes, edges)
        self.assertEqual((len(n), len(e)), (4, 4))
        _, again = merge_flavor_tables(n, e, nodes, edges)
        pd.testing.assert_frame_equal(e, again)

    def test_missing_optional_has_compound_rejected(self):
        nodes, edges = make_view(self.nodes, self.edges, self.evidence)
        with self.assertRaises(ValueError):
            merge_flavor_tables(self.nodes, self.edges, nodes, edges.iloc[1:])

    def test_attached_evidence_on_other_relation_is_not_lost(self):
        self.edges.loc[2, 'rel'] = 'substitute_for'
        self.evidence.loc[self.evidence.index[0], 'rel'] = 'substitute_for'
        _, edges = make_view(self.nodes, self.edges, self.evidence)
        self.assertEqual(int(edges.rel.eq('shares_flavor').sum()), 1)

    def test_name_ids_cannot_silently_enter_new_view(self):
        self.nodes.loc[2, 'node_id'] = 'compound::same name'
        with self.assertRaises(ValueError):
            make_view(self.nodes, self.edges, self.evidence)

    def test_ambiguous_crosswalk_refuses_single_answer(self):
        crosswalk = pd.DataFrame({'legacy_node_id': ['compound::same name'] * 2,
                                  'node_id': ['compound::1', 'compound::2']})
        with self.assertRaisesRegex(ValueError, 'ambiguous'):
            resolve_legacy_compound('compound::same name', crosswalk)
        self.assertEqual(resolve_legacy_compound('compound::same name', crosswalk.iloc[:1]), 'compound::1')


if __name__ == '__main__':
    unittest.main()
