# Flavour layer (FlavorDB-derived) — separately licensed

⚠️ **Read `LICENSE` in this directory first. These files are CC BY-NC-SA 3.0 and the rest
of the release is not.**

## Contents

| file | rows | what |
|---|---:|---|
| `flavor_nodes.parquet` | see below | `compound` nodes — flavour molecules |
| `flavor_edges.parquet` | see below | `has_compound` (ingredient → molecule) and `shares_flavor` (ingredient ↔ ingredient, shared-molecule Jaccard) |

## How to merge with the core graph

Node ids match the core graph exactly, so it is a concatenation:

```python
import pandas as pd
nodes = pd.concat([pd.read_parquet("data/kg/kg_nodes.parquet"),
                   pd.read_parquet("data/kg_flavor/flavor_nodes.parquet")])
edges = pd.concat([pd.read_parquet("data/kg/kg_edges.parquet"),
                   pd.read_parquet("data/kg_flavor/flavor_edges.parquet")])
```

**The moment you do this, the merged graph is CC BY-NC-SA 3.0.**

## Relationship to `pairs_with` in the core graph

The core graph carries a `pairs_with` relation built from **ingredient co-occurrence in
this corpus** (PMI over `has_ingredient`). It is ours, unencumbered, and measures what
Indian cooks actually do.

`shares_flavor` here is a different claim: shared volatile molecules. The two agree on
only **18.6%** of our pairs — which is the direction the literature predicts, since Indian
cuisine is the standard counter-example to the food-pairing hypothesis. **They are
complementary, not redundant.** Use `pairs_with` for empirical pairing and `shares_flavor`
for the molecular hypothesis, and do not silently substitute one for the other.
