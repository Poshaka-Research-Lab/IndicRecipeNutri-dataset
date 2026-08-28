"""Regenerate the in-memory graph objects that the release deliberately omits.

`graph.gpickle` (487 MB) and `kg_dict.json` (337 MB) are excluded from the release
because they are derivable. This script rebuilds both from `kg_nodes.parquet` and
`kg_edges.parquet`, so the omission costs a reader a command, not the artefact.

Usage:  python scripts/build_graph.py --out DIR [--format gpickle|dict|both]
"""

from __future__ import annotations

import argparse
import json
import pickle
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from release_config import REPO_ROOT  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--format", choices=["gpickle", "dict", "both"], default="both")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    kg = REPO_ROOT / "data" / "kg"
    nodes = pd.read_parquet(kg / "kg_nodes.parquet")
    edges = pd.read_parquet(kg / "kg_edges.parquet")
    print(f"loaded {len(nodes):,} nodes / {len(edges):,} edges")

    src_col, dst_col, rel_col = edges.columns[:3]
    print(f"edge columns interpreted as source={src_col!r} target={dst_col!r} relation={rel_col!r}")

    if args.format in ("dict", "both"):
        adj: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
        for s, t, r in zip(edges[src_col], edges[dst_col], edges[rel_col]):
            adj[str(s)][str(r)].append(str(t))
        path = args.out / "kg_dict.json"
        path.write_text(json.dumps({k: dict(v) for k, v in adj.items()}), encoding="utf-8")
        print(f"wrote {path} ({path.stat().st_size / 1e6:.0f} MB)")

    if args.format in ("gpickle", "both"):
        try:
            import networkx as nx
        except ImportError:
            print("networkx not installed; skipping gpickle", file=sys.stderr)
            return 0
        g = nx.MultiDiGraph()
        node_id = nodes.columns[0]
        for row in nodes.itertuples(index=False):
            g.add_node(str(getattr(row, node_id)), **row._asdict())
        for s, t, r in zip(edges[src_col], edges[dst_col], edges[rel_col]):
            g.add_edge(str(s), str(t), key=str(r), relation=str(r))
        path = args.out / "graph.gpickle"
        with path.open("wb") as fh:
            pickle.dump(g, fh, protocol=pickle.HIGHEST_PROTOCOL)
        print(f"wrote {path} ({path.stat().st_size / 1e6:.0f} MB)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
