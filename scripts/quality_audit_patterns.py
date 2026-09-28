"""Vendored audit-pattern dependency, extracted without modifying frozen K006 code.

This is NOT the frozen K006 classifier: only its pattern spec and text helpers.
Source hashes and extraction boundaries are in audit_rule_provenance.json.
"""
import hashlib
import json
import re
SOLID, SEMISOLID, MIXED = 'solid', 'semisolid', 'mixed'
GATE_VERSION = 'k006-110/evidence-sufficiency-gate/1.0.0'

BASE_ENTRY = 'physical_state.classify_full'

DESK_MAX_INSTR = 6000

DESK_TRUNC_MARKER = ' [... truncated]'

TAIL_SENTENCES = 3

_I = re.I

METHOD_VERBS = (r'\b(?:heat|add|mix|stir|cook|boil|fry|fries|bake|pour|take|grind|knead|roll|serve|combine|place|'
                r'blend|whisk|soak|saut[eé]|simmer|steam|toss|spread|cut|chop|slice|marinate|preheat|transfer|'
                r'keep|remove|drain|cover|sprinkle|garnish|arrange|fold|beat|microwave|grill|roast|toast|temper|'
                r'splutter|press|shape|divide|dip|coat|fill|layer|refrigerate|chill|freeze|melt|whip|squeeze|peel|'
                r'wash|rinse|strain|sieve|season|bring|put|make|prepare|let|allow|set|pressure|grate|dissolve|'
                r'caramel[i]?[sz]e|brush|flip|turn|wrap|assemble|scoop|pulse|puree|mash|reduce|thicken|stuff)'
                r'(?:s|es|ing)?\b')

SOLID_PROCESS = (r'\b(?:deep[\s-]*fr(?:y|ied|ying)|shallow[\s-]*fr(?:y|ied|ying)|fr(?:y|ied|ies|ying)|'
                 r'bak(?:e|ed|es|ing)(?!\s+(?:powder|soda))|roast(?:ed|ing)?|grill(?:ed|ing)?|toast(?:ed|ing)?|'
                 r'steam(?:ed|ing)?|crisp(?:y|ness)?|crunchy|knead(?:ed|ing)?|roll(?:ed)?\s+out|'
                 r'set(?:s|ting)?(?!\s+(?:it\s+|them\s+|this\s+)?aside)|sun[\s-]*dr(?:y|ied)|air[\s-]*fr(?:y|ied|yer)|'
                 r'cut\s+(?:it\s+|them\s+|the\s+\w+\s+)?into|brown(?:ed)?|golden|(?:flip|turn)\w*\s+(?:it\s+|them\s+)?'
                 r'(?:over|both\s+sides|to\s+the\s+other\s+side))\b')

SEMISOLID_PROCESS = r'\b(?:thick(?:en(?:s|ed|ing)?|ly|er)?|mash(?:ed|ing)?|creamy|spreadable|porridge)\b'

MIXED_PROCESS = r'\b(?:gravy|gravies|curry\s+consistency|sauce\s+consistency)\b'

LIQUID_PROCESS = (r'\b(?:drink|drinks|sip|glass|glasses|strain(?:ed|ing)?|pour\s+(?:it\s+|them\s+)?into\s+'
                  r'(?:serving\s+)?(?:glasses|cups|bowls)|thin(?:ner)?|watery|runny|soup|broth|rasam|over\s+ice)\b')

PLACEHOLDER = (r'(?:\b(?:watch|see)\s+(?:the\s+)?video\b|\bclick\s+(?:here|on)\b|\brecipe\s+card\b|\bcoming\s+soon\b|'
               r'^\s*(?:n\s*/?\s*a|na|none|null|nil|tbd|-+|\.+)\s*$|\bfull\s+recipe\s+(?:at|on|here)\b)')

PLACEHOLDER_MIN_CHARS = 25

PLACEHOLDER_MAX_CHARS = 200

TRUNC_END_CHARS = ',;:-–—(&/+'

TRUNC_END_WORDS = ('and', 'or', 'the', 'a', 'an', 'to', 'with', 'of', 'in', 'on', 'for', 'till', 'until', 'then',
                   'add', 'is', 'into', 'at', 'by', 'as', 'from', 'some', 'your', 'but')

TERMINAL = '.!?)"\'’”'

TRUNC_PUNCT_SHARE = 0.75

TITLE_ECHO_SHARE = 0.6

LIST_ITEM = r'^\(?\d{1,2}[).:]\s'

FOOTER = (r'\b(?:calories|kcal|nutrition|per\s+serving|protein|carbohydrates?|blogging|marathon|subscribe|follow|'
          r'share|print|pin\s+it|notes?|tips?|variations?|video|https?|www|facebook|twitter|instagram|labels?|'
          r'categor\w*|cookbook|pix)\b')

INTERMEDIATE_TITLE = (r'^(?:(?!\bwith\b|\bstuffed\b).)*\b(?:filling|fillings|stuffing|puff\s+pastry|pastry\s+'
                      r'(?:dough|sheets?)|pie\s+crust|shortcrust|frosting|icing|glaze|marinade)\b|'
                      r'^\s*(?:how\s+to\s+(?:cook|boil)\s+|boiled\s+(?:[\w-]+\s+){0,2}?(?:noodles|sevai|pasta|'
                      r'spaghetti|macaroni|potato(?:es)?|chickpeas|chana|beans|rajma)\b)')

INTERMEDIATE_USE = (r'(?:\buse\s+the\s+(?:[\w-]+\s+){0,4}?(?:as|when)\s+(?:and\s+when\s+)?'
                    r'(?:required|needed|necessary)\b|\bfry\s+(?:it|them)\s+when\b|\bwhen(?:ever)?\s+(?:you|we)\s+'
                    r'(?:require|need)\s+(?:it|them)\b|\bbefore\s+(?:filling|stuffing)\b|\bto\s+(?:fill|stuff)\s+'
                    r'the\b|\bcan\s+be\s+used\s+(?:to|for|in|as)\b|\buse\s+(?:it|this|them|these)\s+(?:to\s+make|in|'
                    r'for\s+making)\b|\bto\s+make\s+other\b)')

FINISH = (r'\b(?:serv(?:e|ed|es|ing)|ready|enjoy(?:ed)?|relish|done|garnish(?:ed|ing)?|store(?:d)?\s+(?:in|it|them)|'
          r'transfer(?:red)?\s+(?:it\s+|them\s+)?(?:to|into|onto)\s+(?:a\s+|the\s+)?(?:serving|plate|bowl|dish|'
          r'container|tray|platter)|cut\s+(?:it\s+|them\s+)?into|(?:is|are|until|till|let\s+it|to)\s+set\b|'
          r'bak(?:e|ed|es|ing)(?!\s+(?:powder|soda))|fry\s+(?:it\s+|them\s+|the\s+\w+\s+)?(?:until|till|on\s+both)|'
          r'(?:until|till)\s+(?:it\s+|they\s+)?(?:turns?\s+|becomes?\s+|is\s+|are\s+)?(?:golden|crisp|brown|'
          r'crunchy|firm|set|thick|dry|absorbed|done|cooked\s+through)|absorbed|evaporated|eat|savou?r|sip|'
          r'pour\s+(?:it\s+|them\s+)?into\s+(?:serving\s+)?(?:glasses|cups|bowls)|steam\s+(?:it\s+|them\s+)?for|'
          r'cool\s+completely|dust(?:ed)?\s+with|drizzle(?:d)?|sprinkle|top\s+(?:it\s+|them\s+)?with|'
          r'plate\s+(?:it|them|up)|arrange\w*|crisp(?:y)?|crunchy|brown(?:ed)?\s+(?:well|on\s+both)|'
          r'(?:make|shape|roll|form)\s+(?:it\s+|them\s+|the\s+\w+\s+)?(?:into\s+)?(?:[\w-]+\s+){0,2}?'
          r'(?:balls|ladoos?|laddus?|rolls|pancakes|patties|tikkis|discs|cutlets|squares|pieces|logs))\b')

LIQUID_ADDED = (r'\b(?<!rose\s)(?:water(?!\s*chestnut)|broth|stock|milk(?!\s*(?:powder|solids|maid))|buttermilk|'
                r'tamarind\s+extract|dashi)\b')

ADD_LIQUID = (r'\b(?:add|adding|added|pour|pouring|with)\s+(?:in\s+)?(?:[\w/.½¼¾-]+\s+){0,4}?'
              r'(?<!rose\s)(?:water(?!\s*chestnut)|broth|stock|milk(?!\s*(?:powder|solids|maid))|buttermilk)\b')

LIQUID_NEGATORS = r"\b(?:no|not|never|without|don'?t|do\s+not|avoid|skip)\b[^.]{0,25}$"

CONSISTENCY = (r'\b(?:thick\w*|thin\w*|reduc\w*|evaporat\w*|absorb\w*|dry|dries|dried|gravy|gravies|consistency|'
               r'semi[\s-]*dry|runny|watery|soupy|moisture|no\s+water|without\s+water|fluff\w*|comes?\s+together|'
               r'forms?\s+a\s+(?:ball|mass|lump)|leaves?\s+the\s+(?:sides?|pan)|'
               r'(?:drain|strain|squeeze)\w*\s+(?:out\s+|off\s+)?(?:the\s+|all\s+|any\s+)?(?:excess\s+|extra\s+)?'
               r'(?:water|liquid|stock|milk)|(?:till|until)\s+the\s+(?:water|liquid|milk)|dough|batter)\b')

SOLIDIFY = (r'\b(?:bak(?:e|ed|es|ing)(?!\s+(?:powder|soda))|oven|deep[\s-]*fr(?:y|ied|ying)|shallow[\s-]*fr(?:y|ied|'
            r'ying)|fry\s+(?:it\s+|them\s+|the\s+\w+\s+)?(?:until|till|on\s+both)|knead\w*|roll(?:ed)?\s+(?:it\s+|'
            r'them\s+)?out|dough|steam(?:er|ed|ing)?|idli|griddle|tawa|tava|pan\s*cakes?|grill\w*|air[\s-]*fr\w*|'
            r'shape\w*|mou?ld\w*|refrigerate\s+(?:until|till|for)|freez\w*|cut\s+(?:it\s+|them\s+)?into|(?:until|'
            r'till|let\s+it|to)\s+set\b)')

_SENT_SPLIT = re.compile(r'(?<=[.!?])\s+|\s*[\n|]+\s*')

GATE_SPEC = {'METHOD_VERBS': METHOD_VERBS, 'SOLID_PROCESS': SOLID_PROCESS, 'SEMISOLID_PROCESS': SEMISOLID_PROCESS,
             'MIXED_PROCESS': MIXED_PROCESS, 'LIQUID_PROCESS': LIQUID_PROCESS, 'PLACEHOLDER': PLACEHOLDER,
             'PLACEHOLDER_MIN_CHARS': PLACEHOLDER_MIN_CHARS, 'TRUNC_END_CHARS': TRUNC_END_CHARS,
             'TRUNC_END_WORDS': list(TRUNC_END_WORDS), 'INTERMEDIATE_TITLE': INTERMEDIATE_TITLE,
             'INTERMEDIATE_USE': INTERMEDIATE_USE, 'FINISH': FINISH, 'LIQUID_ADDED': LIQUID_ADDED,
             'CONSISTENCY': CONSISTENCY, 'SOLIDIFY': SOLIDIFY, 'TAIL_SENTENCES': TAIL_SENTENCES,
             'DESK_MAX_INSTR': DESK_MAX_INSTR, 'DESK_TRUNC_MARKER': DESK_TRUNC_MARKER, 'TERMINAL': TERMINAL,
             'TRUNC_PUNCT_SHARE': TRUNC_PUNCT_SHARE,
             'TITLE_ECHO_SHARE': TITLE_ECHO_SHARE, 'LIST_ITEM': LIST_ITEM, 'FOOTER': FOOTER,
             'PLACEHOLDER_MAX_CHARS': PLACEHOLDER_MAX_CHARS, 'LIQUID_NEGATORS': LIQUID_NEGATORS,
             'FINISH_SCOPE': 'later half of the sentences, at least TAIL_SENTENCES', 'ADD_LIQUID': ADD_LIQUID,
             'intermediate_use_scope': 'last TAIL_SENTENCES sentences',
             'order': ['G12-NO-INSTR', 'G12-PLACEHOLDER', 'G12-NOT-A-METHOD', 'G12-TRUNCATED', 'G12-INTERMEDIATE',
                       'G12-COURSE-ONLY', 'G12-END-UNSTATED', 'G12-LIQUID-UNREDUCED'],
             'dgi_exempt_rule': 'LEX-DGI-FN2', 'liquid_unreduced_states': [SOLID, SEMISOLID, MIXED]}

def gate_spec_sha256():
    body = json.dumps(GATE_SPEC, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(body.encode('utf-8')).hexdigest()

_RX = {k: re.compile(GATE_SPEC[k], _I) for k in (
    'METHOD_VERBS', 'SOLID_PROCESS', 'SEMISOLID_PROCESS', 'MIXED_PROCESS', 'LIQUID_PROCESS', 'PLACEHOLDER',
    'INTERMEDIATE_TITLE', 'INTERMEDIATE_USE', 'FINISH', 'LIQUID_ADDED', 'ADD_LIQUID', 'CONSISTENCY', 'SOLIDIFY',
    'FOOTER')}

def sentences(text):
    return [s.strip() for s in _SENT_SPLIT.split(text or '') if s and s.strip()]

def tail(text, n=TAIL_SENTENCES):
    return ' '.join(sentences(text)[-n:])

def later_half(text, n_min=TAIL_SENTENCES):
    """The last half of the sentences, and never fewer than ``n_min`` (FINISH_SCOPE)."""
    parts = sentences(text)
    k = max(n_min, (len(parts) + 1) // 2)
    return ' '.join(parts[-k:])

def truncated(text, cut_by_desk=False, title=''):
    """-> reason string or None."""
    if cut_by_desk or text.endswith(DESK_TRUNC_MARKER.strip()):
        return 'desk truncation marker'
    s = text.rstrip()
    if not s:
        return None
    if s[-1] in TRUNC_END_CHARS:
        return 'ends on %r' % s[-1]
    words = re.findall(r'[A-Za-z]+', s[-40:])
    if words and s[-1].isalpha() and words[-1].lower() in TRUNC_END_WORDS:
        return 'ends on the word %r' % words[-1]
    # the last segment is unpunctuated while the method otherwise punctuates its sentences ("... Give it a boil and
    # Thai Red"): cut off mid-sentence
    # Not when the last fragment states a finish, is a list item ("3) Adds ..."), or echoes the title.
    parts = sentences(s)
    if s[-1].isalnum() and len(parts) >= 3:
        prev, last = parts[:-1], parts[-1]
        tt = set(re.findall(r'[a-z]+', (title or '').lower()))
        lt = re.findall(r'[a-z]+', last.lower())
        echo = bool(lt) and sum(1 for w in lt if w in tt) >= TITLE_ECHO_SHARE * len(lt)
        if (sum(1 for x in prev if x.rstrip()[-1:] in TERMINAL) >= TRUNC_PUNCT_SHARE * len(prev)
                and not _RX['FINISH'].search(last) and not re.match(LIST_ITEM, last) and not echo
                and not _RX['FOOTER'].search(last)):
            return 'last sentence unpunctuated in a punctuated method'
    return None

def _added_liquid(text):
    """The first non-negated 'add ... water / milk / broth' in the method, or None."""
    for m in _RX['ADD_LIQUID'].finditer(text or ''):
        if not re.search(LIQUID_NEGATORS, text[max(0, m.start() - 30):m.start()], _I):
            return m.group(0)
    return None
