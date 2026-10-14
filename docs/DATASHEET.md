# Datasheet — IndicRecipeNutri

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
| Recipes | 219,384 |
| Wide-view columns | 270 |
| Source sites | 378 |
| Graph nodes | 222,537 |
| Graph triples | 6,432,254 |
| Edge evidence rows | 236,315 |
| Ingredient nodes | 927 |
| Compound nodes | 1,607 |
| Node types / relation types | 17 / 22 |
| Benchmark queries | 67 |

Use `recipe_id` for joins. The wide recipe table is a compatibility view; normalized
recipe, nutrition, labels, quality and allergen tables also ship. Historical columns
must not be mistaken for current labels. See `DATA_DICTIONARY.md` and `PROVENANCE.md`.

## Evaluation split

Use **Split_v3**, described in `SPLIT_PROTOCOL_v3.md`. It groups connected components
of case-folded normalized titles and duplicate families. Legacy splits remain for
historical reproducibility and must not be used implicitly in new evaluation.

| Partition | Recipes |
|---|---:|
| test | 11,094 |
| train | 197,350 |
| val | 10,940 |

The release verifier checks graph/corpus split parity by ID and both group constraints.
These checks do not establish the absence of all possible semantic near-duplicates.
The 67 benchmark queries use graph-derived silver labels, not human relevance judgments.
Synthetic interactions are simulated behaviour, not observations of real users.
`data/interactions/` is regenerated from the published corpus, so every recipe it references
is live in this release. `verify_release.py` checks that, the id maps, both splits, and that
no user with a dietary restriction is served an incompatible or undeclared recipe.

## Representation

Pan-Indian accounts for 135,018 recipes and primarily denotes an unassigned
regional label, not an independently sampled geographic population. Region mixes
states, broad areas and cultural communities. English accounts for 207,657
recipes; 1,430 language values are missing. Use `Lang_base` for primary
language filtering, with appropriate validation. Source and regional sampling are uneven.
Recipe frequency is not population dietary prevalence.

## Nutrition and uncertainty

Nutrition values are estimates with source and basis limitations. The composition
pipeline uses USDA and US/UK composition sources and three IFCT 2017 profiles
(atta, maida and paneer). IFCT use is separately permissioned and owner-attested;
see `THIRD_PARTY_TERMS.md`. This does not establish corpus-wide Indian composition
grounding. Consult `UNITS.json` before use.
53,323 recipes lack numeric servings and 60,431
lack per-100g energy. Never replace missing denominators with 1. Estimated ingredient
density and declared-serving bases remain separate confidence tiers.

Vitamin A is micrograms RAE. Total folate is not dietary folate equivalents (DFE);
DV_Folate is unavailable under folate_basis_v1 because the total-folate numerator
does not establish a DFE percentage. DV_Folate_basis records the reason; previous
values remain in field_history under pre_folate_basis_v1. Other nutrient values
are unchanged by this correction.

## Allergen assessment

There are 17 assessed classes and 2,478 unassessed recipes.
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

## Additive 0.12.0 evidence layers

`data/quality/` adds provisional instruction-quality flags, duplicate candidates,
allergen evidence with a separate fail-closed UNKNOWN status, published item
attributes and nutrition-estimator diagnostics. Legacy values and splits are
preserved. See `quality_0_12_0/README.md` for schemas, measured scope and limitations.
The flags are not independently validated and do not establish food safety.

`data/interactions_v5/` is a separate 50,000-user, 1,000,000-event synthetic log
generated only from published attributes. Oracle probabilities are separate
from normal model inputs. These are fictional users and choices, not observations
of real behaviour or dietary suitability. The previous interaction log is preserved.

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

## Occasion context and historical snapshot

Since 0.11.0, `data/cultural_context/` carries an occasion registry, dietary-rule definitions,
their structured citations and name links to existing occasion and context nodes. All are
silver. The rules are stored as data and are not executed: `destination_executable` is
false for every rule, so a declared occasion yields UNKNOWN per item, never PASS. Rules carry
`evidence_tier` (sourced, descriptive, unsourced), and descriptive or unsourced rules must
not be used as silent hard constraints. Quoted third-party text was reduced to citations.
No column describes a person, and none may be used to infer anyone's religion or diet.

### DietaryContext: provenance, conflation and a conservative v2 (29 Sep 2026)

The legacy `DietaryContext` column (`jain_sattvic`, `vrat_fasting`; 6,923 recipes) is a
keyword label, not a verified practice. It was written by `scraper/enrich_params.py` over
RecipeName + Keywords + Description (the last two are not published, which is why most tagged
titles show no Jain or fasting word), then unioned in v11 with tags inferred from text and from
ingredients alone, and finally copied between duplicate-family look-alikes: **1,827 tags were
inherited from a sibling**, although `Diet` is never inherited for exactly that reason.
`jain_sattvic` conflates three claims (Jain; sattvic; no onion or garlic) that exclude different
foods — a sattvic dish may contain potato, a Jain one may not — and the original vrat pattern
counted `navratri`, a festival, as a fast.

`data/quality/dietary_context_evidence_v1.parquet` records, per tagged recipe, which claim the
source text makes and in which field, whether the tag was inherited, and which parsed canonical
ingredients conflict with it. `DietaryContext_v2` splits the token into `jain`, `sattvic`,
`no_onion_garlic` and `vrat_fasting`, keeping a claim only when it is reproducible from the
recipe's own source text, its ingredients were scraped from the source, and no hard conflict
is found. Of 6,923 tagged recipes, v2 keeps at least one claim on 3,295 and withdraws all claims
on 3,628; the legacy column is unchanged.

A kept v2 token means "claimed by the source and no conflict found among parsed ingredients".
It is not certification: unparsed ingredient text is not assessed, ambiguous items (ginger and
turmeric that may be dried, honey, alcohol) are reported but never demote a claim, and
`kept_optional_conflict` marks recipes whose only conflict is an ingredient listed as optional
or "skip for Jain". Exclusion sets follow the descriptive, partially verified rules in
`data/cultural_context/`; vrat has no encoded exclusion, so its onion/garlic guard is the v11
builder's own and its animal-food guard is recorded as unencoded. Use v2 or the evidence table,
not the legacy column, for any filtering.

`data/historical_snapshot/` maps recipe IDs to a historical snapshot by exact ID. It adds no
recipes and is not independent validation. Its historical snapshot split labels must never
be used as a split; use `Split_v3`. Counts, pins and transformations are in each directory's
manifest, and attribution is in `THIRD_PARTY_TERMS.md`.

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
