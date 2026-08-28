# Datasheet — IndicRecipeNutri

Following Gebru et al., *Datasheets for Datasets*, *Communications of the ACM* 64(12), 2021.

**Release version:** 0.1.0 · **Corpus build:** v11 · **Compiled:** 28 August 2026

> **Status: pre-release.** This datasheet is complete for every field that could be
> verified against an artefact in this repository. Fields marked `⟨TBD⟩` are not yet
> verified and **must not be filled with a plausible value** — they are release gates,
> tracked in [`../CHANGELOG.md`](../CHANGELOG.md). Version 0.1.0 is not a citable
> release.

---

## Motivation

**For what purpose was the dataset created?**
To support nutrition-grounded, culturally-aware recipe recommendation for Indian
cuisine. No public resource combined large scale, multilingual provenance and
dish-level micronutrition at the time of collection; this corpus was assembled to
close that gap and to serve as the retrieval and knowledge-graph substrate for the
IndicRecipeNutri system.

**Who created it and who funded it?**
Hemprasad Yashwant Badgujar, doctoral research in Computer Engineering.
Funding: `⟨TBD⟩`.

---

## Composition

**What do the instances represent?**
Each instance is one recipe: a title, a parsed ingredient list, structured nutrition
estimates, and typed attributes (region, diet, allergens, course, cuisine, cooking
method, occasion, health tags). Free-text instructions and headnotes are **not**
included — see *Distribution*.

**How many instances are there?**

| | count |
|---|---|
| Recipes published | 224,002 (of 224,003 in the master; 1 withdrawn) |
| Published columns | 129 (of 134 in the working master; 5 withheld) |
| Distinct source sites | 380 |
| Knowledge-graph nodes | 227,499 |
| Knowledge-graph edges | 6,169,926 |
| Node types / relation types | 17 / 20 |
| Canonical ingredient vocabulary | 1,205 |
| Ingredient nodes in the graph | 1,199 |
| Benchmark queries | 66 |

The ingredient vocabulary (1,205) and the ingredient node count (1,199) differ by six.
The cause is not yet established: `⟨TBD⟩`.

**Split:** train 201,605 · test 11,202 · val 11,196. Protocol: `⟨TBD⟩` — the split
column is carried from the working master and its assignment rule is not documented
here. Do not describe it as random, temporal or cold-start until this is resolved.

**Language.** 68 distinct `Lang` values. The bulk is English (`en` 126,206, `en-US`
79,601, `en-GB` 5,508) with Indic-language originals normalised to English and the
source language retained: `hi` 3,605 + `hi-IN` 1,699, `kn-IN` 1,258 + `kn` 1,052,
`ta` 1,118, `mr` 934, `bn` 681 + `bn-IN` 9, `ml` 215, `te` 58, `gu` 26, `pa` 1. The
paper states four normalised source languages (Tamil, Kannada, Marathi, Hindi); the
column carries more, including a small tail of misdetections and **at least one
non-language value (`2 servings`, 1 row)**. The tail is a known defect.

**Is any information missing?** Yes, by design (prose) and by coverage limit
(quantities too sparse for a mass estimate on some rows). Every such case carries an
explicit per-row flag rather than a silent null.

**Does the dataset contain data that might be offensive or upsetting?**
Not to our knowledge. It contains no user-generated commentary — only recipe content.

**Does it identify subpopulations?**
It carries a `Region` attribute with 28 values (27 in the graph) describing the
recipe's declared regional origin. This is a **state-level administrative-cultural
region as declared by the source corpus** — not a claim about cuisine or culture, and
not a taxonomy we authored.

---

## Collection

**How was the data acquired?** Scraped from publicly accessible Indian and regional
recipe sites. For each recipe a source identifier and source-language tag are retained.
`robots.txt` and terms of service were honoured at collection time.

**Over what timeframe?** `⟨TBD⟩` — per-recipe collection timestamps are not present in
the v11 master. This is a gap: the paper's §3.5 states a collection timestamp is
retained per recipe, and the published schema does not carry one.

**Was an ethical review conducted?** `⟨TBD⟩`.

---

## Preprocessing

Multi-pass cleaning, then enrichment, snapshotted at every build from v6 to v11 with a
column hash and manifest. The headline steps:

- Ingredient recovery lifted usable (≥1-ingredient) coverage from 93.3% to 99.1%.
- Ingredient NER hardened the vocabulary to 1,205 canonical items, stripping
  navigation artefacts and unit-glued tokens and merging regional synonyms.
- 5,008 recipes whose stated energy violated the Atwater identity by >50% were
  recomputed from macronutrients.
- 2,858 recipes mislabelled non-vegetarian with no animal ingredient were
  reclassified.
- 185 region/dish-name mismatches auto-corrected; **496 ambiguous cases remain for
  manual review** and are published as `fix_region_review.parquet`.
- Fraction of recipes free of any data-quality defect rises from 34.1% to 93.7%,
  **with no rows removed**. Every fix is a companion column plus a per-row flag; the
  original value is preserved alongside.

**Is the raw data available?** The intermediate build masters are not published (about
18 GB of `MASTER_pre_*` snapshots). `docs/VERSIONS.md` and the per-build column lists
record the audit trail.

---

## Uses

**What has it been used for?** The IndicRecipeNutri retriever and its 66-query
benchmark; a synthetic collaborative benchmark (see `data/synthetic_interactions/`).

**What should it NOT be used for?**

1. **Not for allergen-safety decisions by end users.** See *Known defects* below. The
   allergen flags carry a measurable false-negative rate.
2. **Not as evidence about real Indian users.** The interaction log is synthetic and
   encodes region-homophily and a Western-calibrated rating skew.
3. **Not as a uniformly pan-Indian sample.** Per-region coverage is uneven; per-region
   and per-language counts are published so skew can be judged.
4. **Not for clinical or individual dietary advice.** Nutrition values are estimates
   with an explicit confidence tier, not measurements.

---

## Known defects

Measured by `scripts/audit_corpus.py`, which matches the **parsed ingredient list**
against an allergen lexicon and compares the result with the published flag. This is
independent of the flags themselves. **Every rate is an upper bound**: an ingredient
lexicon over-fires, and the negative-phrase list that suppresses plant substitutes
(`almond milk`, `peanut butter`) is not exhaustive. Full output, with examples, is in
[`../data/corpus/ALLERGEN_AUDIT.json`](../data/corpus/ALLERGEN_AUDIT.json).

**Allergen false negatives** — ingredient present in the list, flag says absent. This
is the asymmetric direction: a false negative is the harmful one.

| allergen | lexically present | flagged | false negatives | rate (upper bound) |
|---|---:|---:|---:|---:|
| sesame | 11,896 | 11,105 | 1,117 | 9.39% |
| tree_nuts | 15,227 | 29,140 | 969 | 6.36% |
| shellfish | 1,657 | 3,397 | 93 | 5.61% |
| soy | 7,901 | 8,258 | 431 | 5.46% |
| peanut | 4,312 | 9,868 | 156 | 3.62% |
| mustard | 33,772 | 34,813 | 1,057 | 3.13% |
| egg | 10,462 | 18,512 | 246 | 2.35% |
| fish | 4,601 | 4,954 | 87 | 1.89% |
| milk | 111,952 | 114,388 | 2,073 | 1.85% |
| gluten | 38,330 | 63,162 | 687 | 1.79% |

The `sesame` and `mustard` lexicons include short tokens (`til`, `rai`) that are
expected to over-fire; those two rates are the least reliable in the table.

**Diet-label conflicts** — a diet label contradicted by an ingredient.

| diet label | rows | conflicting | rate | breakdown |
|---|---:|---:|---:|---|
| Vegan | 92,170 | 3,042 | 3.30% | milk 2,960 · egg 53 · fish 42 · shellfish 23 |
| Vegetarian | 88,418 | 331 | 0.37% | fish 274 · shellfish 61 |
| Eggetarian | 14,471 | 10 | 0.07% | fish 6 · shellfish 4 |

The largest single cluster is **paneer in recipes labelled `Vegan`**: 8,815 recipes
list paneer or panir, of which 216 are labelled `Vegan` and 169 carry `has_milk =
False`. Paneer is a dairy cheese. These rows are wrong on both the diet label and the
milk flag.

**Scrape residue in `IngredientsList`.** 100 published rows, all from `SourceSite =
savorytales`, carry site sidebar navigation instead of ingredients — entries such as
*"Train Berth Guide: Lower, Upper, Middle & Side Berth"* and *"Delhi to Manali: Route,
Distance, Train, Bus, Road & Travel Guide"*. All are flagged `has_ingredients = True`,
which is wrong, and all are already listed in
`data/enrichment/quarantine_list.parquet`. The quality pipeline caught them; the
enrich-don't-remove policy kept them in place. They are **not** repaired in this
release. Filter on the quarantine list before using ingredient text at scale.

A 101st row of the same cluster, `recipe_id 211731`, additionally carried a personal
email address and was withdrawn — see below.

**Benchmark gold sets.** Fourteen of the 289 gold-set members for the query
*"Vegan recipes without milk"* (4.84%) are paneer dishes. The other five constraint
queries show no lexical conflict. See
[`../data/benchmark/GOLD_SET_AUDIT.json`](../data/benchmark/GOLD_SET_AUDIT.json).
A prior audit of an earlier benchmark version found a 46.9% contamination rate on an
analogous dairy query; that query was dropped in the v3 rebuild and the rate on its
replacement is 4.84%. **The generating mechanism is unchanged** — gold sets are
templated from the same labels the audit finds defective.

---

## Withdrawn records

**One recipe is withdrawn from the published release: `recipe_id 211731`.**

Its `IngredientsList` contained no ingredients at all — the scrape had captured the
source site's sidebar navigation with the site owner's email address attached. It is
one of 101 rows from `SourceSite = savorytales` carrying that defect; it is the only
one that also carried personal data.

The withdrawal removes 1 corpus row, 1 knowledge-graph node (`recipe::211731`), its 15
incident edges, and 1 row from each of 15 enrichment tables. It appears in no benchmark
gold set and in no synthetic interaction. Published counts are therefore **224,002
recipes, 227,499 nodes, 6,169,926 edges**, and `kg_stats.json` is recomputed from the
published tables rather than carried over from upstream.

**The working master is not modified.** The exclusion lives in
`scripts/release_config.py` as `EXCLUDED_RECIPE_IDS`, is applied by every builder, and
is enforced by `scripts/verify_release.py`, which fails the release if a withdrawn
recipe survives anywhere in the payload. Removing the entry and rebuilding restores the
row, so the withdrawal is reversible and auditable rather than a silent deletion.

Withdrawal requests are handled under [`TAKEDOWN.md`](TAKEDOWN.md).

---

## Distribution

**How is it distributed?** GitHub, archived to Zenodo on each tagged release.

**Two-tier model.** Derived, factual and structured fields are released under
CC BY 4.0 with per-recipe source attribution. **Raw recipe prose is not
redistributed**: `Description`, `Instructions`, `Ingredients` (the raw scraped string),
`Keywords` and `Enrich_Log` are withheld. `IngredientsList` — the *parsed* list — is
published, as are all nutrition, attribute and enrichment columns.

**4,807 rows (2.1%) cannot be rehydrated.** They came from pre-existing datasets
(`3a2m_indian` 3,803 · `indb` 973 · `recipenlg_indian` 30 · `indori` 1) rather than
from a scraped page, and carry a placeholder URL. They are flagged
`source_kind = "derived_dataset"` in the rehydration index. Their upstream terms are
`⟨TBD⟩` and are tracked in [`THIRD_PARTY_TERMS.md`](THIRD_PARTY_TERMS.md).

Withheld text is recoverable for the remaining 219,196 rows:
`data/corpus/rehydration_index.parquet` carries each
recipe's source URL and a SHA-256 digest of the prose the corpus was derived from, and
`scripts/rehydrate.py` re-fetches the pages under `robots.txt`. The digest lets a user
verify they reconstructed the same text. **The bundled extractor is generic and will
not reproduce the digest for most sites**; a per-site parser is needed for exact
reconstruction, and is not supplied.

**Third-party layers** — IFCT 2017, FlavorDB, FoodOn, and the RecipeDB NER training
data — are redistributed only to the extent their own terms permit. See
[`THIRD_PARTY_TERMS.md`](THIRD_PARTY_TERMS.md); those terms are `⟨TBD⟩` and gate the
1.0.0 release.

**PII.** Two mechanisms, and they cover different things.

*Pattern-based, done and recorded.* `scripts/build_corpus.py` redacts personal-data
matches (email, phone, card) from every published string column, and
`scripts/verify_release.py` re-sweeps the written artefacts and fails the release on
any survivor. **In 0.1.0 the sweep finds nothing**, because the single row that carried
an email address was withdrawn outright — see *Withdrawn records* below. The redaction
machinery stays in the build so a future corpus revision cannot reintroduce one
silently.

*Semantic, still outstanding.* The paper states a PII pass removed author names,
contact details and personal anecdotes. Author names and anecdotes are not
pattern-matchable and **no run artefact for that pass exists**, so it remains `⟨TBD⟩`.
The pattern sweep is a guard, not a substitute for it.

**Takedown.** See [`TAKEDOWN.md`](TAKEDOWN.md).

---

## Maintenance

**Who maintains it?** Hemprasad Yashwant Badgujar · `hemprasad.badagujar@gmail.com`

**Will it be updated?** Yes, on tagged releases. Each tag mints a Zenodo version DOI;
the concept DOI always resolves to the latest.

**How can others contribute?** Issues and pull requests on the GitHub repository.
Corrections to the allergen and diet labels are the most valuable contribution.
