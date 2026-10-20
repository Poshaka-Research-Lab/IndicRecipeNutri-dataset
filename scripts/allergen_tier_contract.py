"""Current allergen tiers describe current labels; removed tiers remain in history."""
import pandas as pd
from allergen_taxonomy import TOKENS

GENERATION = 'before_allergen_tier_reconciliation_v1'
# Later transactions that re-derived tier literals on rows of the 401 above. Each records, per changed row, the value it replaced.
LATER_GENERATIONS = ('before_diet_repair_v1',)
# Declared re-additions: a (recipe, class) the reconciliation removed as stale and a later owner-authorised transaction restored after reading the recipe
# text (fail-closed). Each names the generation that recorded the row's prior value and its decision record. The class must be back with the literal it
# was removed with, that generation's prior value must equal the current tiers without it, and the strict-removal check then applies to the rest.
REINSTATED = {
    (99336, 'gluten'): ('before_d16e_v1', 'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_E/LEAD_READ_5_GLUTEN_ROWS_2026-10-10.md; '
                                          'owner "Lead reads, fail-closed", OWNER_DECISIONS_BATCH_E_2026-10-10.json'),
    (99213, 'gluten'): ('before_d16i_v1', 'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I/review/review.md C3; '
                                          'owner "Keep + amend rules", OWNER_DECISIONS_BATCH_I1_ROUND2_2026-10-14.json point 1'),
}
# Declared first additions: a (recipe, class) on a row of the 401 above whose reconciliation prior never carried the class, added by a later
# owner-authorised transaction. There is no removed literal to restore, so the entry pins the literal. The class must be absent from the
# reconciliation prior and present now with exactly that literal, the named generation's prior value must equal the current tiers without it, and
# the strict-removal check then applies to the rest. Such a row may not also carry a REINSTATED entry or a later-generation record.
DECLARED_ADDITIONS = {
    (15690, 'gluten'): ('before_d16i_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I/review/review.md C3; '
                        'owner "Keep + amend rules", OWNER_DECISIONS_BATCH_I1_ROUND2_2026-10-14.json point 1'),
    # batch I-5 (D16M, 2026-10): owner-ruled additions on 401-set rows (I5-R10-1; post-install)
    (28021, 'ghee'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (30758, 'asafoetida'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (30758, 'ghee'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (40775, 'asafoetida'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (45836, 'ghee'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (47525, 'sulphites'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (52510, 'asafoetida'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (54385, 'asafoetida'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (81354, 'sulphites'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (85282, 'ghee'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (85282, 'milk'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (117104, 'ghee'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (119584, 'sulphites'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (126908, 'sulphites'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (126913, 'ghee'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (127710, 'asafoetida'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (127968, 'asafoetida'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (129964, 'gluten'): ('before_d16m_v1', 'derived',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (130331, 'gluten'): ('before_d16m_v1', 'derived',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (139708, 'sulphites'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (144079, 'ghee'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (144079, 'milk'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (155636, 'ghee'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (175159, 'ghee'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (184581, 'sulphites'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (184793, 'ghee'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (184793, 'milk'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (185104, 'asafoetida'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (202905, 'ghee'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (202905, 'milk'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (203067, 'gluten'): ('before_d16m_v1', 'derived',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (209602, 'asafoetida'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (210667, 'asafoetida'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (210679, 'ghee'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (210679, 'milk'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
}

# Declared combined re-addition (I5-R10-1; TODO B11): ONE row of the 401 above on which a later owner-authorised transaction both RE-ADDED a class the
# reconciliation removed (at the literal it was removed with) and ADDED classes the reconciliation prior never carried (at pinned literals). The entry
# pins: the generation of the row's prior record, the re-added {class: literal}, the added {class: literal}, and the exact remaining tiers, which must
# equal both the current tiers without the declared classes and that generation's single prior record. Additions only: any class removed, any literal
# changed or any extra class is refused, and the strict-removal check then applies to the remaining tiers. Such a row may not also carry a REINSTATED
# or DECLARED_ADDITIONS entry or a later-generation record.
COMBINED_READDITIONS = {
    184699: ('before_d16m_v1', {'milk': 'inherited'}, {'ghee': 'inherited', 'tree_nuts': 'inherited'}, 'coconut:direct;sulphites:derived',
             'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json I5-R10-1 (decision 4(a); TODO B11), '
             'BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk); applied only after an independent review APPROVE'),
}


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
        reinstated_history = pd.read_parquet(root / 'data/provenance/field_history.parquet',
                                             filters=[('generation', 'in', sorted({g for g, _ in REINSTATED.values()}) or [''])])
        if not set(rid for rid, _ in REINSTATED) <= set(history.recipe_id):
            return ['a declared re-addition names a row outside the reconciliation history']
        addition_history = pd.read_parquet(root / 'data/provenance/field_history.parquet',
                                           filters=[('generation', 'in', sorted({g for g, _, _ in DECLARED_ADDITIONS.values()}) or [''])])
        if not set(rid for rid, _ in DECLARED_ADDITIONS) <= set(history.recipe_id):
            return ['a declared addition names a row outside the reconciliation history']
        combined_history = pd.read_parquet(root / 'data/provenance/field_history.parquet',
                                           filters=[('generation', 'in', sorted({v[0] for v in COMBINED_READDITIONS.values()}) or [''])])
        if not set(COMBINED_READDITIONS) <= set(history.recipe_id):
            return ['a combined re-addition names a row outside the reconciliation history']
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
            back = {cls: gen for (rid, cls), (gen, _) in REINSTATED.items() if rid == row.recipe_id}
            added = {cls: (gen, literal) for (rid, cls), (gen, literal, _) in DECLARED_ADDITIONS.items() if rid == row.recipe_id}
            combo = COMBINED_READDITIONS.get(row.recipe_id)
            if combo:
                gen, readded, first, remaining, _ = combo
                if back or added or row.recipe_id in later_value:
                    return ['a combined re-addition is combined with another tier exemption']
                prior = combined_history[(combined_history.recipe_id == row.recipe_id) & combined_history.field.eq('allergen_tier')
                                         & combined_history.generation.eq(gen)]
                rest = {k: v for k, v in now.items() if k not in readded and k not in first}
                if (any(old.get(cls) != lit or now.get(cls) != lit for cls, lit in readded.items())
                        or any(cls in old or now.get(cls) != lit for cls, lit in first.items())
                        or rest != parse_tiers(remaining) or len(prior) != 1 or parse_tiers(prior.value_str.iloc[0]) != rest):
                    return ['a combined re-addition is not in its declared form or its prior value is not recorded']
                now = rest
            if added:
                if back or row.recipe_id in later_value:
                    return ['a declared addition is combined with another tier exemption']
                prior = addition_history[(addition_history.recipe_id == row.recipe_id) & addition_history.field.eq('allergen_tier')
                                         & addition_history.generation.isin({gen for gen, _ in added.values()})]
                rest = {k: v for k, v in now.items() if k not in added}
                if (any(cls in old or now.get(cls) != literal for cls, (_, literal) in added.items()) or len(prior) != 1
                        or parse_tiers(prior.value_str.iloc[0]) != rest):
                    return ['a declared addition is not in its declared form or its prior value is not recorded']
                now = rest
            if back:
                prior = reinstated_history[(reinstated_history.recipe_id == row.recipe_id) & reinstated_history.field.eq('allergen_tier')
                                           & reinstated_history.generation.isin(set(back.values()))]
                rest = {k: v for k, v in now.items() if k not in back}
                if (any(cls not in now or cls not in old or now[cls] != old[cls] for cls in back) or len(prior) != 1
                        or parse_tiers(prior.value_str.iloc[0]) != rest):
                    return ['a declared re-addition does not restore the removed tier or its prior value is not recorded']
                now = rest
            if not set(now) < set(old) or any(old[k] != v for k, v in now.items()):
                return ['correction history does not preserve a strict removal of stale tiers']
        return []
    except (OSError, KeyError, ValueError, TypeError) as exc:
        return [f'cannot validate allergen tiers: {exc}']
