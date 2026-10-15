<div align="center">

# IndicRecipeNutri

**A 219,384-recipe Indian corpus with parsed ingredients, a 17-class allergen surface,
dish-level nutrition, and a typed knowledge graph of 6.43 million edges.**

Built for retrieval and recommendation research that needs *culturally specific* food data —
and that needs to know exactly where the data is weak.

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22512534.svg)](https://doi.org/10.5281/zenodo.22512534)
[![Version](https://img.shields.io/badge/candidate-0.12.0-blue.svg)](CHANGELOG.md)
[![Data licence: CC BY-NC-SA 4.0](https://img.shields.io/badge/data-CC%20BY--NC--SA%204.0-lightgrey.svg)](LICENSE-DATA)
[![Code licence: MIT](https://img.shields.io/badge/code-MIT-blue.svg)](LICENSE-CODE)
[![Format: Parquet](https://img.shields.io/badge/format-Parquet%20%2B%20zstd-orange.svg)](#the-data)
[![Size: 474 MB](https://img.shields.io/badge/size-495%20MB-informational.svg)](#the-data)
[![Verified](https://img.shields.io/badge/release-self--verifying-brightgreen.svg)](#verify-what-you-downloaded)

[Quick start](#-quick-start-60-seconds) ·
[What you get](#what-you-get) ·
[The data](#the-data) ·
[Knowledge graph](#knowledge-graph) ·
[Allergens — read first](#-allergens-read-this-first) ·
[Verify your copy](#verify-what-you-downloaded) ·
[Cite](#citation)

</div>

## 0.12.0 local candidate

Adds provisional quality flags, separate allergen evidence/UNKNOWN status, item attributes, nutrition diagnostics, and a published-attribute synthetic log (50,000 fictional users; 1,000,000 events). Legacy data and splits are preserved. See [scope, checks and limitations](docs/quality_0_12_0/README.md). Independent semantic validation and instruction-derived flag publication clearance remain separate requirements; this local update is not a remote release.


> [!NOTE]
> **New in 0.11.0, and additive.** [`data/cultural_context/`](data/cultural_context) adds an occasion
> registry and dietary-rule definitions imported as **silver** data with structured citations.
> The rules are never executed as constraints. [`data/historical_snapshot/`](data/historical_snapshot) adds a
> recipe-ID crosswalk to a historical snapshot. No existing file, identifier, count or split
> changed. The `snapshot_split_*` columns are historical and must never be used as a split.
> See the [changelog](CHANGELOG.md).

---

## At a glance

| | |
|---|---|
| **Recipes** | 219,384, across **378 source sites** |
| **Columns** | 270; field definitions and current fill rates are in the generated data dictionary |
| **Knowledge graph** | 222,537 nodes · **6,432,585 edges** · 17 node types · 22 relation types |
| **Allergen classes** | 17, with an explicit `unknown` sentinel on 2,478 recipes |
| **Benchmark** | 67 fixed queries, 8 templates, graph-derived silver labels |
| **Interaction log** | 50,000 users · 990,273 ratings · 10-core splits, zero train/test leakage |
| **Ingredient text** | 100% English/Roman; original script kept as provenance |
| **Licence** | data CC BY-NC-SA 4.0 · code MIT |

> [!TIP]
> **New here? Read [`docs/DATASHEET.md`](docs/DATASHEET.md) before you build on this.**
> It documents measured defects rather than hiding them. The two that bite people most are
> [Allergens](#-allergens-read-this-first) and
> [Nutrition grounding](#nutrition-grounding-read-this-before-computing-anything).

---

## ⚡ Quick start (60 seconds)

```bash
git clone https://github.com/Poshaka-Research-Lab/IndicRecipeNutri-dataset
cd IndicRecipeNutri-dataset
git lfs pull                      # large artefacts are in Git LFS
pip install pandas pyarrow
```

```python
import pandas as pd

recipes = pd.read_parquet("data/corpus/recipes_structured.parquet")
print(len(recipes), "recipes,", len(recipes.columns), "columns")
# 219384 recipes, 270 columns
```

<details>
<summary><b>Four things you can do in one line each</b></summary>

```python
# 1. High-protein vegan mains
recipes[(recipes.Diet == "Vegan")
        & (recipes.Course == "Main Course")
        & (recipes.per100g_protein > 10)]

# 2. Everything from one state-level region
recipes[recipes.Region == "Kerala"]                    # 11,527 recipes

# 3. Recipes that are green on all four FSA traffic lights
recipes[(recipes.fsa_fat == "green") & (recipes.fsa_saturates == "green")
        & (recipes.fsa_sugars == "green") & (recipes.fsa_salt == "green")]

# 4. The knowledge graph, as edges
kg = pd.read_parquet("data/kg/kg_edges.parquet")       # 6,432,585 rows
kg[kg.rel == "contains_allergen"]                      # 491,208 rows
```

</details>

<details>
<summary><b>Allergen filtering — use the accessor, not the raw column</b></summary>

```python
from scripts.allergen_surface import load_wide

wide = load_wide()          # recipe_id × 17 classes, unassessed sentinel intact
```

Do **not** flatten `unknown` to `False`. It means *"never assessed"*, not *"safe"* — see
[Allergens](#-allergens-read-this-first).

</details>

---

## What you get

<table>
<tr>
<td width="33%" valign="top">

### 🍲 Corpus
**219,384 recipes** from 378 sites, parsed into 270 typed columns. Ingredients normalised to
English/Roman with the original script retained as provenance.

</td>
<td width="33%" valign="top">

### 🕸️ Knowledge graph
**6.43M edges** over 17 node types — ingredients, compounds, allergens, regions, methods,
health tags — with edge-level evidence preserved.

</td>
<td width="33%" valign="top">

### ⚠️ Allergen surface
**17 classes**, fail-closed, with an explicit `unknown` sentinel that never collapses to
"safe". Ships with its own independent audit.

</td>
</tr>
<tr>
<td valign="top">

### 🥗 Nutrition
Dish-level estimates and FSA traffic lights, with units and bases declared
machine-readably — and its Western grounding stated plainly.

</td>
<td valign="top">

### 🎯 Benchmark
**67 fixed retrieval queries** over 8 templates with graph-derived gold sets and a published
contamination audit.

</td>
<td valign="top">

### 👥 Interaction log
**990,273 synthetic ratings** from 50,000 profiled users, with 10-core splits, zero leakage
and a hard diet-compatibility constraint.

</td>
</tr>
<tr>
<td colspan="3" valign="top">

### 🗓️ Occasion context and snapshot crosswalk (0.11.0)
444 occasions and 24 dietary-rule definitions with structured citations and evidence tiers,
**silver and never executed**, plus an exact-ID crosswalk to a historical snapshot. No new
recipes. See [`data/cultural_context/`](data/cultural_context) and [`data/historical_snapshot/`](data/historical_snapshot).

</td>
</tr>
</table>

---

## How it is built

```mermaid
flowchart LR
    A["378 recipe sites<br/>+ open datasets"] --> B["parse & normalise<br/>ingredients → English/Roman"]
    B --> C["corpus<br/>219,384 × 270"]
    C --> D["nutrition<br/>USDA-grounded"]
    C --> E["allergens<br/>17 classes, fail-closed"]
    C --> F["knowledge graph<br/>222,537 nodes / 6.43M edges"]
    F --> G["benchmark<br/>67 queries + gold sets"]
    C --> K["interactions<br/>50K users / 990K ratings"]
    X["occasion context + snapshot crosswalk<br/>silver, staged from 2 repos"] --> I
    D & E & F & G & K --> I["verify_release.py<br/>licence · counts · PII · checksums"]
    I --> J(["release + DOI"])
```

Nothing is published that the verifier has not passed. A failing check aborts the release
instead of shipping it — see [Verify what you downloaded](#verify-what-you-downloaded).

---

## The data

| path | size | what is in it |
|---|---:|---|
| [`data/corpus/`](data/corpus) | 198 MB | the recipe table, plus long-form allergen / nutrition / label / quality tables, the rehydration index and the allergen audit |
| [`data/enrichment/`](data/enrichment) | 159 MB | 27 companion tables — nutrition, region, diet, quality flags, ingredient weights |
| [`data/provenance/`](data/provenance) | 62 MB | build records and per-field change history |
| [`data/interactions/`](data/interactions) | 35 MB | synthetic interaction benchmark v4 — 50,000 users, 990,273 ratings, with its own datasheet |
| [`data/kg/`](data/kg) | 34 MB | nodes, edges, typed store, ingredient vocabulary, pairing + substitution layers |
| [`data/benchmark/`](data/benchmark) | 0.4 MB | 67 queries, gold sets, contamination audit |
| [`data/kg_flavor/`](data/kg_flavor) | 0.1 MB | FlavorDB compound layer, kept separable (CC BY-NC-SA **3.0**) |
| [`data/cultural_context/`](data/cultural_context) | 0.4 MB | **0.11.0** — occasion registry, dietary rules, citations and node links; silver, never executed |
| [`data/historical_snapshot/`](data/historical_snapshot) | 5 MB | **0.11.0** — exact-ID crosswalk and historical split labels of a snapshot; not new recipes |

Parquet, zstd-compressed, 50,000-row groups. **≈495 MB** total.

> [!NOTE]
> **Large files are in Git LFS.** A clone without `git-lfs` gives you 130-byte pointer stubs,
> and `verify_release.py --strict-checksums` fails loudly on them rather than validating a
> stand-in. Run `git lfs pull`. The Zenodo archive always contains the real files — the
> release workflow downloads its own zipball and fails the build if it ever finds pointers.

<details>
<summary><b>What the corpus covers</b></summary>

| facet | distinct | most common |
|---|---:|---|
| `Region` | 27 | Pan-Indian (135,018) · North India (12,112) · South India (11,579) · Kerala (11,527) · Tamil Nadu (11,375) |
| `Cuisine` | 53 | Indian (146,487) · American (12,718) · South Indian (9,879) · Kerala (9,403) |
| `Course` | 12 | Main Course (91,036) · Dessert (37,043) · Breakfast (19,421) |
| `Diet` | 5 | Vegetarian (88,488) · Vegan (78,350) · Non-Vegetarian (32,601) · Eggetarian (15,558) |

`Pan-Indian` dominates because most sources do not declare a region. **Slice on the
state-level regions for cultural work**, and treat `Pan-Indian` as "unlabelled", not as a
region.

</details>

---

## Worked examples

Real queries against the published payload, with the numbers they return.

<details open>
<summary><b>Regional nutrition contrast</b></summary>

```python
import pandas as pd

r = pd.read_parquet("data/corpus/recipes_structured.parquet",
                    columns=["Region", "Diet", "per100g_kcal", "HealthGrade"])

r[r.Region.isin(["Kerala", "Punjab"])].groupby("Region").per100g_kcal.median()
# Region
# Kerala    ...
# Punjab    ...
```

Both regions are on the 14-code state-level axis, so this is a like-for-like comparison.
Comparing either against `Pan-Indian` is not — that bucket is unlabelled, not a region.

</details>

<details>
<summary><b>Diet composition of the corpus</b></summary>

```python
r.Diet.value_counts()
# Vegetarian       88,488
# Vegan            78,350
# Non-Vegetarian   32,601
# Eggetarian       15,558
# unknown           4,387
```

`unknown` is a real category and is **not** a permissive default. The interaction benchmark
excludes those 4,387 recipes from every diet-restricted pool rather than treating them as
vegetarian.

</details>

<details>
<summary><b>Traversing the graph for one ingredient</b></summary>

```python
kg = pd.read_parquet("data/kg/kg_edges.parquet")

kg[(kg.head == "ingredient::sesame-oil")]
# ingredient::sesame-oil  subtype_of     ingredient::oil
# ingredient::sesame-oil  derived_from   ingredient::sesame
```

`subtype_of` answers *what kind of thing is this*; `derived_from` answers *what was it made
from*. A specific oil carries both, and neither is a safety path.

</details>

<details>
<summary><b>Training split, done correctly</b></summary>

```python
train = r[r.Split_v3 == "train"]
test  = r[r.Split_v3 == "test"]
```

Use **Split_v3**. It groups connected components of case-folded titles and duplicate
families, so near-duplicate recipes cannot straddle the boundary. Legacy split columns are
retained for reproducibility and must not be used implicitly.

</details>

---

## Knowledge graph

222,537 nodes, 6,432,585 edges, 17 node types, 22 relation types.

```mermaid
graph LR
    R((recipe)) -->|has_ingredient 1.92M| I((ingredient))
    R -->|has_health_tag 1.73M| H((healthtag))
    R -->|suitable_for 895K| D((condition))
    R -->|contains_allergen 491K| A((allergen))
    R -->|cooked_by 404K| M((method))
    R -->|in_cuisine 219K| C((cuisine))
    R -->|from_region 219K| G((region))
    I -->|has_compound 26K| P((compound))
    I -->|pairs_with 3.3K| I
    I -->|substitute_for 30| I
```

<details>
<summary><b>All 17 node types, with counts</b></summary>

| type | n | | type | n |
|---|---:|---|---|---:|
| `recipe` | 219,384 | | `nutrient` | 22 |
| `compound` | 1,607 | | `allergen` | 18 |
| `ingredient` | 927 | | `condition` | 13 |
| `foodclass` | 363 | | `course` | 12 |
| `cuisine` | 53 | | `method` | 11 |
| `occasion` | 44 | | `category` | 11 |
| `healthtag` | 30 | | `diet` | 8 |
| `region` | 27 | | `zone` | 5 |
| | | | `context` | 2 |

</details>

<details>
<summary><b>All 22 relation types, with counts</b></summary>

| relation | edges | | relation | edges |
|---|---:|---|---|---:|
| `has_ingredient` | 1,916,036 | | `shares_flavor` | 13,670 |
| `has_health_tag` | 1,725,100 | | `in_context` | 7,287 |
| `suitable_for` | 895,452 | | `pairs_with` | 3,265 |
| `contains_allergen` | 491,208 | | `rich_in` | 2,935 |
| `cooked_by` | 404,145 | | `grounded_as` | 369 |
| `has_diet` | 256,132 | | `is_a` | 173 |
| `from_region` | 219,347 | | `typical_region` | 48 |
| `is_course` | 219,347 | | `substitute_for` | 30 |
| `in_cuisine` | 219,347 | | `derived_from` | 30 |
| `for_occasion` | 33,356 | | `in_zone` | 27 |
| `has_compound` | 25,748 | | `subtype_of` | 17 |

`subtype_of` is "is a kind of", ingredient → ingredient. It is **descriptive and never a
safety path** — `contains_allergen` remains the only edge an allergen filter may trust.
`derived_from` answers a different question, *what was this made from*, so a specific oil
carries both: `sesame-oil subtype_of oil` and `sesame-oil derived_from sesame`.

</details>

---

## Benchmark

67 retrieval queries with knowledge-graph-derived gold sets, across 8 templates:

| template | queries | | template | queries |
|---|---:|---|---|---:|
| `ingredient` | 12 | | `diet+allergenfree` | 7 |
| `condition` | 12 | | `course` | 6 |
| `diet+nutrient` | 12 | | `cuisine` | 6 |
| `diet` | 7 | | `diet+ingredient` | 5 |

> [!WARNING]
> Gold sets are **graph-derived silver labels, not human judgments.** They are suitable for
> comparing systems against each other on this corpus; they are not a human relevance
> standard. `data/benchmark/GOLD_SET_AUDIT.json` records the contamination audit.

---

## Interaction benchmark

[`data/interactions/`](data/interactions) is a synthetic collaborative log for training and
comparing recommenders on Indian cuisine, which no existing interaction dataset covers.

| | |
|---|---:|
| Users, each profiled by region / diet / health / spice / age | 50,000 |
| Explicit 1–5 ratings | 990,273 |
| After positives (≥4), iterative 10-core and a temporal 80/20 split | 35,825 users · 16,300 items |
| Train / test pairs | 658,092 / 163,097 |
| Train/test leakage | **0** |
| Attribute KG | 81,497 triples · 16,348 entities |

> [!CAUTION]
> **Simulated behaviour, not observations of real users.** It rewards methods that recover
> the region / diet / health structure the generator encodes, and is not evidence about human
> dietary preference. Diet compatibility is enforced as a hard constraint, but a *synthetic*
> guarantee says nothing about a deployed system's safety.

Regenerate it with `python scripts/build_interactions.py`, re-score it with
`python scripts/build_interaction_baselines.py`. Full method, parameters and reference
baselines are in [`data/interactions/DATASHEET.md`](data/interactions/DATASHEET.md).

---

## 🔺 Allergens: read this first

17 classes — the FALCPA 9, two EU FIC additions (celery, sulphites), five
investigator-defined South Asian classes, and `ghee` tracked separately from `milk`.

| class | recipes | | class | recipes |
|---|---:|---|---|---:|
| `milk` | 116,539 | | `fenugreek` | 20,028 |
| `gluten` | 76,601 | | `sesame` | 13,730 |
| `coconut` | 36,813 | | `tamarind` | 12,163 |
| `mustard` | 36,691 | | `peanut` | 11,464 |
| `ghee` | 33,539 | | `soy` | 9,053 |
| `tree_nuts` | 33,290 | | `fish` | 5,952 |
| `asafoetida` | 30,612 | | `shellfish` | 4,232 |
| `sulphites` | 23,990 | | `celery` | 2,357 |
| `egg` | 21,676 | | **`unknown`** | **2,478** |

**Four things you must know before building anything safety-facing.**

1. **`unknown` is a real value and never means "safe".** 2,478 recipes were never assessed.
   The contract is fail-closed: unknown ⇒ treat as unsafe. Every accessor in `scripts/`
   preserves the sentinel. Flatten it to `False` and you have inverted the safety property.
2. **The South Asian five are investigator-defined, not regulator-derived.** FSSAI's
   mandatory list (Labelling and Display Regulations 2020, clause 5(14)) names none of
   mustard, fenugreek, asafoetida, tamarind or coconut. Do not present them as carrying
   regulatory authority.
3. **The audit is a consistency check, not an accuracy measurement.** It compares two
   independently written lexicons; agreement means they agree, not that either is right. A
   returned pilot has 794 rows: 202 TP, 38 FP, 118 FN, 433 TN and 3 unclear.
   The predicted-positive stratum has 240 rows; zero FN in that selected stratum
   does not measure sensitivity. Raw FNR 118/320 describes this sample only.
   Reviewer independence and population weights are unverified; no corpus rate is claimed.
4. **`sulphites` is not independently auditable, and is reported as such.** The label comes
   from a *carrier* rule — vinegar, raisins, wine, dried fruit — because that is where
   sulphites are. A home recipe never names the additive, so the independent lexicon matches
   0 of 23,989 flagged rows **by construction**. Giving it a carrier list would make it
   agree with the labeller on the labeller's own theory and report that as corroboration,
   so it deliberately does not.

> [!CAUTION]
> **Do not use these flags as the sole basis for an end-user safety decision.**

---

## Nutrition grounding, read this before computing anything

> [!WARNING]
> The food composition table uses the **IFCT 42-nutrient schema**, but **contains no IFCT
> data and no Indian composition data.** Its values are **7,793 USDA rows (97.5%)** plus
> 198 INDB US/UK rows, established by reading `primarysource` in the source spreadsheets.
>
> **The schema is Indian; the data is Western.** Do not describe this corpus as
> IFCT-grounded or as India-grounded in its nutrition. Grounding in IFCT 2017 or INDB proper
> is an open enhancement, not a property of this release — which is why the column ships as
> `nut_suppl_fct_frac`. The narrow quality table also retains `nut_indb_frac` as a
> deprecated compatibility alias with identical values. This is the share of
> computed ingredient calories from supplemental FCT rows. Legacy zero values can
> also indicate an unavailable calorie denominator.

Two nutrient bases were traced to the builder and are easy to get wrong:

| column | basis | consequence |
|---|---|---|
| `Nut_VitaminA` | **µg RAE** (FoodData Central nutrient 1106) | not IU, not retinol — they differ by up to 12× for plant carotenoids |
| `Nut_Folate` | **total folate** (nutrient 1177), **not DFE** | `DV_Folate` is unavailable; `DV_Folate_basis` explains the mismatch. Previous unsupported percentages are retained in field history. |

Unit and basis declarations are machine-readable in the Parquet field metadata and
human-readable in [`docs/UNITS.json`](docs/UNITS.json).

---

## What is *not* here, and why

**Recipe prose is not redistributed.** Headnotes, free-text instructions, the raw ingredient
string and keywords can be copyrightable. The parsed ingredient list, nutrition estimates and
every typed attribute are published; the prose is not.

<details>
<summary><b>How to get the prose back yourself (rehydration)</b></summary>

`data/corpus/rehydration_index.parquet` carries each recipe's source URL and a SHA-256 digest
of the prose the corpus was derived from, so you can re-fetch and verify you reconstructed
the same text:

```bash
python scripts/rehydrate.py --out prose.parquet --limit 100
```

**214,577 of 219,384 rows are rehydratable.** The other 4,807 came from pre-existing datasets
rather than scraped pages and carry placeholder URLs, flagged
`source_kind = "derived_dataset"`.

</details>

Large derived artefacts — dense and structural embedding matrices, the pickled graph — are
excluded. The graph is regenerable with `python scripts/build_graph.py --out DIR`. The
embedding matrices are planned as a separate Zenodo record, which does not exist yet.

---

## Verify what you downloaded

The release verifies itself, and **the check runs on your clone, not only on ours**:

```bash
python scripts/verify_release.py --strict-checksums
```

| check | what it protects |
|---|---|
| licence | no withheld prose column, by stem, in any artefact |
| integrity | row, node, edge and query counts against pinned expectations |
| privacy | PII pattern sweep over every string column |
| checksums | SHA-256 manifest, **in both directions** — a file with no digest fails too |
| authorship | `.zenodo.json` and `CITATION.cff` name the same people |
| interactions | id maps, split integrity and diet compatibility in the interaction log |
| disclosure | every audit artefact the datasheet refers to is present |

No network, no source tree, no credentials required.

<details>
<summary><b>Reproducing the whole build</b></summary>

```bash
python scripts/build_corpus.py
python scripts/build_kg.py
python scripts/build_enrichment.py
python scripts/build_benchmark.py
python scripts/build_interactions.py
python scripts/build_interaction_baselines.py
python scripts/build_region_crosswalk.py
python scripts/audit_corpus.py
python scripts/validate_sa5.py
python scripts/make_data_dictionary.py
python scripts/build_release_facts.py
python scripts/make_checksums.py
python scripts/verify_release.py --strict-checksums
```

`scripts/release_config.py` is the single source of truth for the withheld-column list and
the expected counts; builders and verifier both import it, so the licence guard cannot drift
from what is published.

Releasing is tag-driven and verifies before it publishes — see
[`docs/RELEASING.md`](docs/RELEASING.md).

</details>

---

## FAQ and known gotchas

<details>
<summary><b>Why is <code>Pan-Indian</code> 62% of the corpus?</b></summary>

Because most sources do not declare a region. It means "unlabelled", not "a region". For
cultural analysis, slice on the state-level regions and exclude the supra-regional buckets —
otherwise you are comparing a labelled slice against an unlabelled remainder.

</details>

<details>
<summary><b>Why do allergen counts exceed what the ingredient text says?</b></summary>

Deliberately, for composite spices. Chaat masala, sambar powder and pav bhaji masala contain
asafoetida without naming it, so a recipe calling for chaat masala is labelled for
asafoetida. That is the fail-closed behaviour Codex CXC 80-2020 requires, and it is why that
class's text-agreement is 77.6% while the others are 89–99%. The breakdown ships with the
figure in [`docs/allergen_sa5_v1_validation.md`](docs/allergen_sa5_v1_validation.md).

</details>

<details>
<summary><b>Can I join the old interaction sets to the new one?</b></summary>

No. The retired `synthetic_interactions/` and `synthetic_interactions_v3/` were independent
simulations with colliding remapped id spaces, and their `recipe_id` column held positional
offsets rather than corpus ids. `data/interactions/` emits real `recipe_id`s. Use the v0.6.0
tag if you are reproducing a result published against the old sets.

</details>

<details>
<summary><b>My clone has 130-byte files where the data should be</b></summary>

Those are Git LFS pointer stubs. Install `git-lfs` and run `git lfs pull`. The verifier
fails loudly on them rather than validating a stand-in, which is deliberate.

</details>

<details>
<summary><b>Can I use this commercially?</b></summary>

No. The data is CC BY-NC-SA 4.0. The **code** is MIT and has no such restriction.

</details>

<details>
<summary><b>Which DOI should I cite?</b></summary>

The **concept DOI**, `10.5281/zenodo.22512534` — it always resolves to the latest version.
Pin a version DOI only if your result depends on an exact snapshot.

</details>

---

## Licence

| | |
|---|---|
| **Data** | **CC BY-NC-SA 4.0** ([`LICENSE-DATA`](LICENSE-DATA)) — per-recipe attribution retained in the `SourceSite` and `URL` columns |
| **Code** | **MIT** ([`LICENSE-CODE`](LICENSE-CODE)) |

**Third-party layers** — USDA SR Legacy (public domain), UK CoFID (Open Government Licence),
FoodOn (CC BY 4.0), FlavorDB (CC BY-NC-SA 3.0 — present in `data/kg/` as well as
`data/kg_flavor/`, 1,607 compound nodes and 39,418 `has_compound`/`shares_flavor` edges, so the core graph is **not** free
of its terms).

> **RecipeDB NER, IFCT 2017 and INDB were previously listed as dependencies and are not used
> at all.** The per-layer audit is in
> [`docs/THIRD_PARTY_TERMS.md`](docs/THIRD_PARTY_TERMS.md).

<details>
<summary><b>Why NonCommercial, when most layers are permissive?</b></summary>

The licence moved twice while the dependencies were audited. Three of six recorded
third-party layers turned out never to have been used, which would have allowed CC BY 4.0 —
but **9,384 recipes (4.28%) from upstream NC/NC-SA datasets are retained by decision**, so
NonCommercial and ShareAlike apply to the whole corpus. `LICENSE-DATA` records the one-line
route back to CC BY 4.0 if those recipes are ever dropped.

</details>

To request removal of content, see [`docs/TAKEDOWN.md`](docs/TAKEDOWN.md).

---

## Citation

```bibtex
@dataset{badgujar_borde_gurav_indicrecipenutri,
  author    = {Badgujar, Hemprasad Y. and Borde, Santosh P. and Gurav, Yogesh},
  title     = {IndicRecipeNutri},
  year      = {2026},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.22512534},
  url       = {https://doi.org/10.5281/zenodo.22512534}
}
```

Cite the **concept DOI** above unless you need to pin a version:
`10.5281/zenodo.22512535` (0.3.0) · `10.5281/zenodo.22537252` (0.4.0).

Machine-readable metadata is in [`CITATION.cff`](CITATION.cff) and
[`.zenodo.json`](.zenodo.json), and the two are checked against each other at release time —
the published record is generated from `.zenodo.json`, so a disagreement would mean the DOI
credits a different author list than the repository does.

The associated paper is *IndicRecipeNutri: A Single-Store, Tri-Modal, Explainable Retriever
for Nutrition-Grounded Indian Recipe Recommendation* — venue and DOI pending.

---

## Documentation map

| document | read it when |
|---|---|
| [`docs/DATASHEET.md`](docs/DATASHEET.md) | **before using the data** — motivation, composition, measured defects |
| [`docs/DATA_DICTIONARY.md`](docs/DATA_DICTIONARY.md) | you need to know what a column means |
| [`docs/UNITS.json`](docs/UNITS.json) | you are computing on a numeric column |
| [`docs/PROVENANCE.md`](docs/PROVENANCE.md) | you need to trace where a value came from |
| [`data/interactions/DATASHEET.md`](data/interactions/DATASHEET.md) | you are training a recommender on the interaction log |
| [`docs/THIRD_PARTY_TERMS.md`](docs/THIRD_PARTY_TERMS.md) | you are redistributing or building a product |
| [`docs/SPLIT_PROTOCOL_v3.md`](docs/SPLIT_PROTOCOL_v3.md) | you are training and need the current splits |
| [`docs/BENCHMARK_VERSIONING.md`](docs/BENCHMARK_VERSIONING.md) | you are comparing results across releases |
| [`docs/RELEASING.md`](docs/RELEASING.md) | you are cutting a release |
| [`docs/TAKEDOWN.md`](docs/TAKEDOWN.md) | you want content removed |
| [`data/cultural_context/CONTEXT_MANIFEST.json`](data/cultural_context/CONTEXT_MANIFEST.json) | you use the occasion or dietary-rule layer — pins, tiers, transformations |
| [`data/historical_snapshot/SNAPSHOT_MANIFEST.json`](data/historical_snapshot/SNAPSHOT_MANIFEST.json) | you join to results keyed to the historical snapshot |
| [`CHANGELOG.md`](CHANGELOG.md) | you want to know what moved, and why |

<div align="center">

**Known defects are published, not hidden.**
If you find one we have not, please open an issue.

</div>
