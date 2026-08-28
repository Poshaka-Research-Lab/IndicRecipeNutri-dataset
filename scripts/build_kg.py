"""Stage the typed knowledge graph and the ingredient vocabulary into the release.

The node and edge tables are already Parquet in the working tree, but they are
**re-encoded rather than copied**. The working copies were written by pyarrow 25 with
Parquet size statistics that pyarrow 19 cannot read at all — it raises
"Repetition level histogram size mismatch" on any read, including a single-column one.
Shipping those files would hand anyone on an older Arrow a knowledge graph they cannot
open. Re-encoding through the release's own writer settings means every published file
comes from one writer and reads on both.

No value is altered by the re-encode; only the container changes. The row counts are
checked against `kg_stats.json` afterwards.

If the local pyarrow cannot read the source, the script falls back to DuckDB, which
parses Parquet independently. Install it with `pip install duckdb` if that path is
needed.

Deliberately does NOT copy `graph.gpickle` (487 MB) or `kg_dict.json` (337 MB): both
are regenerable from the node and edge tables via `scripts/build_graph.py`.

Usage:  python scripts/build_kg.py [--source PATH] [--out PATH]
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))
from release_config import (  # noqa: E402
    EXPECTED_KG_EDGES,
    PARQUET_COMPRESSION,
    PARQUET_COMPRESSION_LEVEL,
    PARQUET_ROW_GROUP_SIZE,
    EXPECTED_KG_NODES,
    KG_DIR,
    REPO_ROOT,
)

# name in source tree -> name in release
TABLES = {
    "kg_nodes.parquet": "kg_nodes.parquet",
    "kg_edges.parquet": "kg_edges.parquet",
}

VOCAB = {
    "kg_stats.json": "kg_stats.json",
    "ingredient_map.json": "ingredient_map.json",
    "ingredient_tier.json": "ingredient_tier.json",
    "ingredient_freq.json": "ingredient_freq.json",
}

# Regenerable, deliberately excluded. Recorded so the omission is explicit rather
# than silent — a reader of the release should be able to see what is missing and why.
EXCLUDED = {
    "graph.gpickle": "487 MB; regenerable from kg_nodes/kg_edges via scripts/build_graph.py",
    "kg_dict.json": "337 MB; regenerable from kg_nodes/kg_edges via scripts/build_graph.py",
}


def read_parquet_resilient(path: Path) -> "pa.Table":
    """Read a Parquet file, falling back to DuckDB when Arrow refuses it.

    pyarrow 19 cannot read files carrying the size statistics that pyarrow 25 writes.
    DuckDB parses Parquet independently and is unaffected.
    """
    try:
        return pq.read_table(path)
    except OSError as exc:
        print(f"  pyarrow could not read {path.name} ({exc}); falling back to DuckDB")

    try:
        import duckdb
    except ImportError:
        print(
            f"FATAL: {path.name} is unreadable by this pyarrow "
            f"({pa.__version__}) and DuckDB is not installed. "
            "Install it with `pip install duckdb`, or rebuild the source table with "
            "a matching Arrow version.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None

    result = duckdb.sql(f"select * from '{path.as_posix()}'")
    # DuckDB renamed this in 1.5; support both without tripping the deprecation.
    fetch = getattr(result, "to_arrow_table", None) or result.fetch_arrow_table
    fetched = fetch()
    if isinstance(fetched, pa.Table):
        return fetched
    return pa.Table.from_batches(fetched, fetched.schema)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, default=KG_DIR)
    ap.add_argument("--out", type=Path, default=REPO_ROOT / "data" / "kg")
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)

    for src_name, dst_name in TABLES.items():
        src = args.source / src_name
        if not src.exists():
            print(f"FATAL: missing {src}", file=sys.stderr)
            return 1
        table = read_parquet_resilient(src)
        dst = args.out / dst_name
        pq.write_table(
            table,
            dst,
            compression=PARQUET_COMPRESSION,
            compression_level=PARQUET_COMPRESSION_LEVEL,
            row_group_size=PARQUET_ROW_GROUP_SIZE,
        )
        # A published file that this Arrow cannot read back is not publishable.
        pq.read_table(dst, columns=[pq.read_schema(dst).names[0]])
        print(f"re-encoded {dst_name}  ({dst.stat().st_size / 1e6:.1f} MB, verified readable)")

    for src_name, dst_name in VOCAB.items():
        src = args.source / src_name
        if not src.exists():
            print(f"FATAL: missing {src}", file=sys.stderr)
            return 1
        dst = args.out / dst_name
        shutil.copy2(src, dst)
        print(f"copied     {dst_name}  ({dst.stat().st_size / 1e6:.1f} MB)")

    # ------------------------------------------------- check against the stats file
    stats = json.loads((args.out / "kg_stats.json").read_text(encoding="utf-8"))
    n_nodes = pq.read_metadata(args.out / "kg_nodes.parquet").num_rows
    n_edges = pq.read_metadata(args.out / "kg_edges.parquet").num_rows

    problems = []
    if stats["nodes"] != EXPECTED_KG_NODES:
        problems.append(f"kg_stats nodes={stats['nodes']} != expected {EXPECTED_KG_NODES}")
    if stats["edges"] != EXPECTED_KG_EDGES:
        problems.append(f"kg_stats edges={stats['edges']} != expected {EXPECTED_KG_EDGES}")
    if n_nodes != stats["nodes"]:
        problems.append(f"kg_nodes.parquet rows={n_nodes} != kg_stats nodes={stats['nodes']}")
    if n_edges != stats["edges"]:
        problems.append(f"kg_edges.parquet rows={n_edges} != kg_stats edges={stats['edges']}")

    if problems:
        print("FATAL: knowledge-graph counts disagree:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    print(f"verified {n_nodes:,} nodes / {n_edges:,} edges against kg_stats.json")

    (args.out / "EXCLUDED.json").write_text(json.dumps(EXCLUDED, indent=2), encoding="utf-8")
    print("wrote    EXCLUDED.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
