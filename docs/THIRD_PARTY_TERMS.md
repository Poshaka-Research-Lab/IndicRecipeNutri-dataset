# Third-party layers and their terms

## Current IFCT source declaration (0.12.0 correction, 2026-09-28)

The 0.11.0 payload already contains IFCT 2017 source profiles for atta, maida and paneer in `data/enrichment/ifct_source_profiles.json`, associated recipe source shares in `recipe_ifct_fraction.parquet`, and `nutrition_source_provenance.json`. The prior blanket denial of IFCT use below is superseded. This is a declaration correction, not newly added IFCT values or proof of full Indian nutrient coverage.

Source: T. Longvah, R. Ananthan, K. Bhaskarachary and K. Venkaiah, *Indian Food Composition Tables 2017*, ICMR-National Institute of Nutrition, Hyderabad. Copyright ICMR-NIN. [Official publication and copyright notice](https://www.nin.res.in/ebooks/IFCT2017_16122024.pdf), inspected via official indexed text on 2026-09-28. Its notice permits acknowledged personal reproduction and requires prior written permission for electronic product use. A web copy is not an unrestricted redistribution licence.

DS-9: on 2026-09-28 the dataset owner confirmed that the required permission is already held and instructed retention ("alrady have it please proceed"). This release records an **owner-attested permission**, not an independently inspected permission instrument; no document path, grant date or scope beyond that confirmation has been supplied. Do not infer that this confirmation grants every downstream user an unrestricted licence. IFCT source rights remain separate from our own-contribution licence.

Consuming/export path: `scripts/build_enrichment.py::export_ifct_companions` and `sanitized_ifct_profiles`; schema/documentation consumer: `scripts/make_data_dictionary.py`. Nutrition lineage is recorded in `data/enrichment/nutrition_source_provenance.json`, including its limited component set, source digests and estimated-composition limitations. Scope and traceability checks belong in the 0.12.0 provenance report.


**Current local candidate, 2026-09-12:** the CID identity repair yields 1,607 compound
nodes, 25,869 has_compound and 14,180 shares_flavor edges in the core, plus 580
molecular-sharing assertions retained on pairing edges in the evidence table.
The optional flavour view is generated from these same assertions. Earlier counts
below are historical audit records; see `COMPOUND_ID_MIGRATION.md` and the generated
release facts for the current payload. The source terms remain separately recorded.

> ## 🔴 SUPERSEDED 2026-09-02 — THE RELEASE IS **NOT** DEPENDENCY-FREE
>
> **Read this before the 2026-08-29 banner below, which is now false.** FlavorDB was
> re-inserted into the core graph on instruction later on 2026-08-29, and this document was
> never updated. Measured against the shipped artefact today:
>
> | | in `data/kg/` — the CORE graph |
> |---|--:|
> | FlavorDB `compound` nodes | **1,601** |
> | `has_compound` edges | **25,854** |
> | `shares_flavor` edges | **14,181** |
> | total FlavorDB-derived edges | **40,035** |
>
> So `data/kg/` inherits **CC BY-NC-SA 3.0** obligations. `data/kg_flavor/` still exists as a
> separate copy, which is why three other documents describe the layer as "isolated" there —
> it is in **both** places, and taking `data/kg/` alone does not avoid FlavorDB's terms.
> `LICENSE-DATA` line 12 has this right; its lines 49 and 92, and `README.md`, do not.
>
> The correction is kept above the original rather than replacing it, because a licence
> document that quietly rewrites its own history is worse than one that shows the change.
>
> Corrected counts supersede the ones in the table below (1,641 nodes / 43,185 edges), which
> were the pre-removal figures.

> ## ⚠️ 2026-08-29 — superseded, see above
>
> Every NonCommercial and ShareAlike layer has been removed. The release no longer inherits
> any third-party licence obligation, and the data licence is a free choice again.
>
> | layer | was | now |
> |---|---|---|
> | **FlavorDB** `CC BY-NC-SA 3.0` | 1,641 compound nodes + 43,185 edges | ~~REMOVED~~ — **re-inserted into `data/kg/` later the same day; see the correction above** |
> | **3A2M, foodcom, yummly, RecipeNLG** `CC BY-NC(-SA)` | 9,384 recipes | **REMOVED from the release** via `EXCLUDED_SOURCE_SITES`. The master keeps them |
> | ~~RecipeDB NER~~ | listed as a dependency | **never used** — see correction below |
> | ~~IFCT 2017~~ | listed as a dependency | **never used** — see correction below |
>
> **Remaining, and all permissive:**
>
> | layer | licence | obligation |
> |---|---|---|
> | USDA SR Legacy (7,847 FCT rows) | **US Government public domain** | none |
> | UK CoFID (144 FCT rows) | **Open Government Licence** | attribution |
> | FoodOn (377 nodes, 384 edges) | **CC BY 4.0** | attribution |
> | `indori` (2,554 recipes) | **CC BY 4.0** | attribution |
> | `indb` (973 recipes) | Open Access | citation |
>
> **Three of the six originally-listed layers turned out not to exist in the build at all.**
> That is the reason for the standing rule at the end of this document.
>
> **This does not clear the release.** 207,276 rows (94.14%) are our own scrapes of publisher
> sites, marked `Proprietary (Copyright)`. That question is untouched by any of the above.


The knowledge graph fuses external resources. Each is redistributable only to the
extent its own licence permits, and the combined graph is released only to that extent.

> **Status: RESOLVED 2026-08-29 — the data licence is now `CC BY-NC-SA 4.0`.**
>
> The per-layer terms below are correct. What had not been carried through was their
> consequence, which rule 4 of this document already stated: *"if any layer is share-alike,
> CC BY 4.0 on the combined graph may be wrong."* **Four layers are `CC BY-NC-SA`, and
> `data/` was published as `CC BY 4.0`** — incompatible on both **NC** (forbids commercial
> use, which CC BY grants) and **SA** (requires copyleft, which CC BY does not).
>
> ### Decision taken
>
> **Option 2 — relicense `data/` as `CC BY-NC-SA 4.0`.** This project's use is
> non-commercial, so the NC restriction costs nothing in practice, and this keeps every
> layer including the FlavorDB flavour graph (1,641 compound nodes, 43,185 edges) and the
> 3,833 NC-SA-derived recipes that option 1 would have dropped.
>
> **One thing to keep straight, because it is the easy mistake:** being non-commercial
> ourselves did **not** make CC BY 4.0 acceptable. NC governs what we *grant onward* — CC BY
> would have handed downstream users commercial rights we do not hold. And **SA binds the
> publisher regardless of the publisher's own commercial status.** The relicense, not our
> usage, is what resolves this.
>
> CC BY-NC-SA 3.0 permits relicensing adaptations under a later version of the same licence,
> so 4.0 is the correct target for the combined work.
>
> ### Scope that drove the decision (measured 2026-08-29)
>
> | source | licence | artefacts derived from it |
> |---|---|---|
> | FlavorDB | `CC BY-NC-SA 3.0` | 1,641 `compound` nodes · 26,705 `has_compound` · 15,649 `shares_flavor` · 831 `pairs_with` edges |
> | ~~RecipeDB NER~~ | — | **NOT USED — removed from this list 2026-08-29** |
> | 3A2M / RecipeNLG-derived | `CC BY-NC-SA 4.0` | 3,803 recipes |
> | RecipeNLG (Indian subset) | `CC BY-NC-SA 4.0` | 30 recipes |
> | | | **3,833 recipes = 1.71% of 224,002** |
>
> Historical compatibility wording superseded: FoodOn is CC BY 4.0; IFCT is a separately permissioned source, not automatically absorbed by the dataset licence.
>
> ### Historical IFCT non-use correction - SUPERSEDED for the 0.11.0/0.12.0 payload
>
> This document listed **IFCT 2017 (Indian Food Composition Tables), Copyright ICMR-NIN** as
> the nutrient-grounding layer. **No IFCT 2017 data is present or read.** `compute_ifct.py`
> reads exactly two things: `nutrition/USDA_sr_legacy/` and the two spreadsheets
> `US_fct.xlsx` / `UK_fct.xlsx` (labelled `INDB-US` / `INDB-UK`). The resulting table is
> **7,793 USDA rows + 198 INDB rows**, and the `source` column says so.
>
> "IFCT" here names only the **42-nutrient schema**, not the data. The file is called
> `fct_ifct.parquet` because it follows that column layout. This is the same misreading
> that produced the retracted "IFCT-grounded" claim; the terms document had not caught up.
>
> **This is good news for licensing.** USDA SR Legacy is **US Government public domain**,
> which carries no restriction at all — so 97.5% of the nutrition layer is unencumbered.
>
> ⚠ **One open item:** the provenance of `US_fct.xlsx` and `UK_fct.xlsx` is asserted as
> "INDB / Open Access" but has not been independently confirmed. `UK_fct.xlsx` in
> particular may be McCance & Widdowson CoFID (Open Government Licence), which would be
> fine but should be named correctly. **Confirm before publication.**

> ### ⚠ CORRECTION — RecipeDB NER was never used
>
> This document listed **RecipeDB NER training data** as the source of a "CRF ingredient
> tagger", and that was the one NC-SA item that could not be tiered away because it
> supposedly touched `IngredientsList` corpus-wide. **It is not used, and never was.**
> Checked 2026-08-29:
>
> - `D:\datasets
ecipedb\` **does not exist**. `README_DATASETS.md` lists it among the
>   "empty / placeholder folders (no data yet)", and `STATUS_TABLE.md` records the bulk
>   export as still requiring "a data-dump request to cosylab" — it was never obtained.
> - **There is no CRF tagger anywhere in the pipeline.** No model file, no training script,
>   no inference call. The only "NER" in the codebase is `_NER_JUNK` in
>   `ingredient_vocab.py`: a hand-written blacklist of nutrition-panel and web-nav words.
> - `IngredientsList` is parsed by `build_kg_v3.clean_ing_head` — regex plus our own
>   controlled vocabulary. `ingredient_map.json` is built by `build_ingredient_map_v3.py`
>   from **our own master corpus** (head-noun frequency, threshold >=20), a hand-curated
>   `FOOD_VOCAB`, hand-written `ALIAS`/`NOISE`/`DISH_PREP` lists, and FCT validation
>   against IFCT/USDA.
>
> **RecipeDB contributed nothing to this dataset.** The entry was aspirational — a source
> that was planned, listed, and never acquired.
>
> **Consequence, and it is a large one.** The remaining NC-SA exposure is only FlavorDB and
> 3,833 recipes, and **both are physically separable**. The corpus and nutrition tables --
> the main deliverable -- have **no NC-SA input at all**. Tiering, which was ruled out
> because of this entry, is now clean and available.



| layer | used for | licence | redistribution of derived data | verified |
|---|---|---|---|---|
| **IFCT 2017** | Existing atta, maida and paneer source profiles and associated provenance | Copyright ICMR-NIN; separately permissioned | Retained on owner confirmation; not an unrestricted sublicence | Owner-attested permission; instrument not independently inspected. See current declaration above |
| **USDA SR Legacy** | 7,793 of 7,991 FCT foods (97.5%) | **US Government public domain / CC0** | Unrestricted | Yes |
| **INDB** (`US_fct.xlsx`, `UK_fct.xlsx`) | 198 FCT foods (2.5%) | Open Access, citation | Permitted with citation | ⚠ provenance of the two spreadsheets not independently confirmed |
| **FlavorDB** | `compound` nodes (1,601), `has_compound` (25,854) / `shares_flavor` (14,181) edges | `CC BY-NC-SA 3.0` | Permitted with attribution under copyleft | Yes |
| **FoodOn** | `foodclass` nodes (377), `grounded_as` edges (384) | `CC BY 4.0` | Permitted | Yes |
| ~~**RecipeDB NER training data**~~ | ~~CRF ingredient tagger~~ | — | **NOT USED — see correction below** | n/a |

## Upstream recipe datasets — found during the 0.1.0 build, not in the paper's list

4,807 of the 220,187 published recipes (2.18%) did not come from a scraped page. They came from
pre-existing datasets and carry a placeholder URL, so they cannot be rehydrated by
re-fetching. They are flagged `source_kind = "derived_dataset"` in
`data/corpus/rehydration_index.parquet`.

These are **additional third-party sources that the paper's section 3.5 does not name**,
and their terms gate the release exactly as the four layers above do.

| upstream dataset | `SourceSite` | recipes | licence | redistribution | verified |
|---|---|---:|---|---|---|
| 3A2M / RecipeNLG-derived Indian subset | `3a2m_indian` | 3,803 | `CC BY-NC-SA 4.0` | Permitted with attribution | Yes |
| IndB | `indb` | 973 | Open Access (citation) | Permitted with citation | Yes |
| RecipeNLG (Indian subset) | `recipenlg_indian` | 30 | `CC BY-NC-SA 4.0` | Permitted with attribution | Yes |
| indori | `indori` | 1 | `CC BY 4.0` | Permitted | Yes |

## Occasion registry and dietary-rule table — internal source S1 (added in 0.11.0)

| | occasion registry | dietary rules |
|---|---|---|
| Upstream file | internal source S1, `data/registry/occasions.csv` | internal source S1, `data/rules/rules.yaml` (meta version 0.2.0) |
| Upstream version | git blob `e0f408d556119205e26e5d9a851f18a837e30619` at commit `5d8d7808d0252ecc23e66255d2616d74e1d5d3b2`; SHA-256 of the file as read `4da2145b711618e40775ee7a4c5b0cfcde7434f11cc5845745f687547f641d68` | **uncommitted working copy** against commit `5d8d780` (HEAD blob `d6b1458f`); SHA-256 `b1ed03b0a4fcda4aa2d05d3b164b7e988e68c3a5c94ab00a3b8be73076952c9f`; would-be blob `67ae6bbf…` is not in any commit |
| Released as | `data/cultural_context/occasion_registry.parquet`, with its sources in `context_citations.parquet` and its node links in `context_tag_links.parquet` | `data/cultural_context/dietary_rules.parquet`, with its sources in `context_citations.parquet` |
| Consumed by | `scripts/stage_cultural_context.py` (reads the CSV, re-verifies its SHA-256 before reading, and stops on a mismatch) | `scripts/stage_cultural_context.py` (reads the YAML under the same guard). `scripts/context_rule_adapter.py` reads the released tables, not the upstream file |
| Upstream licence | CC BY 4.0 (the source's `LICENSE-DATA`) | CC BY 4.0 (the source's `LICENSE-DATA`) |
| Licence here | CC BY-NC-SA 4.0, as part of `data/`, by licensor statement (H. Y. Badgujar, 2026-09-23). The corpus-derived upstream columns `corpus_recipe_count` and `in_corpus` are **not** shipped | CC BY-NC-SA 4.0, as part of `data/` |
| Redistribution of derived data | Permitted by upstream with attribution, a licence link and an indication of changes | Same |
| Share-alike | Not upstream; applies here through `data/` | Same |
| Changes made | Namespaced IDs (`occ::<id>`, `rule::<name>`). `source` is not shipped: each cell became structured `context_citations` rows (title, publisher, locator, identifier, URL, access date) plus `source_text_sha256`, and every quoted span was dropped with it. `corpus_recipe_count` and `in_corpus` were dropped. Renames: `occasion_id`→`source_occasion_id`, `evidence_tier`→`registry_evidence_tier`, `date_rule`→`date_rule_text`, `note`→`registry_note`. Quotations and percentages were removed from `registry_note` and `date_rule_text` through a reviewed span table. Booleans, `n_sources` and `date_2026` were typed. Provenance and flag columns were added (`source_locatable`, `corpus_circular_source`, `label_status = silver`, `prov_*`) | Namespaced IDs. **Predicates stored as data, not executed**; `destination_executable = false` on every rule, and the upstream `executable` flag is carried as `source_executable`. `evidence_tier` added (sourced / descriptive / unsourced). `source`, `certification_source`, `time_of_day_source` and the standing-rule sources were reduced to citations, and quotations were dropped. `meta.prevalence_source` (Pew 2021 percentages) was dropped, and Pew was kept only as a number-free `prevalence_reference` citation. `note` became `rule_note` with quotations and percentages removed. The full list is under `transformations` and `dropped_fields` in `CONTEXT_MANIFEST.json` |
| Checked | 2026-09-23, rights review; entry completed at promotion | 2026-09-23, rights review; entry completed at promotion |

**Attribution (required by the upstream licence).** These are the strings recorded in
`data/cultural_context/CONTEXT_MANIFEST.json`, where "this manifest" refers:

    Badgujar, H. Y., Borde, S. P. and Gurav, Y. Occasion registry for constrained food
    recommendation (internal source S1, data/registry/occasions.csv, git blob e0f408d5);
    licensor H. Y. Badgujar; CC BY 4.0. https://creativecommons.org/licenses/by/4.0/
    Modified for IndicRecipeNutri 0.11.0: see `transformations` in this manifest.

    Badgujar, H. Y., Borde, S. P. and Gurav, Y. Dietary-rule predicates
    (data/rules/rules.yaml, version 0.2.0, internal source S1, uncommitted working copy of
    commit 5d8d780, SHA-256 b1ed03b0...952c9f); licensor H. Y. Badgujar; CC BY 4.0.
    https://creativecommons.org/licenses/by/4.0/ Modified for IndicRecipeNutri 0.11.0: see
    `transformations` in this manifest.

**Facts are not ours.** Every registry row and every rule keeps its source attribution as
structured citations in `context_citations.parquet`. The underlying facts and any third-party
text are not licensed by this dataset. **Verbatim quotations were reduced to citations, not
kept.** This covers the quoted text from Codex, *Paenitemini*, SGPC, bahai.org,
eos.learnpunjabi.org and sikhmissionarysociety.org. The original cells survive here only as
SHA-256 digests (`source_text_sha256`, `note_text_sha256`).

**Upstream vocabulary is kept as written.** Rule and occasion identifiers, occasion names, note
text and cited URLs keep the source's own wording, including common English and Sanskrit words
for festive meals and religious fasts. They are cultural vocabulary and name no project.

**Evidence limits that travel with these tables:**
- Registry: 233 of 444 rows are `single_source`. 94 rows name a genre rather than a document
  (81 `single_source`, 13 `needs_gazette`). 10 rows cite this corpus's own knowledge graph as
  their source and are **not independent evidence**.
- Rules: 5 verified, 12 partial, 7 unverified. The 7 unverified rules **are included**, tiered
  `unsourced`, each with one `none_recorded` citation that preserves the upstream's failed
  search. Tiers are 6 sourced, 11 descriptive and 7 unsourced.
- Rules do not certify compliance. `certifies: false` marks predicates that only narrow a
  catalogue.

**Not imported from the same source:** `data/rules/item_tags.yaml` (derived from FAO/WHO GIFT
IND-00062 FoodEx2 descriptions; redistribution of derivatives unverified upstream), the US
occasion file, all survey-derived build arrays, and the source's code.

**Two licence texts, one outcome.** A notice in internal source S2 describes a different upstream
registry licence, which splits CC BY 4.0 registry material from CC BY-NC-SA 4.0 corpus-linked
tables. The source's own `LICENSE-DATA` licenses the registry and `rules.yaml` under CC BY 4.0
with no split. The stricter term was applied. Because `data/` is already CC BY-NC-SA 4.0, both
readings give the same release licence.

## Historical-snapshot crosswalk and split metadata — internal source S2 (added in 0.11.0)

| | |
|---|---|
| Upstream | internal source S2, commit `051c975a37e2e32bd7e7172016b6f5b318a097e6`; snapshot receipts `logs/dataset_current_20260914/` (read from HEAD blobs) |
| What it is | Recipe-ID crosswalk (exact `recipe_id` join) between an **uncommitted working copy of this dataset** (declared 0.9.0, 2026-09-14, parquet SHA-256 `ffbb5d14…b4d6`) and 0.10.0, plus **aggregate** split counts from the snapshot's consumer. Not new recipes. Not independent validation |
| Released as | `data/historical_snapshot/recipe_id_crosswalk.parquet`, `data/historical_snapshot/snapshot_recipe_meta.parquet`, `data/historical_snapshot/SNAPSHOT_MANIFEST.json` |
| Consumed by | `scripts/stage_historical_snapshot.py` (reads the snapshot parquet and receipts after re-verifying their SHA-256, and stops on a mismatch) |
| Licence | This dataset's own CC BY-NC-SA 4.0. The S2 repository's code licence covers its code only and grants no data rights. No S2 code is included |
| Third-party layers | None. The snapshot's `kg_edges.parquet` (FlavorDB-derived content, CC BY-NC-SA 3.0) was **not** imported. Hash recorded for provenance only |
| Withdrawn records | The snapshot contains 2 recipes withdrawn from this dataset for personal data. They are **not** imported, and their IDs appear nowhere in the release. Only the count (2) is recorded, in `SNAPSHOT_MANIFEST.json` |
| Per-recipe split of the consumer | Unrecoverable (its split manifest is absent). Only aggregate counts are carried |
| Checked | 2026-09-23, rights review; entry completed at promotion |

## What to record for each

1. The licence identifier, or the exact terms URL if it is not a standard licence.
2. Whether redistribution of *derived* data (not the source table) is permitted.
3. Whether attribution is required, and in what form.
4. Whether share-alike applies — if any layer is share-alike, CC BY 4.0 on the
   combined graph is wrong and the licence must be revisited. **This is exactly what
   happened; see the status block above. The rule was right and was not applied.**
5. The date checked and by whom.

## If a layer turns out not to be redistributable

Withhold that layer's nodes and edges from the release and publish the join keys plus
a build script instead, the same pattern used for the recipe prose. Record the
exclusion in `data/kg/EXCLUDED.json`.


---

## Standing rule this document earned

**Previously misidentified layers:** RecipeDB NER is absent; INDB was a misleading label for USDA/UK CoFID sources. IFCT non-use was a historical statement and is false for the current payload: see the three-profile declaration above. Check actual source consumers before asserting absence.

> Before recording a dependency, verify it is actually imported, read or joined, and name
> the file or code path that consumes it. A licence document is a factual claim about the
> build, not a record of intentions.
