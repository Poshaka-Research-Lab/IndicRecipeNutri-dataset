# Datasheet — IndicRecipeNutri

Following Gebru et al., *Datasheets for Datasets*, *Communications of the ACM* 64(12), 2021.

**Release version:** 0.2.0 · **Corpus build:** v17 · **Compiled:** 2 September 2026

> **Status: NOT release-ready.** The figures below were refreshed for the v15 corpus build
> (release 0.2.0) on 1 September 2026, and the licensing questions are resolved. **The
> allergen validation is not.**
>
> The per-class false-negative table in §"Allergen false negatives" is measured with the
> same lexicon that produced the labels, so it is **circular** — that caveat is stated
> there, but the headline sentence "the worst remaining rate is `peanut` at 0.46%" is not
> qualified and should not be read as an accuracy claim. An independent 794-row human
> annotation measured **28.2% false negatives on the hard-negative population**
> (sulphites 72.7%, tree_nuts 59.5%, fenugreek 50.0%, n=394 for the hard-negative stratum).
> The full held-out run that would replace the circular figure is `TODO_VERIFICATION`
> item V8 and has not been carried out.
>
> **Do not use the allergen flags for end-user safety decisions**, and do not cite the
> per-class rates below as measured accuracy. See `TODO_VERIFICATION.md` §0.1 for the
> human-measured figures.

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
| Recipes published | 220,187 (of 220,188 in the master; 1 withdrawn) |
| Published columns | 251 (of 259 in the working master v17; 8 prose columns withheld) |
| Distinct source sites | 379 |
| Knowledge-graph nodes | 223,407 |
| Knowledge-graph edges | 6,270,620 |
| Node types / relation types | 17 / 21 |
| Canonical ingredient vocabulary | ⟨TBD — recompute⟩ |
| Ingredient nodes in the graph | 988 |
| Benchmark queries | 68 |

The ingredient vocabulary artefact (`data/kg/ingredient_tier.json`, 1,205 entries) was last
regenerated on 2026-08-23 and is stale relative to this build: the graph now carries 988
ingredient nodes. The 2026-08-30 P6 pass dropped 16 zero-quantity-share tokens and the V7
withdrawal removed two more (`gajak`, `prepacks`) that existed only inside withdrawn rows.
**Regenerate the vocabulary artefact and restate this row.**

**Split — use `Split_v3`.**

| column | train | test | val | groups spanning a boundary |
|---|--:|--:|--:|--:|
| `Split_v2` | 198,099 | 11,123 | 10,966 | **2,223** |
| **`Split_v3`** | 198,064 | 11,140 | 10,984 | **0** |

> **⚠️ `Split_v2` LEAKS, measured 2026-09-02.** Its protocol says "Grouped by
> Title_normalized and stratified by Region ... to eliminate data leakage". The grouping key
> is **not case-folded** (4,682 titles differ from another only by case, and 844 such groups
> straddle a boundary) and it **ignores `dup_family_id`** entirely — the column built to
> identify near-duplicates — where a further 1,379 families straddle one.
>
> The effect: **1,325 test rows (11.9%)** and 1,264 val rows (11.5%) have a near-duplicate in
> train. Any Recall@K or NDCG@K measured on `Split_v2` is inflated by an unmeasured amount.
>
> `Split_v3` groups on connected components over **both** relations (union-find, so the
> relation is transitive), stratifies by Region at group level, and matches v2's proportions
> to within 0.02pp. Seed 20260902. `Split_v2` is retained under the same convention as the
> existing `Split_v1_leaky` column rather than renamed mid-release.
> Record: `scraped_indian_recipes/data/split_v3_meta.json`.

**Language — filter on `Lang_base`, not `Lang`.** `Lang` mixes bare ISO 639-1 with BCP-47
region subtags, so `Lang == 'en'` returns 122,569 rows and misses 85,090 more — **41% of the
English corpus**. `Lang_base` carries the primary subtag only; verified 2026-09-02 at row
level (not by matching totals): the set `Lang_base == 'en'` and the set matching
`^en([-_].*)?$` have a symmetric difference of **0**.

66 distinct non-null `Lang` values over 218,757 rows; **1,430 rows carry no language at all**
(a true null, not a sentinel). The bulk is English — 207,659 rows: `en` 122,569, `en-US`
79,581, `en-GB` 5,508, **`en-AU` 1**. Indic-language originals are normalised to English with
the source language retained: `hi` 3,603 + `hi-IN` 1,699, `kn-IN` 1,258 + `kn` 1,052,
`ta` 1,062, `mr` 934, `bn` 681 + `bn-IN` 9, `ml` 211, `te` 58, `gu` 26, `pa` 1.

A further **50 values covering 504 rows** are not listed above — `id` 78, `it` 72, `sw` 31,
`ne` 25, `es` 23 and a long tail below 20. These are misdetections, together with **at least
one non-language value (`2 servings`, 1 row)**. The tail is a known defect.

> The `en-AU` row and the null count were added 2026-09-02. The previous enumeration summed
> to 207,658 against an English total of 207,659 and read as exhaustive when it was not —
> the same shape of error as an enumeration elsewhere in this project that listed five
> sub-threshold region codes when there were ten.

**Is any information missing?** Yes, by design (prose) and by coverage limit
(quantities too sparse for a mass estimate on some rows). Every such case carries an
explicit per-row flag rather than a silent null.

**Does the dataset contain data that might be offensive or upsetting?**
Not to our knowledge. It contains no user-generated commentary — only recipe content.

**Does it identify subpopulations?**
It carries a `Region` attribute with 27 values (27 in the graph) describing the
recipe's declared regional origin. This is a **state-level administrative-cultural
region as declared by the source corpus** — not a claim about cuisine or culture, and
not a taxonomy we authored.

---

## Collection

**How was the data acquired?** Scraped from publicly accessible Indian and regional
recipe sites. For each recipe a source identifier and source-language tag are retained.
`robots.txt` and terms of service were honoured at collection time.

**Over what timeframe?** `⟨TBD⟩` — per-recipe collection timestamps are not present in
the v15 master. This is a gap: the paper's §3.5 states a collection timestamp is
retained per recipe, and the published schema does not carry one.

**Was an ethical review conducted?** `⟨TBD⟩`.

---

## Preprocessing

Multi-pass cleaning, then enrichment, snapshotted at every build from v6 to v15 with a
column hash and manifest. v13 and v14 ran in place and retained no snapshot; that is
recorded in `docs/VERSIONS.md`. The headline steps:

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

**What has it been used for?** The IndicRecipeNutri retriever and its 68-query
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
5. **FSA traffic lights are per-100 g only.** The per-portion override rule (FSA
   guidance step 3.2, p.15) is not implemented. Use `per100g_confident` alongside the
   FSA columns — a traffic light on a non-confident per-100 g value inherits that
   uncertainty.

---

## Known defects

Reported by `scripts/audit_corpus.py`, which re-scans the **parsed ingredient list** with a
second term list and compares the result with the published flag.

> **⚠️ CORRECTED 2 September 2026.** This paragraph used to say the check "is independent of
> the flags themselves" and that "every rate is an upper bound". Both were wrong, and in the
> reassuring direction. The two term lists were written by the same author and share their
> blind spots: on 2 September the R5 pass fixed eight blind spots in the labelling lexicon,
> and the audit lexicon is blind to **all eight** of them — `chestnut`, the ancient wheats,
> the `mava`/`kova` spellings, and the `oyster mushroom` false positive. Where both lists
> miss a food, this check reports zero defects for it.
>
> It is also far narrower than the lexicon it checks. **Six of sixteen classes sit under 60%
> coverage and about 92,000 flagged rows are not audited at all** — `sulphites` at 0%. A low
> rate for those classes is not evidence of anything, and the audit now publishes its own
> coverage and blind-spot count per build so this cannot be read the wrong way again.
>
> The figure that does measure accuracy is **28.2% false negatives** (T12 pilot, n=394,
> held-out human annotation).

Full output, with per-class coverage and the blind-spot probe, is in
[`../data/corpus/ALLERGEN_AUDIT.json`](../data/corpus/ALLERGEN_AUDIT.json).

## Portion weights — the density defect, and what fixing it did

**Superseded 2026-08-29 (evening).** An earlier version of this section reported the estimator
as systematically over-predicting dish weight by a median factor of 1.173 and framed the cause
as dried herbs. **Both the framing and the remedy have changed**, and the earlier text is kept
below only as the record of what was believed.

### The actual defect

`UNIT_G` priced a cup at 240 g regardless of what was in it. Measured against Recipe1M+'s
311,435 ground-truth ingredient weights, empirical grams-per-cup runs from **8 g (popcorn) to
341 g (corn syrup)** — a 43× span on one constant, across the **86.19%** of rows priced
volumetrically.

**Dried herbs were not the problem.** They are 1.63% of rows and 2.80% of the over-prediction;
fixing only them closes **1.9%** of the gap. The mass sits in `cup`: flour 30.4% of signed
error, granulated sugar 24.7%, fresh vegetables 24.2%, fresh fruit 20.4%, nuts 18.6%.

And the constant was wrong in **both** directions, not just one:

| ingredient | measured | effect of the old constant |
|---|---|---|
| salt | 288 g/cup = 6.0 g/tsp | **under**-predicted 0.83× |
| sugar, white | 201.6 g/cup | over-predicted 1.19× |
| sugar, brown | 144.0 g/cup | over-predicted 1.67× |
| syrup / honey | 339 g/cup | **under**-predicted 0.71× |

### The fix and its measured effect

A 43-entry family density table (`retrieval/enrichment/ingredient_density.py`), keyed on
**grams-per-cup only** — the ground truth scales at exactly ×16 and ×48 across all 69
reference names having n≥30 in all three units, so one number per family determines the rest.

| | before | after |
|---|---:|---:|
| dish-level median predicted/true | 1.1729 | **1.0567** |
| dish-level median APE | 21.0% | **7.9%** |
| within ±25% | 54.4% | **79.1%** |
| within ±50% | 77.2% | **92.4%** |
| ingredient-level median APE | 19.0% | **3.6%** |

Judge on the **ratio**, not MAPE. The same 0.70 g dried-basil row that scores 614% APE
contributes 4.3 g to a dish total.

### The per-100g columns HAVE now been recomputed (G3.1, 2026-08-29 evening)

Regenerating `ingredients_weights.parquet` with the density layer changed **686,237 of
2,367,005 ingredient lines (29.0%)** — 567,988 lower and **118,249 higher**. The rises are the
correction, not an error: salt and syrup were previously *under*-predicted.

Per-recipe dish weight was then recomputed (median ratio **0.9898**, IQR 0.881–1.000) and
every per-100g value and FSA light re-derived for **214,242 recipes**.

| nutrient | rows with a light | band changed | to worse | **to better** |
|---|---:|---:|---:|---:|
| fat | 151,347 | 11,021 | 7,802 | **3,219** |
| saturates | 151,737 | 10,344 | 7,764 | **2,580** |
| sugars | 151,737 | 9,443 | 7,156 | **2,287** |
| salt | 151,737 | 11,060 | 8,154 | **2,906** |

**This is a recompute, not the scalar correction originally planned.** The 1.173 factor was
measured with the old single-density converter, which the density table replaced; applying it
on top would have corrected the same cause twice. The difference is visible in the table: a
recompute moves rows in *both* directions, and **2,287–3,219 rows per nutrient move to a
BETTER band** — something a blanket multiplier cannot do.

Pre-correction values are preserved in `*_predensity` columns, and
`per100g_density_corrected` marks the affected rows. Rows whose `per100g_basis` is
`unavailable_no_servings` stay NULL: no servings count means no per-100g value, and the
density fix does not change that.

### What remains

* A **1.0567 residual** over-prediction persists. It is measured on a Western corpus, so it is
  disclosed rather than applied as a scalar — the structural cause is now fixed, and scaling on
  top would correct the same cause twice.
* **The published `per100g_*` columns were computed with the OLD estimator** and have not yet
  been recomputed with the density layer. Treat them as carrying the pre-fix bias until this
  note says otherwise.
* `grated coconut` is deliberately **absent** from the table: 10,364 Indian lines say
  grated/desiccated coconut and Recipe1M+ has too few rows to fit a value. Guessing one would
  be worse than the status quo, so those lines keep the old constant.
* Only **40.23%** of Indian ingredient lines carry a volumetric unit at all; 50.63% carry no
  unit and are unreachable by any density table.

---

### Superseded record — the earlier portion-weight section

## Portion weights and per-100g values — validated 2026-08-29, read before using them

Per-100g nutrition divides dish nutrition by an **estimated** dish weight. That estimate was
validated against Recipe1M+'s 311,435 weighed ingredients (`docs/weights_validation_v2.json`,
`docs/weights_validation_dishlevel.json`). Three findings, in order of what they cost you.

**1. The headline "MAPE 64.3%" is a metric artefact, and the earlier reading of it was
wrong.** MAPE divides by the true weight, so a 6 g spice predicted at 12 g scores 100% while
a 400 g protein predicted at 430 g scores 7.5%. Over an ingredient list that is mostly
teaspoon-scale spices, the mean reports the spices. Per ingredient, **mean APE 67.3% vs
median 19.0%** — a 3.5× ratio, the signature of a small tail dominating:

| true ingredient weight | share | MAPE | median abs. error | within ±25% |
|---|---:|---:|---:|---:|
| 0–5 g | 12.2% | 171.4% | **0.8 g** | 41.3% |
| 5–15 g | 12.5% | 67.1% | 1.6 g | 64.3% |
| 15–50 g | 17.0% | 68.4% | 6.0 g | 53.0% |
| 50–150 g | 17.0% | 59.6% | 14.0 g | 59.9% |
| 150–500 g | 21.6% | 37.2% | 32.0 g | 61.8% |
| 500 g+ | 19.6% | 41.4% | **435.2 g** | 57.9% |

**2. But that does not make the estimator good, and the reframe must not be read that way.**
The heavy band carries a **435 g median absolute error**, and heavy ingredients are exactly
what a dish total is made of. Measured where it matters — the **dish total**, over 51,235
recipes — median APE is **21.0%**, with **54.4% within ±25%** and **77.2% within ±50%**.

**3. There is a systematic directional bias.** Median predicted/true dish weight is
**1.173**, with an interquartile range of **1.020–1.452**: at least three quarters of dishes
have their total weight *over*-estimated. Dividing by a too-large total **understates every
per-100g figure**, which is the optimistic direction for a traffic light.

Its consequence is measured, not asserted. Correcting per-100g values by that factor would
move **6.3%–8.3% of rows to a worse FSA band**, every one of them in the worse direction:

| nutrient | rows with a light | would change band | share |
|---|---:|---:|---:|
| fat | 151,347 | 10,727 | 7.1% |
| saturates | 151,737 | 11,135 | 7.3% |
| sugars | 151,737 | 9,563 | 6.3% |
| salt | 151,737 | 12,568 | 8.3% |

**No such correction has been applied**, and the reason is the caveat below, not oversight:
the 1.173 factor is derived from a Western corpus. Calibrating Indian dishes on it would
substitute one unquantified bias for another. **Treat a green FSA light near a threshold as
provisional**, and prefer `per100g_confident` rows for any analysis that turns on the band.

**4. ~33% of the corpus is not validated by this at all.** Tiers D and E — the nominal
constants used when no quantity can be parsed — require `qty is None`, and every Recipe1M+
record carries a quantity, which is *how* it has a ground-truth weight. Those tiers are
**unreachable by this reference, by construction**. A number for them would need weighed
dishes whose ingredient lists lack quantities; no such corpus is held here.

**Standing caveat.** Recipe1M+ uses USDA-style ingredient names. Indian units — *katori*,
*chhatak*, *mutthi* — do not occur in it. This validates the quantity-to-gram mechanics only,
never Indian unit coverage.

## Ingredient preparation state — new feature, 2026-08-29

`CookingMethod` is recipe-level and 12-valued (fried, boiled, roasted…). It cannot say *which*
ingredient was prepared how. `"1 onion, finely chopped | 2 potatoes, boiled | 4 green chillies,
slit"` carries three operations on three ingredients, and none of it survived into any column.

Tokens like `deseeded`, `slit`, `soaked` and `boil` kept appearing in the ingredient
vocabulary and kept being proposed for deletion as junk. They are not ingredients — but they
are not junk either. They are a **second signal in the same field**.

| | value |
|---|---|
| recipes with ≥1 preparation state | **139,154 (62.1%)** |
| per-ingredient preparation rows | **451,929** |
| distinct states | 72, grouped into 7 families |
| recipes with a mass-changing prep | 54,227 (24.2%) |
| recipes with ≥2 marked components | 921 (0.4%) |

Families by ingredient mentions: cut 292,103 · thermal 68,171 · milled 42,966 ·
separated 20,189 · hydration 18,565 · mechanical 8,905 · biological 1,030.

Tables: `data/enrichment/prep_features.parquet` (per recipe) and
`data/enrichment/prep_ingredient.parquet` (per ingredient occurrence).

### What it revealed about the portion-weight estimator

The hypothesis was that mass-changing preparation explains the estimator's systematic
over-prediction. **Tested, and the answer is "partly, and disproportionately — but it is not
the cause".** On Recipe1M+'s 311,435 weighed rows, median predicted/true is 1.111 with no
prep, 2.222 for cut-only and **4.167 for mass-changing**.

That 4.167 is a metric artefact and must not be quoted alone: median *true* weight for those
rows is **18 g** against 85 g for the rest. The dominant case is dried herbs in teaspoons —
`1 teaspoon spices, basil, dried` predicted at 5 g against a true 1 g, a **4-gram error and a
7× ratio**. In absolute terms these rows are **3.6% of the corpus and carry 13.9% of the
total over-prediction**, with a median absolute error of 22.8 g against 9.6 g.

**The defect it actually exposes** is that the volume→mass conversion uses **one density per
unit, independent of the ingredient** — correct for salt or sugar, 5–7× wrong for a fluffy
dried herb. An ingredient-aware density for dried herbs and leaf spices is the concrete fix,
and `prep_state` is the feature that identifies which rows need it.

### Limits

* Extracted from `IngredientsList` text only. A preparation described solely in the method
  steps is not captured.
* **`n_components` is a lower bound.** Only 1.1% of recipes mark sections explicitly
  (`"For the dough:"`). A value of 0 or 1 means *not marked*, never *single-component*.

## Sulphites — the one class a text lexicon cannot determine

Across all 220,188 recipes the corpus mentions `sulphite`/`sulfite`/`SO2`/`preservative`
**⟨TBD — rescan⟩ times**, and `unsulphured` **⟨TBD — rescan⟩ times**. Sulphite content is a property of how a
*producer* processed a *batch*, not of the dish: two bags of raisins differ and the recipe
says "raisins" for both.

That makes sulphites unlike the other fifteen classes, which are properties of the ingredient
itself — if a recipe names paneer, it contains milk.

So the corpus carries two separate things:

| field | meaning | rows |
|---|---|---:|
| `sulphites` in `Allergens_v2` | the ingredient **is** a declared source — wine, wine vinegar, dried apricot/fig/mango | **⟨TBD — recompute⟩ |
| `sulphites_possible` (separate bool) + `sulphites_possible_src` | the ingredient is in a category **commonly** treated, and the recipe cannot say whether this instance was | **14,066 (6.39%)** |

`sulphites_possible` is **not a seventeenth class** and never enters `Allergens_v2` — the
16-class invariant asserted by `gate_v12.py` and `verify_release.check_kg_allergens` is
load-bearing, and it is what caught the knowledge graph being built from a 12-class column.

**Consumer contract.** Avoiding sulphites → treat `sulphites_possible` as **unsafe**
(fail-closed, per Codex CXC 80-2020: "never guess or assume that an allergen is not present").
Computing prevalence → treat it as **unknown** and exclude it from both numerator and
denominator; counting it as present overstates sulphite prevalence roughly threefold.

Terms: raisin/sultana/kishmish (6,956 new), amchur/mango powder (5,169), desiccated coconut
(1,973), tutti frutti (388), candied cherry (140). **`vinegar` was measured and rejected** —
10,280 rows at 24.9% labelled, and that 24.9% is entirely *wine* vinegar; plain distilled
vinegar is not a declared source and adding it would have inverted the corpus's own policy on
7,719 rows. `pickle` rejected likewise: Indian achar is oil- and salt-preserved.

## Ingredient lists that are not ingredient lists — re-measured 2026-09-01

A share of this corpus was scraped with the wrong field captured. `449. raw banana and paneer
kofta curry` has cooking *instructions* in its `IngredientsList`; one of six `Palak paneer`
records lists "spinach | garlic | ginger | green chilli" and no paneer; `recipe_id 211731` was
withdrawn for PII because its list was the site's sidebar navigation.

Six detectors now flag this, per row (`badlist_*` columns):

| detector | rows | share |
|---|---:|---:|
| instruction text | 887 | 0.40% |
| prose | 892 | 0.41% |
| site navigation | 464 | 0.21% |
| empty | 731 | 0.33% |
| metadata captured instead | 356 | 0.16% |
| single over-long item | 17 | 0.01% |
| **any** | **2,743** | **1.25%** |
| **hard** — the whole field is wrong | **1,384** | **0.63%** |

**The consequence that matters is not lost information but a confident wrong answer.** A
broken list yields no allergen match, so the row is labelled `none_detected` — reported
allergen-free:

* hard-broken rows labelled `none_detected`: **⟨TBD — recompute⟩**
* `none_detected` rate on hard-broken rows: **⟨TBD — recompute⟩**
* `none_detected` rate on clean rows: **⟨TBD — recompute⟩** → **⟨TBD⟩× enrichment**

It concentrates by scraper, so it is a source-integrity problem rather than a parsing one:
⟨TBD — recompute per-site hard-broken shares⟩

**1,808 recipes (0.82%) have no `has_ingredient` edge in the knowledge graph at all** — the
subset where zero tokens survived parsing. This was recorded in four planning documents as
"7", which was a coconut-labelled subset count generalised without a corpus-wide scan.

**Nothing has been dropped or quarantined.** These are flags; disposition is a separate
decision. Use `badlist_hard` to exclude the worst rows from any analysis where an absent
allergen label would be read as an absent allergen.

**Allergen false negatives** — ingredient present in the list, flag says absent. This
is the asymmetric direction: a false negative is the harmful one.

**The `coverage` column is the one to read first.** It is the share of flagged rows the audit
lexicon can even match. The `disagreement` rate is computed only over the rows it matched, so
where coverage is low the rate describes a narrow slice and says nothing about the rest.
`sulphites` is in the table at 0%: it was previously omitted because its rate was `n/a`, which
made an entirely unaudited class invisible rather than visible.

| allergen | lexically present | flagged | coverage of flagged | unaudited rows | disagreements | rate over matched |
|---|---:|---:|---:|---:|---:|---:|
| **sulphites** | 0 | 5,121 | **0%** | **5,121** | — | **no audit at all** |
| shellfish | 1,636 | 4,242 | 38% | 2,615 | 9 | 0.55% |
| peanut | 4,284 | 10,646 | 40% | 6,397 | 35 | 0.82% |
| tree_nuts | 15,009 | 32,518 | 46% | 17,526 | 17 | 0.11% |
| egg | 10,546 | 21,012 | 50% | 10,469 | 3 | 0.03% |
| gluten | 38,116 | 68,628 | 55% | 30,562 | 50 | 0.13% |
| asafoetida | 22,377 | 28,958 | 77% | 6,585 | 4 | 0.02% |
| fenugreek | 17,865 | 19,781 | 90% | 1,928 | 12 | 0.07% |
| soy | 8,040 | 8,717 | 90% | 847 | 170 | 2.11% |
| fish | 4,844 | 5,351 | 90% | 510 | 3 | 0.06% |
| sesame | 11,865 | 12,965 | 91% | 1,148 | 48 | 0.40% |
| mustard | 33,634 | 36,172 | 93% | 2,557 | 19 | 0.06% |
| milk | 110,866 | 115,942 | 95% | 5,270 | 194 | 0.17% |
| coconut | 35,528 | 36,677 | 97% | 1,186 | 37 | 0.10% |
| celery | 2,317 | 2,344 | 99% | 32 | 5 | 0.22% |
| tamarind | 12,053 | 12,080 | 100% | 44 | 17 | 0.14% |

**Six of sixteen classes have under 60% coverage, and about 92,000 flagged rows are not
audited by this check at all.** For those rows a low disagreement rate is not evidence of
anything.

> **⚠ Read these rates with the circularity in mind.** Before 2026-08-29 the labels and this
> audit came from partly different lexicons, so a disagreement was informative — that is how
> the shellfish plural bug (5.61%) and the sesame gap (9.17%) were found. A full 16-class
> rescan has since applied essentially *this* lexicon to the labels, so the two now agree
> **partly by construction**. A 0.00% row means "no row where this lexicon fires lacks the
> flag"; it does **not** mean "no false negatives remain".
>
> What the rescan cannot see is unchanged, and is the real residual: an ingredient list that
> never names the allergen. `449. raw banana and paneer kofta curry` has cooking instructions
> in its ingredients field; one `Palak paneer` record lists no paneer. The title channel
> catches some of these; nothing catches an incomplete list that also has an uninformative
> title. **An independent channel — a held-out human-labelled sample — is what would give
> these rates their meaning back, and it does not exist yet.**


`sulphites` is **absent from this table because it has no ingredient lexicon**, not because
it scored zero. Its 5,121 flags come from the source corpus only, and no independent channel
checks them. An empty row would have read as "audited, clean"; it has not been audited.

**Two detection channels, 2026-08-29.** Labels are drawn from the ingredient text and,
separately, from the recipe TITLE. The title channel exists because a large share of this
corpus was scraped with a truncated or wrong-field ingredient list — one `Palak paneer`
record lists "spinach | garlic | ginger | green chilli" and no paneer, and
`449. raw banana and paneer kofta curry` has cooking *instructions* in its ingredients field.
Such rows were being reported allergen-free.

It is applied conservatively and its output is **kept separable**: `allergens_title_src`
names the classes a row got from its title, so a consumer can discount them. 4,052 rows are
affected.

* **Applied** where the title word names the food and is not used as a comparison:
  shellfish, fish, peanut, tree_nuts, coconut, sesame, tamarind, fenugreek, mustard, egg;
  milk restricted to the paneer family; gluten restricted to bread words and to
  rava/sooji/semolina; soy restricted to soybean and soya-chunk.
* **Refused, with the counterexample.** `halwa` / `upma` (1,963 rows) — *Moong Daal Halwa*
  is sugar, ghee and nuts and *Quinoa Pilaf (Upma)* is quinoa; neither contains wheat.
  Bare `tofu` (202 rows) — *Paneer Shashlik … In Mood For A Tofu …* names tofu as a
  comparison. `rava` is skipped when the title names a non-wheat grain, because
  *Foxtail Millet Rava Idli* is millet semolina.
* **12,091 titles are suppressed** by a free-from or substitute phrasing (`without`,
  `eggless`, `vegan*`, `mock`), which is what stops *Palak Paneer - Veganized!* — a tofu
  dish — being labelled milk.
* **Rows with no assessment are never touched.** A title tells you one allergen is present;
  it does not tell you the other fifteen are absent. Labelling an `unknown` row would
  convert it into an apparently-assessed one and make it read as safe for every class not
  named — a fail-open. The 1,091 unassessed rows keep that status.

**`tree_nuts` evidence breakdown (2026-08-29).** All 31,750 flagged rows were classified
by the evidence supporting them:

| evidence class | rows | share |
|---|---:|---:|
| text-confirmed — a FALCPA tree nut is named in the ingredient list | 31,575 | 99.45% |
| kg-edge — the graph asserts it where text does not | 154 | 0.49% |
| coconut-only — coconut is the sole nut present | 21 | 0.07% |
| **unexplained** | **0** | **0.00%** |

An earlier internal audit reported 41% of this label as unexplained. That figure was an
artefact of a checker whose regex lacked plural forms (`almond` does not match
"almonds"); it is withdrawn. Three ingredients were also excluded as decoys because they
are **not** tree nuts despite their names: **water chestnut / singhara** (an aquatic
vegetable), **makhana / fox nut** (a lotus seed), and **chestnut mushroom** (a mushroom).

The false-negative rate fell from 6.36% to 0.13% on 2026-08-29 when 2,668 recipes naming a
genuine tree nut, and carrying no flag, were labelled. The residual 20 are single-mention
edge cases. Rows changed by that pass are marked `allergens_tn_fix = True`, so the change
is auditable and reversible.

### Semantic PII — scanned, with an artefact, and the paper's wording needs correcting

Pattern-based redaction (email, phone, card) runs in `build_corpus.py` and reports zero
matches. The *semantic* half — author names, personal anecdotes — previously had no run
artefact. It now does: `data/corpus/PII_SEMANTIC_SCAN.json`, produced by
`scripts/scan_semantic_pii.py`.

**Anecdotes are not published at all.** The eight withheld columns (`Description`,
`Instructions`, `Ingredients`, `Keywords`, `Enrich_Log`, `IngredientsList_pretitle`,
`IngredientsList_preclean`, `RecipeName_preclean`) are dropped at build time —
verified, `prose_columns_present: []`. Anecdotes live in prose, so the exposure is removed
structurally rather than mitigated. A rehydrating user who re-fetches the source page reads
the publisher's own page under the publisher's own terms.

**Names do remain in `RecipeName`, and that is deliberate:**

| | count |
|---|---:|
| titles with a possessive name | 2,132 |
| ... containing a kinship term (`Amma's`, `Mom's`, `Dad's`) | 488 |

Inspection of the candidates shows three kinds, none of which is a leaked identifier:

1. **Public figures and brands** — *Gordon Ramsay's Tikka Masala*, *Nigella's Masala
   Omelette*, *Aarti Sequeira's Aloo Gobi*, *Cook's Illustrated*. This is attribution, and
   §3.5 **requires** per-recipe source attribution.
2. **Kinship terms** — *Amma's Daal*, *Dad's Biryani*. These identify nobody.
3. **First names on community submissions** — *Charishma's Paneer Butter Masala*,
   *Alok's Shahi Paneer*. A name the submitter themselves attached to a recipe they
   published publicly.

No contact details, addresses or identifiers accompany any of them; the pattern sweep
confirms that independently.

> **Correction required in accompanying text.** Any statement that the PII pass *"removed
> author names"* is **inaccurate** — names were retained, on purpose, as attribution. The
> defensible claim is narrower: *personal contact identifiers were pattern-redacted (zero
> matches), free-text prose is withheld entirely, and attributed names are retained as
> source credit.* The 2,116 non-publisher candidates are listed in the scan artefact and
> remain available for human review if a stricter policy is later adopted.

### Collection timestamps — NOT retained per recipe

The corpus carries **no per-recipe collection timestamp**, and none is recoverable. Any
statement that per-recipe scrape dates are retained is incorrect and should be removed
from accompanying text.

What can be established is a **collection window, at source-site granularity only**: the
modification times of the 410 per-site CSV artefacts span **2026-06-21 to 2026-06-28**,
covering ⟨TBD⟩ of the 379 source sites in the corpus (⟨TBD⟩% of rows).

This is deliberately **not** published as a column. Two reasons:

1. A file mtime bounds the collection date from above; it is not a recorded scrape time.
   A later copy, move or re-encode resets it.
2. 330 of the 410 artefacts share a single date (2026-06-28), which is the signature of a
   bulk file operation rather than 330 same-day scrapes.

Publishing that as `scrape_date` would put weak evidence into the schema where it would
subsequently be cited as fact. The window above is the honest claim, and it is stated here
rather than encoded per row.

### ⚠ Per-100g basis — corrected 2026-08-29, and the error ran in the unsafe direction

`per100g_X` was computed as `Nut_X / grams_per_serving_v3 * 100`. The ratio test confirms
that exactly (published ÷ implied = 1.0000 over 209,482 rows). But the two inputs sit on
different bases:

| input | basis | evidence |
|---|---|---|
| `Nut_X` | **per serving** | median 244.7 kcal — a plausible serving |
| `grams_per_serving_v3` | **total dish**, despite the name | median 777.5 g — not a per-person serving. Divided by the median 4 servings it gives 210.8 g, which is credible |

So per-serving nutrition was divided by whole-dish grams, understating every per-100g value
by roughly the servings count. **Median `per100g_kcal` was 32.0** — below thin broth, and
impossible for cooked food. ⟨leave — this is the pre-fix state, see why⟩

**This propagated into the FSA traffic lights, in the direction that matters:**

Shares are of *labelled* rows (206,356 before, 151,347 after):

| nutrient | before (g / a / r) | after (g / a / r) | Recipe1M+ reference (green) |
|---|---|---|---:|
| fat | **74.3** / 22.9 / 2.8 | 29.4 / 52.9 / 17.7 | ~35% |
| saturates | **84.0** / 12.4 / 3.6 | 51.1 / 28.7 / 20.2 | ~44% |
| sugars | **90.7** / 8.0 / 1.3 | 67.7 / 23.5 / 8.8 | ~43% |
| salt | **76.3** / 21.0 / 2.7 | 37.3 / 53.9 / 8.8 | ~51% |

The corrected distributions sit close to the Recipe1M+ reference on fat and saturates.
Sugars remains greener than the reference (67.7% vs ~43%), which is expected for a savoury
Indian corpus rather than a defect — but it has not been independently validated and should
not be presented as one.

A nutrition dataset with a health framing was labelling **three-quarters to nine-tenths of
its recipes "green"**. For a health signal, understating is the unsafe direction.

**The band logic was never wrong** — it scores 100.000% against Recipe1M+'s labels under
matched thresholds. The inputs were wrong, not the classifier.

**The fix:** `per100g_X = Nut_X × Servings_num / grams_per_serving_v3 × 100`, applied only
where `Servings_num` is known and positive. Median `per100g_kcal` is now **168.4**.

**The cost, and it is deliberate:** per-100g coverage falls from ~93.5% to **80.99%** (178,333 rows carry `per100g_available_v3`; 168,318 are FSA-labelled in the release).
Where servings are unknown the value is **NULL**, not a figure known to be four-fold wrong —
a missing number is honest; an understatement inside a health label is not. `per100g_basis`
records which of the two applies per row, and every prior value is preserved in
`<column>_uncorrected` so nothing was destroyed.

Two flags that over-claimed were also corrected: `per100g_available_v3` (214,289 → 151,737, now **178,333** after the v13 recompute) and `per100g_confident` (162,021 → 134,440, now **149,276**) were asserting availability over rows the fix had nulled. Prior values kept in `<column>_uncorrected`.

Five gate checks now guard this: the basis column must exist, median `per100g_kcal` must
sit in 60–350, and `fsa_fat` green share must stay under 60%.

### Nutrition provenance — there is no Indian composition data in this dataset

Established 2026-08-29 by reading `primarysource` in the two supplementary spreadsheets:

| FCT `source` label | rows | what it actually is | licence |
|---|---:|---|---|
| `USDA` | 7,793 | USDA SR Legacy | **US Government public domain** |
| `INDB-US` | 54 | **USDA** (`primarysource: usda`) — mislabelled | public domain |
| `INDB-UK` | 144 | **UK CoFID / McCance & Widdowson** (`primarysource: ukfct`) — mislabelled | Open Government Licence |

**Consequences, all of them corrections to earlier claims:**

1. **`IFCT 2017` is not used.** No IFCT data is read anywhere; `compute_ifct.py` reads USDA
   SR Legacy plus the two spreadsheets above. "IFCT" names the **42-nutrient schema** only.
   The file is called `fct_ifct.parquet` because it follows that column layout.
2. **`INDB` is not used either.** The two `INDB-*` labels are misattributions; the data is
   USDA and UK CoFID. There is **no Indian Nutrient Databank content** in the table.
3. **`nut_indb_frac` is therefore misnamed** and is **published as `nut_suppl_fct_frac`** —
   the share of dish calories drawn from the supplementary tables rather than USDA SR
   Legacy. The quantity is unchanged; only the name, which asserted India-grounding that
   does not exist.

**The upside:** the nutrition layer is **97.5% US Government public domain**, with the
remaining 144 rows under the Open Government Licence. It carries no NonCommercial or
ShareAlike obligation of any kind.

**The limitation, stated plainly:** this dataset applies an Indian-schema, Indian-recipe
corpus to **Western food composition values**. Grounding in Indian composition data (IFCT
2017 or INDB proper) remains future work and must not be claimed until it is done.

### Per-ingredient gram estimates — measured accuracy, not just coverage

`ing_weight_confident_frac` (corpus mean **0.590**) reports how many of a recipe's
ingredients the estimator *believed* it could convert. It says nothing about how close
those grams are. Measured 2026-08-29 against Recipe1M+'s **311,435 ingredient rows with
ground-truth weights** (`weights_validation_recipe1m.json`):

| tier | rows | share | MAPE | median abs. error |
|---|---:|---:|---:|---:|
| A — unit + quantity ("confident") | 305,120 | 98.0% | **64.3%** | 9.6 g |
| B — quantity + known count-food ("confident") | 3,489 | 1.1% | 156.9% | 0.4 g |
| C — quantity, unknown food | 2,826 | 0.9% | 281.6% | 467.2 g |

**Within-tolerance rate for the confident tiers (A+B): 35.7% within ±10%, 57.5% within
±25%, 63.5% within ±50%.**

Two things follow, and both belong on any per-serving figure derived from these weights:

1. **"Confident" means the parser found a unit and a quantity — not that the gram value is
   accurate.** A tier-A estimate lands within a quarter of the truth about 58% of the time.
2. **The estimator over-predicts systematically**: median predicted 113.4 g against median
   true 84.0 g on the same rows.

**What this validation could NOT do.** Recipe1M+ always supplies a quantity and unit, so
tiers **D and E produced zero rows** — the nominal-constant fallbacks, roughly a third of
our own corpus, remain **unvalidated**. Their error is still unknown, and summing them
still yields a plausible-looking total from no evidence.

**Scope caveat.** Recipe1M+ is a Western corpus with USDA-style ingredient names; `katori`,
`chhata` and `mutthi` do not occur in it. This measures the quantity-to-gram *mechanics*,
not coverage of Indian units.

**Note on `sulphites`.** All 5,121 sulphite flags come from source-declared allergen
metadata; **`lexical_present` is 0**, meaning not one is corroborated by an ingredient
string. That is expected -- sulphites occur in wine, vinegar and dried fruit and are
declared on a label rather than named in a recipe -- but it does mean this flag rests
entirely on an uncorroborated upstream source and its precision is unmeasured. Do not
present it with the same confidence as the text-corroborated classes.

**Note on `flagged` exceeding `lexically present`.** For several allergens the flagged
count is far higher than the lexical count (gluten 63,162 vs 38,330; peanut 9,868 vs
4,312). This is expected and is not an error: flags come from the union of a text lexicon
and the knowledge-graph `has_ingredient` channel, and the lexical column counts only the
text side. It does mean the "false positives" implied by the difference are unmeasured.

A curated composite-spice blend map (`blend_allergen_map_v1.yaml`) expanded coverage for 6 blends (chaat masala, sambar powder, rasam powder, panch phoron, puliyogare masala, podi), adding 9,642 flags across 8,128 recipes. **Celery was closed on 2026-08-29** (79.12% -> 0.00%, 1,902 rows labelled from ingredient text; rows marked `allergens_celery_fix`). The lexicon is `celery` and `celeriac` only. **`ajwain` / carom seed is deliberately excluded** -- it is routinely conflated with celery seed in recipe writing but is a different genus (*Trachyspermum ammi* vs *Apium graveolens*), and including it would have added 5,240 false positives to a safety label. `radhuni` ("wild celery", also *Trachyspermum*) is excluded for the same reason. The worst remaining rate **as measured by the lexicon against itself** is `peanut` at 0.46%. That number is circular and is not an accuracy claim: the independent human annotation measured 28.2% false negatives on the hard-negative population. See the status note at the top of this datasheet. The `sesame` and `mustard` lexicons include short tokens (`til`, `rai`) that are expected to over-fire; those two rates are the least reliable in the table.

**Diet-label conflicts** — a diet label contradicted by an ingredient.

| diet label | rows | conflicting | rate | breakdown |
|---|---:|---:|---:|---|
| Vegan | 85,205 | 282 | 0.33% | milk 204 · egg 72 · fish 4 · shellfish 2 |
| Vegetarian | 88,805 | 13 | 0.01% | fish 11 · shellfish 2 |
| Eggetarian | 14,269 | 0 | 0.00% | fish 0 · shellfish 0 |

The largest single cluster is **paneer in recipes labelled `Vegan`**: 9,314 recipes
list paneer or panir, of which 9 are labelled `Vegan`. Paneer is a dairy cheese.
⟨TBD — recompute the `has_milk = False` subset of those 9.⟩

**Scrape residue in `IngredientsList` — resolved in this build.** In 0.1.0, 100 published
rows from `SourceSite = savorytales` carried site sidebar navigation instead of ingredients
and were flagged `has_ingredients = True`. The V7 non-recipe pass withdrew them:
`savorytales` now contributes 167 published rows, none of which trips `badlist_nav` or
`badlist_hard`. Corpus-wide, 464 rows still trip `badlist_nav`; filter on `badlist_hard`
(1,384 rows) before using ingredient text at scale.

A 101st row of the same cluster, `recipe_id 211731`, additionally carried a personal
email address and was withdrawn — see below.

**Benchmark gold sets.** One of the 245 gold-set members for the query
*"Diabetic-Friendly recipes without tree_nuts"* (0.41%) carries a contradicting flag and
is also a lexical candidate. The other six constraint queries show no conflict. See
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
gold set and in no synthetic interaction. Separately, the **V7 non-recipe pass withdrew
3,815 rows that were never recipe pages** — they are removed from the master, not filtered
at build time, and preserved in full at `MASTER_nonrecipe_quarantine_v7.csv`
(`rows_destroyed 0`). Record: `_docs/V7_NONRECIPE_2026-09-01.md`. Published counts are
therefore **220,187 recipes, 223,406 nodes, 6,270,620 edges**, and `kg_stats.json` is
recomputed from the published tables rather than carried over from upstream.

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
**CC BY-NC-SA 4.0** with per-recipe source attribution. 9,384 recipes (4.26%) come from
upstream datasets under NC or NC-SA terms and are retained by decision, so those terms
apply to the whole corpus; the FlavorDB flavour layer in `data/kg_flavor/` is CC BY-NC-SA
3.0. See `LICENSE-DATA`. **Raw recipe prose is not
redistributed**: `Description`, `Instructions`, `Ingredients` (the raw scraped string),
`Keywords` and `Enrich_Log` are withheld, as are three pre-edit backup columns
(`IngredientsList_pretitle`, `IngredientsList_preclean`, `RecipeName_preclean`) that
duplicate published columns. `IngredientsList` — the *parsed* list — is
published, as are all nutrition, attribute and enrichment columns.

**4,807 rows (2.18%) cannot be rehydrated.** They came from pre-existing datasets
(`3a2m_indian` 3,803 · `indb` 973 · `recipenlg_indian` 30 · `indori` 1) rather than
from a scraped page, and carry a placeholder URL. They are flagged
`source_kind = "derived_dataset"` in the rehydration index. Their upstream terms are verified and documented in [`THIRD_PARTY_TERMS.md`](THIRD_PARTY_TERMS.md).

Withheld text is recoverable for the remaining 215,380 rows:
`data/corpus/rehydration_index.parquet` carries each
recipe's source URL and a SHA-256 digest of the prose the corpus was derived from, and
`scripts/rehydrate.py` re-fetches the pages under `robots.txt`. The digest lets a user
verify they reconstructed the same text. **The bundled extractor is generic and will
not reproduce the digest for most sites**; a per-site parser is needed for exact
reconstruction, and is not supplied.

**Third-party layers** — USDA SR Legacy, UK CoFID, FoodOn and FlavorDB — are
redistributed only to the extent their own terms permit. **IFCT 2017 and RecipeDB NER
are not used and never were**; see `THIRD_PARTY_TERMS.md`. See
[`THIRD_PARTY_TERMS.md`](THIRD_PARTY_TERMS.md); those terms are verified and documented.

**PII.** Two mechanisms, and they cover different things.

*Pattern-based, done and recorded.* `scripts/build_corpus.py` redacts personal-data
matches (email, phone, card) from every published string column, and
`scripts/verify_release.py` re-sweeps the written artefacts and fails the release on
any survivor. **In 0.2.0 the sweep finds nothing**, because the single row that carried
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
