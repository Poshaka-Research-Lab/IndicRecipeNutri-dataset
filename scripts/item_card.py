"""Published-attribute item view. Text rendering is local-only and contains no oracle truth."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import pandas as pd

from audit_quality_inputs import sha256
from build_quality_flags import atomic_json, atomic_parquet, validate_output_root

VERSION = 'irn-item-card-0.12.0-v1'
SOURCE_COLUMNS = ['recipe_id', 'SpiceLevel', 'SpiceLevel_src', 'HealthGrade',
                  'RatingCount', 'RatingAverage', 'Region', 'Cuisine']


def rating_bin(value) -> str:
    if value is None or pd.isna(value):
        return 'unknown'
    x = float(value)
    if not math.isfinite(x) or x < 0:
        return 'unknown'
    if x == 0:
        return 'zero'
    if x < 10:
        return '1_9'
    if x < 100:
        return '10_99'
    return '100_plus'


def attributes(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.recipe_id.isna().any() or frame.recipe_id.duplicated().any():
        raise ValueError('Item-card IDs must be unique and non-null')
    out = frame[SOURCE_COLUMNS].copy().sort_values('recipe_id').reset_index(drop=True)
    out['rating_count_bin'] = out.RatingCount.map(rating_bin)
    out['spice_is_rule_inferred'] = out.SpiceLevel_src.eq('ingredient-rule')
    out['cuisine_generic_or_missing'] = out.Cuisine.fillna('').str.strip().str.casefold().isin(['', 'indian'])
    return out


def render_local_card(recipe: dict, attrs: dict) -> str:
    """Caller owns local-use permissions; do not commit or remotely send this output."""
    if int(recipe['recipe_id']) != int(attrs['recipe_id']):
        raise ValueError('Recipe/attribute key mismatch')
    def value(x):
        return 'unknown' if x is None or (isinstance(x, float) and math.isnan(x)) else str(x)
    # Explicit allowlist: no generator rank, hidden quality, oracle or exposure field.
    try:
        ingredients = json.loads(recipe.get('IngredientsList') or '[]')
    except (TypeError, ValueError):
        ingredients = []
    ingredient_text = '; '.join(x for x in ingredients if isinstance(x, str)) if isinstance(ingredients, list) else ''
    return '\n'.join([
        'Title: ' + value(recipe.get('Title_normalized')),
        'Ingredients: ' + (ingredient_text or 'unknown'),
        'Region: ' + value(attrs.get('Region')),
        'Spice level: ' + value(attrs.get('SpiceLevel')) + ' (source: ' + value(attrs.get('SpiceLevel_src')) + ')',
        'Published HealthGrade: ' + value(attrs.get('HealthGrade')) + ' (dataset label; not clinical advice)',
        'Rating count bin: ' + value(attrs.get('rating_count_bin')) + ' (observed ratings; not exposure)',
    ])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--protected-root', type=Path, required=True)
    ap.add_argument('--input-manifest', type=Path, required=True)
    a = ap.parse_args()
    output = validate_output_root(a.root, a.protected_root)
    receipt = json.loads(a.input_manifest.read_text(encoding='utf-8'))
    rel = 'data/corpus/recipes_structured.parquet'
    expected = next(x['expected'] for x in receipt['checksum_files'] if x['path'] == rel)
    if sha256(a.root / rel) != expected:
        raise ValueError('Source corpus changed')
    source = pd.read_parquet(a.root / rel, columns=SOURCE_COLUMNS)
    result = attributes(source)
    path = output / 'item_attributes_v1.parquet'
    atomic_parquet(result, path)
    manifest = {'version': VERSION, 'rows': len(result), 'source_sha256': expected,
                'payload_sha256': sha256(path), 'builder_sha256': sha256(Path(__file__)),
                'text_view': 'render_local_card; not materialized in the release',
                'private_text_exported': False, 'new_external_sources': [],
                'counts': {c: {str(k): int(v) for k, v in result[c].value_counts(dropna=False).items()}
                           for c in ['SpiceLevel_src', 'rating_count_bin', 'cuisine_generic_or_missing']},
                'limits': ['Spice provenance retained; rule-inferred is not independently sourced.',
                           'Missing ratings remain unknown, distinct from zero.',
                           'No synthetic hidden rank, quality, noise or exposure enters the view.']}
    atomic_json(manifest, output / 'item_card_manifest.json')
    print(json.dumps({'rows': len(result), 'counts': manifest['counts']}))


if __name__ == '__main__':
    main()
