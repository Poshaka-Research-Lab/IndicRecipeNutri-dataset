# Provenance

## Where the recipes came from

380 distinct source sites, scraped from publicly accessible Indian and regional recipe
pages. Every published row carries `SourceSite` and `URL`, so each recipe traces to the
page it came from. The five largest sources by row count:

| source | recipes |
|---|---:|
| cookpad | 13,988 |
| pachakam | 11,392 |
| archanaskitchen | 7,500 |
| plattershare | 7,422 |
| TarlaDalal_Dataset | 7,409 |

Per-source and per-region counts are derivable from
`data/corpus/recipes_structured.parquet`; they are not summarised further here because
the corpus is the authority and a summary in prose would go stale.

**Collection timestamps are not in the published schema.** The paper states a
collection timestamp is retained per recipe; the v11 master does not carry one. This is
recorded as a gap in `docs/DATASHEET.md`, not papered over.

## Build lineage

The working master is versioned v6 through v11, each snapshotted with a column hash and
a manifest. `docs/VERSIONS.md` carries the per-build record and
`data/versions/columns_v*.txt` the per-build column lists. This release is built from
**v11** (224,003 rows × 134 columns), of which 129 columns and 224,002 rows are
published — one recipe is withdrawn, see `DATASHEET.md`.

The roughly 18 GB of intermediate `MASTER_pre_*` snapshots are not published. They are
build states, not product; the column lists and the enrichment companion tables carry
the audit trail.

## How to reproduce this release from the working master

```
python scripts/build_corpus.py       # structured corpus + rehydration index
python scripts/build_kg.py           # nodes, edges, vocabulary, count check
python scripts/build_enrichment.py   # 23 companion tables, CSV -> Parquet
python scripts/build_benchmark.py    # 66 queries + two-leg gold-set audit
python scripts/audit_corpus.py       # independent allergen and diet audit
python scripts/make_checksums.py
python scripts/verify_release.py --strict-checksums
```

`scripts/release_config.py` holds the expected counts and the withheld-column list;
both the builders and the verifier import from it, so the licence guard and the
invariants cannot drift apart.

## What is deliberately omitted, and how to regenerate it

| omitted | size | regenerate with |
|---|---|---|
| `graph.gpickle` | 487 MB | `python scripts/build_graph.py --out DIR --format gpickle` |
| `kg_dict.json` | 337 MB | `python scripts/build_graph.py --out DIR --format dict` |
| `recipe_text.parquet` | 959 MB | **not regenerable — contains withheld prose** |
| dense / structural embedding matrices | ~930 MB | separate Zenodo record, see README |
| `MASTER_pre_*.bak.csv` | ~18 GB | not published |
