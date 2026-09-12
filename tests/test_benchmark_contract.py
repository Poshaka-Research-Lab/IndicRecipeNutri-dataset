from pathlib import Path
import hashlib
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import benchmark_contract as contract


class BenchmarkContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.folder = self.root / 'data/benchmark'
        self.folder.mkdir(parents=True)
        (self.root / 'data/kg').mkdir()
        self.graph = self.root / 'data/kg/kg_edges.parquet'
        self.graph.write_bytes(b'graph fixture')
        frozen = self.folder / 'silver_regression_v1.jsonl'
        frozen.write_text(''.join(json.dumps({'query': f'q{i}', 'template': 'ingredient'})+'\n' for i in range(67)), encoding='utf-8')
        current = self.folder / 'eval_queries.jsonl'
        current.write_text(''.join(json.dumps({'query': f'q{i}', 'template': 'ingredient',
            'query_id': 'silver_' + hashlib.sha256(f'ingredient\nq{i}'.encode()).hexdigest()[:16],
            'label_source': 'full_graph_silver'})+'\n' for i in range(contract.EXPECTED_BENCHMARK_QUERIES)), encoding='utf-8')
        self.frozen_hash = contract.digest(frozen)
        (self.folder / 'eval_queries_protocol.json').write_text(json.dumps({
            'protocol': 'fixed_silver_v1', 'queries_sha256': contract.digest(current),
            'frozen_definition_sha256': self.frozen_hash, 'definitions_changed': 0,
        }), encoding='utf-8')
        self.manifest = {
            'frozen_regression_sha256': self.frozen_hash,
            'current_queries_sha256': contract.digest(current),
            'graph_edges_sha256': contract.digest(self.graph),
            'current_query_count': contract.EXPECTED_BENCHMARK_QUERIES,
            'evaluation_mode': 'full-graph transductive diagnostic; not held-out human relevance',
        }
        (self.folder / 'BENCHMARK_MANIFEST.json').write_text(json.dumps(self.manifest), encoding='utf-8')
        self.pin = patch.object(contract, 'EXPECTED_SILVER_REGRESSION_SHA256', self.frozen_hash)
        self.pin.start()

    def tearDown(self):
        self.pin.stop()
        self.tmp.cleanup()

    def test_consistent_snapshots(self):
        self.assertEqual(contract.validate_benchmark(self.root), [])

    def test_new_graph_requires_new_manifest(self):
        self.graph.write_bytes(b'changed graph')
        self.assertTrue(any('current graph' in p for p in contract.validate_benchmark(self.root)))

    def test_baseline_must_not_be_replaced_by_new_generation(self):
        (self.folder / 'silver_regression_v1.jsonl').write_bytes((self.folder / 'eval_queries.jsonl').read_bytes())
        problems = contract.validate_benchmark(self.root)
        self.assertTrue(any('frozen regression' in p for p in problems))


if __name__ == '__main__':
    unittest.main()
