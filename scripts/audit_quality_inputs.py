"""Read-only inventory for the 0.12.0 quality layer; never export recipe text."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

BASELINE = '620496feb4aeffaee7b01e1892418924d8b2fd47'
HISTORICAL = '083229c1e04343aa573cc878d1eaf4b9a90ab01e'


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def inventory(root: Path, source_root: Path | None = None) -> dict:
    manifest = root / 'checksums/SHA256SUMS'
    checked, problems = [], []
    for line in manifest.read_text(encoding='utf-8').splitlines():
        expected, rel = line.split('  ', 1)
        p = (root / rel).resolve()
        if not p.is_relative_to(root.resolve()):
            raise ValueError('Checksum manifest path escapes repository')
        actual = sha256(p) if p.is_file() else None
        checked.append({'path': rel, 'expected': expected, 'actual': actual})
        if expected != actual:
            problems.append('checksum mismatch: ' + rel)
    schemas = {}
    for path in sorted((root / 'data').rglob('*.parquet')):
        with path.open('rb') as f:
            if f.read(4) != b'PAR1':
                raise ValueError('Non-materialized or invalid Parquet: ' + str(path))
        pf = pq.ParquetFile(path)
        schemas[path.relative_to(root).as_posix()] = {
            'rows': pf.metadata.num_rows,
            'fields': [{'name': x.name, 'type': str(x.type)} for x in pf.schema_arrow],
        }
    columns = ['recipe_id', 'Region', 'Lang_base', 'Split_v3', 'dup_family_id',
               'has_instructions', 'has_ingredients', 'allergen_scan_incomplete']
    frame = pd.read_parquet(root / 'data/corpus/recipes_structured.parquet', columns=columns)
    if frame.recipe_id.isna().any() or frame.recipe_id.duplicated().any():
        problems.append('corpus has null/duplicate recipe IDs')
    aggregate = {}
    for col in columns[1:]:
        if col != 'dup_family_id':
            aggregate[col] = {str(k): int(v) for k, v in frame[col].fillna('UNKNOWN').astype(str).value_counts().sort_index().items()}
    fam = frame.dropna(subset=['dup_family_id'])
    source = {'status': 'not_requested', 'instructions_exported': False}
    if source_root is not None:
        # Use the actual gated source API before even reading the CSV header.
        sys.path.insert(0, str(source_root.resolve()))
        import paths
        master = source_root / 'scraped_indian_recipes/data/MASTER_indian_recipes_enriched.csv'
        try:
            digest = paths.source_gate().require_master_ready(str(master.resolve()))
            header = pd.read_csv(master, nrows=0).columns.tolist()
            projection = pd.read_csv(master, usecols=['recipe_id', 'Instructions',
                                     'IngredientsList', 'Title_normalized'], low_memory=False)
            released = pd.read_parquet(root / 'data/corpus/recipes.parquet',
                                       columns=['recipe_id', 'IngredientsList', 'Title_normalized'])
            joined = released.merge(projection, on='recipe_id', how='left', validate='one_to_one',
                                    indicator=True, suffixes=('_release', '_source'))
            reconciliation = {
                'source_rows': len(projection), 'release_rows': len(released),
                'matched_ids': int(joined._merge.eq('both').sum()),
                'missing_ids': int(joined._merge.ne('both').sum()),
                'source_extra_ids_not_admitted': int((~projection.recipe_id.isin(released.recipe_id)).sum()),
                'nonempty_instructions': int(joined.Instructions.fillna('').str.strip().ne('').sum()),
            }
            for column in ['IngredientsList', 'Title_normalized']:
                reconciliation[column + '_differences'] = int(
                    joined[column + '_release'].fillna('').astype(str).ne(
                        joined[column + '_source'].fillna('').astype(str)).sum())
            source = {'status': 'gate_passed', 'alias': 'local_source_master',
                      'sha256': digest, 'bytes': master.stat().st_size,
                      'columns': header, 'reconciliation': reconciliation,
                      'instructions_exported': False}
        except Exception as exc:
            source = {'status': 'gate_refused', 'error_type': type(exc).__name__,
                      'reason': str(exc), 'instructions_exported': False}
    return {
        'baseline_commit': BASELINE, 'historical_commit': HISTORICAL,
        'baseline_tree': git(root, 'rev-parse', BASELINE + '^{tree}'),
        'historical_tree': git(root, 'rev-parse', HISTORICAL + '^{tree}'),
        'observed_head': git(root, 'rev-parse', 'HEAD'),
        'checksum_manifest_sha256': sha256(manifest),
        'checksum_files': checked, 'problems': problems, 'schemas': schemas,
        'corpus_rows': len(frame), 'unique_recipe_ids': int(frame.recipe_id.nunique()),
        'aggregate_counts': aggregate,
        'legacy_families': {'assigned_rows': len(fam),
                            'unique_families': int(fam.dup_family_id.nunique()),
                            'cross_split_families': int(fam.groupby('dup_family_id').Split_v3.nunique().gt(1).sum())},
        'source_master': source,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--source-workspace', type=Path)
    args = ap.parse_args()
    report = inventory(args.root.resolve(), args.source_workspace)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({'rows': report['corpus_rows'], 'tables': len(report['schemas']),
                      'checksum_files': len(report['checksum_files']), 'problems': report['problems'],
                      'source_status': report['source_master']['status']}))
    return bool(report['problems'])


if __name__ == '__main__':
    raise SystemExit(main())
