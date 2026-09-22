# Provenance

## Where the recipes came from

379 distinct source sites, scraped from publicly accessible Indian and regional recipe
pages. Every published row carries `SourceSite` and `URL`, so each recipe traces to the
page it came from. The five largest sources by row count:

| source | recipes |
|---|---:|
| cookpad | 13,988 |
| pachakam | 11,392 |
| archanaskitchen | 7,500 |
| plattershare | 7,422 |
| TarlaDalal_Dataset | 7,407 |

Per-source and per-region counts are derivable from
`data/corpus/recipes_structured.parquet`; they are not summarised further here because
the corpus is the authority and a summary in prose would go stale.

**Collection timestamps are not in the published schema.** The paper states a
collection timestamp is retained per recipe; the v15 master does not carry one. This is
recorded as a gap in `docs/DATASHEET.md`, not papered over.

## Build lineage

The working master is versioned v6 through v15. Every build except v13 and v14 is
snapshotted with a column hash and a manifest; those two ran in place and retained no
snapshot. `docs/VERSIONS.md` carries the per-build record and
`data/versions/columns_v*.txt` the per-build column lists. This release is built from
**v17** (220,188 rows × 259 columns, col-hash `1a310834`). The published row and column
counts are the ones in `DATASHEET.md`, which is generated from the payload itself; an
earlier revision of this paragraph restated them here and went stale.

The roughly 18 GB of intermediate `MASTER_pre_*` snapshots are not published. They are
build states, not product; the column lists and the enrichment companion tables carry
the audit trail.

## How to reproduce this release from the working master

```
python scripts/build_corpus.py                 # structured corpus + rehydration index
python scripts/build_kg.py                     # nodes, edges, vocabulary, count check
python scripts/build_enrichment.py             # 26 companion tables, CSV -> Parquet
python scripts/build_benchmark.py              # 67 queries + two-leg gold-set audit
python scripts/build_interactions.py           # synthetic interaction benchmark
python scripts/build_interaction_baselines.py  # its reference top-N baselines
python scripts/build_region_crosswalk.py       # user home_region -> KG entity resolution
python scripts/audit_corpus.py                 # independent allergen and diet audit
python scripts/make_data_dictionary.py         # regenerate docs/DATA_DICTIONARY.md
python scripts/build_release_facts.py          # regenerate release facts + datasheet
python scripts/make_checksums.py               # LAST before verifying: hashes docs/ too
python scripts/verify_release.py --strict-checksums
```

Order matters at the tail. `make_checksums.py` hashes `data/`, `docs/` and five root files,
so anything that regenerates prose — the data dictionary, the release facts, the datasheet —
has to run **before** it. Regenerating a document afterwards leaves a digest that no longer
matches the file, and `--strict-checksums` fails on it.

`scripts/release_config.py` holds the expected counts and the withheld-column list;
both the builders and the verifier import from it, so the licence guard and the
invariants cannot drift apart.

## Context layers added in 0.11.0

Two directories do not come from the working master and are not rebuilt by the pipeline above.

| directory | upstream | pinned input | produced by |
|---|---|---|---|
| `data/cultural_context/` | internal source S1 | `occasions.csv` SHA-256 `4da2145b…1d68` (commit `5d8d780`, blob `e0f408d5`); `rules.yaml` SHA-256 `b1ed03b0…2c9f`, an uncommitted working copy | `scripts/stage_cultural_context.py` |
| `data/historical_snapshot/` | internal source S2 @ `051c975` | snapshot `recipes_structured.parquet` SHA-256 `ffbb5d14…b4d6` (uncommitted; declares 0.9.0) and 0.10.0 `recipes_structured.parquet` | `scripts/stage_historical_snapshot.py` |

Every row carries `prov_source_repo`, `prov_source_path`, `prov_source_sha256`,
`prov_source_commit` (a commit, or `uncommitted:<sha256>`), `prov_source_blob_id`,
`prov_source_locator`, `prov_import_script` and `prov_schema_version`. `prov_import_script`
names a file in this repository's `scripts/`. The SHA-256 each manifest records for it
(`import_scripts`) equals the file that ships. The manifests record every transformation,
dropped field and count.

The two staging scripts are **provenance records, not rebuild steps**. They take machine-local
source locations from a private source map that is not part of the release, name the sources
only as `internal source S1` and `internal source S2` (with commit and file SHA-256), and stop
on any pinned-hash mismatch.
`stage_historical_snapshot.py` also refuses to run unless the destination is byte-identical to
0.10.0. So they document how these bytes were produced, but they cannot regenerate them from
a clone. `scripts/context_rule_adapter.py` is a read-only consumer that maps a declared
occasion to three-state per-item predicates (`python scripts/context_rule_adapter.py --check`
runs its fixtures). It never evaluates a rule against a recipe's own labels.

Both layers are silver. Neither adds a recipe, a graph node or a graph edge.

## What is deliberately omitted, and how to regenerate it

| omitted | size | regenerate with |
|---|---|---|
| `graph.gpickle` | 487 MB | `python scripts/build_graph.py --out DIR --format gpickle` |
| `kg_dict.json` | 337 MB | `python scripts/build_graph.py --out DIR --format dict` |
| `recipe_text.parquet` | 959 MB | **not regenerable — contains withheld prose** |
| dense / structural embedding matrices | ~930 MB | separate Zenodo record, see README |
| `MASTER_pre_*.bak.csv` | ~18 GB | not published |
