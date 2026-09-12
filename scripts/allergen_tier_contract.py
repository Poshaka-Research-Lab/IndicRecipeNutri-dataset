"""Current allergen tiers describe current labels; removed tiers remain in history."""
import pandas as pd
from allergen_taxonomy import TOKENS

GENERATION = 'before_allergen_tier_reconciliation_v1'


def parse_tiers(value):
    if value is None or pd.isna(value) or value == '':
        return {}
    out = {}
    for part in value.split(';'):
        token, separator, tier = part.partition(':')
        if not separator or token not in TOKENS or tier not in {'direct', 'derived', 'blend', 'inherited'} or token in out:
            raise ValueError('invalid or duplicate allergen tier')
        out[token] = tier
    return out


def validate_row(labels, tiers):
    expected = set(str(labels).split(';')) - {'unknown', 'none_detected', ''}
    if not expected.issubset(TOKENS):
        raise ValueError('invalid allergen label')
    if set(parse_tiers(tiers)) != expected:
        raise ValueError('current tier classes disagree with current labels')


def validate_release_tiers(root):
    try:
        wide = pd.read_parquet(root / 'data/corpus/recipes_structured.parquet',
                               columns=['recipe_id', 'Allergens_v2', 'allergen_tier']).set_index('recipe_id')
        narrow = pd.read_parquet(root / 'data/corpus/recipes.parquet',
                                 columns=['recipe_id', 'allergen_tier']).set_index('recipe_id')
        if not wide.index.is_unique or not narrow.index.is_unique or set(wide.index) != set(narrow.index):
            return ['tier surfaces have missing or duplicate recipe keys']
        if not wide.allergen_tier.fillna('').sort_index().equals(narrow.allergen_tier.fillna('').sort_index()):
            return ['current tiers disagree across recipe surfaces']
        for labels, tiers in wide[['Allergens_v2', 'allergen_tier']].itertuples(index=False, name=None):
            validate_row(labels, tiers)
        history = pd.read_parquet(root / 'data/provenance/field_history.parquet',
                                  filters=[('generation', '==', GENERATION)])
        if len(history) != 401 or history.recipe_id.duplicated().any() or not history.field.eq('allergen_tier').all():
            return ['401 unique prior tier values missing from correction history']
        for row in history.itertuples(index=False):
            old = parse_tiers(row.value_str)
            now = parse_tiers(wide.loc[row.recipe_id, 'allergen_tier'])
            if not set(now) < set(old) or any(old[k] != v for k, v in now.items()):
                return ['correction history does not preserve a strict removal of stale tiers']
        return []
    except (OSError, KeyError, ValueError, TypeError) as exc:
        return [f'cannot validate allergen tiers: {exc}']
