"""Regression guard for reviewed source ingredients previously omitted from recipe 23064."""
import json
import pandas as pd

RID = 23064


def validate_recovered_row(row):
    problems = []
    try:
        items = json.loads(row['IngredientsList'])
        if not isinstance(items, list) or not all(isinstance(x, str) for x in items):
            return ['invalid recovered ingredient list']
        if len(items) != 10 or not any('walnuts' in x.casefold() for x in items) or not any('brown sugar' in x.casefold() for x in items):
            problems.append('reviewed source ingredients are missing')
    except (TypeError, ValueError):
        return ['invalid recovered ingredient list']
    if 'tree_nuts' not in str(row['Allergens_v2']).split(';'):
        problems.append('source walnuts are absent from the allergen surface')
    if 'tree_nuts:direct' not in str(row['allergen_tier']).split(';'):
        problems.append('source walnuts lack direct ingredient evidence')
    return problems


def validate_release_source_recovery(root):
    try:
        wide = pd.read_parquet(root / 'data/corpus/recipes_structured.parquet', filters=[('recipe_id', '==', RID)])
        narrow = pd.read_parquet(root / 'data/corpus/recipes.parquet', filters=[('recipe_id', '==', RID)])
        if len(wide) != 1 or len(narrow) != 1:
            return ['reviewed recipe identity missing or duplicated']
        problems = validate_recovered_row(wide.iloc[0])
        if wide.iloc[0].IngredientsList != narrow.iloc[0].IngredientsList:
            problems.append('reviewed ingredient lists disagree across corpus surfaces')
        labels = pd.read_parquet(root / 'data/corpus/allergens.parquet', filters=[('recipe_id', '==', RID)])
        nut = labels[labels.allergen.eq('tree_nuts')]
        if len(nut) != 1 or nut.iloc[0].status != 'present':
            problems.append('reviewed source allergen missing from long table')
        edges = pd.read_parquet(root / 'data/kg/kg_edges.parquet', filters=[('head', '==', f'recipe::{RID}')])
        # `edges.tail` is the DataFrame METHOD, never the column of that name, so the original
        # attribute form raised TypeError every time this line was reached - and TypeError is
        # not in the except tuple below, so it escaped as a crash rather than a finding. This
        # guard had never actually checked the KG. Bracket access is the only correct form for
        # a column that collides with a pandas method name.
        triples = set(zip(edges['rel'], edges['tail']))
        if ('contains_allergen', 'allergen::tree_nuts') not in triples or ('has_ingredient', 'ingredient::walnut') not in triples:
            problems.append('reviewed ingredient/allergen evidence missing from KG')
        language_id = 131172
        for filename in ['recipes_structured.parquet', 'recipes.parquet']:
            language = pd.read_parquet(root / 'data/corpus' / filename,
                columns=['recipe_id', 'URL', 'Lang', 'Lang_base'], filters=[('recipe_id', '==', language_id)])
            if (len(language) != 1 or language.iloc[0].URL != 'https://www.sharmispassions.com/thengai-podi-recipe/'
                    or not language[['Lang', 'Lang_base']].eq('en').all().all()):
                problems.append(f'reviewed language correction missing from {filename}')
        history = pd.read_parquet(root / 'data/provenance/field_history.parquet',
            filters=[('recipe_id', '==', language_id), ('generation', '==', 'before_language_source_review_v1')])
        if (len(history) != 2 or set(history.field) != {'Lang', 'Lang_base'}
                or not history.value_str.eq('2 servings').all()):
            problems.append('reviewed prior language values missing from history')
        return problems
    except (OSError, KeyError, ValueError, AttributeError) as exc:
        return [f'cannot check reviewed source recovery: {exc}']
