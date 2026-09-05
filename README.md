# IndicRecipeNutri — dataset

A corpus of **220,187 Indian recipes** with multilingual provenance and estimated
dish-level micronutrition, a typed **knowledge graph** of 223,406 nodes
and 6,270,620 edges, a **68-query retrieval benchmark**, and a **synthetic
collaborative interaction log**.

> ### ⚠️ Version 0.2.0 is a pre-release. Do not cite it.
>
> Five release gates are open, tracked in [`CHANGELOG.md`](CHANGELOG.md). Two of them
> are licence questions that could change what is redistributable. The data is real and
> the build is reproducible; the paperwork is not finished.
>
> **Read [`docs/DATASHEET.md`](docs/DATASHEET.md) before using this.** It documents
> measured defects, including allergen false negatives.

---

> **Nutrition grounding, stated precisely (corrected again 2026-08-29).** The food
> composition table uses the **IFCT 42-nutrient schema**, but **no IFCT data and no Indian
> composition data are in it.** Its values are **7,847 USDA** (SR Legacy plus a 54-row
> supplement) and **144 UK CoFID**, established by reading `primarysource` in the source
> spreadsheets. An earlier note here said "2.5% INDB India-curated"; those 198 rows carry
> `primarysource: usda` and `ukfct`, so that was a misattribution too.
>
> The schema is IFCT; the data is Western. **Do not describe this corpus as IFCT-grounded
> or as India-grounded in its nutrition.** Grounding in IFCT 2017 or INDB proper is an open
> enhancement, not a property of this release. The `nut_indb_frac` column is published as
> `nut_suppl_fct_frac` for the same reason. Upside: the layer is public domain and OGL, so
> it carries no NonCommercial or ShareAlike obligation.

## What is here

| path | contents |
|---|---|
| `data/corpus/` | 220,187 recipes × 251 published columns; rehydration index; corpus manifest; allergen audit |
| `data/kg/` | knowledge-graph nodes and edges, statistics, ingredient vocabulary |
| `data/enrichment/` | 28 companion tables — allergens, nutrition, region, diet, quality flags |
| `data/benchmark/` | 68-query retrieval benchmark with gold sets, plus its audit |
| `data/synthetic_interactions/` | 50,000 users, 990,273 ratings, with its own datasheet |
| `docs/` | datasheet, data dictionary, provenance, third-party terms, takedown policy |
| `scripts/` | builders, auditors, the release verifier, and the rehydration client |

Everything is Parquet with zstd compression and 50,000-row groups. The whole release is
about **440 MB** — no Git LFS, so the Zenodo archive contains the real files rather than
LFS pointer stubs.

## Quick start

```python
import pandas as pd

recipes = pd.read_parquet("data/corpus/recipes_structured.parquet")
kg_edges = pd.read_parquet("data/kg/kg_edges.parquet")

vegan_high_protein = recipes[
    (recipes.Diet == "Vegan") & (recipes.per100g_protein > 10)
]
```

## What is *not* here, and why

**Recipe prose is not redistributed.** Headnotes, free-text instructions, the raw
ingredient string and keywords can be copyrightable. The parsed ingredient list,
nutrition estimates and every typed attribute are published; the prose is not.

`data/corpus/rehydration_index.parquet` carries each recipe's source URL and a SHA-256
digest of the prose the corpus was derived from, so you can re-fetch the pages yourself
and verify you reconstructed the same text:

```bash
python scripts/rehydrate.py --out prose.parquet --limit 100
```

**215,380 of 220,187 rows are rehydratable.** The other 4,807 came from pre-existing
datasets rather than scraped pages and carry placeholder URLs; they are flagged
`source_kind = "derived_dataset"`.

Large derived artefacts — dense and structural embedding matrices, the pickled graph —
are excluded. The pickled graph and edge dictionary are regenerable:

```bash
python scripts/build_graph.py --out DIR --format both
```

The embedding matrices will be published as a **separate Zenodo record** linked to this
one. That record does not exist yet.

## Reproducing the release

```bash
python scripts/build_corpus.py
python scripts/build_kg.py
python scripts/build_enrichment.py
python scripts/build_benchmark.py
python scripts/audit_corpus.py
python scripts/make_data_dictionary.py
python scripts/make_checksums.py
python scripts/verify_release.py --strict-checksums
```

`scripts/release_config.py` is the single source of truth for the withheld-column list
and the expected counts; builders and verifier both import it, so the licence guard
cannot drift from what is published.

## Releasing

Tag-driven. Pushing a `v*.*.*` tag runs
[`.github/workflows/release.yml`](.github/workflows/release.yml), which **verifies
before it publishes** — licence guard, row and graph counts, PII sweep, checksums, and
the presence of the required audit artefacts. A failing check aborts the release rather
than shipping it.

```bash
git tag -a v0.2.0 -m "pre-release"
git push origin v0.2.0
```

Zenodo archives each published GitHub release and mints a version DOI. **Cite the
concept DOI**, which always resolves to the latest version.

Zenodo setup, once: enable this repository in Zenodo *before* the first release, and
grant the Zenodo OAuth app access to the `Poshaka-Research-Lab` organisation — an org
repo will not appear in the Zenodo list otherwise.

## Licence

- **Data** — **CC BY-NC-SA 4.0** ([`LICENSE-DATA`](LICENSE-DATA)); `data/kg_flavor/` is CC BY-NC-SA 3.0, with per-recipe source
  attribution retained in the `SourceSite` and `URL` columns.
- **Code** — MIT ([`LICENSE-CODE`](LICENSE-CODE)).
- **Third-party layers** — USDA SR Legacy (public domain), UK CoFID (Open Government
  Licence), FoodOn (CC BY 4.0), and FlavorDB (CC BY-NC-SA 3.0 — **in `data/kg/` as well as
  `data/kg_flavor/`**; 1,601 compound nodes and 40,035 edges, so the core graph is NOT free
  of its terms. "isolated in `data/kg_flavor/`" here was wrong and was corrected 2026-09-02). **RecipeDB NER, IFCT 2017 and INDB were previously listed here and
  are not used at all** — the per-layer audit is in
  [`docs/THIRD_PARTY_TERMS.md`](docs/THIRD_PARTY_TERMS.md).

> **Licence, 2026-08-29 — settled at CC BY-NC-SA 4.0.** It moved twice while the
> dependencies were audited. Three of six recorded third-party layers turned out never
> to have been used (RecipeDB NER, IFCT 2017, INDB), and FlavorDB was isolated into
> `data/kg_flavor/`. That would have allowed CC BY 4.0 — but **9,384 recipes (4.26%)
> from upstream NC/NC-SA datasets are retained by decision**, so NonCommercial and
> ShareAlike apply to the corpus. `LICENSE-DATA` records the one-line route back to
> CC BY 4.0 if those recipes are ever dropped.

To request removal of content, see [`docs/TAKEDOWN.md`](docs/TAKEDOWN.md).

## Citation

See [`CITATION.cff`](CITATION.cff). The associated paper is *IndicRecipeNutri: A
Single-Store, Tri-Modal, Explainable Retriever for Nutrition-Grounded Indian Recipe
Recommendation* — venue and DOI pending.
