#!/usr/bin/env python3
"""Build the FlavorDB-derived flavour layer as a SEPARATELY LICENSED tier.

Why this is its own file, and its own directory
-----------------------------------------------
FlavorDB is `CC BY-NC-SA 3.0`. NonCommercial and ShareAlike propagate to anything they
are mixed into. Putting compound nodes and shared-compound edges inside `data/kg/` would
force the whole knowledge graph -- and by extension the whole release -- onto NC-SA terms.

So the layer ships in `data/kg_flavor/` with its own `LICENSE` file. A consumer who wants
permissive terms uses `data/kg/` and ignores this directory; a consumer who accepts NC-SA
loads both and gets the flavour graph. The join key is `ingredient::<canonical>`, which is
the same node id the core graph uses, so merging is a concat.

This is the "tiered release" option: it keeps the layer without contaminating the core.

Emits
-----
    data/kg_flavor/flavor_nodes.parquet   compound nodes
    data/kg_flavor/flavor_edges.parquet   has_compound + shares_flavor
    data/kg_flavor/LICENSE                CC BY-NC-SA 3.0, with attribution
    data/kg_flavor/README.md              how to merge, and what the terms mean
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SRC = Path(r"D:\datasets\scraped_indian_recipes\data\kg")
OUT = REPO / "data" / "kg_flavor"

LICENSE = """# Licence for this directory ONLY — CC BY-NC-SA 3.0

**This directory is licensed differently from the rest of the release.**

The rest of `data/` carries the dataset's own licence. The files here are derived from
**FlavorDB** and are therefore governed by FlavorDB's terms:

    Creative Commons Attribution-NonCommercial-ShareAlike 3.0
    https://creativecommons.org/licenses/by-nc-sa/3.0/

## What that means

- **NonCommercial** — you may not use these files for commercial advantage.
- **ShareAlike** — anything you build from them must carry the same terms.
- **Attribution** — FlavorDB must be credited.

## Attribution

    Garg, N., Sethupathy, A., Tuwani, R., et al. FlavorDB: a database of flavor
    molecules. Nucleic Acids Research (2018).
    https://cosylab.iiitd.edu.in/flavordb/

## Why it is separated

If these files were merged into `data/kg/`, NonCommercial and ShareAlike would propagate
to the entire knowledge graph and to the release as a whole. Keeping them in their own
directory means a consumer who needs permissive terms can simply not load them, and the
core graph stays unencumbered.

**Do not copy these tables into `data/kg/`.** That single act would relicense everything.
"""

README = """# Flavour layer (FlavorDB-derived) — separately licensed

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
"""


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    # ---- compound nodes + has_compound -------------------------------------
    cf = SRC / "fix_flavor_compounds.csv"
    rows = list(csv.reader(open(cf, encoding="utf-8")))[1:]
    comp_nodes, has_comp = {}, []
    for r in rows:
        if len(r) < 3:
            continue
        ing, pid, name = r[0], r[1], r[2]
        cid = f"compound::{pid}"
        comp_nodes[cid] = name
        has_comp.append((f"ingredient::{ing}", "has_compound", cid))
    nodes = pd.DataFrame(
        [(k, "compound", v) for k, v in comp_nodes.items()],
        columns=["node_id", "type", "name"])

    # ---- shares_flavor -----------------------------------------------------
    ff = SRC / "fix_flavor_pairs.csv"
    sf = []
    for r in list(csv.reader(open(ff, encoding="utf-8")))[1:]:
        if len(r) < 4:
            continue
        sf.append((f"ingredient::{r[0]}", "shares_flavor", f"ingredient::{r[1]}",
                   int(r[2]), float(r[3])))

    edges = pd.DataFrame(
        [(h, r, t, None, None) for h, r, t in has_comp] + sf,
        columns=["head", "rel", "tail", "shared_compounds", "jaccard"])

    nodes.to_parquet(OUT / "flavor_nodes.parquet", index=False, compression="zstd")
    edges.to_parquet(OUT / "flavor_edges.parquet", index=False, compression="zstd")
    (OUT / "LICENSE").write_text(LICENSE, encoding="utf-8")
    (OUT / "README.md").write_text(README, encoding="utf-8")

    print(f"wrote {OUT}")
    print(f"  flavor_nodes.parquet : {len(nodes):,} compound nodes")
    print(f"  flavor_edges.parquet : {len(edges):,} edges "
          f"({len(has_comp):,} has_compound + {len(sf):,} shares_flavor)")
    print(f"  LICENSE              : CC BY-NC-SA 3.0 (this directory only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
