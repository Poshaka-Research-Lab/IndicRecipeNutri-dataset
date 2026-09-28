"""Conservative, provisional quality observations; no recipe text is returned."""
from __future__ import annotations

import ast
import hashlib
import json
import re
import unicodedata

RULE_VERSION = 'quality-v1-draft-2-audit-aligned'
COARSE = {'Pan-Indian', 'North India', 'South India', 'East India', 'West India'}
SPECIFIC = {'Andhra Pradesh', 'Assam', 'Bihar', 'Goa', 'Gujarat', 'Himachal Pradesh',
            'Jammu & Kashmir', 'Karnataka', 'Kerala', 'Maharashtra', 'Manipur', 'Nagaland',
            'Odisha', 'Parsi', 'Punjab', 'Rajasthan', 'Sindhi', 'Tamil Nadu', 'Telangana',
            'Uttar Pradesh', 'Uttarakhand', 'West Bengal'}
FIELDS = ['record_completeness', 'end_state_stated', 'is_intermediate',
          'title_method_mismatch', 'garbled', 'coarse_stratum', 'dup_cluster_id']
DOMAINS = {'record_completeness': ['sufficient', 'partial', 'unusable', 'unknown'],
           'end_state_stated': ['yes', 'no', 'unknown'], 'is_intermediate': ['yes', 'no', 'unknown'],
           'title_method_mismatch': ['suspected', 'not_detected', 'unknown'],
           'garbled': ['suspected', 'not_detected', 'unknown'],
           'coarse_stratum': ['coarse', 'specific', 'unknown']}
EXTRA_FIELDS = {'audit_record_completeness', 'audit_end_state_stated', 'audit_is_intermediate',
                'audit_liquid_fate_unstated', 'liquid_fate_unstated', 'over_desk_cut',
                'instruction_language_supported', 'source_instruction_available',
                'has_instructions_mismatch', 'region_stratum', 'region_level',
                'cuisine_generic_or_missing'}
CONFIG = {
    'version': RULE_VERSION, 'status': 'provisional_not_independently_validated',
    'supported_method_language': ['en'], 'terminal_window_characters': 600,
    'placeholder_pattern': r'^(?:n/?a|none|null|not available|coming soon|see (?:above|below)|instructions?)(?:[.! ]*)$',
    'action_pattern': r'\b(?:add|mix|stir|cook|bake|boil|fry|roast|steam|blend|knead|simmer|chop|heat|combine)\b',
    'finish_pattern': r'\b(?:serve|enjoy|ready|cool|refrigerate|store)\b',
    'state_pattern': r'\b(?:crispy|crisp|crunchy|liquid|solid|thick|thin|smooth|dry|soft|firm|runny|pourable|golden brown)\b',
    'intermediate_pattern': r'\b(?:use|used|reserve|reserved|store|stored)\b.{0,55}\b(?:as (?:a |the )?|for (?:the )?)(?:filling|paste|dough|batter|base)\b',
    'dish_words': ['salad', 'soup', 'idli', 'dosa', 'cake', 'dough', 'batter', 'paste'],
    'coarse_regions': sorted(COARSE), 'specific_regions': sorted(SPECIFIC),
    'ingredient_signature_min_items': 3,
    'duplicate_policy': 'candidate components: legacy family, normalized title, or identical normalized ingredient list; never confirmed equivalence',
}


def normalize(value: str) -> str:
    return ' '.join(unicodedata.normalize('NFKC', value).casefold().split())


def text(value) -> str:
    if value is None or (isinstance(value, float) and value != value):
        return ''
    return str(value).strip()


def items(value) -> list[str]:
    if isinstance(value, (list, tuple)):
        return [text(x) for x in value if text(x)]
    raw = text(value)
    if not raw:
        return []
    if raw[:1] in '[(':
        try:
            parsed = ast.literal_eval(raw)
        except (ValueError, SyntaxError, MemoryError, RecursionError):
            return [raw]
        if isinstance(parsed, (list, tuple)):
            return [text(x) for x in parsed if text(x)]
    return [raw]


def observe(row: dict, instruction: str | None, source_available: bool, config: dict = CONFIG) -> dict:
    """Each output is a closed enum/reason. UNKNOWN never means defect-free."""
    out = {}
    def set_field(field, value, reason):
        out[field] = value
        out[field + '_reason'] = reason
    title = text(row.get('Title_normalized'))
    ingredients = items(row.get('IngredientsList'))
    method = '\n'.join(items(instruction)) if source_available else ''
    lang = text(row.get('Lang_base'))
    region = text(row.get('Region'))
    set_field('coarse_stratum', 'coarse' if region in config['coarse_regions'] else
              'specific' if region in config['specific_regions'] else 'unknown',
              'taxonomy_match' if region in config['coarse_regions'] + config['specific_regions'] else 'taxonomy_unmapped')
    visible = '\n'.join([title, *ingredients, method])
    corrupt = '\ufffd' in visible or any(unicodedata.category(c) == 'Cc' and c not in '\n\r\t' for c in visible)
    set_field('garbled', 'suspected' if corrupt else 'not_detected' if visible else 'unknown',
              'encoding_or_control_artifact' if corrupt else 'no_encoding_artifact_detected' if visible else 'input_unavailable')
    for field in ['record_completeness', 'end_state_stated', 'is_intermediate', 'title_method_mismatch']:
        set_field(field, 'unknown', 'input_unavailable' if not source_available else 'input_missing_in_source')
    # Existing observed suspicion is retained as legacy evidence, not a new adjudication.
    legacy_mismatch = text(row.get('title_unsupported_by_body')).casefold() in {'true', '1', '1.0'}
    if legacy_mismatch:
        set_field('title_method_mismatch', 'suspected', 'legacy_body_support_flag')
    if not source_available:
        return out
    if not method:
        set_field('record_completeness', 'partial' if ingredients else 'unusable', 'input_missing_in_source')
        return out
    if lang not in config['supported_method_language']:
        for field in ['record_completeness', 'end_state_stated', 'is_intermediate']:
            set_field(field, 'unknown', 'language_not_supported')
        if not legacy_mismatch:
            set_field('title_method_mismatch', 'unknown', 'language_not_supported')
        return out
    lower = normalize(method)
    if re.fullmatch(config['placeholder_pattern'], lower):
        set_field('record_completeness', 'partial' if ingredients else 'unusable', 'placeholder_method')
        return out
    if ingredients and normalize(' '.join(ingredients)) == normalize(' '.join(items(instruction))):
        set_field('record_completeness', 'partial', 'ingredient_list_as_method')
        return out
    action = bool(re.search(config['action_pattern'], lower))
    tail = lower[-config['terminal_window_characters']:]
    finish = bool(re.search(config['finish_pattern'], tail))
    truncated = lower.endswith(('...', '\u2026'))
    structural = bool(ingredients) and action and finish and not truncated
    set_field('record_completeness', 'sufficient' if structural else 'partial',
              'structural_action_and_finish' if structural else 'truncation_marker' if truncated else
              'ingredients_missing' if not ingredients else 'structural_evidence_incomplete')
    if truncated or not action or corrupt:
        reason = 'truncation_marker' if truncated else 'encoding_or_control_artifact' if corrupt else 'no_action_evidence'
        for field in ['end_state_stated', 'is_intermediate']:
            set_field(field, 'unknown', reason)
        return out
    stated = bool(re.search(config['state_pattern'], tail))
    set_field('end_state_stated', 'yes' if stated else 'no',
              'terminal_state_descriptor' if stated else 'no_terminal_state_descriptor')
    intermediate = bool(re.search(config['intermediate_pattern'], tail))
    served = bool(re.search(r'\b(?:serve|enjoy)\b', tail))
    set_field('is_intermediate', 'unknown' if intermediate and served else 'yes' if intermediate else 'no' if served else 'unknown',
              'conflicting_use_signals' if intermediate and served else 'explicit_intermediate_use' if intermediate else
              'explicit_serving_signal' if served else 'no_intended_use_evidence')
    if not legacy_mismatch:
        categories = [w for w in config['dish_words'] if re.search(r'\b' + re.escape(w) + r'\b', normalize(title))]
        final_categories = [w for w in config['dish_words'] if re.search(
            r'\b(?:your |the |this )?' + re.escape(w) + r'\s+is\s+(?:now\s+)?ready\b', tail)]
        if len(categories) == 1 and len(final_categories) == 1:
            same = categories == final_categories
            set_field('title_method_mismatch', 'not_detected' if same else 'suspected',
                      'explicit_dish_agreement' if same else 'explicit_dish_disagreement')
        else:
            set_field('title_method_mismatch', 'unknown', 'no_comparable_dish_assertion')
    return out


def observe_audit_aligned(row: dict, instruction: str | None, source_available: bool,
                         region_codes: dict, config: dict = CONFIG) -> dict:
    """Preserve exact audit observations and expose language-aware consumer summaries."""
    import quality_audit_patterns as patterns
    import quality_audit_rules as audit
    out = observe(row, instruction, source_available, config)
    try:
        parsed = json.loads(row.get('IngredientsList'))
    except (ValueError, TypeError):
        parsed = []
    ing = tuple(s.strip() for s in parsed if isinstance(s, str) and s.strip()) if isinstance(parsed, list) else ()
    raw = text(instruction) if source_available else ''
    supported = text(row.get('Lang_base')) == 'en'
    observation = audit.instruction_status(patterns, text(row.get('RecipeName')), ing, raw) if source_available else None
    tri = lambda x: 'unknown' if x is None else 'yes' if x else 'no'
    out.update(audit_record_completeness=observation['record_completeness'] if observation else 'UNASSESSED',
               audit_end_state_stated=tri(observation['end_state_stated']) if observation else 'unknown',
               audit_is_intermediate=tri(observation['is_intermediate']) if observation else 'unknown',
               audit_liquid_fate_unstated=tri(observation['liquid_fate_unstated']) if observation else 'unknown',
               liquid_fate_unstated=tri(observation['liquid_fate_unstated']) if observation and supported else 'unknown',
               over_desk_cut=observation['over_desk_cut'] if observation else False,
               instruction_language_supported=supported, source_instruction_available=source_available,
               has_instructions_mismatch=(bool(row.get('has_instructions')) != bool(raw)) if source_available else False,
               cuisine_generic_or_missing=text(row.get('Cuisine')).casefold() in {'', 'indian'})
    if observation and supported:
        complete = observation['record_completeness']
        out['record_completeness'] = 'sufficient' if complete == 'COMPLETE' else 'partial' if ing else 'unusable'
        out['record_completeness_reason'] = 'audit_' + complete.lower()
        for field in ['end_state_stated', 'is_intermediate']:
            out[field] = tri(observation[field])
            out[field + '_reason'] = 'audit_rule_observation' if observation[field] is not None else 'no_assessable_method'
    elif observation:
        for field in ['record_completeness', 'end_state_stated', 'is_intermediate']:
            out[field] = 'unknown'
            out[field + '_reason'] = 'language_not_supported'
    region = text(row.get('Region')) or '(missing)'
    if region not in region_codes:
        raise ValueError('Unmapped region code: ' + region)
    entry = region_codes[region]
    out['region_stratum'], out['region_level'] = entry['stratum'], entry['level']
    out['coarse_stratum'] = 'coarse' if entry['level'] == 'coarse' else 'unknown' if entry['stratum'] == 'unassigned' else 'specific'
    out['coarse_stratum_reason'] = 'frozen_region_taxonomy'
    return out


def candidate_clusters(rows: list[dict], config: dict = CONFIG) -> tuple[dict[int, str], dict]:
    """Linear-size signature indexing; candidate grouping never rewrites split labels."""
    ids = [int(r['recipe_id']) for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate recipe keys')
    parent = {i: i for i in ids}
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    def union(a, b):
        a, b = find(a), find(b)
        if a != b:
            parent[max(a, b)] = min(a, b)
    seen = {}
    links = {'legacy_family': 0, 'normalized_title': 0, 'ingredient_signature': 0}
    for r in sorted(rows, key=lambda x: int(x['recipe_id'])):
        i = int(r['recipe_id'])
        signatures = []
        family = text(r.get('dup_family_id'))
        if family:
            signatures.append(('legacy_family', str(int(float(family)))))
        title = normalize(text(r.get('Title_normalized')))
        if title:
            signatures.append(('normalized_title', title))
        ingredients = sorted(normalize(x) for x in items(r.get('IngredientsList')))
        if len(set(ingredients)) >= config['ingredient_signature_min_items']:
            signatures.append(('ingredient_signature', json.dumps(ingredients, ensure_ascii=False)))
        for kind, signature in signatures:
            key = (kind, signature)
            if key in seen:
                union(i, seen[key])
                links[kind] += 1
            else:
                seen[key] = i
    members = {}
    for i in sorted(ids):
        members.setdefault(find(i), []).append(i)
    result = {}
    for group in members.values():
        # A short fixed prefix plus a full digest; IDs encode membership, never text.
        cid = 'q1_' + hashlib.sha256(','.join(map(str, group)).encode()).hexdigest()
        result.update((i, cid) for i in group)
    return result, {'candidate_components': len(members), 'signature_links': links,
                    'not_confirmed_equivalence': True}
