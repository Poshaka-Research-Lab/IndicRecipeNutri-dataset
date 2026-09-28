"""Reproduce proposal-rule aggregate counts on the audit DEV frame, with no raw-text output."""
import argparse
from collections import Counter
import json
from pathlib import Path

import pandas as pd

from audit_quality_inputs import sha256
from build_quality_flags import load_rows, atomic_json
import quality_audit_patterns as patterns
import quality_audit_rules as rules


def parse_items(raw):
    try:
        parsed = json.loads(raw)
    except (ValueError, TypeError):
        return ()
    return tuple(s.strip() for s in parsed if isinstance(s, str) and s.strip()) if isinstance(parsed, list) else ()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ['root', 'source-workspace', 'input-manifest', 'audit-stats', 'heldout-ids', 'output']:
        ap.add_argument('--' + name, required=True, type=Path)
    args = ap.parse_args()
    manifest = json.loads(args.input_manifest.read_text(encoding='utf-8'))
    reference = json.loads(args.audit_stats.read_text(encoding='utf-8'))
    frame, instructions, source = load_rows(args.root, args.source_workspace, manifest)
    excluded = {int(x) for x in args.heldout_ids.read_text().split()}
    frame = frame.loc[~frame.recipe_id.isin(excluded)]
    if len(frame) != reference['n_dev']:
        raise ValueError('DEV population mismatch')
    # The source audit used RecipeName, not Title_normalized; preserve that choice.
    names = pd.read_parquet(args.root / 'data/corpus/recipes_structured.parquet', columns=['recipe_id', 'RecipeName'])
    name_of = dict(zip(names.recipe_id, names.RecipeName.fillna('')))
    labels_path = args.root / 'data/corpus/allergens.parquet'
    expected = next(x['expected'] for x in manifest['checksum_files'] if x['path'] == 'data/corpus/allergens.parquet')
    if sha256(labels_path) != expected:
        raise ValueError('Allergen input digest mismatch')
    allergens = pd.read_parquet(labels_path)
    statuses = {(int(i), c): s for i, c, s in allergens[['recipe_id', 'allergen', 'status']].itertuples(index=False, name=None)
                if int(i) not in excluded and c in rules.IMPLICIT}
    tally = Counter()
    carrier = {c: Counter() for c in rules.IMPLICIT}
    for row in frame.to_dict(orient='records'):
        rid = int(row['recipe_id'])
        ing = parse_items(row['IngredientsList'])
        state = rules.instruction_status(patterns, name_of[rid], ing, instructions[rid])
        tally['n'] += 1
        tally['record_completeness=' + state['record_completeness']] += 1
        tally['incomplete'] += state['record_completeness'] != 'COMPLETE'
        tally['end_state_unstated'] += state['end_state_stated'] is False
        tally['is_intermediate'] += state['is_intermediate']
        tally['liquid_fate_unstated'] += state['liquid_fate_unstated'] is True
        tally['over_desk_cut'] += state['over_desk_cut']
        tally['any_text_insufficiency'] += state['record_completeness'] != 'COMPLETE' or state['end_state_stated'] is False or state['is_intermediate']
        low = [s.lower() for s in ing]
        for c, counts in carrier.items():
            implicit = any(rules.IMPLICIT_RX[c].search(s) for s in low)
            absent = statuses.get((rid, c)) == 'absent'
            ambiguous = bool(rules.ambiguous_hits(c, low)) and not implicit
            counts['implicit_hit_and_silver_absent'] += implicit and absent
            counts['ambiguous_only_and_silver_absent'] += ambiguous and absent
    mismatches = []
    for name, value in tally.items():
        expected = reference['instructions']['tally']['overall'].get(name, 0)
        if value != expected:
            mismatches.append({'metric': name, 'actual': value, 'expected': expected})
    for cls, counts in carrier.items():
        for name, value in counts.items():
            expected = reference['allergen_text']['by_class_dev'][cls].get(name, 0)
            if value != expected:
                mismatches.append({'metric': cls + '/' + name, 'actual': value, 'expected': expected})
    result = {'status': 'passed' if not mismatches else 'failed', 'population': 'DEV',
              'heldout_ids_sha256': sha256(args.heldout_ids), 'audit_stats_sha256': sha256(args.audit_stats),
              'gate_spec_sha256': patterns.gate_spec_sha256(), 'lexicon_sha256': rules.lexicon_sha256(),
              'instruction_counts': dict(tally), 'allergen_counts': carrier,
              'mismatches': mismatches, 'source': source,
              'scope': 'instruction proposal and carrier-lexicon counts only; not classifier correctness or K006 output reproduction'}
    atomic_json(result, args.output)
    print(json.dumps({k: result[k] for k in ['status', 'instruction_counts', 'mismatches']}))
    return bool(mismatches)


if __name__ == '__main__':
    raise SystemExit(main())
