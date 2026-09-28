"""Mandatory additive 0.12.0 contracts; no independent semantic accuracy claim."""
import json
from pathlib import Path

import pandas as pd

from audit_quality_inputs import sha256
from build_quality_flags import canonical_digest


def receipt(root, name):
    return json.loads((root / 'data/quality' / name).read_text(encoding='utf-8'))


def check_hash(path, expected):
    if sha256(path) != expected:
        raise ValueError('digest mismatch: ' + str(path))


def validate_quality(root):
    from quality_contract import validate_release_quality
    errors = validate_release_quality(root)
    manifest = receipt(root, 'quality_manifest.json')
    if manifest['pilot'] or manifest['raw_text_exported']:
        errors.append('pilot or raw-text quality output cannot be released')
    sources = {
        'builder_sha256': 'scripts/build_quality_flags.py',
        'rules_code_sha256': 'scripts/quality_rules.py',
        'audit_pattern_code_sha256': 'scripts/quality_audit_patterns.py',
        'audit_rule_code_sha256': 'scripts/quality_audit_rules.py',
        'rule_config_sha256': 'docs/quality_0_12_0/quality_rules_v1.json',
        'region_taxonomy_sha256': 'docs/quality_0_12_0/region_taxonomy.json',
    }
    for key, relative in sources.items():
        check_hash(root / relative, manifest[key])
    for name in ['recipe_quality_v1.parquet', 'duplicate_crosswalk_v1.parquet']:
        path = root / 'data/quality' / name
        check_hash(path, manifest['payload_sha256'][name])
        frame = pd.read_parquet(path)
        key = 'logical_sha256' if name.startswith('recipe_') else 'crosswalk_logical_sha256'
        if len(frame) != manifest['rows'] or canonical_digest(frame) != manifest[key]:
            errors.append('quality logical receipt mismatch: ' + name)
    return errors


def validate_item_card(root):
    from item_card import SOURCE_COLUMNS, VERSION, attributes
    manifest = receipt(root, 'item_card_manifest.json')
    source = root / 'data/corpus/recipes_structured.parquet'
    path = root / 'data/quality/item_attributes_v1.parquet'
    check_hash(source, manifest['source_sha256'])
    check_hash(path, manifest['payload_sha256'])
    check_hash(root / 'scripts/item_card.py', manifest['builder_sha256'])
    actual = pd.read_parquet(path)
    expected = attributes(pd.read_parquet(source, columns=SOURCE_COLUMNS))
    errors = []
    if manifest['version'] != VERSION or len(actual) != manifest['rows']:
        errors.append('item-card manifest version/cardinality mismatch')
    if not expected.equals(actual):
        errors.append('item-card does not reproduce from published attributes')
    return errors


def validate_nutrition(root):
    from build_nutrition_evidence import summarize
    manifest = receipt(root, 'nutrition_evidence_manifest.json')
    for relative, digest in manifest['inputs'].items():
        check_hash(root / relative, digest)
    check_hash(root / 'scripts/build_nutrition_evidence.py', manifest['builder_sha256'])
    path = root / 'data/quality/nutrition_evidence_v1.parquet'
    check_hash(path, manifest['payload_sha256'])
    corpus = pd.read_parquet(root / 'data/corpus/recipes_structured.parquet', columns=[
        'recipe_id','Region','Split_v3','per100g_confident','per100g_basis',
        'serving_basis_v3','ing_weight_confident_frac'])
    weights = pd.read_parquet(root / 'data/enrichment/ingredients_weights.parquet',
                              columns=['recipe_id','ing_index','tier','grams'])
    nutrition = pd.read_parquet(root / 'data/enrichment/ingredients_nutrition.parquet',
                                columns=['recipe_id','ing_index','grams','Nut_Calories'])
    expected = summarize(corpus, weights, nutrition)
    actual = pd.read_parquet(path)
    return [] if expected.equals(actual) else ['nutrition evidence does not reproduce from published occurrences']


def validate_release_quality_layers(root: Path):
    from allergen_evidence_contract import validate as validate_allergens
    from verify_interactions_v5 import verify as validate_generator
    checks = [
        ('quality', validate_quality), ('item-card', validate_item_card),
        ('nutrition-evidence', validate_nutrition),
        ('allergen-evidence', lambda p: validate_allergens(p)['errors']),
        ('generator-v5', lambda p: validate_generator(p, replay=False)['errors']),
    ]
    errors = []
    for name, check in checks:
        try:
            errors.extend(name + ': ' + problem for problem in check(root))
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            errors.append(name + ': cannot validate: ' + str(exc))
    return errors
