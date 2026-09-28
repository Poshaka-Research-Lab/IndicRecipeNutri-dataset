"""Generate provisional quality sidecars from pinned release inputs and gated local text.

Instructions are used in memory only. Outputs contain closed enums, reasons and IDs.
Run in an isolated worktree. Neither source masters nor legacy payloads are written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import pandas as pd

from audit_quality_inputs import sha256
from quality_rules import CONFIG, RULE_VERSION, FIELDS, observe_audit_aligned, candidate_clusters


def canonical_digest(frame: pd.DataFrame) -> str:
    stable = frame.sort_values('recipe_id').reset_index(drop=True)
    return hashlib.sha256(stable.to_json(orient='records', force_ascii=False).encode('utf-8')).hexdigest()


def atomic_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.stem + '.', suffix='.tmp', dir=path.parent)
    os.close(fd)
    try:
        frame.to_parquet(temp, index=False)
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)


def atomic_json(value: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.stem + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + '\n')
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)


def validate_output_root(root: Path, protected: Path) -> Path:
    root, protected = root.resolve(), protected.resolve()
    if root == protected or root.is_relative_to(protected) or protected.is_relative_to(root):
        raise ValueError('Candidate output cannot overlap protected checkout')
    output = (root / 'data/quality').resolve()
    if not output.is_relative_to(root) or output.is_relative_to(protected):
        raise ValueError('Output resolves outside candidate or into protected checkout')
    return output


def load_rows(root: Path, source_workspace: Path | None, manifest: dict) -> tuple[pd.DataFrame, dict, dict]:
    columns = ['recipe_id', 'RecipeName', 'Title_normalized', 'IngredientsList', 'Region', 'Lang_base', 'SourceSite', 'Cuisine',
               'dup_family_id', 'Split_v3', 'has_instructions', 'title_unsupported_by_body']
    p = root / 'data/corpus/recipes_structured.parquet'
    expected = next(x['expected'] for x in manifest['checksum_files'] if x['path'] == 'data/corpus/recipes_structured.parquet')
    if sha256(p) != expected:
        raise ValueError('Corpus input does not match pinned baseline')
    frame = pd.read_parquet(p, columns=columns).sort_values('recipe_id').reset_index(drop=True)
    if frame.recipe_id.isna().any() or frame.recipe_id.duplicated().any():
        raise ValueError('Null/duplicate corpus IDs')
    from release_config import all_withdrawn_ids
    if set(frame.recipe_id) & set(all_withdrawn_ids()):
        raise ValueError('Withdrawn ID in corpus')
    instructions = {}
    source_info = {'status': 'unavailable', 'instructions_exported': False}
    if source_workspace is not None:
        source_workspace = source_workspace.resolve()
        sys.path.insert(0, str(source_workspace))
        import paths
        master = source_workspace / 'scraped_indian_recipes/data/MASTER_indian_recipes_enriched.csv'
        digest = paths.source_gate().require_master_ready(str(master))
        if digest != manifest['source_master']['sha256']:
            raise ValueError('Local master differs from approved input manifest')
        src = pd.read_csv(master, usecols=['recipe_id', 'Instructions', 'Title_normalized', 'IngredientsList'], low_memory=False)
        if src.recipe_id.isna().any() or src.recipe_id.duplicated().any():
            raise ValueError('Null/duplicate source IDs')
        joined = frame[['recipe_id', 'Title_normalized', 'IngredientsList']].merge(
            src, on='recipe_id', how='left', validate='one_to_one', indicator=True,
            suffixes=('_release', '_source'))
        if not joined._merge.eq('both').all():
            raise ValueError('Source lacks eligible IDs')
        for name in ['Title_normalized', 'IngredientsList']:
            if not joined[name + '_release'].fillna('').astype(str).equals(joined[name + '_source'].fillna('').astype(str)):
                raise ValueError('Source/release join content differs: ' + name)
        instructions = dict(zip(joined.recipe_id, joined.Instructions.fillna('')))
        source_info = {'status': 'gate_passed', 'sha256': digest, 'instructions_exported': False,
                       'joined_ids': len(joined), 'extra_source_ids_excluded': len(src) - len(joined)}
    return frame, instructions, source_info


def build(root: Path, protected: Path, source_workspace: Path | None, manifest_path: Path,
          config_path: Path, pilot_limit: int | None = None) -> dict:
    output = validate_output_root(root, protected)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    config = json.loads(config_path.read_text(encoding='utf-8'))
    if config['version'] != RULE_VERSION:
        raise ValueError('Rule config/version mismatch')
    frame, instructions, source_info = load_rows(root, source_workspace, manifest)
    region_path = config_path.with_name('region_taxonomy.json')
    region_codes = json.loads(region_path.read_text(encoding='utf-8'))['codes']
    if pilot_limit is not None:
        if pilot_limit < 1:
            raise ValueError('Pilot limit must be positive')
        # Explicit development pilot: one deterministic rotating pass through region/language cells.
        pilot = frame.loc[frame.Split_v3.ne('test')].copy()
        pilot = pilot.assign(_order=pilot.recipe_id.map(lambda i: hashlib.sha256(f'quality-pilot-v1:{i}'.encode()).hexdigest()))
        pilot = pilot.sort_values('_order')
        pilot['_cell_index'] = pilot.groupby(['Region', 'Lang_base'], dropna=False).cumcount()
        frame = pilot.sort_values(['_cell_index', '_order']).head(pilot_limit).drop(columns=['_order', '_cell_index'])
        output = (root / '.local/quality_0_12_0/pilot').resolve()
        if not output.is_relative_to(root.resolve()):
            raise ValueError('Private pilot output escapes candidate')
    rows = frame.to_dict(orient='records')
    clusters, duplicate_report = candidate_clusters(rows, config)
    results = []
    for row in rows:
        rid = int(row['recipe_id'])
        obs = observe_audit_aligned(row, instructions.get(rid), rid in instructions, region_codes, config)
        results.append({'recipe_id': rid, **obs, 'dup_cluster_id': clusters[rid],
                        'dup_cluster_id_reason': 'candidate_signature_component'})
    result = pd.DataFrame(results).sort_values('recipe_id').reset_index(drop=True)
    from quality_contract import validate_frames
    errors = validate_frames(result, frame)
    if errors:
        raise ValueError('; '.join(errors))
    crosswalk = frame[['recipe_id', 'dup_family_id', 'Split_v3']].copy()
    crosswalk['dup_cluster_id'] = crosswalk.recipe_id.map(clusters)
    crossing = crosswalk.groupby('dup_cluster_id').Split_v3.nunique().gt(1)
    crosswalk['crosses_legacy_split'] = crosswalk.dup_cluster_id.map(crossing)
    for source_col, suffix in [('Region', 'regions'), ('SourceSite', 'sites')]:
        family_counts = frame.dropna(subset=['dup_family_id']).groupby('dup_family_id')[source_col].nunique(dropna=False)
        crosswalk['dup_family_' + suffix] = crosswalk.dup_family_id.map(family_counts).astype('Int64')
    crosswalk = crosswalk.sort_values('recipe_id').reset_index(drop=True)
    duplicate_report['cross_split_candidate_components'] = int(crossing.sum())
    duplicate_report['rows_in_cross_split_candidate_components'] = int(crosswalk.crosses_legacy_split.sum())
    duplicate_report['legacy_splits_modified'] = False
    aggregate = []
    sliced = frame[['recipe_id', 'Region', 'Lang_base']].merge(result, on='recipe_id', validate='one_to_one')
    for slice_col in ['Region', 'Lang_base']:
        for label, group in sliced.groupby(slice_col, dropna=False, sort=True):
            for field in FIELDS[:-1]:
                for value, count in group[field].value_counts().sort_index().items():
                    aggregate.append({'slice': slice_col, 'label': 'UNKNOWN' if pd.isna(label) else str(label),
                                      'field': field, 'value': value, 'count': int(count), 'denominator': len(group)})
    report = {
        'rule_version': RULE_VERSION, 'status': config['status'], 'rows': len(result),
        'pilot': pilot_limit is not None, 'baseline_commit': manifest['baseline_commit'],
        'input_manifest_sha256': sha256(manifest_path), 'rule_config_sha256': sha256(config_path),
        'builder_sha256': sha256(Path(__file__)), 'rules_code_sha256': sha256(Path(__file__).with_name('quality_rules.py')),
        'source': source_info, 'logical_sha256': canonical_digest(result),
        'crosswalk_logical_sha256': canonical_digest(crosswalk),
        'counts': {f: {str(k): int(v) for k, v in result[f].value_counts().sort_index().items()} for f in FIELDS[:-1]},
        'reasons': {f: {str(k): int(v) for k, v in result[f + '_reason'].value_counts().sort_index().items()} for f in FIELDS},
        'duplicate_candidates': duplicate_report, 'slices': aggregate,
        'independent_validation': 'not_performed', 'raw_text_exported': False,
    }
    import quality_audit_patterns as patterns
    report['gate_spec_sha256'] = patterns.gate_spec_sha256()
    report['region_taxonomy_sha256'] = sha256(region_path)
    report['audit_pattern_code_sha256'] = sha256(Path(__file__).with_name('quality_audit_patterns.py'))
    report['audit_rule_code_sha256'] = sha256(Path(__file__).with_name('quality_audit_rules.py'))
    diagnostics = frame[['recipe_id', 'Region', 'SourceSite', 'Split_v3']].merge(result, on='recipe_id', validate='one_to_one')
    diagnostics['audit_incomplete'] = diagnostics.audit_record_completeness.ne('COMPLETE')
    diagnostics['audit_any_text_insufficiency'] = (diagnostics.audit_incomplete | diagnostics.audit_end_state_stated.eq('no') | diagnostics.audit_is_intermediate.eq('yes'))
    report['audit_counts'] = {}
    report['site_diagnostics'] = []
    for population, subset in [('ALL', diagnostics), ('DEV', diagnostics.loc[diagnostics.Split_v3.ne('test')])]:
        report['audit_counts'][population] = {'n': len(subset), 'any_text_insufficiency': int(subset.audit_any_text_insufficiency.sum()),
            'record_completeness': {str(k): int(v) for k,v in subset.audit_record_completeness.value_counts().items()},
            'has_instructions_mismatch': int(subset.has_instructions_mismatch.sum())}
        for region, group in subset.groupby('Region', dropna=False):
            for site, rows in group.groupby('SourceSite', dropna=False):
                report['site_diagnostics'].append({'population': population,
                    'region': None if pd.isna(region) else str(region), 'site': None if pd.isna(site) else str(site),
                    'n': len(rows), 'region_n': len(group), 'source_share': len(rows)/len(group),
                    'audit_text_insufficiency': int(rows.audit_any_text_insufficiency.sum()),
                    'end_state_unstated': int(rows.audit_end_state_stated.eq('no').sum())})
    atomic_parquet(result, output / 'recipe_quality_v1.parquet')
    atomic_parquet(crosswalk, output / 'duplicate_crosswalk_v1.parquet')
    report['payload_sha256'] = {name: sha256(output / name) for name in ['recipe_quality_v1.parquet', 'duplicate_crosswalk_v1.parquet']}
    atomic_json(report, output / 'quality_manifest.json')
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--protected-root', type=Path, required=True)
    ap.add_argument('--source-workspace', type=Path)
    ap.add_argument('--input-manifest', type=Path, required=True)
    ap.add_argument('--config', type=Path, required=True)
    ap.add_argument('--pilot-limit', type=int)
    args = ap.parse_args()
    started = time.perf_counter()
    report = build(args.root.resolve(), args.protected_root, args.source_workspace,
                   args.input_manifest, args.config, args.pilot_limit)
    print(json.dumps({'rows': report['rows'], 'logical_sha256': report['logical_sha256'],
                      'counts': report['counts'], 'duplicates': report['duplicate_candidates'],
                      'elapsed_seconds': round(time.perf_counter() - started, 2)}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
