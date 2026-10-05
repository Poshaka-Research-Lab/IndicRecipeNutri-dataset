"""Additive allergen evidence and fail-closed status, never a food-safety certificate.

Legacy labels remain immutable. Positive-name/legacy-absence conflicts become
UNKNOWN review candidates, not automatic presence corrections. Carrier patterns
are provisional; their absence is not evidence of absence.
"""
from __future__ import annotations

import json
import re

import allergen_taxonomy as _AT
from allergen_taxonomy import TOKENS
from quality_audit_rules import IMPLICIT_RX, ambiguous_hits, _NOT_DAIRY

POLICY_VERSION = 'irn-allergen-evidence-0.12.0-v1'
DIRECT = {
    'milk': _NOT_DAIRY + r'\bmilk\b', 'egg': r'\beggs?\b',
    'fish': r'\bfish\b', 'shellfish': r'\b(?:shellfish|prawns?|shrimps?|crabs?|lobsters?|mussels?|clams?|oysters?)\b',
    'tree_nuts': r'\b(?:tree nuts?|cashews?|almonds?|walnuts?|pistachios?|hazelnuts?|pecans?)\b',
    'peanut': r'\bpeanuts?\b', 'gluten': r'\b(?:gluten|wheat|barley|rye)\b',
    'soy': r'\b(?:soy|soya)\b', 'sesame': r'\bsesame\b', 'mustard': r'\bmustard\b',
    'fenugreek': r'\bfenugreek\b', 'asafoetida': r'\b(?:asafoetida|asafetida)\b',
    'tamarind': r'\btamarind\b', 'coconut': r'\bcoconut\b', 'celery': r'\bcelery\b',
    'sulphites': r'\b(?:sulphites?|sulfites?)\b', 'ghee': r'\bghee\b',
}
# gate_m27 M27.1b guard: the KEYS are part of the declared vocabulary, the VALUES are independent evidence.
_bad = sorted(set(DIRECT) - set(_AT.TOKENS))
assert not _bad, f"DIRECT names undeclared allergen token(s): {_bad}"
del _bad
DIRECT_RX = {k: re.compile(v, re.I) for k, v in DIRECT.items()}
KINDS = {'explicit', 'implicit_name', 'ambiguous_carrier', 'text_silent', 'unassessed'}
STATUSES = {'present', 'absent', 'unknown'}


def parse_ingredients(raw):
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return (), False
    if not isinstance(parsed, list) or not all(isinstance(x, str) for x in parsed):
        return (), False
    values = tuple(s.strip().lower() for s in parsed if s.strip())
    return values, bool(values)


def evidence_for_class(cls: str, items: tuple[str, ...], assessable: bool) -> tuple[str, str]:
    if cls not in TOKENS:
        raise ValueError('Unknown allergen class')
    if not assessable:
        return 'unassessed', 'ingredient_evidence_unassessed'
    # Negated/exclusion mentions are unresolved statements, not positive evidence.
    negated = False
    explicit = False
    implicit = False
    for line in items:
        for name, rx in [('explicit', DIRECT_RX[cls]), ('implicit', IMPLICIT_RX.get(cls))]:
            if rx is None:
                continue
            for match in rx.finditer(line):
                before = line[max(0, match.start() - 22):match.start()]
                after = line[match.end():match.end() + 10]
                exclusion = re.search(r'\b(?:no|without|omit|avoid|excluding)\s*$', before) or re.match(r'[ -]?free\b', after)
                if exclusion:
                    negated = True
                elif name == 'explicit':
                    explicit = True
                else:
                    implicit = True
    if explicit:
        return 'explicit', 'explicit_name_match'
    if implicit:
        return 'implicit_name', 'implicit_name_match'
    # Audit whole-line exclusions can hide a second, unspecified alternative oil.
    # Conservatively inspect alternatives too; this is a documented v1 delta.
    segments = [part for line in items for part in re.split(r';|\bor\b|\band\b', line)]
    if ambiguous_hits(cls, segments):
        return 'ambiguous_carrier', 'ambiguous_carrier_match'
    if negated:
        return 'ambiguous_carrier', 'negated_name_requires_review'
    return 'text_silent', 'no_supported_name_or_carrier_match'


def decide_status(legacy: str, kind: str, scan_incomplete: bool, assessable: bool) -> tuple[str, str]:
    if legacy not in {'present', 'absent', 'unassessed'} or kind not in KINDS:
        raise ValueError('Invalid legacy label or evidence kind')
    if legacy == 'present':
        return 'present', 'legacy_positive_preserved'
    if legacy == 'unassessed':
        return 'unknown', 'legacy_unassessed'
    if scan_incomplete:
        return 'unknown', 'scan_incomplete'
    if not assessable or kind == 'unassessed':
        return 'unknown', 'ingredient_evidence_unassessed'
    if kind in {'explicit', 'implicit_name'}:
        return 'unknown', 'name_conflicts_with_legacy_absence'
    if kind == 'ambiguous_carrier':
        return 'unknown', 'text_open_legacy_absence'
    return 'absent', 'silver_inferred_absence_not_verified_safe'


def decide_constraint(status: str) -> str:
    """Reference consumer: reject positive, abstain on UNKNOWN; absence is silver only."""
    if status not in STATUSES:
        raise ValueError('Unknown status')
    return {'present': 'FAIL', 'unknown': 'UNKNOWN', 'absent': 'PASS_SILVER_ONLY'}[status]
