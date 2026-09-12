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


def edge_columns(edges):
    """Resolve columns by name; the release order is head, rel, tail."""
    if {"head", "rel", "tail"} <= set(edges.columns):
        return "head", "tail", "rel"
    if {"src", "rel", "dst"} <= set(edges.columns):
        return "src", "dst", "rel"
    raise ValueError("edge table requires head/rel/tail or src/rel/dst")


def restore_graph(nodes, edges, evidence=None):
    import networkx as nx
    source, target, relation = edge_columns(edges)
    g = nx.MultiDiGraph()
    if nodes.node_id.duplicated().any() or nodes.node_id.isna().any():
        raise ValueError("null or duplicate node IDs")
    for row in nodes.itertuples(index=False):
        g.add_node(str(row.node_id), **row._asdict())
    for s, t, r in zip(edges[source], edges[target], edges[relation]):
        s, t, r = str(s), str(t), str(r)
        if s not in g or t not in g:
            raise ValueError(f"dangling edge {(s, r, t)}")
        if g.has_edge(s, t, key=r):
            raise ValueError(f"duplicate triple {(s, r, t)}")
        g.add_edge(s, t, key=r, rel=r, relation=r)
    if evidence is not None:
        es, et, er = edge_columns(evidence)
        if evidence.duplicated([es, er, et]).any():
            raise ValueError("duplicate edge evidence keys")
        for row in evidence.to_dict('records'):
            s, t, r = str(row[es]), str(row[et]), str(row[er])
            if not g.has_edge(s, t, key=r):
                raise ValueError(f"evidence refers to absent triple {(s, r, t)}")
            attrs = json.loads(row['attributes_json'])
            if not isinstance(attrs, dict) or {'rel', 'relation'} & set(attrs):
                raise ValueError("invalid edge evidence attributes")
            g[s][t][r].update(attrs)
    return g


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--format", choices=["gpickle", "dict", "both"], default="both")
    ap.add_argument("--root", type=Path, default=REPO_ROOT)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    kg = args.root / "data" / "kg"
    nodes = pd.read_parquet(kg / "kg_nodes.parquet")
    edges = pd.read_parquet(kg / "kg_edges.parquet")
    print(f"loaded {len(nodes):,} nodes / {len(edges):,} edges")

    src_col, dst_col, rel_col = edge_columns(edges)
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
        evidence_path = kg / "kg_edge_evidence.parquet"
        evidence = pd.read_parquet(evidence_path) if evidence_path.exists() else None
        g = restore_graph(nodes, edges, evidence)
        path = args.out / "graph.gpickle"
        with path.open("wb") as fh:
            pickle.dump(g, fh, protocol=pickle.HIGHEST_PROTOCOL)
        print(f"wrote {path} ({path.stat().st_size / 1e6:.0f} MB)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
