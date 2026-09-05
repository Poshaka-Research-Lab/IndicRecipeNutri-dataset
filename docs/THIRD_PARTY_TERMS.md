# Third-party layers and their terms

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
> `FoodOn` (`CC BY 4.0`) and `IFCT 2017` are compatible; they are absorbed by the more
> restrictive combined terms rather than being the cause of them.
>
> ### ⚠ CORRECTION — IFCT 2017 was never used either
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
| ~~**IFCT 2017**~~ | ~~nutrient grounding~~ | — | **NOT USED — see correction below** | n/a |
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

**Three of the six layers listed here were never used**: RecipeDB NER (folder does not
exist, no tagger), IFCT 2017 (no IFCT data is read), and INDB (the two spreadsheets say
`primarysource: usda` and `ukfct`). All three were checkable in minutes.

> Before recording a dependency, verify it is actually imported, read or joined, and name
> the file or code path that consumes it. A licence document is a factual claim about the
> build, not a record of intentions.
