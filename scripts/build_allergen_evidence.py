"""Stream additive per-class evidence/status to Parquet without exporting ingredient text."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from allergen_taxonomy import TOKENS
from allergen_evidence import POLICY_VERSION, parse_ingredients, evidence_for_class, decide_status
from audit_quality_inputs import sha256
from build_quality_flags import atomic_json, validate_output_root
from quality_audit_rules import lexicon_sha256

SCHEMA = pa.schema([
    ('recipe_id', pa.int64()), ('allergen', pa.string()), ('legacy_status', pa.string()),
    ('evidence_kind', pa.string()), ('evidence_reason', pa.string()),
    ('status_v012', pa.string()), ('status_reason', pa.string()),
    ('assessment_language_supported', pa.bool_()), ('scan_incomplete', pa.bool_()),
])


def build(root: Path, protected: Path, input_manifest: Path, heldout_ids: Path) -> dict:
    started = time.perf_counter()
    output = validate_output_root(root, protected)
    receipt = json.loads(input_manifest.read_text(encoding='utf-8'))
    checksums = {e['path']: e['expected'] for e in receipt['checksum_files']}
    inputs = {}
    for rel in ['data/corpus/recipes_structured.parquet', 'data/corpus/allergens.parquet']:
        digest = sha256(root / rel)
        if digest != checksums[rel]:
            raise ValueError('Baseline input changed: ' + rel)
        inputs[rel] = digest
    recipes = pd.read_parquet(root / 'data/corpus/recipes_structured.parquet', columns=[
        'recipe_id', 'IngredientsList', 'Lang_base', 'Region', 'allergen_scan_incomplete'])
    recipes = recipes.sort_values('recipe_id')
    if recipes.recipe_id.isna().any() or recipes.recipe_id.duplicated().any():
        raise ValueError('Invalid recipe IDs')
    from release_config import all_withdrawn_ids
    if set(recipes.recipe_id) & set(all_withdrawn_ids()):
        raise ValueError('Withdrawn ID would be admitted')
    labels = pd.read_parquet(root / 'data/corpus/allergens.parquet')
    if labels.duplicated(['recipe_id', 'allergen']).any():
        raise ValueError('Duplicate legacy allergen keys')
    if set(labels.recipe_id) != set(recipes.recipe_id) or set(labels.allergen) != set(TOKENS):
        raise ValueError('Legacy key/taxonomy mismatch')
    classes = sorted(TOKENS)
    statuses = labels.pivot(index='recipe_id', columns='allergen', values='status').reindex(recipes.recipe_id)[classes]
    if statuses.isna().any().any() or not statuses.isin(['present', 'absent', 'unassessed']).all().all():
        raise ValueError('Incomplete/invalid legacy label grid')
    del labels
    heldout = {int(x) for x in heldout_ids.read_text().split()}
    if not heldout <= set(recipes.recipe_id):
        raise ValueError('Evaluation partition has unknown recipe IDs')
    totals = defaultdict(Counter)
    slices = defaultdict(Counter)
    logical = hashlib.sha256()
    output.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='allergen_evidence.', suffix='.tmp', dir=output)
    os.close(fd)
    path = output / 'allergen_evidence_v1.parquet'
    buffer = []
    n = 0
    try:
        with pq.ParquetWriter(tmp, SCHEMA, compression='zstd') as writer:
            for rec, legacy_values in zip(recipes.itertuples(index=False, name=None), statuses.itertuples(index=False, name=None)):
                rid, raw, lang, region, incomplete = rec
                rid = int(rid)
                ing, parsed = parse_ingredients(raw)
                supported = isinstance(lang, str) and lang == 'en'
                assessable = parsed and supported
                # Missing scan status is unknown, never a negative scan.
                incomplete = bool(incomplete) if pd.notna(incomplete) else True
                region = str(region) if pd.notna(region) else 'UNKNOWN'
                population = 'heldout' if rid in heldout else 'dev'
                for cls, legacy in zip(classes, legacy_values):
                    kind, reason = evidence_for_class(cls, ing, assessable)
                    status, why = decide_status(legacy, kind, incomplete, assessable)
                    row = dict(recipe_id=rid, allergen=cls, legacy_status=legacy,
                               evidence_kind=kind, evidence_reason=reason, status_v012=status,
                               status_reason=why, assessment_language_supported=supported,
                               scan_incomplete=incomplete)
                    buffer.append(row)
                    logical.update((json.dumps(row, sort_keys=True, separators=(',', ':')) + '\n').encode())
                    key = (population, cls)
                    totals[key]['rows'] += 1
                    totals[key]['legacy_' + legacy] += 1
                    totals[key]['new_' + status] += 1
                    totals[key]['kind_' + kind] += 1
                    totals[key]['reason_' + why] += 1
                    changed = legacy == 'absent' and status == 'unknown'
                    totals[key]['absent_to_unknown'] += changed
                    slices[(population, region, cls)]['rows'] += 1
                    slices[(population, region, cls)]['absent_to_unknown'] += changed
                    slices[(population, region, cls)]['new_unknown'] += status == 'unknown'
                    n += 1
                if len(buffer) >= 16384:
                    writer.write_table(pa.Table.from_pylist(buffer, schema=SCHEMA))
                    buffer.clear()
                if n % (20000 * len(classes)) == 0:
                    print(json.dumps({'recipes_processed': n // len(classes)}), flush=True)
            if buffer:
                writer.write_table(pa.Table.from_pylist(buffer, schema=SCHEMA))
        if n != len(recipes) * len(classes):
            raise ValueError('Unexpected output cardinality')
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)
    result = {
        'policy_version': POLICY_VERSION, 'status': 'provisional_rule_evidence_not_independent_validation',
        'recipe_count': len(recipes), 'class_count': len(classes), 'rows': n,
        'inputs': inputs, 'input_manifest_sha256': sha256(input_manifest),
        'heldout_ids_sha256': sha256(heldout_ids),
        'policy_code_sha256': sha256(Path(__file__).with_name('allergen_evidence.py')),
        'builder_code_sha256': sha256(Path(__file__)), 'audit_lexicon_sha256': lexicon_sha256(),
        'logical_sha256': logical.hexdigest(), 'payload_sha256': sha256(path),
        'population_counts': [{'population': pop, 'allergen': cls, **dict(v)} for (pop, cls), v in sorted(totals.items())],
        'region_counts': [{'population': pop, 'region': region, 'allergen': cls, **dict(v)}
                          for (pop, region, cls), v in sorted(slices.items())],
        'deltas_from_audit_proposal': ['explicit-name evidence separated', 'negated mentions need review',
                                     'alternative carrier clauses assessed independently',
                                     'unsupported languages and invalid lists unassessed'],
        'legacy_labels_modified': False, 'raw_text_exported': False,
        'interpretation': 'Absent remains silver inferred absence, not verified safe; UNKNOWN is abstention.',
    }
    atomic_json(result, output / 'allergen_evidence_manifest.json')
    print(json.dumps({'rows': n, 'logical_sha256': logical.hexdigest(),
                      'seconds': round(time.perf_counter() - started, 2)}), flush=True)
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ['root', 'protected-root', 'input-manifest', 'heldout-ids']:
        ap.add_argument('--' + name, type=Path, required=True)
    a = ap.parse_args()
    build(a.root, a.protected_root, a.input_manifest, a.heldout_ids)


if __name__ == '__main__':
    main()
