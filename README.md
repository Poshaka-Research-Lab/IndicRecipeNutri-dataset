# IndicRecipeNutri — dataset

A corpus of **224,003 Indian recipes** with multilingual provenance and estimated
dish-level micronutrition, a typed **IFCT-grounded knowledge graph** of 227,500 nodes
and 6,169,941 edges, a **66-query retrieval benchmark**, and a **synthetic
collaborative interaction log**.

> ### ⚠️ Version 0.1.0 is a pre-release. Do not cite it.
>
> Five release gates are open, tracked in [`CHANGELOG.md`](CHANGELOG.md). Two of them
> are licence questions that could change what is redistributable. The data is real and
> the build is reproducible; the paperwork is not finished.
>
> **Read [`docs/DATASHEET.md`](docs/DATASHEET.md) before using this.** It documents
> measured defects, including allergen false negatives.

---

## What is here

| path | contents |
|---|---|
| `data/corpus/` | 224,003 recipes × 129 published columns; rehydration index; corpus manifest; allergen audit |
| `data/kg/` | knowledge-graph nodes and edges, statistics, ingredient vocabulary |
| `data/enrichment/` | 23 companion tables — allergens, nutrition, region, diet, quality flags |
| `data/benchmark/` | 66-query retrieval benchmark with gold sets, plus its audit |
| `data/synthetic_interactions/` | 50,000 users, 990,273 ratings, with its own datasheet |
| `docs/` | datasheet, data dictionary, provenance, third-party terms, takedown policy |
| `scripts/` | builders, auditors, the release verifier, and the rehydration client |

Everything is Parquet with zstd compression and 50,000-row groups. The whole release is
about **170 MB** — no Git LFS, so the Zenodo archive contains the real files rather than
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

**219,196 of 224,003 rows are rehydratable.** The other 4,807 came from pre-existing
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
git tag -a v0.1.0 -m "pre-release"
git push origin v0.1.0
```

Zenodo archives each published GitHub release and mints a version DOI. **Cite the
concept DOI**, which always resolves to the latest version.

Zenodo setup, once: enable this repository in Zenodo *before* the first release, and
grant the Zenodo OAuth app access to the `Poshaka-Research-Lab` organisation — an org
repo will not appear in the Zenodo list otherwise.

## Licence

- **Data** — CC BY 4.0 ([`LICENSE-DATA`](LICENSE-DATA)), with per-recipe source
  attribution retained in the `SourceSite` and `URL` columns.
- **Code** — MIT ([`LICENSE-CODE`](LICENSE-CODE)).
- **Third-party layers** — IFCT 2017, FlavorDB, FoodOn, the RecipeDB NER training data,
  and four upstream recipe datasets, each under its own terms. Those terms are
  **unverified** and are a release gate; see
  [`docs/THIRD_PARTY_TERMS.md`](docs/THIRD_PARTY_TERMS.md).

To request removal of content, see [`docs/TAKEDOWN.md`](docs/TAKEDOWN.md).

## Citation

See [`CITATION.cff`](CITATION.cff). The associated paper is *IndicRecipeNutri: A
Single-Store, Tri-Modal, Explainable Retriever for Nutrition-Grounded Indian Recipe
Recommendation* — venue and DOI pending.
