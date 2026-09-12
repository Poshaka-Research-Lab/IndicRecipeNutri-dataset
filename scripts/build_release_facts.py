"""Generate current release facts and datasheet from the actual payload; --check is read-only."""
from pathlib import Path
import argparse
import hashlib
import json
import re
from collections import Counter
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def collect(root):
    paths = ['data/corpus/recipes_structured.parquet', 'data/kg/kg_nodes.parquet', 'data/kg/kg_edges.parquet',
             'data/kg/kg_edge_evidence.parquet']
    corpus = pd.read_parquet(root / paths[0], columns=['recipe_id', 'Split_v3', 'Region', 'Lang_base', 'SourceSite', 'per100g_kcal', 'Servings_num'])
    nodes = pd.read_parquet(root / paths[1], columns=['type', 'pubchem_id'])
    edges = pd.read_parquet(root / paths[2], columns=['rel'])
    allergens = pd.read_parquet(root / 'data/corpus/allergens.parquet', columns=['recipe_id', 'allergen', 'status'])
    queries = [json.loads(line) for line in (root / 'data/benchmark/eval_queries.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    return {
        'schema_version': 1, 'scope': 'local release payload', 'canonical_split': 'Split_v3',
        'recipes': len(corpus), 'columns': len(pq.read_schema(root / paths[0])),
        'source_sites': int(corpus.SourceSite.nunique()),
        'split_counts': {k: int(v) for k, v in corpus.Split_v3.value_counts().sort_index().items()},
        'nodes': len(nodes), 'edges': len(edges),
        'edge_evidence_rows': pq.read_metadata(root / paths[3]).num_rows,
        'node_types': {k: int(v) for k, v in nodes.type.value_counts().sort_index().items()},
        'relations': {k: int(v) for k, v in edges.rel.value_counts().sort_index().items()},
        'benchmark_queries': len(queries),
        'benchmark_templates': dict(sorted(Counter(q['template'] for q in queries).items())),
        'allergen_counts': {k: int(v) for k, v in allergens.loc[allergens.status.eq('present'), 'allergen'].value_counts().sort_index().items()},
        'pan_indian': int(corpus.Region.eq('Pan-Indian').sum()),
        'english': int(corpus.Lang_base.eq('en').sum()),
        'missing_language': int(corpus.Lang_base.isna().sum()),
        'missing_servings': int(corpus.Servings_num.isna().sum()),
        'missing_per100g_energy': int(corpus.per100g_kcal.isna().sum()),
        'unassessed_allergen_recipes': int(allergens.loc[allergens.status.eq('unassessed'), 'recipe_id'].nunique()),
        'input_sha256': {p: digest(root / p) for p in paths},
    }


def render(f):
    split_rows = '\n'.join(f'| {k} | {v:,} |' for k, v in f['split_counts'].items())
    return f'''# Datasheet — IndicRecipeNutri

Generated from the local payload by `scripts/build_release_facts.py`.
Exact source hashes and current counts are in `data/provenance/release_facts.json`.
Historical assessments are preserved in [the archived datasheet](history/DATASHEET_pre_2026-09-12.md),
not presented as current measurements. Its detailed audit history remains available.

## Purpose and composition

IndicRecipeNutri supports research on recipe retrieval, nutrition estimates and cultural context.
Each record represents a recipe. Structured ingredients and attributes are published;
original instructions, headnotes and other withheld prose are not redistributed.

| Current payload | Count |
|---|---:|
| Recipes | {f['recipes']:,} |
| Wide-view columns | {f['columns']:,} |
| Source sites | {f['source_sites']:,} |
| Graph nodes | {f['nodes']:,} |
| Graph triples | {f['edges']:,} |
| Edge evidence rows | {f['edge_evidence_rows']:,} |
| Ingredient nodes | {f['node_types']['ingredient']:,} |
| Compound nodes | {f['node_types']['compound']:,} |
| Node types / relation types | {len(f['node_types'])} / {len(f['relations'])} |
| Benchmark queries | {f['benchmark_queries']} |

Use `recipe_id` for joins. The wide recipe table is a compatibility view; normalized
recipe, nutrition, labels, quality and allergen tables also ship. Historical columns
must not be mistaken for current labels. See `DATA_DICTIONARY.md` and `PROVENANCE.md`.

## Evaluation split

Use **Split_v3**, described in `SPLIT_PROTOCOL_v3.md`. It groups connected components
of case-folded normalized titles and duplicate families. Legacy splits remain for
historical reproducibility and must not be used implicitly in new evaluation.

| Partition | Recipes |
|---|---:|
{split_rows}

The release verifier checks graph/corpus split parity by ID and both group constraints.
These checks do not establish the absence of all possible semantic near-duplicates.
The {f['benchmark_queries']} benchmark queries use graph-derived silver labels, not human relevance judgments.
Synthetic interactions are simulated behaviour, not observations of real users.
`data/interactions/` is regenerated from the published corpus, so every recipe it references
is live in this release. `verify_release.py` checks that, the id maps, both splits, and that
no user with a dietary restriction is served an incompatible or undeclared recipe.

## Representation

Pan-Indian accounts for {f['pan_indian']:,} recipes and primarily denotes an unassigned
regional label, not an independently sampled geographic population. Region mixes
states, broad areas and cultural communities. English accounts for {f['english']:,}
recipes; {f['missing_language']:,} language values are missing. Use `Lang_base` for primary
language filtering, with appropriate validation. Source and regional sampling are uneven.
Recipe frequency is not population dietary prevalence.

## Nutrition and uncertainty

Nutrition values are estimates with source and basis limitations. The composition
pipeline uses an IFCT-shaped schema but USDA and US/UK composition sources; this
does not establish Indian composition grounding. Consult `UNITS.json` before use.
{f['missing_servings']:,} recipes lack numeric servings and {f['missing_per100g_energy']:,}
lack per-100g energy. Never replace missing denominators with 1. Estimated ingredient
density and declared-serving bases remain separate confidence tiers.

Vitamin A is micrograms RAE. Total folate is not dietary folate equivalents (DFE);
DV_Folate is unavailable under folate_basis_v1 because the total-folate numerator
does not establish a DFE percentage. DV_Folate_basis records the reason; previous
values remain in field_history under pre_folate_basis_v1. Other nutrient values
are unchanged by this correction.

## Allergen assessment

There are 17 assessed classes and {f['unassessed_allergen_recipes']:,} unassessed recipes.
The long table uses `unassessed`; other surfaces expose `unknown`. Neither means absent.
Use `scripts/allergen_surface.py` and retain uncertainty. These inferred flags are
not sufficient as the sole basis of an end-user safety decision.

`ALLERGEN_AUDIT.json` is primarily a consistency assessment, not measured accuracy.
The earlier 28.2% headline was not reproducible and is withdrawn. Current T12
disclosure reports 794 returned labels: 202 TP, 38 FP, 118 FN, 433 TN and 3 unclear.
The predicted-positive stratum has 240 rows; its zero FN follows from selection and
does not measure sensitivity. Raw FNR 118/320 is conditional on this sample. Reviewer
independence and population weights remain unverified; no corpus-wide rate is claimed.
Sulphite carrier inference is not independently validated by an ingredient-text
lexicon looking for a declared additive. Investigator-defined South Asian classes
must not be described as a regulatory list.

## Flavour and substitution

The core contains FlavorDB compounds and molecular-sharing evidence; the optional
flavour directory is not an isolation boundary from those sources. Use source
attribution and terms in `THIRD_PARTY_TERMS.md`. Presence-derived molecular descriptors
are not measured dish flavour, concentration, allergen evidence or substitution validity.
The released `substitutes_ours` table is a documented negative result, not an approved
recommendation table. Co-occurrence, functional role and sensory similarity answer
different questions.

`data/kg/kg_edge_evidence.parquet` preserves non-topological edge attributes keyed
by `(head, rel, tail)`, including PMI, support, scope and molecular evidence attached
to empirical pairing edges. `scripts/build_graph.py` restores these attributes.
The adjacency-dictionary format represents topology only; use the graph or evidence
table when an explanation needs weights or supporting attributes.

## Provenance, access and maintenance

Per-record attribution is retained. Original prose can be rehydrated where source
URLs permit; see the rehydration index and script. Exclusion records are in
`data/provenance/`; removal procedures are in `TAKEDOWN.md`.
Data and code licences are documented in `LICENSE-DATA` and `LICENSE-CODE`;
third-party fields retain their own source obligations. See `CITATION.cff` for creators
and citation metadata. Funding information has not been supplied.

Rebuild through the source pipeline, then run:

```sh
python scripts/build_release_facts.py --check
python scripts/verify_release.py --strict-checksums
```

A passing verifier certifies the checks it implements, not complete semantic accuracy.
Known uncertainty, historical exceptions and pending independent evaluation remain
part of the dataset's limitations.
'''


def refresh_count_prose(text, facts):
    """Update specifically named current metadata quantities, preserving prose."""
    text = re.sub(r'corpus of [\d,]+ Indian recipes', f"corpus of {facts['recipes']:,} Indian recipes", text)
    text = re.sub(r'across [\d,]+ source sites', f"across {facts['source_sites']:,} source sites", text)
    text = re.sub(r'graph of [\d,]+ nodes and [\d,]+ edges',
                  f"graph of {facts['nodes']:,} nodes and {facts['edges']:,} edges", text)
    return re.sub(r'a \d+-query', f"a {facts['benchmark_queries']}-query", text)


def current_readme(text, facts):
    rows = {
        'Recipes': f"{facts['recipes']:,}, across **{facts['source_sites']:,} source sites**",
        'Columns': f"{facts['columns']}; field definitions and current fill rates are in the generated data dictionary",
        'Knowledge graph': f"{facts['nodes']:,} nodes · **{facts['edges']:,} edges** · {len(facts['node_types'])} node types · {len(facts['relations'])} relation types",
        'Allergen classes': f"{len(facts['allergen_counts'])}, with an explicit `unknown` sentinel on {facts['unassessed_allergen_recipes']:,} recipes",
        'Benchmark': f"{facts['benchmark_queries']} fixed queries, {len(facts['benchmark_templates'])} templates, graph-derived silver labels",
    }
    for key, value in rows.items():
        pattern = r'^\| \*\*' + re.escape(key) + r'\*\* \|.*$'
        text, count = re.subn(pattern, f'| **{key}** | {value} |', text, flags=re.M)
        if count != 1:
            raise ValueError(f'README current-facts row missing or duplicated: {key}')
    text = re.sub(r'^[\d,]+ nodes, [\d,]+ edges, \d+ node types, \d+ relation types\.$',
                  f"{facts['nodes']:,} nodes, {facts['edges']:,} edges, {len(facts['node_types'])} node types, {len(facts['relations'])} relation types.", text, flags=re.M)
    text = re.sub(r'(kg = pd\.read_parquet\("data/kg/kg_edges\.parquet"\)\s+# )[\d,]+ rows',
                  lambda m: m[1]+f"{facts['edges']:,} rows", text)
    for name, count in facts['allergen_counts'].items():
        text = re.sub(r'(\| `' + re.escape(name) + r'` \| )[\d,]+',
                      lambda m, count=count: m[1]+f'{count:,}', text)
    return text


def outputs(root):
    facts = collect(root)
    result = {
        root / 'data/provenance/release_facts.json': json.dumps(facts, indent=2, ensure_ascii=False) + '\n',
        root / 'docs/DATASHEET.md': render(facts),
    }
    readme = root / 'README.md'
    if readme.exists():
        result[readme] = current_readme(readme.read_text(encoding='utf-8'), facts)
    citation = root / 'CITATION.cff'
    if citation.exists():
        result[citation] = refresh_count_prose(citation.read_text(encoding='utf-8'), facts)
    zenodo = root / '.zenodo.json'
    if zenodo.exists():
        metadata = json.loads(zenodo.read_text(encoding='utf-8'))
        metadata['description'] = refresh_count_prose(metadata['description'], facts)
        result[zenodo] = json.dumps(metadata, indent=2, ensure_ascii=False) + '\n'
    return result


def check(root):
    return [str(p.relative_to(root)) for p, content in outputs(root).items()
            if not p.exists() or p.read_text(encoding='utf-8') != content]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, default=ROOT)
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    if args.check:
        stale = check(args.root)
        print('stale: ' + ', '.join(stale) if stale else 'release facts and datasheet match payload')
        return int(bool(stale))
    for path, content in outputs(args.root).items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8', newline='\n')
        print(path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
