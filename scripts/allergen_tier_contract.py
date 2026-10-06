"""Current allergen tiers describe current labels; removed tiers remain in history."""
import pandas as pd
from allergen_taxonomy import TOKENS

GENERATION = 'before_allergen_tier_reconciliation_v1'
# Later transactions that re-derived tier literals on rows of the 401 above. Each records, per changed row, the value it replaced.
LATER_GENERATIONS = ('before_diet_repair_v1',)


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
        later = pd.read_parquet(root / 'data/provenance/field_history.parquet',
                                filters=[('generation', 'in', list(LATER_GENERATIONS))])
        if later.recipe_id.duplicated().any() or not later.field.eq('allergen_tier').all() or not set(later.recipe_id) <= set(wide.index):
            return ['later tier history is duplicated, off-field or names an unknown recipe']
        later_value = dict(zip(later.recipe_id, later.value_str))
        for row in history.itertuples(index=False):
            old = parse_tiers(row.value_str)
            # A later transaction replaced this row's tiers: the strict removal must have held at the value it replaced.
            if row.recipe_id in later_value:
                # The later record must be non-empty and name exactly the classes the row carries now: only literals may have moved.
                replaced = parse_tiers(later_value[row.recipe_id])
                if not replaced or set(replaced) != set(parse_tiers(wide.loc[row.recipe_id, 'allergen_tier'])):
                    return ['later tier history is empty or its classes differ from the current tier']
                now = replaced
            else:
                now = parse_tiers(wide.loc[row.recipe_id, 'allergen_tier'])
            if not set(now) < set(old) or any(old[k] != v for k, v in now.items()):
                return ['correction history does not preserve a strict removal of stale tiers']
        return []
    except (OSError, KeyError, ValueError, TypeError) as exc:
        return [f'cannot validate allergen tiers: {exc}']
