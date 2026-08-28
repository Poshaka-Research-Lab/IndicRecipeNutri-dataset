"""Convert the enrichment companion tables to Parquet for the release.

Every table is checked against the licence guard before it is written: a column whose
stem matches a withheld prose column (so `Description`, but also `Description_fix`)
aborts the build. Two source tables are excluded outright for exactly that reason and
the exclusion is recorded rather than left silent.

Usage:  python scripts/build_enrichment.py [--source PATH] [--out PATH]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))
from release_config import (  # noqa: E402
    PARQUET_COMPRESSION,
    PARQUET_COMPRESSION_LEVEL,
    PARQUET_ROW_GROUP_SIZE,
    PROSE_COLUMNS,
    REPO_ROOT,
    RETRIEVAL_DIR,
)

# Suffixes the pipeline appends to a column when it writes a repaired or inferred
# companion value. Stripped before the prose check so `Description_fix` is caught.
COMPANION_SUFFIXES = ("_fix", "_fill", "_orig", "_variant", "_inferred", "_src")

INCLUDE = [
    "allergens_v8.csv",
    "allergens_full.csv",
    "fix_allergens.csv",
    "renutrition_v3.csv",
    "nutrition_totals.csv",
    "fix_nutrition.csv",
    "fix7_atwater.csv",
    "gluten_confidence_v2.csv",
    "fix11_nonveg.csv",
    "fix14_region.csv",
    "fix_region.csv",
    "fix_region_review.csv",
    "fix_subcontinental_region.csv",
    "fix_cuisine_scope.csv",
    "fix_occasion_context.csv",
    "fix_spicelevel.csv",
    "fix_glhg.csv",
    "fix_savory_convert.csv",
    "fix_ingredient_reclassify.csv",
    "fix_recipe_rename.csv",
    "fix_variants.csv",
    "fix_text.csv",
    "quarantine_list.csv",
]

EXCLUDED = {
    "mojibake_rows.csv": (
        "carries raw Description and Ingredients prose; withheld under the two-tier "
        "release model (paper section 3.5). The per-row outcome is published as the "
        "`mojibake_fixed` flag in recipes_structured.parquet."
    ),
    "fix_mojibake.csv": (
        "carries Description_fix and Ingredients_fix prose; withheld for the same "
        "reason as mojibake_rows.csv."
    ),
}


def prose_stem(column: str) -> str:
    """Reduce a companion column name to the source column it derives from."""
    stem = column
    changed = True
    while changed:
        changed = False
        for suffix in COMPANION_SUFFIXES:
            if stem.endswith(suffix) and len(stem) > len(suffix):
                stem = stem[: -len(suffix)]
                changed = True
    return stem


def check_licence(name: str, columns: list[str]) -> list[str]:
    """Return the offending columns, empty if the table is clean."""
    return [c for c in columns if prose_stem(c) in PROSE_COLUMNS]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, default=RETRIEVAL_DIR / "enrichment")
    ap.add_argument("--out", type=Path, default=REPO_ROOT / "data" / "enrichment")
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    total_in = total_out = 0
    written = []

    for name in INCLUDE:
        src = args.source / name
        if not src.exists():
            print(f"FATAL: missing {src}", file=sys.stderr)
            return 1

        df = pd.read_csv(src, low_memory=False)
        offending = check_licence(name, list(df.columns))
        if offending:
            print(
                f"FATAL: {name} carries withheld prose columns {offending}. "
                "Add it to EXCLUDED or drop the columns; do not release it.",
                file=sys.stderr,
            )
            return 1

        dst = args.out / (src.stem + ".parquet")
        pq.write_table(
            pa.Table.from_pandas(df, preserve_index=False),
            dst,
            compression=PARQUET_COMPRESSION,
            compression_level=PARQUET_COMPRESSION_LEVEL,
            row_group_size=PARQUET_ROW_GROUP_SIZE,
        )
        total_in += src.stat().st_size
        total_out += dst.stat().st_size
        written.append({"table": dst.name, "rows": int(len(df)), "columns": int(len(df.columns))})
        print(f"  {dst.name:38s} {len(df):>9,} rows  {dst.stat().st_size / 1e6:6.1f} MB")

    print(f"\n{len(written)} tables: {total_in / 1e6:.0f} MB CSV -> {total_out / 1e6:.0f} MB Parquet")

    (args.out / "ENRICHMENT_MANIFEST.json").write_text(
        json.dumps({"tables": written, "excluded": EXCLUDED}, indent=2), encoding="utf-8"
    )
    print("wrote    ENRICHMENT_MANIFEST.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
