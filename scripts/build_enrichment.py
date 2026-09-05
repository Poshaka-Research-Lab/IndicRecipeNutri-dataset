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
    EXCLUDED_RECIPE_IDS,
    MASTER_CSV,
    PARQUET_COMPRESSION,
    PARQUET_COMPRESSION_LEVEL,
    PARQUET_ROW_GROUP_SIZE,
    PROSE_COLUMNS,
    REPO_ROOT,
    RETRIEVAL_DIR,
    WITHDRAWN_NONRECIPE_IDS,
    all_withdrawn_ids,
)

# Suffixes the pipeline appends to a column when it writes a repaired or inferred
# companion value. Stripped before the prose check so `Description_fix` is caught.
COMPANION_SUFFIXES = ("_fix", "_fill", "_orig", "_variant", "_inferred", "_src")

INCLUDE = [
    # DROPPED 2026-09-04 (decision D-4, option A). It published a superseded generation
    # of the allergen label -- 16 classes, no `ghee`, `sulphites` on 5,118 rows where
    # the corpus says 23,955 -- and its flags were 100% consistent with its OWN
    # `Allergens_v8` column, which differed from the master on 120,147 rows. The
    # release now has one allergen surface, `data/corpus/allergens.parquet`, and the
    # wide `has_*` view is derived from it by `scripts/allergen_surface.py`.
    # "allergens_v8.csv",
    # DROPPED 2026-09-04 (decision D-5). A SECOND published allergen surface, in a
    # vocabulary the corpus abolished: `peanuts` on 7,897 rows (retired for `peanut`)
    # and `none` on 58,574 (the corpus separates `none_detected` from `unknown`; this
    # table has no unassessed sentinel at all, so a scanned-clean row and a
    # never-assessed row are indistinguishable -- a fail-open Codex CXC 80-2020
    # forbids). The South Asian 5 and ghee are absent entirely.
    #
    # Its only unique content was 10,944 upstream `source/v5` assertions; those were
    # extracted before removal to SALVAGE_allergens_REVIEW/REJECTED_2026-09-04.csv.
    # Its other column, `has_ing`, duplicates the master `has_ingredients`.
    # "allergens_full.csv",
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


# Enrichment tables are built from the SOURCE csv/parquet files, not from the master, so
# they do not shrink when the master does. The V7 pass removed 3,812 non-recipe rows from
# the master (2026-09-01) and those rows still existed in every source enrichment table --
# `allergens_v8.parquet` published 224,002 rows against a 220,190-row corpus. Filtering on
# EXCLUDED_RECIPE_IDS alone could not catch it, because the V7 rows are not build-time
# exclusions: they are gone from the master entirely.
#
# Both id sets are dropped here. `verify_release.py` scans the published payload for both,
# so a table that misses this filter fails the build rather than shipping orphan rows.
# Read from the registry, not written out here. This line named two sets; a third was
# added to the corpus and not to this line, and all 801 of its rows shipped in 21
# published tables. release_config.WITHDRAWAL_SETS is now the one place a withdrawal
# population is declared.
DROP_IDS = set(all_withdrawn_ids())


def check_licence(name: str, columns: list[str]) -> list[str]:
    """Return the offending columns, empty if the table is clean."""
    return [c for c in columns if prose_stem(c) in PROSE_COLUMNS]



# ------------------------------------------------- master-authoritative columns
#
# ADDED 2026-09-04, after two published tables were found frozen at a superseded state:
#
#   renutrition_v3.per100g_kcal        byte-identical to the master's
#                                      `per100g_kcal_uncorrected`, and differing from the
#                                      master's CORRECTED `per100g_kcal` on 211,080 of
#                                      219,386 rows -- the per-serving/density defect the
#                                      datasheet describes as fixed and gated.
#   gluten_confidence_v2.*             0 differences against the master's `*_pre_r6`
#                                      snapshot; 37,006 and 26,681 against the current
#                                      columns.
#
# The cause is the comment above DROP_IDS: these tables are built from source CSVs, not
# from the master, so they cannot shrink when it shrinks and cannot GAIN a correction
# either. This block is the second half of that fix -- the row SET now follows the master
# (DROP_IDS) and these VALUES now follow it too.
#
# WHY THIS IS AN EXPLICIT DECLARATION AND NOT "refresh every shared column name".
# A shared name is a hypothesis, not a finding. An audit of these tables found five
# apparent 100% divergences that were name collisions:
#   * `Cuisine` in four fix_* tables is the fix's INPUT and equals the master's
#     `Cuisine_orig` with 0 differences -- refreshing it from the master's `Cuisine`
#     would overwrite the input with the output and destroy the record of what was fixed.
#   * `fix_spicelevel.SpiceLevel_inferred` holds mild/medium/hot while the identically
#     named master column holds True/False; it equals the master's `SpiceLevel` exactly.
# Refreshing on name alone would have silently corrupted roughly 54,000 cells. So nothing
# is refreshed unless it is named here, with the measurement that justified it.
#
# NOT LISTED, DELIBERATELY -- allergens_v8.csv. It publishes its own older generation of
# the label (its `has_*` flags are 100% consistent with its own `Allergens_v8` column,
# which differs from the master's `Allergens_v2` on 120,147 rows) and it shares ZERO
# column names with the master. Its `src_<class>` columns record WHICH channel fired --
# ingredient-text, kg-edge, both -- and cannot be reconstructed from a label string.
# Refreshing `has_*` while leaving `src_*` at the old scan would create rows asserting a
# class with no recorded evidence channel, which is a worse defect than the one being
# fixed. See decision D-4.
MASTER_AUTHORITATIVE: dict[str, list[str]] = {
    # same column name on both sides; the master's value wins
    "renutrition_v3.csv": [
        "confident_coverage", "grams_per_serving_v3", "serving_basis_v3",
        "per100g_confident", "per100g_available_v3", "energy_capped_v3",
        "per100g_kcal", "per100g_protein", "per100g_carb", "per100g_fat",
        "per100g_satfat", "per100g_sugar", "per100g_fiber", "per100g_sodium",
    ],
    "gluten_confidence_v2.csv": ["gluten_confidence", "gluten_declared"],
    # Found by gate M33, 2026-09-04. Both are small and both are genuine staleness, not
    # name collisions: the published value is NULL where the master has one (46 rows,
    # e.g. recipe 166869: master 105.0, published NaN), and False where the master says
    # True (5 rows). A collision looks like a systematic difference in DOMAIN; these are
    # a handful of cells missing a value the master has.
    "fix7_atwater.csv": ["Nut_Calories_orig"],
    "fix14_region.csv": ["region_corrected"],
}

_MASTER_CACHE: dict = {}


def _master_columns(cols: list[str]) -> "pd.DataFrame":
    """Read `cols` from the master once per process, keyed by recipe_id."""
    want = tuple(sorted(cols))
    if want not in _MASTER_CACHE:
        _MASTER_CACHE[want] = pd.read_csv(
            MASTER_CSV, usecols=["recipe_id"] + list(want), low_memory=False
        ).set_index("recipe_id")
    return _MASTER_CACHE[want]


def apply_master_authority(name: str, df: "pd.DataFrame") -> tuple["pd.DataFrame", int]:
    """Overwrite the declared columns from the master. Returns (df, cells_changed).

    Fails loudly rather than skipping if a declared column is missing on either side: a
    silently skipped refresh is how the original defect survived five days of rebuilds.
    """
    cols = MASTER_AUTHORITATIVE.get(name)
    if not cols or "recipe_id" not in df.columns:
        return df, 0

    missing_here = [c for c in cols if c not in df.columns]
    if missing_here:
        raise KeyError(
            f"{name}: MASTER_AUTHORITATIVE names column(s) {missing_here} that the table "
            f"does not have. Fix the declaration rather than letting the refresh skip."
        )

    m = _master_columns(cols)
    idx = df["recipe_id"].astype("int64")
    changed = 0
    for c in cols:
        new = idx.map(m[c])
        old = df[c]
        # NaN != NaN, so compare on the filled-string form to avoid counting two nulls
        # as a change. This is a report count only; the assignment below is unconditional.
        differs = old.astype(str).fillna("") != new.astype(str).fillna("")
        changed += int(differs.sum())
        df[c] = new.values
    return df, changed


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

        df, refreshed = apply_master_authority(name, df)

        if DROP_IDS and "recipe_id" in df.columns:
            before = len(df)
            df = df[~df["recipe_id"].isin(DROP_IDS)].reset_index(drop=True)
            dropped = before - len(df)
        else:
            dropped = 0

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
        written.append({
            "table": dst.name,
            "rows": int(len(df)),
            "columns": int(len(df.columns)),
            "rows_dropped_by_exclusion": dropped,
        })
        flag = f"  (-{dropped} excluded)" if dropped else ""
        if refreshed:
            flag += f"  [{refreshed:,} cells refreshed from master]"
        print(f"  {dst.name:38s} {len(df):>9,} rows  {dst.stat().st_size / 1e6:6.1f} MB{flag}")

    # ---------------- Special case: copy and exclude from parquet companions (M8, M9, M10) ----------------
    PARQUETS_INCLUDE = [
        # 2026-08-29: ingredient PREPARATION STATE, extracted from the ingredient text.
        # `deseeded`, `slit`, `soaked`, `boiled` kept being proposed for deletion from the
        # ingredient vocabulary as junk. They are not ingredients, but they are not junk
        # either -- they are a second signal in the same field, and 62.1% of recipes carry
        # one. `CookingMethod` is recipe-level and 12-valued; it cannot say WHICH ingredient
        # was prepared how.
        "prep_features.parquet",
        "prep_ingredient.parquet",
        "ingredients_recovered.parquet",
        "ingredients_weights.parquet",
        "ingredients_nutrition.parquet"
    ]
    
    for name in PARQUETS_INCLUDE:
        src = args.source / name
        if not src.exists():
            print(f"FATAL: missing {src}", file=sys.stderr)
            return 1
            
        df = pd.read_parquet(src)
        offending = check_licence(name, list(df.columns))
        if offending:
            print(
                f"FATAL: {name} carries withheld prose columns {offending}. "
                "Drop the columns; do not release it.",
                file=sys.stderr,
            )
            return 1
            
        if DROP_IDS and "recipe_id" in df.columns:
            before = len(df)
            df = df[~df["recipe_id"].isin(DROP_IDS)].reset_index(drop=True)
            dropped = before - len(df)
        else:
            dropped = 0
            
        dst = args.out / name
        pq.write_table(
            pa.Table.from_pandas(df, preserve_index=False),
            dst,
            compression=PARQUET_COMPRESSION,
            compression_level=PARQUET_COMPRESSION_LEVEL,
            row_group_size=PARQUET_ROW_GROUP_SIZE,
        )
        total_in += src.stat().st_size
        total_out += dst.stat().st_size
        written.append({
            "table": dst.name,
            "rows": int(len(df)),
            "columns": int(len(df.columns)),
            "rows_dropped_by_exclusion": dropped,
        })
        flag = f"  (-{dropped} excluded)" if dropped else ""
        print(f"  {dst.name:38s} {len(df):>9,} rows  {dst.stat().st_size / 1e6:6.1f} MB{flag}")

    print(f"\n{len(written)} tables: {total_in / 1e6:.0f} MB total input -> {total_out / 1e6:.0f} MB Parquet")

    (args.out / "ENRICHMENT_MANIFEST.json").write_text(
        json.dumps({"tables": written, "excluded": EXCLUDED}, indent=2), encoding="utf-8"
    )
    print("wrote    ENRICHMENT_MANIFEST.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
