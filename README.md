# IndicRecipeNutri

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22512534.svg)](https://doi.org/10.5281/zenodo.22512534)
[![Data licence: CC BY-NC-SA 4.0](https://img.shields.io/badge/data-CC%20BY--NC--SA%204.0-lightgrey.svg)](LICENSE-DATA)
[![Code licence: MIT](https://img.shields.io/badge/code-MIT-blue.svg)](LICENSE-CODE)

**219,386 Indian recipes** across **378 source sites**, with parsed ingredients, a
17-class allergen surface, dish-level nutrition estimates and FSA traffic lights; a typed
**knowledge graph** of 222,578 nodes and 6,292,393 edges; a **67-query retrieval
benchmark** with gold sets; and two **synthetic collaborative interaction logs**.

Every ingredient field is English/Roman. Every published figure in this file was measured
from the payload at build time, not carried over from a previous release.

**DOI:** [10.5281/zenodo.22512534](https://doi.org/10.5281/zenodo.22512534) — the **concept
DOI**, which always resolves to the latest version. **Cite this** unless you need to pin a
specific one; the badge above points at it for the same reason, so it does not go stale
every release. Per-version DOIs: `10.5281/zenodo.22512535` (0.3.0),
`10.5281/zenodo.22537252` (0.4.0).

> **Read [`docs/DATASHEET.md`](docs/DATASHEET.md) before using this.** It documents
> measured defects, and the allergen surface has known limits that matter if you build
> anything safety-facing on it. The short version is in
> [Allergens: read this first](#allergens-read-this-first).

---

> **Nutrition grounding, stated precisely.** The food composition table uses the **IFCT
> 42-nutrient schema**, but **contains no IFCT data and no Indian composition data.** Its
> values are **7,793 USDA** rows (97.5%) plus **198 INDB US/UK** rows, established by
> reading `primarysource` in the source spreadsheets. An earlier note here claimed "2.5%
> INDB India-curated"; those 198 rows carry `primarysource: usda` and `ukfct`, so that was
> a misattribution too.
>
> The schema is IFCT; the data is Western. **Do not describe this corpus as IFCT-grounded
> or as India-grounded in its nutrition.** Grounding in IFCT 2017 or INDB proper is an open
> enhancement, not a property of this release. The column is published as
> `nut_suppl_fct_frac` rather than `nut_indb_frac` for the same reason. The upside: that
> layer is US public domain and OGL, so it carries no NonCommercial or ShareAlike
> obligation of its own.
>
> Two nutrient bases were resolved from the builder on 2026-09-05 and are worth knowing
> before you compute anything from them: `Nut_VitaminA` is **µg RAE** (FoodData Central
> nutrient 1106), and `Nut_Folate` is **total folate, not DFE** (nutrient 1177) — so
> `DV_Folate` divides a total-folate numerator by a 400 µg **DFE** Daily Value and is not a
> DFE percentage.

## What is here

| path | contents |
|---|---|
| `data/corpus/` | 219,386 recipes × 268 columns; long-form allergen, nutrition, label and quality tables; rehydration index; allergen audit |
| `data/kg/` | knowledge graph — 222,578 nodes, 6,292,393 edges, typed store, ingredient vocabulary, pairing and substitution layers |
| `data/kg_flavor/` | FlavorDB compound layer, kept separable (CC BY-NC-SA **3.0**) |
| `data/enrichment/` | 26 companion tables — nutrition, region, diet, quality flags, ingredient weights |
| `data/benchmark/` | 67-query retrieval benchmark with gold sets, plus its contamination audit |
| `data/synthetic_interactions/` | 50,000 users, 990,273 ratings, with its own datasheet |
| `data/synthetic_interactions_v3/` | later generation, same scale, clean of the V7 withdrawal |
| `data/provenance/` | build records, field history, withdrawn-id lists |
| `docs/` | datasheet, data dictionary, provenance, units registry, third-party terms, takedown policy |
| `scripts/` | builders, auditors, the release verifier, and the rehydration client |

Parquet with zstd compression and 50,000-row groups; **≈508 MB** in total.

**Large files are in Git LFS.** A `git clone` without `git-lfs` installed gives you
130-byte pointer files, and `verify_release.py --strict-checksums` will fail loudly on
them rather than validating a stand-in. Install git-lfs and `git lfs pull`. The Zenodo
archive contains the real files — the release workflow downloads its own zipball and fails
the build if it ever contains pointers.

## Quick start

```python
import pandas as pd

recipes = pd.read_parquet("data/corpus/recipes_structured.parquet")
kg_edges = pd.read_parquet("data/kg/kg_edges.parquet")

vegan_high_protein = recipes[
    (recipes.Diet == "Vegan") & (recipes.per100g_protein > 10)
]
```

Allergens are published in two equivalent forms. Prefer the long table, and reach it
through the accessor rather than reading the column yourself:

```python
from scripts.allergen_surface import load_wide

wide = load_wide()            # recipe_id × 17 classes, with the unassessed sentinel intact
```

## Allergens: read this first

The corpus carries **17 allergen classes**: the FALCPA 9, two EU FIC additions (celery,
sulphites), five investigator-defined South Asian classes (mustard, fenugreek, asafoetida,
tamarind, coconut), and `ghee` tracked separately from `milk`.

Four things you need to know before building on them.

1. **The South Asian five are investigator-defined, not regulator-derived.** FSSAI's
   mandatory list (Labelling and Display Regulations 2020, clause 5(14)) does not name any
   of them. Do not present them as carrying regulatory authority.
2. **`unknown` is a real value and must not be read as "safe".** 1,274 recipes are marked
   unassessed. The contract is fail-closed: unknown means unsafe, never absent. Every
   accessor in `scripts/` preserves that sentinel; if you flatten it to `False` you have
   inverted the safety property.
3. **The audit is a consistency check, not an accuracy measurement.** `ALLERGEN_AUDIT.json`
   compares two independently written lexicons. Agreement between them is evidence that
   they agree — not that either is right. The held-out pilot (n=794) found 0 false
   negatives in 202 positive-stratum rows (95% upper bound 1.87%); the corpus-level rate is
   **withheld** because it rested on 10 rows per class.
4. **`sulphites` is not independently auditable and is reported as such.** The label comes
   from a carrier rule — vinegar, raisins, wine, dried fruit — because that is where
   sulphites occur. A home recipe never names the additive, so the independent lexicon
   matches 0 of 23,989 flagged rows *by construction*. Giving it a carrier list would make
   it agree with the labeller on the labeller's own theory and report that as
   corroboration, so it deliberately does not.

## What is *not* here, and why

**Recipe prose is not redistributed.** Headnotes, free-text instructions, the raw
ingredient string and keywords can be copyrightable. The parsed ingredient list, nutrition
estimates and every typed attribute are published; the prose is not.

`data/corpus/rehydration_index.parquet` carries each recipe's source URL and a SHA-256
digest of the prose the corpus was derived from, so you can re-fetch the pages yourself and
verify you reconstructed the same text:

```bash
python scripts/rehydrate.py --out prose.parquet --limit 100
```

**214,579 of 219,386 rows are rehydratable.** The other 4,807 came from pre-existing
datasets rather than scraped pages and carry placeholder URLs; they are flagged
`source_kind = "derived_dataset"`.

**4,617 recipes were withdrawn** and are absent from every published artefact: 3,815 pages
that were never recipes (archive listings, shop pages, image attachments), 801 from a site
whose "ingredient list" was the page navigation bar, and 1 for PII. Their ids — ids only,
never the records — are published in `data/provenance/withdrawn_ids.json` so you can verify
their absence yourself.

Large derived artefacts — dense and structural embedding matrices, the pickled graph — are
excluded. The graph and edge dictionary are regenerable:

```bash
python scripts/build_graph.py --out DIR --format both
```

The embedding matrices will be published as a **separate Zenodo record** linked to this
one. That record does not exist yet.

## Verifying what you downloaded

The release verifies itself, and **the check runs on your clone, not only on ours** —
until 2026-09-06 it did not, because it imported a module that existed on one machine.

```bash
python scripts/verify_release.py --strict-checksums
```

Licence guard (no withheld prose column, by stem, in any artefact), row and graph counts,
PII sweep, SHA-256 manifest in both directions, and the presence of every audit artefact
the datasheet refers to. It needs no network and no source tree.

## Reproducing the release

```bash
python scripts/build_corpus.py
python scripts/build_kg.py
python scripts/build_enrichment.py
python scripts/build_benchmark.py
python scripts/audit_corpus.py
python scripts/validate_sa5.py
python scripts/make_data_dictionary.py
python scripts/make_checksums.py
python scripts/verify_release.py --strict-checksums
```

`scripts/release_config.py` is the single source of truth for the withheld-column list and
the expected counts; builders and verifier both import it, so the licence guard cannot
drift from what is published.

## Releasing

Tag-driven, and it verifies *before* it publishes. See
[`docs/RELEASING.md`](docs/RELEASING.md) for the full procedure and the two repository
settings that must be on before the first tag.

```bash
git tag -a v0.4.1 -m "..." && git push origin v0.4.1
```

Zenodo archives each published GitHub release and mints a version DOI.

## Licence

- **Data** — **CC BY-NC-SA 4.0** ([`LICENSE-DATA`](LICENSE-DATA)), with per-recipe source
  attribution retained in the `SourceSite` and `URL` columns.
- **Code** — MIT ([`LICENSE-CODE`](LICENSE-CODE)).
- **Third-party layers** — USDA SR Legacy (public domain), UK CoFID (Open Government
  Licence), FoodOn (CC BY 4.0), and FlavorDB (CC BY-NC-SA 3.0 — **in `data/kg/` as well as
  `data/kg_flavor/`**; 1,601 compound nodes and 40,034 edges, so the core graph is **not**
  free of its terms). **RecipeDB NER, IFCT 2017 and INDB were previously listed here and
  are not used at all** — the per-layer audit is in
  [`docs/THIRD_PARTY_TERMS.md`](docs/THIRD_PARTY_TERMS.md).

> **Licence — settled at CC BY-NC-SA 4.0.** It moved twice while the dependencies were
> audited. Three of six recorded third-party layers turned out never to have been used
> (RecipeDB NER, IFCT 2017, INDB). That would have allowed CC BY 4.0 — but **9,384 recipes
> (4.28%) from upstream NC/NC-SA datasets are retained by decision**, so NonCommercial and
> ShareAlike apply. `LICENSE-DATA` records the one-line route back to CC BY 4.0 if those
> recipes are ever dropped.

To request removal of content, see [`docs/TAKEDOWN.md`](docs/TAKEDOWN.md).

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

The DOI above is the **concept DOI** and always resolves to the latest version. To pin a
specific one: `10.5281/zenodo.22512535` (0.3.0), `10.5281/zenodo.22537252` (0.4.0).

Machine-readable metadata is in [`CITATION.cff`](CITATION.cff) and
[`.zenodo.json`](.zenodo.json), and the two are checked against each other at release time
— the published record is generated from `.zenodo.json`, so a disagreement between them
would mean the DOI credits a different author list than the repository does.

The associated paper is *IndicRecipeNutri: A Single-Store, Tri-Modal, Explainable Retriever
for Nutrition-Grounded Indian Recipe Recommendation* — venue and DOI pending.
