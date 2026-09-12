# Changelog

## [0.7.0] — 2026-09-12 — one interaction benchmark, regenerated clean

**Breaking: `data/synthetic_interactions/` and `data/synthetic_interactions_v3/` are removed**
and replaced by a single `data/interactions/`. Any path or manifest entry naming the old
directories breaks, and the interaction id space is different (see defect 3 below), so stored
user/item pairs from either retired set must not be joined to the new one. Both remain
reachable at the `v0.6.0` tag and its DOI for anyone reproducing published results.

**They were not merged, because they could not be.** The two directories were independent
simulations, not two halves of one dataset: their remapped id spaces collide. `user_id 0`
rated recipe 4489 in v1 and recipe 121171 in v3, and exactly 2 of ~16,000 `item_list` entries
agreed. Concatenating them would have invented users who rated across two different
catalogues and destroyed both guarantees the verifier checks — the 10-core property and
`train_test_leakage = 0`. One coherent set could only come from regeneration.

`scripts/build_interactions.py` now generates it from `data/corpus/recipes_structured.parquet`
— the published corpus — with no machine-specific path. `scripts/build_interaction_baselines.py`
re-scores it. Both replace scripts that shipped *inside* the data directory and hardcoded
`/tmp/bench/synth50` and `/mnt/user-data/uploads/...`, which is why the artefact could never be
rebuilt and had to be pinned instead.

**The pins are retired, and that is the substance of this release.** v0.6.0 declared the two
directories pinned to the pre-withdrawal corpus at 385 / 385 / 20,161 and 12 / 12 / 1,087
withdrawn-recipe references. Generating from the published corpus makes the count **0** by
construction rather than by declaration; `verify_release.py` now expects zero and fails on
anything else instead of accepting a number.

### Fixed — three defects in the retired generator, all of them silent

1. **The glycemic term never operated, in either published generation.** `gen.py` mapped
   `GlycemicLoad` through `{'low','medium','high'}`, but that column is ~98.6% **numeric** in
   both source CSVs and holds no such value — so `.map()` returned NaN for every row,
   `.fillna(0.5)` made the score a constant, and the `diabetic` profile (15% of users)
   silently reduced to HealthGrade alone. The published datasheet's "diabetic→low
   glycemic/grade A-B" described a term that had never run. The categorical column it wanted,
   `gl_bucket`, was sitting directly beside it. v4 maps `gl_bucket` — **216,353 of 219,386
   recipes (98.62%)** against 0.00% before — and the build now fails if that ratio ever falls
   below half.
2. **Diet normalisation failed open on a hard constraint.** `norm_diet()` returned
   `'Vegetarian'` for anything it did not recognise, so **731** recipes carrying
   `Diet == 'unknown'` entered the Vegan, Vegetarian and Eggetarian candidate pools — and the
   audit reported zero violations because it re-used the same function on the same values. An
   undeclared diet is now its own class, excluded from every pool, and the audit reads the raw
   corpus column so it can fail. `scripts/interactions_contract.py` re-checks it at release
   time against the corpus, independently of the generator that produced the artefact.
3. **Ids were positional, not recipe ids.** Candidate selection produced dataframe row
   offsets, which were written into a column named `recipe_id` and read as corpus ids by
   `item_list.txt`, `entity_list.txt` and the static-id gate alike. Position is mapped to
   `recipe_id` explicitly now.

### The payload

50,000 users · **990,273** ratings over 18,010 distinct recipes · after positives (≥4),
iterative 10-core and a per-user temporal 80/20 split: **35,801 users / 16,567 items /
820,566 interactions** (train 657,610, test 162,956) · **0** leakage · attribute KG of
**82,835** triples over 16,614 entities · all 27 published `Region` codes represented.
`data/` is now 83 files, ≈474 MB.

- `scripts/synthetic_history_contract.py` is replaced by `scripts/interactions_contract.py`.
  The old one staged two frozen generations and pinned their `SNAPSHOT.json` digests; a
  regenerable artefact needs no byte-pin, because `checksums/SHA256SUMS` already covers every
  file in both directions. The new contract checks what a digest cannot see: injective id
  maps, item/entity namespace agreement, KG and split referential integrity, no train/test
  overlap, every referenced recipe live and unwithdrawn, and the diet hard constraint.
- `scripts/build_region_crosswalk.py` is rewritten. Its old premise — a vocabulary mismatch
  needing a hand-maintained rename table for `Sindhi (community)`, `Parsi (community)` and
  `Mughlai (North India)` — is gone, because users and KG entities are now drawn from the same
  published `Region` column and every code resolves by exact string. What remains is smaller
  and real: 4 codes and 289 users (**0.578%**) whose regions had no item survive the 10-core.
- `.gitattributes` LFS globs widened from `data/synthetic_interactions*/` to
  `data/*interactions*/`. An anchored glob would have matched the new directory **not at all**
  and committed its 24.7 MB `interactions.csv` raw — the same failure the previous widening
  was written to prevent, one directory later.

## [0.6.0] — 2026-09-12 — vocabulary, a new relation, and the salt family

**Breaking: `pairs_with` is recomputed.** The empirical co-occurrence layer had been PMI over a
corpus generation that predated the token splits, the plant-analogue block and salt recovery —
`pairs_ours.parquet` was written at 06:17 against a graph rebuilt at 17:01. The knowledge graph
builds twice by design for exactly this reason, and it had been built once. Every `pairs_with`
edge is regenerated here, so stored pairs from an earlier release will not all reappear.

Recorded as a gap in the guard suite, not only in the data: **all 14 gates pass without catching
this.** None asserts that the pairing layer is current relative to the graph it describes.


- Suppressed unsupported `DV_Folate` percentages and added `DV_Folate_basis`.
  Previous values remain in field history as `pre_folate_basis_v1`; total folate
  and all other nutrient values are unchanged. Upstream builders and release
  checks prevent reintroducing the unsupported conversion.
- Added canonical `nut_suppl_fct_frac` to the narrow quality table, retained
  `nut_indb_frac` as a deprecated identical alias, and added a recipe-ID parity gate.
  Metadata now describes the computed-calorie basis and legacy zero-denominator
  ambiguity on both surfaces. Values are unchanged.
- Graph recipe splits now require Split_v3; corrected 40,773 stale v2 labels.
- **Breaking:** compound IDs use PubChem CIDs. Five ambiguous names had collapsed
  distinct chemicals; restored 6 compound nodes and 15 has_compound edges. See
  `docs/COMPOUND_ID_MIGRATION.md` and the generated ambiguity-aware crosswalk.
- Optional flavour tables now derive from the live core and its evidence, with a
  deduplicating loader and no dangling ingredient references.
- Preserve edge attributes in `kg_edge_evidence.parquet`; correct graph reconstruction
  column interpretation and retain 580 molecular assertions attached to pairing edges.
- Generate current release facts and datasheet; enforce split, evidence and flavour
  contracts in verification and regression tests. These changes are not yet published.
- **Fixed — a published allergen false negative.** Recipe 23064 carried
  `100 gms walnuts (akhrot)` in `recipes_structured.parquet` and a `contains_allergen`
  edge in the graph, while `data/corpus/allergens.parquet` published `tree_nuts` as
  **absent** and `recipes.parquet` omitted two ingredient lines entirely. Both surfaces
  are rebuilt from the master: the list is back to 10 items and `tree_nuts` reads
  `present`. Measured as isolated — 1 of 219,386 recipes on each surface. The regression
  guard written to catch exactly this had been failing open: `edges.tail` resolves to the
  pandas DataFrame *method*, never the column, so it raised `TypeError` outside its own
  except clause and never once executed its KG check. Repaired.
- **Breaking: ingredient vocabulary.** Twelve singular/plural duplicate nodes merged and
  two truncation fragments (`mato`, `matoes`) folded into `tomato`; ingredient nodes
  **960 → 946**, graph 222,584 → 222,567 nodes. The graph had held e.g. `cranberries`
  *and* `cranberry` as separate foods, splitting one food's recipes. The surviving node
  is the one carrying compound links, not the one with more edges — edges are re-pointed
  by the rebuild, but `fix_flavor_compounds.csv` is keyed by NAME, so keeping the larger
  member would have orphaned 898 ingredient→compound links; **1,011 are preserved**.
  Every dropped spelling remains a resolvable surface in `ingredient_map.json`, so a
  lookup of `cranberries` still returns `cranberry`.
- Added `data/kg/ingredient_bridge_food.csv` (18 rows): the bridge food whose compound
  profile an Indian ingredient borrows, **with the form it differs by**. Nine are
  `direct` (toor dal *is* dehulled split pigeon pea; maida *is* refined wheat flour);
  seven are `with_caveat` — amchur is dried **unripe** mango, so it inherits ripe fresh
  mango's profile only with the transform and caveat recorded. `ragi` and `bajra` are
  withdrawn: no source held carries finger or pearl millet, and the generic `Millet` is
  a different grain.
- Benchmark regenerated from the rebuilt graph: **68 → 67** queries. One template moved
  (`diet+ingredient` 6 → 5) because `recipes with sprout` lost its subject to the merge;
  the other seven are unchanged, and all 52 shared queries keep identical relevant ID
  sets. `data/kg_flavor/` and the corpus surfaces were regenerated to match.

- **Added — `subtype_of`, a new relation.** "Is a kind of", which neither existing relation
  could carry: `derived_from` asserts a derivation that is false here, and all 148 `is_a` edges
  go ingredient → one of ten fixed *category* nodes, never ingredient → ingredient. 17 edges —
  eleven oils and six salts. Relation types **21 → 22**, and `data/kg/typed/rel_map.json` gains
  an entry. A specific oil now carries both: `subtype_of` → `oil` (what kind of thing it is) and
  `derived_from` → its source material (what it was made from).
- **Breaking: ingredient vocabulary, again.** Across three passes, 33 ingredient node names were
  removed and 14 added. Ingredient nodes **931 → 927**; graph **222,548 → 222,539 nodes,
  6,292,011 → 6,428,210 edges**. Every dropped spelling that names a real food remains a
  resolvable surface in `ingredient_map.json`; the ones removed outright were not foods
  (`season`, `salted`, `cooks`, `table`, `feet`…).
- **Thirty multiword token splits.** `pearl` was five foods, `finger` three, `root` a plant part,
  `plant` a food and a diet qualifier. **871 ingredient lines that previously resolved to nothing
  were recovered** — the phrase pass repairs lines the last-noun fallback mangled, e.g.
  `'vegetable oil omit'` used to walk to `omit` and drop — and 8,359 were re-routed between
  foods. `oil` shed 6,510 lines to a new `vegetable-oil` node.
- **The salt family was un-folded.** The node named `salt` was in practice *kala namak*: 3,111 of
  its 4,233 lines were the `black salt` surface. `black-salt`, `kosher-salt`, `pink-salt` and
  `fruit-salt` are now separate nodes, each `subtype_of salt`; `salt` falls to 1,191 lines.
  **`fruit salt` had been landing on the real food node `fruit`** (705 lines) — Eno fruit salt is
  a leavening agent, and that subtype edge is a naming claim, not a compositional one, recorded
  as such beside the declaration.
- **A plant-analogue block, so an analogue never lands on an animal food.** 1,629 lines whose
  primary item was a plant analogue resolved onto `butter` (477), `milk` (397), `yogurt` (307),
  `cheese` (172), `cream` (126), `ghee` (71) and the meat nodes including `beef` (18). Eight new
  nodes — `plant-milk`, `vegan-butter`, `vegan-yogurt`, `vegan-cheese`, `vegan-cream`,
  `vegan-ghee`, `vegan-meat`, `egg-replacer` — capture 94.5% of them. Substitution *notes* are
  deliberately untouched: `'1 cup whole milk (or non dairy milk)'` is milk, and the parenthetical
  is advice to a vegan reader.
- **Benchmark labels refreshed against the rebuilt graph, question definitions frozen.** All 67
  questions unchanged (`fixed_silver_v1`, `definitions_changed: 0`); only gold sets were
  re-derived, and `unknown`/`unassessed` recipes are excluded from allergen-absence gold sets
  rather than read as absence. Both audit legs now report **0.00%** across 7 constraint queries
  and 1,592 gold entries.
- **Salt is in the graph.** It was not. `"salt"` sat in the resolver's generic-word list, so
  *"salt to taste"* resolved to nothing and **147,749 of the 163,252 salt-mentioning lines
  (90.5%) were dropped** — while the node *named* `salt` was in practice kala namak, because
  `black salt` was 3,111 of its own 4,233 lines. Recovering it took two changes, neither
  sufficient alone: the generic-word removal and a `salt` map surface. **`salt` is now the
  corpus's most common ingredient at 135,548 recipes**, above chili's 100,427. `sea-salt` (3,093)
  and `rock-salt` (1,313, including *sendha namak*) recovered lines that also resolved to nothing.
- **Seventeen non-food tokens removed from the vocabulary**, 487 lines: `season` (*"berry in
  season"*), `salted`/`salty`/`unsalted` (preparation states), `cooks`, `past` (the word is
  "paste"), `table` (*"GARNISHES FOR THE TABLE"*), `pink` (food colouring), `himalayan`
  (sparkling water), and others. `cardamon` was merged into `cardamom`, and `eno` repointed to
  `fruit-salt` — the corpus names it fruit salt in its own text.
  - **`card` was deliberately kept**, though it looks like the same kind of junk. It is a
    working truncation alias carrying **26,323 lines** to `cardamom`, with zero lines resolving
    to itself. Removing it would have destroyed those lines while the node count still looked
    correct, since `cardamom` has seven other surfaces. The builder asserts the mapping and
    refuses to run without it.
- Every graph movement across all three passes was **pre-registered before the rebuild and
  scored after**, in
  `_admin/progress/KG_DELTA_{PREDICTION,RECONCILED}_{splits,salt_analogue,round2}_20260912.md`.
  All three closed to zero residual. `contains_allergen` was required not to move and did not:
  **485,120** throughout. A vocabulary change that shifts an allergen count is a defect, not a
  delta.
- Known and recorded, not hidden: recipes emitting the maximum 20 ingredients rose 2,624 → 3,741
  as salt entered. Small falls on `black-salt`, `kosher-salt`, `pink-salt` and the oils are
  *consistent with* displacement past that cap, but were not separately isolated.

Versions follow semver and describe the **release**, not the corpus build. The corpus
build (`v15`) is recorded separately in `data/corpus/corpus_manifest.json` and
`.zenodo.json`.

**Why a minor bump and not a patch.** Under `0.y.z` the minor position is the breaking position,
so *any* breaking change forces it — the number of them does not multiply the bump. What is
breaking here is that identifiers consumers store and join on changed: compound ids became
PubChem CIDs, and ingredient node names were removed. Not 1.0.0, which would assert a stable
public interface while the open gates listed under 0.1.0 remain open.

## [0.4.1] — 2026-09-06

Metadata only. No data, no code behaviour, no counts changed.

### Fixed — 0.4.0 dropped two co-authors from its own DOI

The published 0.3.0 Zenodo record credits three authors with affiliations. `.zenodo.json`
and `CITATION.cff` in this repository named **one**: the co-authors had been added by hand
on the Zenodo record and never written back here. Zenodo regenerates a record's metadata
from `.zenodo.json` on every release, so publishing 0.4.0 **silently dropped Dr. Santosh P.
Borde and Dr. Yogesh Gurav** into a permanent DOI (`10.5281/zenodo.22537252`). Nothing
failed; the release was green.

All three authors and their affiliations are now declared in both files, preserved exactly
as published on the 0.3.0 record so an existing citation does not change form.

`verify_release.py` gained a **`check_authorship`** guard: `.zenodo.json` and
`CITATION.cff` must name the same people, compared by surname because the two formats
spell a name differently by design (`Dr. Santosh P. Borde` against family/given plus
`name-prefix`). Attribution is not a cosmetic field — a metadata file that disagrees with
the record it generates is the same class of defect as a count that disagrees with its
payload, and this one is harder to notice because nobody re-reads the author list.

The surname rule is positional, not longest-token: `Hemprasad Y. Badgujar` yields
`Hemprasad` on a longest-token rule, which is how the first version of the guard failed.

### Changed — one name format across every record

The dataset spelled its own authors two ways: `.zenodo.json` supplied a literal
`Given Family` string, while a record edited through Zenodo's structured form composes
`Family, Given`. So 0.3.0 and 0.4.1 render as `Hemprasad Y. Badgujar` and 0.4.0 — corrected
by hand — renders as `Badgujar, Hemprasad Y.`. Cosmetic, but citation tools match on
strings, and two spellings of one author across versions of one dataset is exactly the kind
of thing that fragments a citation record.

`.zenodo.json` now uses `Family, Given`, which is the DataCite convention and what the web
form produces, so every future release matches by construction. `check_authorship` compares
**surnames** rather than whole strings, which is why it kept passing across the change —
that was the right call when it was written.

Honorifics are kept as published. `Dr.` in a given-name field is not standard DataCite
practice and does interfere with author disambiguation, but these are other people's names
as they already appear on a minted DOI, and normalising them is the authors' call.

### Fixed — the citation prose described a payload three releases old

`.zenodo.json`'s description and `CITATION.cff`'s abstract both still said 220,187 recipes,
223,406 nodes, 6,270,560 edges and a 68-query benchmark. Neither is regenerated by
anything, and that text is what a reader sees **first** — on the Zenodo landing page, in
the citation, in every index that harvests the record — and the DOI carries it permanently.
Both re-measured.

`verify_release.py` gained **`check_metadata_figures`**: every comma-formatted integer of
four digits or more in that prose must be a figure the payload actually has. Deliberately
mechanical rather than clever; small numbers (17 node types, the 42-nutrient schema) are
left alone because they are not row counts and do not go stale the same way.

### Fixed
- README BibTeX lists all three authors and both version DOIs.

## [0.4.0] — 2026-09-06

First release whose verification runs anywhere but the authoring machine, and the first
whose two long-standing audit disclosures were investigated rather than restated. No
recipe data changed: row, column and graph counts are identical to 0.3.0.

### Fixed — the audit lexicon's coverage was a regex bug, not a design limit

0.3.0 disclosed that the independent audit lexicon "covers under 60% of flagged rows" for
six classes, and 121,480 flagged rows went unaudited. That was read for months as
deliberate narrowness. **It was a plural-matching bug.** Every pattern was singular and
`\b`-anchored on both sides, so `\bcashew\b` could not match `cashews` — `s` is a word
character, so the closing boundary fails — and recipe text writes count nouns in the
plural nearly always.

The giveaway was in the numbers the whole time: the classes that scored well are exactly
the **mass nouns**, which have no plural to miss (milk 95.1%, ghee 99.8%, tamarind 99.1%,
coconut 96.5%), and the ones that scored badly are exactly the **count nouns**. A
vocabulary gap does not sort itself by grammatical number.

| class | 0.3.0 | 0.4.0 |
|---|---:|---:|
| peanut | 37.4% | **92.9%** |
| tree_nuts | 45.1% | **92.6%** |
| shellfish | 38.9% | **88.9%** |
| egg | 48.7% | **86.6%** |
| gluten | 53.0% | **74.8%** |

Unaudited flagged rows **121,480 → 72,919**, of which 23,989 are sulphites (below). Rows
the audit lexicon now matches that the labeller did *not* flag stayed near zero, so this
is coverage, not over-matching. `s?` does not compromise the audit's independence: it is a
morphology fix, not an import of the labelling lexicon's vocabulary.

Gluten was extended with unambiguous wheat products (`suji`, `vermicelli`, `semiya`,
`noodles`, `breadcrumbs`, qualified flours). **Bare `flour` is deliberately excluded** —
rice, gram and corn flour are gluten-free, and it appears in 22,426 of the previously
unmatched rows, so matching it would manufacture agreement on no evidence.

### Changed — `sulphites` is reported as unauditable, not as 0% covered

The two legs ask different questions. The labeller uses a **carrier rule** — vinegar
(10,227 flagged rows), raisins (7,089), wine, dried fruit — because that is where
sulphites are. The independent leg asks whether the recipe *declares* the additive, which
a home recipe never does. Coverage is 0 by construction and always will be.

Giving the independent leg a carrier list would make it agree with the labeller on the
labeller's own theory and report that agreement as corroboration. It deliberately does
not, and the release now says the class is **not independently auditable** rather than
reporting it as a coverage failure.

### Fixed — the static-id guard checked one population of three and one directory of two

`synthetic_interactions` is pinned to the pre-withdrawal corpus by decision (V9.5): its
generator cannot be re-run here, and regenerating would invalidate the published
`baseline_results.json`. That decision stands. What was wrong is that "pinned" meant
"pinned against the subset we happened to check".

- It tested `WITHDRAWN_NONRECIPE_IDS` (V7 only) while `all_withdrawn_ids()` exists so a
  population cannot be added without every consumer seeing it — the very failure the
  registry was built for. **V8 references it never counted: 70 / 70 / 3,462.**
- **`data/synthetic_interactions_v3/` was published and entirely unchecked.** It is a
  later generation and is V7-clean (0 references where v1 has 315), but carries 12 / 12 /
  1,087 V8 references of its own.

Both directories are now pinned against all **4,617** withdrawn ids across every
population: `synthetic_interactions` 385 / 385 / 20,161, `synthetic_interactions_v3`
12 / 12 / 1,087.

### Fixed — the repository was not self-contained

`release_config.py` imported `allergen_taxonomy` from `D:\datasets`, a path that exists on
one machine, and read both withdrawal lists from the source tree. The first release
workflow run died with `ModuleNotFoundError` before executing a single check.

The consequence was larger than a red build: **every check the release makes about itself
could only ever run here** — not in CI, not for a reviewer, not for a Zenodo depositor,
not for anyone cloning the archive to check the payload against `SHA256SUMS`.

- `scripts/allergen_taxonomy.py` — verbatim vendored copy, regenerated in the build chain.
  The datasets root stays first on the path, so the canonical file still wins locally and
  the copy can never mask a stale canonical. `verify_release` compares its payload hash to
  a pin, which is the drift check that works on a clone.
- `data/provenance/withdrawn_ids.json` — **ids only**. The source files are quarantine
  records holding the withdrawn rows, and one population was withdrawn for PII, so
  vendoring them wholesale would republish exactly what the withdrawal removed. Publishing
  the ids lets a user verify their absence for themselves.
- `INDICRECIPE_ALLOW_NO_WITHDRAWN_LIST=1` exists and is deliberately **not** used: an
  empty list makes the exclusion check pass vacuously.
- `SOURCE_ROOT` is now genuinely overridable via `INDICRECIPE_SOURCE_ROOT`. Its comment
  had claimed "overridable" while the path was a literal.

Verified by simulating a clone with neither root present: `verify_release
--strict-checksums` exits 0.

### Changed
- **README rewritten.** Every figure re-measured from the payload; the previous one still
  described 220,187 rows, 68 benchmark queries, 251 columns and "no Git LFS". Adds the
  DOI, an allergen section stating the four things that matter before building on the
  labels, and a section on verifying a download.

## [0.3.0] — 2026-09-05

Corpus still on master **v15**. **Breaking:** two published enrichment tables are removed,
801 further `recipe_id`s are absent, and every ingredient field is now English/Roman.

### Changed
- Published rows 220,187 → **219,386**; published columns 235 → **268**.
- Knowledge graph 223,406 / 6,270,560 → **222,578 nodes / 6,292,304 edges**. Every movement
  is reconciled per relation and per allergen class in `scripts/release_config.py`, beside
  the constant it moves.
- Retrieval benchmark 68 → **67 queries**; distinct source sites 379 → **378**.

### Removed — breaking
- `data/enrichment/allergens_v8.parquet` (decision D-4). A superseded generation whose own
  `has_*` flags disagreed with the corpus label on 120,147 rows. The single allergen surface
  is `data/corpus/allergens.parquet`, with `scripts/allergen_surface.py` as its accessor.
- `data/enrichment/allergens_full.parquet` (decision D-5). A second published allergen
  surface in a retired vocabulary (`peanuts`, and `none` on 58,574 rows), with **no
  unassessed sentinel at all** — so a scanned-clean row and an unchecked one were
  indistinguishable in it.

### Withdrawn
- 801 rows, the whole of `SourceSite=grihshobha` (V8). The scraper never located an
  ingredient list there; what it captured was the page's navigation bar plus the words of
  the title. Records kept in full outside the release.

### Added
- **Every ingredient field is English/Roman.** `IngredientsList`, `Ingredients` and
  `Servings` no longer contain Indic script; 23,718 words were translated through
  `INDIC_GLOSSARY.tsv` (3,074 entries, 100% coverage of the 2,014 distinct words) and none
  transliterated. `IngredientsList_src_script` publishes the original text as provenance
  (decision D-2). `ingredients_romanised` records the tier per row.
  - 58 rows gained an allergen class that had been written in a script the scanner could not
    read — `sulphites` +23 alone, because the carriers are raisins, dried fruit and vinegar
    (`किशमिश`, `ಒಣದ್ರಾಕ್ಷಿ`, `કિસમિસ`, `വിനാഗിരി`).
  - URLs carrying Indic are **percent-encoded (RFC 3986), not transliterated** — a
    transliterated URL is a dead link that still looks plausible.
- **FSA per-portion red override** applied per the FSA/DH front-of-pack guidance, Step 3.2
  p.15: above a 100 g portion a nutrient over its per-portion cut-off is red regardless of
  its per-100 g value. 88,266 cells across 55,312 recipes. New columns `fsa_portion_g`
  (per-serving, unlike the column it derives from) and `fsa_portion_override_applied`.
  60,519 rows have no usable serving count and were left untouched, not defaulted.
- `allergen_from_instructions` — 290 rows whose `mustard` or `asafoetida` label comes from
  the instruction channel rather than the ingredient list. Only those two classes cleared
  the pre-registered bar (Wilson 95% lower bound ≥ 0.70); the channel's true precision is
  0.601, not the 0.337 previously recorded on a two-site sample.

### Fixed
- `musterd` / `mustered` were unknown spellings; 12 rows carried no mustard label at all.
- `contains_allergen` now carries all 17 declared classes on every surface. `ghee` reaches
  the tabular surfaces, not only the graph.

### Fixed — an allergen fail-open (V27)

**89 recipes named asafoetida in a spelling the labelling lexicon did not carry, and so held
no asafoetida label.** None was marked `unknown`, and 70 carried other classes confidently
(`mustard:direct` and the like) — so the row *was* assessed and this class was missed. The
fail-closed sentinel did not cover them. That is the direction the guardrails say is never
traded, and it is now closed: the class goes 30,518 → **30,607**, and `contains_allergen`
30,518 → 30,607 for a KG total of **6,292,393** (+89), reconciling both ways with no
remainder.

The corpus spells this word 24 ways beyond the canonical two — `aseftida`, `asaefoetida`,
`asafotedia`, `asafatedia` — and glues quantities to it (`teaspoonasafoetida` on 30 rows,
`pinchasafoetida` on 18), where a word boundary cannot fire. All of it is now in
`allergen_lexicon_v14`, explicitly and observed-in-context rather than as a fuzzy pattern,
with the one wildcard confined to the canonical spelling, which is not a substring of any
other word. Harness 63/63 positive, 33/33 negative.

Found by widening `scripts/validate_sa5.py` until its recall stopped being a tautology.
Two rounds were needed: the first arm listed only spellings ending in `-a` and left 11 rows
behind. Two candidate rows (14006, 14048) were deliberately **not** labelled — they are
`unknown`, and asserting a class on an unassessed row collapses the sentinel; gate M28.7
caught that on the first attempt, along with 3 rows that would have carried both a class and
`none_detected`.

`scripts/validate_sa5.py` also joins the build chain rather than only the gate suite: it
writes a checksummed document, so leaving it out meant every rebuild produced the staleness
its own gate then failed on.

### Fixed — documentation that described a superseded payload

Two shipped validation reports carried figures that no longer matched the data beside them.
Neither was regenerated by anything, so neither could fail.

- `docs/allergen_sa5_v1_validation.md` **regenerated from the published payload** and now
  produced by `scripts/validate_sa5.py`, wired into the gate suite as `--check`. It had
  asserted a corpus size of 224,003 that was a **string literal in its own generator** — a
  re-run could never move it — beside a computed table; the payload is 219,386 rows. Its
  scan targeted a raw `Ingredients` column **that does not ship**, so no reader of the
  release could reproduce it. Its synonym list omitted the US spelling `asafetida`, turning
  1,096 correctly-labelled recipes into phantom false positives. Its `Status: Verified`
  column was a hardcoded literal printed regardless of the numbers. And it attributed the
  asafoetida false positives to *"valid knowledge-graph (KG-sourced) labels"* — **there is
  no KG allergen source in the payload**; `allergens_sa5_src` takes only `lexicon_v8` and
  `none`. The real cause is measured and now shipped with the figure: **93.4%** of those
  rows name a **composite masala** that contains asafoetida without declaring it (chaat
  masala 4,287, sev, sambar powder, pav bhaji masala). Labelling them is correct and
  fail-closed; it is simply why that class's precision is 76.93% and not ~99%.
- `docs/validate_fsa_recipe1m.md` **scoped and de-overclaimed**. It validates the per-100 g
  band function, but since V17 the shipped `fsa_*` columns also carry the per-portion red
  override — **88,266 cells over 55,312 recipes, 25.2% of the corpus** — which the report
  never mentioned. It now states that `fsa_*_pre_portion` is the column it validates.
  Its conclusion that 100% agreement *"proves our classification code contains zero
  calculation, rounding, or boundary-handling bugs"* is replaced: agreement between two
  implementations of one rule is silent about what both get wrong.

### Infrastructure
- **`verify_release.py` now checks the checksum manifest in both directions.** It walked
  `SHA256SUMS` and compared each entry to disk, so a file *added* to `data/` or `docs/`
  after the last `make_checksums.py` run shipped with no digest and the gate stayed green.
  `docs/RELEASING.md` entered the payload that way on 2026-09-05.
- Large data artefacts move to **Git LFS**. `data/corpus/recipes_structured.parquet` had
  reached 99.1 MB against GitHub's 100 MB per-file limit and grows with every added column.
  A clone without git-lfs gets pointer files and `verify_release.py --strict-checksums`
  fails loudly rather than validating a stand-in.

## [0.2.0] — 2026-09-01

Corpus rebuilt on master **v15**. **Breaking:** 3,816 `recipe_id`s present in 0.1.0 are
absent here, and the benchmark gold set is regenerated rather than carried over.

### Changed
- Corpus build v12 → v15. Published rows 224,002 → **220,187**; published columns
  150 → **235** (243 in the master, 8 withheld).
- Knowledge graph 225,666 / 6,132,916 → **223,406 nodes / 6,270,560 edges**.
  Per-relation reconciliation is in `scripts/release_config.py`.
- Retrieval benchmark 66 → **68 queries**. The set churned by 15 out / 16 in: gold sets
  are regenerated from the KG on every rebuild, so results measured against the 0.1.0
  benchmark are **not** comparable to results measured against this one.
- Distinct source sites 380 → **379**.

### Withdrawn
- **3,815 rows that were never recipe pages** — WordPress `/tag/`, `/category/` and
  `/recipe_difficulty/` archive listings, single-food commodity records,
  image-attachment pages, shop product pages, glossary and listicle pages. Moved to
  `MASTER_nonrecipe_quarantine_v7.csv`; **rows_destroyed 0**, fully reversible. Every
  row was read individually by an adjudicating agent and again by a third reader whose
  default was RESTORE. Record: `_docs/V7_NONRECIPE_2026-09-01.md`.
- Together with `recipe_id 211731` (withdrawn in 0.1.0 for PII), published totals are
  **220,187 / 223,406 / 6,270,560**.

### Fixed
- 4,516 titles repaired rather than deleted (breadcrumbs, site brands, mastheads, image
  filenames, and a scraper off-by-one on two sites).
- Plural fail-open in the diet meat lexicon: 237 strict-vegetarian rows carried a plural
  meat term in their own ingredient list. Diet constraint re-run.
- `recipe_id` decoupled from row position in the KG builders.

### Measured effect on the published defect profile
- Broken ingredient lists: `badlist_any` 24,285 (10.84%) → **2,743 (1.25%)**;
  `badlist_hard` 6,265 (2.80%) → **1,384 (0.63%)**. The 100 `savorytales`
  sidebar-navigation rows listed as a known defect in 0.1.0 were withdrawn and are gone.
- Recipes with no `has_ingredient` edge: 2,530 (1.13%) → **1,808 (0.82%)**.
- Diet-label conflicts, `Vegan`: 3,042 (3.30%) → **282 (0.33%)**.

## [0.1.0] — 2026-08-28

First assembled release. **Pre-release: not citable.** Five gates below are open.

### Added
- Structured corpus: 224,002 recipes × 150 columns, Parquet + zstd (53.8 MB).
- South Asian 5 allergens populated (`coconut`, `tamarind`, `fenugreek`, `asafoetida`) with strict word-boundary token matching.
- UK FSA traffic light classifications (`fsa_fat`, `fsa_saturates`, `fsa_sugars`, `fsa_salt`) and `per100g_salt` calculated.
- Grouped stratified split `Split_v2` ensuring zero normalized title leakage across splits.
- Rehydration index with source URL, SHA-256 prose digest, and a `rehydratable` flag.
- Knowledge graph: 225,666 nodes / 6,132,916 edges, recomputed from the published
  tables after exclusion rather than copied from upstream.
- 26 enrichment companion tables (including recovered ingredient quantities and portion weights).
- 66-query retrieval benchmark with a two-leg gold-set audit.
- Synthetic interaction log: 50,000 users, 990,273 ratings, with its datasheet.
- Datasheet, data dictionary, provenance, third-party terms, takedown policy.
- Build, audit and verification scripts; tag-driven release workflow.

### Fixed
- **Knowledge-graph Parquet re-encoded.** The working `kg_nodes.parquet` and
  `kg_edges.parquet` were written by pyarrow 25 with size statistics that pyarrow 19
  cannot read at all ("Repetition level histogram size mismatch") — a reader on an
  older Arrow could not have opened the graph. Re-encoded through the release's own
  writer. No value changed; the counts were re-verified afterwards.
- **Tree nuts / Coconut separation.** Coconut-only recipes have been explicitly separated from generic `tree_nuts` labels per the South Asian taxonomy divergence rule.

### Withdrawn
- **`recipe_id 211731` is withdrawn from the release.** Its `IngredientsList` held no
  ingredients — the scrape captured the source site's sidebar navigation with the
  owner's email address attached. Removes 1 corpus row, 1 KG node, its 15 edges, and
  1 row from each of 15 enrichment tables; it is in no gold set and no synthetic
  interaction. Published totals are now **224,002 / 225,666 / 6,132,916** and
  `kg_stats.json` is recomputed from the published tables.
- The working master is unmodified. The exclusion is declared in
  `release_config.py:EXCLUDED_RECIPE_IDS`, applied by every builder, and enforced by
  `verify_release.py`, so it is reversible and auditable rather than a silent delete.

### Privacy
- The pattern-based redaction pass (email, phone, card) runs on every build and now
  finds nothing, the one match having been withdrawn outright. It stays in place so a
  future corpus revision cannot reintroduce personal data silently.

### Known defects — measured, published, not fixed
- Allergen false negatives, upper bounds across all 16 canonical tokens: celery 79.12%, sesame 9.39%, tree_nuts 6.36%,
  shellfish 5.61%, soy 5.46%, peanut 3.62%, mustard 3.13%, egg 2.35%, fish 1.89%,
  milk 1.85%, gluten 1.79%, asafoetida 0.00%, coconut 0.00%, fenugreek 0.00%, tamarind 0.00%, sulphites n/a. See `data/corpus/ALLERGEN_AUDIT.json`.
- Diet-label conflicts: 3,042 `Vegan` rows (3.30%) name a dairy, egg, fish or
  shellfish ingredient. Largest cluster is paneer: 216 paneer recipes labelled `Vegan`,
  169 with `has_milk = False`.
- Benchmark: 14 of 289 gold-set members (4.84%) for *"Vegan recipes without milk"* are
  paneer dishes. The other five constraint queries show no lexical conflict.
- **100 `savorytales` rows carry sidebar navigation instead of ingredients**, all
  wrongly flagged `has_ingredients = True`. Already present in the published
  quarantine list; not repaired here. A 101st, `recipe_id 211731`, also carried an
  email address and was withdrawn entirely — see *Withdrawn*.

### Open gates for 1.0.0
1. **Third-party terms unverified** — IFCT 2017, FlavorDB, FoodOn, RecipeDB NER, plus
   four upstream recipe datasets found during this build (3a2m, IndB, RecipeNLG,
   indori; 4,807 rows). If any is share-alike, CC BY 4.0 on the graph is wrong.
2. **Semantic PII pass has no run artefact.** Pattern-based redaction is now done and
   recorded, but author names and personal anecdotes are not pattern-matchable and the
   pass the paper describes is still unevidenced.
3. **Split protocol undocumented.** Do not describe the train/test/val split as
   random, temporal or cold-start until the assignment rule is established.
4. **No collection timestamps** in the published schema, though the paper states they
   are retained per recipe.
5. **Ingredient vocabulary (1,205) and graph ingredient nodes (1,199) differ by six**,
   cause unestablished.
