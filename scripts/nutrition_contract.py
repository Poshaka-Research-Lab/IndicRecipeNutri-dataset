"""Canonical nutrition provenance names and cross-surface checks."""
import pandas as pd

CANONICAL = 'nut_suppl_fct_frac'
LEGACY = 'nut_indb_frac'
FOLATE_BASIS = 'unavailable_total_folate_not_dfe'


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
    return problems


def validate_release_nutrition_alias(root):
    try:
        wide = pd.read_parquet(root / 'data/corpus/recipes_structured.parquet', columns=['recipe_id', CANONICAL])
        quality = pd.read_parquet(root / 'data/corpus/quality.parquet')
        return validate_fraction_frames(wide, quality)
    except (OSError, KeyError, ValueError) as exc:
        return [f'cannot validate nutrition provenance aliases: {exc}']
