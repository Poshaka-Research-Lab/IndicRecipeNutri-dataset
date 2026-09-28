import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import allergen_evidence_contract as contract
from allergen_taxonomy import TOKENS
from allergen_evidence import POLICY_VERSION
from audit_quality_inputs import sha256
from build_allergen_evidence import SCHEMA
from quality_audit_rules import lexicon_sha256


class AllergenContractTests(unittest.TestCase):
    def make_fixture(self, root, mutation=None):
        (root / 'data/corpus').mkdir(parents=True)
        (root / 'data/quality').mkdir(parents=True)
        pd.DataFrame({'recipe_id': [1]}).to_parquet(root / 'data/corpus/recipes_structured.parquet', index=False)
        classes = sorted(TOKENS)
        pd.DataFrame([{'recipe_id': 1, 'allergen': c, 'status': 'absent'} for c in classes]).to_parquet(
            root / 'data/corpus/allergens.parquet', index=False)
        rows = [dict(recipe_id=1, allergen=c, legacy_status='absent', evidence_kind='ambiguous_carrier',
                     evidence_reason='ambiguous_carrier_match', status_v012='unknown',
                     status_reason='text_open_legacy_absence', assessment_language_supported=True,
                     scan_incomplete=False) for c in classes]
        if mutation:
            mutation(rows)
        target = root / 'data/quality/allergen_evidence_v1.parquet'
        pq.write_table(pa.Table.from_pylist(rows, schema=SCHEMA), target)
        digest = hashlib.sha256()
        for row in rows:
            digest.update((json.dumps(row, sort_keys=True, separators=(',', ':')) + '\n').encode())
        scripts = Path(contract.__file__).parent
        manifest = {'policy_version': POLICY_VERSION, 'rows': len(rows), 'payload_sha256': sha256(target),
                    'logical_sha256': digest.hexdigest(), 'audit_lexicon_sha256': lexicon_sha256(),
                    'policy_code_sha256': sha256(scripts / 'allergen_evidence.py'),
                    'builder_code_sha256': sha256(scripts / 'build_allergen_evidence.py'),
                    'inputs': {rel: sha256(root / rel) for rel in ['data/corpus/recipes_structured.parquet', 'data/corpus/allergens.parquet']}}
        (root / 'data/quality/allergen_evidence_manifest.json').write_text(json.dumps(manifest))

    def test_valid_complete_grid(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.make_fixture(root)
            self.assertEqual(contract.validate(root)['status'], 'passed')

    def test_semantic_error_fails_even_with_updated_digests(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.make_fixture(root, lambda rows: rows[0].update(status_v012='absent'))
            result = contract.validate(root)
            self.assertEqual(result['status'], 'failed')
            self.assertEqual(result['failure_counts']['policy_disagrees'], 1)

    def test_duplicate_key_fails_even_with_updated_digests(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.make_fixture(root, lambda rows: rows[1].update(allergen=rows[0]['allergen']))
            self.assertGreater(contract.validate(root)['failure_counts']['key_order_or_coverage'], 0)

    def test_legacy_label_change_fails_even_with_updated_digests(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.make_fixture(root, lambda rows: rows[0].update(legacy_status='present', status_v012='present', status_reason='legacy_positive_preserved'))
            self.assertGreater(contract.validate(root)['failure_counts']['legacy_value_changed'], 0)


if __name__ == '__main__':
    unittest.main()
