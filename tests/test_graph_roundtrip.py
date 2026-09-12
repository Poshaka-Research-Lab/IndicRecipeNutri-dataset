import json
import sys
import unittest
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from build_graph import restore_graph, edge_columns
from edge_evidence import validate_evidence


class GraphRoundtripTests(unittest.TestCase):
    def setUp(self):
        self.nodes = pd.DataFrame({'node_id': ['ingredient::a', 'ingredient::b'], 'type': ['ingredient'] * 2})
        self.edges = pd.DataFrame([('ingredient::a', 'pairs_with', 'ingredient::b'),
                                   ('ingredient::a', 'shares_flavor', 'ingredient::b')], columns=['head', 'rel', 'tail'])

    def test_relation_is_not_interpreted_as_target(self):
        graph = restore_graph(self.nodes, self.edges)
        self.assertEqual(set(graph.nodes), set(self.nodes.node_id))
        self.assertTrue(graph.has_edge('ingredient::a', 'ingredient::b', key='shares_flavor'))
        self.assertEqual(graph.number_of_edges(), 2)

    def test_evidence_restored_on_correct_relation(self):
        evidence = self.edges.iloc[:1].assign(attributes_json=json.dumps({'pmi': 1.5, 'also_shares_flavor': True, 'shared_compounds': 7}))
        graph = restore_graph(self.nodes, self.edges, evidence)
        self.assertEqual(graph['ingredient::a']['ingredient::b']['pairs_with']['shared_compounds'], 7)
        self.assertNotIn('pmi', graph['ingredient::a']['ingredient::b']['shares_flavor'])

    def test_missing_endpoint_fails_instead_of_creating_node(self):
        with self.assertRaises(ValueError):
            restore_graph(self.nodes.iloc[:1], self.edges)

    def test_orphan_evidence_fails(self):
        evidence = self.edges.iloc[:1].assign(rel='unknown', attributes_json='{}')
        with self.assertRaises(ValueError):
            restore_graph(self.nodes, self.edges, evidence)

    def test_source_schema_and_reordered_columns(self):
        edges = self.edges.rename(columns={'head': 'src', 'tail': 'dst'})[['rel', 'dst', 'src']]
        self.assertEqual(edge_columns(edges), ('src', 'dst', 'rel'))
        self.assertEqual(restore_graph(self.nodes, edges).number_of_edges(), 2)

    def test_evidence_validator_rejects_nonfinite_and_orphan(self):
        evidence = self.edges.iloc[:1].assign(attributes_json='{"pmi": NaN}')
        self.assertTrue(validate_evidence(self.edges, evidence))
        evidence = evidence.assign(rel='unknown', attributes_json='{"support": 2}')
        self.assertTrue(any('absent triples' in p for p in validate_evidence(self.edges, evidence)))

    def test_evidence_validator_accepts_supported_claim(self):
        evidence = self.edges.iloc[:1].assign(attributes_json='{"support": 2}')
        self.assertEqual(validate_evidence(self.edges, evidence), [])


if __name__ == '__main__':
    unittest.main()
