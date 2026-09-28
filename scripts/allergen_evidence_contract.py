"""Full keyed legacy comparison and fail-closed policy validation, in bounded batches."""
import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from allergen_taxonomy import TOKENS
from allergen_evidence import KINDS, POLICY_VERSION, decide_status
from audit_quality_inputs import sha256
from build_allergen_evidence import SCHEMA
from build_quality_flags import atomic_json
from quality_audit_rules import lexicon_sha256


def validate(root: Path) -> dict:
    quality = root / 'data/quality'
    manifest = json.loads((quality / 'allergen_evidence_manifest.json').read_text(encoding='utf-8'))
    path = quality / 'allergen_evidence_v1.parquet'
    errors = []
    if manifest['policy_version'] != POLICY_VERSION:
        errors.append('policy version mismatch')
    if manifest['policy_code_sha256'] != sha256(Path(__file__).with_name('allergen_evidence.py')):
        errors.append('policy code changed since generation')
    if manifest['builder_code_sha256'] != sha256(Path(__file__).with_name('build_allergen_evidence.py')):
        errors.append('builder code changed since generation')
    if manifest['audit_lexicon_sha256'] != lexicon_sha256():
        errors.append('carrier lexicon changed since generation')
    if manifest['payload_sha256'] != sha256(path):
        errors.append('payload digest mismatch')
    for rel, expected in manifest['inputs'].items():
        if sha256(root / rel) != expected:
            errors.append('input digest mismatch: ' + rel)
    parquet = pq.ParquetFile(path)
    if not parquet.schema_arrow.equals(SCHEMA, check_metadata=False):
        return {'status': 'failed', 'errors': errors + ['schema mismatch']}
    corpus = pd.read_parquet(root / 'data/corpus/recipes_structured.parquet', columns=['recipe_id'])
    ids = sorted(int(i) for i in corpus.recipe_id)
    if len(ids) != len(set(ids)):
        return {'status': 'failed', 'errors': errors + ['duplicate corpus IDs']}
    legacy = pd.read_parquet(root / 'data/corpus/allergens.parquet')
    if legacy.duplicated(['recipe_id', 'allergen']).any():
        return {'status': 'failed', 'errors': errors + ['duplicate legacy keys']}
    classes = sorted(TOKENS)
    if set(legacy.recipe_id) != set(ids) or set(legacy.allergen) != set(classes):
        return {'status': 'failed', 'errors': errors + ['legacy grid mismatch']}
    grid = legacy.pivot(index='recipe_id', columns='allergen', values='status').reindex(ids)[classes].to_numpy()
    logical = hashlib.sha256()
    n = 0
    failures = {'key_order_or_coverage': 0, 'legacy_value_changed': 0, 'invalid_evidence_kind': 0,
                'policy_disagrees': 0, 'positive_downgraded': 0}
    for batch in parquet.iter_batches(batch_size=32768):
        for row in batch.to_pylist():
            i, j = divmod(n, len(classes))
            if i >= len(ids) or (row['recipe_id'], row['allergen']) != (ids[i], classes[j]):
                failures['key_order_or_coverage'] += 1
            elif row['legacy_status'] != grid[i, j]:
                failures['legacy_value_changed'] += 1
            if row['evidence_kind'] not in KINDS:
                failures['invalid_evidence_kind'] += 1
            else:
                assessed = row['evidence_kind'] != 'unassessed' and row['assessment_language_supported']
                try:
                    expected = decide_status(row['legacy_status'], row['evidence_kind'], row['scan_incomplete'], assessed)
                except ValueError:
                    failures['policy_disagrees'] += 1
                else:
                    if (row['status_v012'], row['status_reason']) != expected:
                        failures['policy_disagrees'] += 1
            if row['legacy_status'] == 'present' and row['status_v012'] != 'present':
                failures['positive_downgraded'] += 1
            logical.update((json.dumps(row, sort_keys=True, separators=(',', ':')) + '\n').encode())
            n += 1
    if n != len(ids) * len(classes) or n != manifest['rows']:
        errors.append('row count mismatch')
    if logical.hexdigest() != manifest['logical_sha256']:
        errors.append('logical digest mismatch')
    errors.extend(f'{k}: {v}' for k, v in failures.items() if v)
    return {'status': 'failed' if errors else 'passed', 'rows_checked': n,
            'errors': errors, 'failure_counts': failures,
            'logical_sha256': logical.hexdigest(),
            'scope': 'All row keys, legacy values and stored-evidence policy checked; no claim of independent semantic accuracy.'}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    result = validate(a.root)
    atomic_json(result, a.output)
    print(json.dumps(result))
    return result['status'] != 'passed'


if __name__ == '__main__':
    raise SystemExit(main())
