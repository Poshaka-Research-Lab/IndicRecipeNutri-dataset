"""Unmodified proposal-rule logic extracted from the received K006 dataset audit.

Counts are unvalidated rule hits, not confirmed error rates or safety judgments.
See audit_rule_provenance.json. No dependency on the live K006 workspace.
"""
import hashlib
import json
import re

import allergen_taxonomy as _AT
_NOT_DAIRY = r'(?<!coconut\s)(?<!almond\s)(?<!soy\s)(?<!soya\s)(?<!oat\s)(?<!cashew\s)(?<!rice\s)(?<!peanut\s)'

IMPLICIT = {
    'milk': r'\b(?:paneer|khoya|khoa|mawa|dahi|curd|malai|chhena|chenna|ghee|makhan|makkhan|chaas|chaach|lassi|'
            r'rabri|rabdi|shrikhand|' + _NOT_DAIRY + r'butter(?!\s*milk)|' + _NOT_DAIRY + r'cream(?!\s+of\s+tartar)|'
            r'buttermilk|cheese|yogh?urt|' + _NOT_DAIRY + r'milk(?!\s*powder\s*substitute))\b',
    'gluten': r'\b(?:maida|atta|sooji|suji|rava|rawa|semolina|dalia|daliya|wheat|seviyan|'
              r'pav|pasta|barley|jau)\b',
    'peanut': r'\b(?:peanuts?|groundnuts?|moongphali|mungfali|moongfali|shengdana|shenga|kadalai|verkadalai|'
              r'nilakadalai)\b',
    'sesame': r'\b(?:sesame|til|gingelly|tahini|ellu|nuvvulu)\b',
    'tree_nuts': r'\b(?:kaju|cashews?|badam|almonds?|pista|pistachios?|akhrot|walnuts?|chironji|charoli|'
                 r'hazelnuts?|pecans?)\b',
    'soy': r'\b(?:soy|soya|tofu|edamame|tempeh|miso)\b',
    'mustard': r'\b(?:mustard|sarson|sarsoon|rai|kadugu|avalu|sorshe|shorshe)\b',
    'fenugreek': r'\b(?:fenugreek|methi|vendhayam|menthulu)\b',
    'asafoetida': r'\b(?:asafoetida|asafetida|hing|heeng|perungayam|inguva)\b',
    'tamarind': r'\b(?:tamarind|imli|puli|chintapandu)\b',
    'coconut': r'\b(?:coconut|nariyal|narial|copra|khopra|kopra|thengai|thenga|kobbari)\b',
    'egg': r'\b(?:eggs?|anda|ande|mayonnaise|mayo)\b',
}

_UNSPEC_OIL = (r'\b(?:(?:refined|vegetable|cooking|salad|any|neutral|flavou?rless|white)\s+oil|oil)\b')

_OIL_NAMED = (r'\b(?:olive|mustard|sarson|coconut|sesame|til|gingelly|groundnut|peanut|sunflower|canola|rapeseed|'
              r'rice\s*bran|soy|soya|corn|avocado|ghee|palm|cottonseed|almond)\b')

AMBIGUOUS = {
    'peanut': [('unspecified_oil', _UNSPEC_OIL, _OIL_NAMED),
               ('podi_or_mixture', r'\b(?:podi|chutney\s+powder|gun\s*powder|namkeen|mixture|chikki)\b', None)],
    'soy': [('unspecified_oil', _UNSPEC_OIL, _OIL_NAMED),
            ('unspecified_sauce_or_seasoning', r'\b(?:sauce|seasoning|stock\s+cubes?|bouillon|maggi\s+masala)\b',
             r'\b(?:soy|soya|tomato|white|cheese|chocolate|caramel|apple|mint|curd)\s+sauce\b'),
            ('bread_or_biscuit', r'\b(?:bread|biscuits?|cookies?|rusk|bun)\b', None)],
    'sesame': [('unspecified_oil', _UNSPEC_OIL, _OIL_NAMED),
               ('podi_or_masala_blend', r'\b(?:podi|chutney\s+powder|gun\s*powder|masala\s+powder|spice\s+mix)\b',
                None)],
    'gluten': [('unspecified_flour_or_blend', r'\b(?:flour|ready\s*mix|batter\s+mix|hing|asafoetida|bread|bun|noodles?|'
                                              r'vermicelli|sevai|biscuits?)\b',
                r'\b(?:rice|gram|besan|corn|maize|ragi|jowar|bajra|millet|almond|coconut|tapioca|potato|'
                r'buckwheat|kuttu|singhara|rajgira|amaranth|chickpea|urad|moong)\s+flour\b')],
    'milk': [('unspecified_fat_or_blend', r'\b(?:shortening|margarine|chocolate|biscuits?|ice\s*cream)\b', None)],
}

# gate_m27 M27.1b guard (added 2026-10-04; the rule tables above are unchanged). IMPLICIT is a
# subset of the declared classes by design, so the check is subset, not equality.
_bad = sorted(set(IMPLICIT) - set(_AT.TOKENS))
assert not _bad, f"IMPLICIT names undeclared allergen token(s): {_bad}"
del _bad

def _rx(p):
    return re.compile(p, re.I)

IMPLICIT_RX = {k: _rx(v) for k, v in IMPLICIT.items()}

AMBIG_RX = {k: [(n, _rx(p), _rx(x) if x else None) for n, p, x in v] for k, v in AMBIGUOUS.items()}

def lexicon_sha256():
    body = json.dumps({'implicit': IMPLICIT, 'ambiguous': AMBIGUOUS}, sort_keys=True).encode('utf-8')
    return hashlib.sha256(body).hexdigest()

def ambiguous_hits(cls, items):
    out = set()
    for name, rx, excl in AMBIG_RX.get(cls, ()):
        for s in items:
            if rx.search(s) and not (excl and excl.search(s)):
                out.add(name)
                break
    return out

def instruction_status(V, title, items, raw):
    """State-independent 0.12.0 flag proposal built from the frozen v109.12 patterns (the full text, no desk cut).
    -> dict(record_completeness, end_state_stated, is_intermediate, liquid_fate_unstated, over_desk_cut)."""
    text = raw.strip() if isinstance(raw, str) else ''
    title = title if isinstance(title, str) else ''
    ing = ' ; '.join(items or ())
    rx = V._RX
    out = {'over_desk_cut': len(text) > V.DESK_MAX_INSTR, 'is_intermediate': False, 'end_state_stated': None,
           'liquid_fate_unstated': None}
    if rx['INTERMEDIATE_TITLE'].search(title):
        out['is_intermediate'] = True
    if not text:
        out['record_completeness'] = 'MISSING'
        return out
    if len(text) < V.PLACEHOLDER_MIN_CHARS or (len(text) <= V.PLACEHOLDER_MAX_CHARS
                                               and rx['PLACEHOLDER'].search(text)):
        out['record_completeness'] = 'PLACEHOLDER'
        return out
    if not rx['METHOD_VERBS'].search(text):
        out['record_completeness'] = 'NOT_A_METHOD'
        return out
    out['record_completeness'] = 'TRUNCATED' if V.truncated(text, False, title) else 'COMPLETE'
    if rx['INTERMEDIATE_USE'].search(V.tail(text)):
        out['is_intermediate'] = True
    out['end_state_stated'] = bool(rx['FINISH'].search(V.later_half(text)))
    liq = rx['LIQUID_ADDED'].search(ing) or V._added_liquid(text)
    out['liquid_fate_unstated'] = bool(liq) and not rx['CONSISTENCY'].search(text) and not rx['SOLIDIFY'].search(text)
    return out
