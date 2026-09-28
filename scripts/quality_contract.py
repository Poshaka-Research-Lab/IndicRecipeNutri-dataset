"""Integrity of the additive P1 quality layer; semantic validation remains separate."""
from pathlib import Path
import re
import pandas as pd
from quality_rules import DOMAINS, FIELDS, EXTRA_FIELDS


def validate_frames(quality: pd.DataFrame, corpus: pd.DataFrame) -> list[str]:
    problems = []
    required = {'recipe_id', *FIELDS, *(f + '_reason' for f in FIELDS), *EXTRA_FIELDS}
    if set(quality.columns) != required:
        return ['quality schema has missing or unexpected columns']
    for name, frame in [('quality', quality), ('corpus', corpus)]:
        if frame.recipe_id.isna().any() or frame.recipe_id.duplicated().any():
            problems.append(name + ' has null/duplicate recipe IDs')
    if set(quality.recipe_id) != set(corpus.recipe_id):
        problems.append('quality/corpus recipe ID sets differ')
    for field, domain in DOMAINS.items():
        if not quality[field].isin(domain).all():
            problems.append('invalid domain: ' + field)
    for field in FIELDS:
        if not quality[field + '_reason'].fillna('').str.fullmatch(r'[a-z][a-z0-9_]*').all():
            problems.append('invalid reason code: ' + field)
    if not quality.dup_cluster_id.fillna('').str.fullmatch(r'q1_[a-f0-9]{64}').all():
        problems.append('invalid assessed duplicate cluster ID')
    for field in ['end_state_stated', 'is_intermediate', 'record_completeness']:
        unavailable = quality[field + '_reason'].isin(['input_unavailable', 'language_not_supported'])
        if not quality.loc[unavailable, field].eq('unknown').all():
            problems.append('unavailable input masquerades as assessment: ' + field)
    if not quality.audit_record_completeness.isin(['COMPLETE', 'MISSING', 'PLACEHOLDER', 'NOT_A_METHOD', 'TRUNCATED', 'UNASSESSED']).all():
        problems.append('invalid detailed audit completeness')
    for field in ['audit_end_state_stated', 'audit_is_intermediate', 'audit_liquid_fate_unstated', 'liquid_fate_unstated']:
        if not quality[field].isin(['yes','no','unknown']).all():
            problems.append('invalid tri-state field: ' + field)
    if not quality.region_stratum.isin(['primary_axis','coarse_stratum','unassigned','descriptive']).all():
        problems.append('invalid region stratum')
    unsupported = ~quality.instruction_language_supported
    if not quality.loc[unsupported, ['record_completeness','end_state_stated','is_intermediate','liquid_fate_unstated']].eq('unknown').all().all():
        problems.append('unsupported method language produces actionable assessment')
    return problems


def validate_release_quality(root: Path) -> list[str]:
    path = root / 'data/quality/recipe_quality_v1.parquet'
    if not path.exists():
        return ['quality sidecar missing']
    quality = pd.read_parquet(path)
    corpus = pd.read_parquet(root / 'data/corpus/recipes_structured.parquet', columns=['recipe_id', 'Split_v3', 'dup_family_id'])
    problems = validate_frames(quality, corpus)
    cross = pd.read_parquet(root / 'data/quality/duplicate_crosswalk_v1.parquet')
    if cross.recipe_id.isna().any() or cross.recipe_id.duplicated().any():
        return problems + ['crosswalk contains null/duplicate recipe IDs']
    if set(cross.recipe_id) != set(corpus.recipe_id):
        return problems + ['crosswalk/corpus recipe ID sets differ']
    cross = cross.set_index('recipe_id').sort_index()
    original = corpus.set_index('recipe_id').sort_index()
    for column in ['Split_v3', 'dup_family_id']:
        if not cross[column].equals(original[column]):
            problems.append('crosswalk changes legacy ' + column)
    if not cross.dup_cluster_id.equals(quality.set_index('recipe_id').sort_index().dup_cluster_id):
        problems.append('quality/crosswalk clusters differ')
    expected = cross.dup_cluster_id.map(cross.groupby('dup_cluster_id').Split_v3.nunique().gt(1))
    if not expected.equals(cross.crosses_legacy_split):
        problems.append('cross-split flags do not reproduce')
    return problems
