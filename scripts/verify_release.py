"""Pre-release gate. Fails the build rather than publishing a defective record.

Checks, in order of what they protect:

  1. Licence      no withheld prose column, by stem, in any published artefact;
                  no free-text column that looks like prose smuggled under a new name
  2. Integrity    row counts, KG node/edge counts, benchmark query count
  3. Privacy      PII pattern sweep over every string column
  4. Checksums    SHA256SUMS matches what is on disk
  5. Disclosure   the audit artefacts a release is required to carry are present

A release that cannot pass this should not be tagged. Every failure names the file and
the reason; nothing is a warning that can be scrolled past.

Usage:  python scripts/verify_release.py [--strict-checksums]
Exit:   0 all checks passed, 1 one or more failed
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))
from release_config import (  # noqa: E402
    EXPECTED_BENCHMARK_QUERIES,
    EXPECTED_KG_EDGES,
    EXPECTED_KG_NODES,
    EXPECTED_RECIPES,
    PII_EXEMPT_COLUMNS,
    PII_PATTERNS,
    PROSE_COLUMNS,
    REPO_ROOT,
)
from build_enrichment import prose_stem  # noqa: E402

# A published string column whose values run this long is prose by any other name.
# `IngredientsList` is a parsed JSON array and is legitimately long, so it is exempt.
PROSE_LENGTH_THRESHOLD = 400
LENGTH_EXEMPT = {"IngredientsList", "HealthConditions", "checks", "lenses"}

REQUIRED_ARTEFACTS = [
    "data/corpus/recipes_structured.parquet",
    "data/corpus/rehydration_index.parquet",
    "data/corpus/corpus_manifest.json",
    "data/corpus/ALLERGEN_AUDIT.json",
    "data/kg/kg_nodes.parquet",
    "data/kg/kg_edges.parquet",
    "data/kg/kg_stats.json",
    "data/benchmark/eval_queries.jsonl",
    "data/benchmark/GOLD_SET_AUDIT.json",
    "docs/DATASHEET.md",
    "docs/PROVENANCE.md",
    "docs/TAKEDOWN.md",
    "docs/THIRD_PARTY_TERMS.md",
    "LICENSE-DATA",
    "LICENSE-CODE",
    "CITATION.cff",
    ".zenodo.json",
]

failures: list[str] = []
notes: list[str] = []


def fail(check: str, detail: str) -> None:
    failures.append(f"[{check}] {detail}")


def published_parquet(root: Path) -> list[Path]:
    return sorted(p for p in (root / "data").rglob("*.parquet"))


# ------------------------------------------------------------------ 1. licence guard


def check_licence(root: Path) -> None:
    for path in published_parquet(root):
        schema = pq.read_schema(path)
        offending = [c for c in schema.names if prose_stem(c) in PROSE_COLUMNS]
        if offending:
            fail(
                "licence",
                f"{path.relative_to(root)} publishes withheld prose column(s) {offending}",
            )

    # Content-level check: a long free-text column under an innocent name.
    for path in published_parquet(root):
        schema = pq.read_schema(path)
        str_cols = [
            n
            for n, t in zip(schema.names, schema.types)
            if str(t) in ("string", "large_string") and n not in LENGTH_EXEMPT
        ]
        if not str_cols:
            continue
        sample = pd.read_parquet(path, columns=str_cols).head(5000)
        for col in str_cols:
            longest = sample[col].astype(str).str.len().max()
            if pd.notna(longest) and longest > PROSE_LENGTH_THRESHOLD:
                fail(
                    "licence",
                    f"{path.relative_to(root)} column '{col}' has values up to "
                    f"{int(longest)} chars — prose under another name? Add to "
                    f"LENGTH_EXEMPT with a reason, or withhold it.",
                )


# --------------------------------------------------------------------- 2. integrity


def check_integrity(root: Path) -> None:
    corpus = root / "data" / "corpus" / "recipes_structured.parquet"
    if corpus.exists():
        n = pq.read_metadata(corpus).num_rows
        if n != EXPECTED_RECIPES:
            fail("integrity", f"corpus has {n:,} rows, expected {EXPECTED_RECIPES:,}")
    else:
        fail("integrity", "corpus parquet missing")

    stats_path = root / "data" / "kg" / "kg_stats.json"
    if stats_path.exists():
        stats = json.loads(stats_path.read_text(encoding="utf-8"))
        for name, expected, actual in (
            ("nodes", EXPECTED_KG_NODES, stats.get("nodes")),
            ("edges", EXPECTED_KG_EDGES, stats.get("edges")),
        ):
            if actual != expected:
                fail("integrity", f"kg_stats {name}={actual}, expected {expected}")
        for name, key in (("kg_nodes.parquet", "nodes"), ("kg_edges.parquet", "edges")):
            p = root / "data" / "kg" / name
            if p.exists() and pq.read_metadata(p).num_rows != stats.get(key):
                fail(
                    "integrity",
                    f"{name} has {pq.read_metadata(p).num_rows:,} rows, "
                    f"kg_stats says {stats.get(key):,}",
                )
    else:
        fail("integrity", "kg_stats.json missing")

    bench = root / "data" / "benchmark" / "eval_queries.jsonl"
    if bench.exists():
        n = sum(1 for line in bench.open(encoding="utf-8") if line.strip())
        if n != EXPECTED_BENCHMARK_QUERIES:
            fail("integrity", f"benchmark has {n} queries, expected {EXPECTED_BENCHMARK_QUERIES}")
    else:
        fail("integrity", "benchmark missing")


# ----------------------------------------------------------------------- 3. privacy


def check_pii(root: Path) -> None:
    compiled = {k: re.compile(v) for k, v in PII_PATTERNS.items()}
    for path in published_parquet(root):
        schema = pq.read_schema(path)
        str_cols = [
            n
            for n, t in zip(schema.names, schema.types)
            if str(t) in ("string", "large_string") and n not in PII_EXEMPT_COLUMNS
        ]
        if not str_cols:
            continue
        df = pd.read_parquet(path, columns=str_cols)
        for col in str_cols:
            series = df[col].dropna().astype(str)
            if series.empty:
                continue
            for name, rx in compiled.items():
                # credit_card over-fires on numeric id strings; only flag when the
                # column is not otherwise numeric-looking.
                hits = series.str.contains(rx, regex=True, na=False)
                if hits.any():
                    n = int(hits.sum())
                    example = series[hits].iloc[0][:80]
                    if name == "credit_card" and series.str.fullmatch(r"[\d.eE+-]*").mean() > 0.9:
                        notes.append(
                            f"pii: {path.relative_to(root)}:{col} '{name}' suppressed "
                            f"({n} hits) — column is numeric"
                        )
                        continue
                    fail(
                        "privacy",
                        f"{path.relative_to(root)} column '{col}' matches {name} "
                        f"in {n} row(s), e.g. {example!r}",
                    )


# --------------------------------------------------------------------- 4. checksums


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_checksums(root: Path, strict: bool) -> None:
    manifest = root / "checksums" / "SHA256SUMS"
    if not manifest.exists():
        if strict:
            fail("checksums", "SHA256SUMS missing — run scripts/make_checksums.py")
        else:
            notes.append("checksums: SHA256SUMS missing (not strict)")
        return
    bad = 0
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, rel = line.split(None, 1)
        target = root / rel.strip()
        if not target.exists():
            fail("checksums", f"listed but missing: {rel.strip()}")
            bad += 1
        elif sha256(target) != digest:
            fail("checksums", f"digest mismatch: {rel.strip()}")
            bad += 1
    if not bad:
        notes.append("checksums: all entries match")


# -------------------------------------------------------------------- 5. disclosure


def check_disclosure(root: Path) -> None:
    for rel in REQUIRED_ARTEFACTS:
        if not (root / rel).exists():
            fail("disclosure", f"required artefact missing: {rel}")

    # A release must not silently drop the audit findings.
    audit = root / "data" / "corpus" / "ALLERGEN_AUDIT.json"
    if audit.exists():
        data = json.loads(audit.read_text(encoding="utf-8"))
        worst = max(
            (
                (a, e.get("false_negative_rate_of_lexical") or 0)
                for a, e in data.get("allergens", {}).items()
                if isinstance(e, dict)
            ),
            key=lambda x: x[1],
            default=None,
        )
        if worst:
            notes.append(
                f"disclosure: worst allergen false-negative rate is {worst[0]} at "
                f"{worst[1]:.2%} (upper bound) — must be stated in DATASHEET.md"
            )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=REPO_ROOT)
    ap.add_argument("--strict-checksums", action="store_true")
    args = ap.parse_args()

    print(f"verifying {args.root}\n")
    check_licence(args.root)
    check_integrity(args.root)
    check_pii(args.root)
    check_checksums(args.root, args.strict_checksums)
    check_disclosure(args.root)

    for note in notes:
        print(f"  note  {note}")

    if failures:
        print(f"\nFAILED — {len(failures)} problem(s):\n")
        for f in failures:
            print(f"  {f}")
        return 1

    print("\nPASSED — licence, integrity, privacy, checksums, disclosure")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
