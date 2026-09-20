"""Canonical nutrition provenance names and cross-surface checks."""
import pandas as pd
import numpy as np

WEIGHT_CONFIDENCE_CONTRACT = {
    'version':'occurrence_weight_confidence_v1',
    'field':'ing_weight_confident_frac',
    'numerator':'Number of current ingredient occurrence rows whose estimator confident flag is true.',
    'denominator':'Number of current ingredient occurrence rows for that recipe.',
    'missingness':'No occurrence rows means unavailable (null), not zero. Zero means rows exist and none has the flag.',
    'limitation':'Estimator-tier fraction, not calibrated probability, source-quantity accuracy or nutrient accuracy.',
}


def validate_weight_confidence_frames(wide, quality, weights):
    field='ing_weight_confident_frac'
    if not {'recipe_id','ing_index','confident'}<=set(weights):return ['weight occurrence confidence fields missing']
    if weights[['recipe_id','ing_index']].isna().any().any() or weights.duplicated(['recipe_id','ing_index']).any():
        return ['invalid or duplicate weight occurrence keys']
    if not weights.confident.isin([True,False]).all():return ['weight confidence flags missing or invalid']
    count=weights.groupby('recipe_id').confident.count()
    numerator=weights.confident.eq(True).groupby(weights.recipe_id).sum()
    expected=numerator/count
    problems=[]
    for name,frame in [('wide',wide),('quality',quality)]:
        if not {'recipe_id',field}<=set(frame):
            problems.append(name+': weight confidence fraction missing');continue
        if frame.recipe_id.isna().any() or frame.recipe_id.duplicated().any():
            problems.append(name+': duplicate or missing recipe IDs');continue
        if not set(weights.recipe_id)<=set(frame.recipe_id):problems.append(name+': weight recipes absent from corpus')
        actual=pd.to_numeric(frame[field],errors='coerce')
        if (frame[field].notna() & actual.isna()).any():problems.append(name+': invalid numeric fraction')
        target=frame.recipe_id.map(expected)
        if not np.isclose(actual,target,rtol=0,atol=1e-12,equal_nan=True).all():
            problems.append(name+': weight confidence differs from current occurrence flags or missingness')
    if 'recipe_id' in wide and 'recipe_id' in quality and set(wide.recipe_id)!=set(quality.recipe_id):
        problems.append('weight confidence corpus ID sets differ')
    return problems


def validate_release_weight_confidence(root):
    try:
        columns=['recipe_id','ing_weight_confident_frac']
        wide=pd.read_parquet(root/'data/corpus/recipes_structured.parquet',columns=columns)
        quality=pd.read_parquet(root/'data/corpus/quality.parquet',columns=columns)
        weights=pd.read_parquet(root/'data/enrichment/ingredients_weights.parquet',columns=['recipe_id','ing_index','confident'])
        return validate_weight_confidence_frames(wide,quality,weights)
    except (OSError,KeyError,ValueError) as exc:
        return [f'cannot validate occurrence weight confidence: {exc}']

CANONICAL = 'nut_suppl_fct_frac'
LEGACY = 'nut_indb_frac'
FOLATE_BASIS = 'unavailable_total_folate_not_dfe'
DENSITY_UNAVAILABLE = 'unavailable_incomplete_ingredient_layer'
DENSITY_BASIS_CONTRACT = {
    'version': 'ingredient_density_completeness_v1',
    'field': 'per100g_basis',
    'unavailable_value': DENSITY_UNAVAILABLE,
    'meaning': 'A prior ingredient-density estimate lacks complete valid ingredient contributions or otherwise fails density eligibility.',
    'required_behavior': 'Density nutrient values and associated traffic-light labels are null; availability and confidence are false. Missing is not zero and must not satisfy an upper-bound nutrition filter.',
    'complete_contribution_limit': 'Arithmetic completeness does not establish ingredient identity, quantity accuracy, cooking yield or compatible raw/cooked source basis.',
}
FRACTION_BASIS_CONTRACT = {
    'version': 'supplemental_fraction_basis_v1',
    'field': 'nut_suppl_fct_basis',
    'meaning': 'Denominator evidence for the fraction of computed ingredient calories attributed to supplemental FCT records.',
    'values': ['complete_computed_ingredient_energy','partial_computed_ingredient_energy',
               'unavailable_no_energy','unavailable_zero_energy','unavailable_no_summary','legacy_denominator_unverified'],
    'required_behavior': 'Unavailable fractions remain null. Numeric zero describes a usable denominator with no supplemental energy only when the basis is verified; legacy zero has an unverified denominator.',
    'limitation': 'Not a fraction of Indian laboratory data, ingredient mass, all nutrients or independently validated recipe energy.',
}


def validate_density_frame(frame):
    required = {'per100g_basis', 'per100g_available_v3', 'per100g_confident'}
    if not required <= set(frame):
        return ['density basis or availability/confidence fields missing']
    unavailable = frame.per100g_basis.eq(DENSITY_UNAVAILABLE)
    fields = ['per100g_kcal', 'per100g_protein', 'per100g_fat', 'per100g_carb',
              'per100g_fiber', 'per100g_sugar', 'per100g_sodium', 'per100g_salt',
              'per100g_satfat', 'fsa_fat', 'fsa_saturates', 'fsa_sugars', 'fsa_salt']
    missing = set(fields) - set(frame)
    if missing:
        return ['density nutrient/label fields missing: ' + ', '.join(sorted(missing))]
    fields += [c for c in ['fsa_n_red','fsa_n_green','fsa_n_labelled','fsa_portion_g'] if c in frame]
    problems = []
    if frame.loc[unavailable, fields].notna().any().any():
        problems.append('unavailable ingredient-density rows retain values or traffic-light labels')
    flags = ['per100g_available_v3', 'per100g_confident']
    if 'fsa_portion_override_applied' in frame:
        flags.append('fsa_portion_override_applied')
    for flag in flags:
        if not frame.loc[unavailable, flag].eq(False).all():
            problems.append('unavailable ingredient-density rows require explicit false ' + flag)
    return problems


def validate_release_density(root):
    problems = []
    for name in ['recipes_structured', 'nutrition_derived']:
        try:
            frame = pd.read_parquet(root / f'data/corpus/{name}.parquet')
            problems.extend(f'{name}: {p}' for p in validate_density_frame(frame))
        except (OSError, KeyError, ValueError) as exc:
            problems.append(f'cannot validate {name} density availability: {exc}')
    return problems


def validate_folate_frame(frame):
    if not {'DV_Folate', 'DV_Folate_basis'} <= set(frame):
        return ['folate value or basis column missing']
    if frame.DV_Folate.notna().any():
        return ['unsupported total-folate-derived DV_Folate remains populated']
    if not frame.DV_Folate_basis.eq(FOLATE_BASIS).all():
        return ['unsupported folate percentage lacks the explicit unavailable basis']
    return []


def validate_release_folate(root):
    problems = []
    try:
        for name in ['recipes_structured', 'nutrition_derived']:
            frame = pd.read_parquet(root / f'data/corpus/{name}.parquet')
            problems.extend(f'{name}: {p}' for p in validate_folate_frame(frame))
        history = pd.read_parquet(root / 'data/provenance/field_history.parquet')
        old = history[history.field.eq('DV_Folate') & history.generation.eq('pre_folate_basis_v1')]
        if old.recipe_id.duplicated().any() or set(old.recipe_id) != set(frame.recipe_id) or old.value_num.isna().any():
            problems.append('folate history must preserve exactly one numeric pre-correction value per current recipe')
    except (OSError, KeyError, ValueError) as exc:
        problems.append(f'cannot validate folate suppression: {exc}')
    return problems


def normalize_fraction_name(frame, retain_legacy=False):
    frame = frame.copy()
    if LEGACY in frame and CANONICAL in frame:
        a, b = frame[LEGACY], frame[CANONICAL]
        if not (a.eq(b) | (a.isna() & b.isna())).all():
            raise ValueError('conflicting supplemental FCT fraction aliases')
    elif LEGACY in frame:
        frame[CANONICAL] = frame[LEGACY]
    if CANONICAL in frame:
        values = pd.to_numeric(frame[CANONICAL], errors='raise')
        if not values.dropna().between(0, 1).all():
            raise ValueError('supplemental FCT fraction outside [0,1]')
        if 'nut_suppl_fct_basis' in frame:
            basis = frame['nut_suppl_fct_basis']
            available = basis.isin(['partial_computed_ingredient_energy','complete_computed_ingredient_energy'])
            unavailable = basis.isin(['unavailable_no_energy','unavailable_zero_energy','unavailable_no_summary'])
            legacy = basis.eq('legacy_denominator_unverified')
            if not (available | unavailable | legacy).all():
                raise ValueError('unknown supplemental FCT fraction basis')
            if (available & values.isna()).any() or (unavailable & values.notna()).any():
                raise ValueError('supplemental FCT fraction contradicts availability basis')
        if retain_legacy:
            frame[LEGACY] = frame[CANONICAL]
        elif LEGACY in frame:
            frame = frame.drop(columns=LEGACY)
    return frame


def validate_fraction_frames(wide, quality):
    problems = []
    if CANONICAL not in wide or not {CANONICAL, LEGACY} <= set(quality):
        return ['canonical fraction missing from wide/quality, or compatibility alias missing from quality']
    try:
        normalize_fraction_name(wide)
        normalize_fraction_name(quality, retain_legacy=True)
    except (ValueError, TypeError) as exc:
        problems.append(str(exc))
    if wide.recipe_id.duplicated().any() or quality.recipe_id.duplicated().any():
        return problems + ['duplicate recipe IDs in fraction surfaces']
    if set(wide.recipe_id) != set(quality.recipe_id):
        return problems + ['recipe ID sets differ in fraction surfaces']
    a = wide.set_index('recipe_id')[CANONICAL].sort_index()
    b = quality.set_index('recipe_id')[CANONICAL].sort_index()
    if not (a.eq(b) | (a.isna() & b.isna())).all():
        problems.append('supplemental FCT fraction differs by recipe ID')
    basis = 'nut_suppl_fct_basis'
    if basis in wide or basis in quality:
        if basis not in wide or basis not in quality:
            problems.append('supplemental FCT fraction basis missing from one surface')
        elif not wide.set_index('recipe_id')[basis].sort_index().equals(quality.set_index('recipe_id')[basis].sort_index()):
            problems.append('supplemental FCT fraction basis differs by recipe ID')
    return problems


def validate_release_nutrition_alias(root):
    try:
        wide = pd.read_parquet(root / 'data/corpus/recipes_structured.parquet')
        quality = pd.read_parquet(root / 'data/corpus/quality.parquet')
        return validate_fraction_frames(wide, quality)
    except (OSError, KeyError, ValueError) as exc:
        return [f'cannot validate nutrition provenance aliases: {exc}']
