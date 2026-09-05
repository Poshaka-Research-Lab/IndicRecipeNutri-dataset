"""Build the redistributable corpus tier from the working master.

Produces two artefacts under `data/corpus/`:

  recipes_structured.parquet   the v15 master with every prose column removed
  rehydration_index.parquet    recipe_id -> source URL + a digest of the prose we held

The prose columns are never written. Their SHA-256 digest goes into the rehydration
index so a user who re-fetches a source page can check they reconstructed the same
text this corpus was derived from, without us redistributing the text.

Usage:  python scripts/build_corpus.py [--source PATH] [--out PATH]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))
from release_config import (  # noqa: E402
    EXPECTED_CORPUS_BUILD,
    PII_EXEMPT_COLUMNS,
    PII_PATTERNS,
    EXCLUDED_RECIPE_IDS,
    EXCLUDED_SOURCE_SITES,
    EXPECTED_RECIPES,
    EXPECTED_SOURCE_RECIPES,
    MASTER_CSV,
    PARQUET_COMPRESSION,
    PARQUET_COMPRESSION_LEVEL,
    PARQUET_ROW_GROUP_SIZE,
    PROSE_COLUMNS,
    REPO_ROOT,
)


def prose_digest(row: pd.Series) -> str:
    """SHA-256 over the prose fields, in the fixed order given by PROSE_COLUMNS.

    Fields are joined with a NUL separator so that concatenation is unambiguous.
    A missing field contributes an empty string, not the literal "nan".
    """
    parts = []
    for col in PROSE_COLUMNS:
        val = row.get(col)
        parts.append("" if pd.isna(val) else str(val))
    return hashlib.sha256("\x00".join(parts).encode("utf-8")).hexdigest()


def redact_pii(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Replace personal-data matches in published string columns with a marker.

    This is a privacy action, not a data repair. Only the matched substring is
    replaced; the surrounding cell is left exactly as it was, so no recipe content is
    altered and the redaction is visible rather than silent. The working master is
    never modified — the redaction lives in the published artefact only, and is
    reapplied on every build.

    Every match is recorded by column, row and pattern so the action is auditable.
    """
    frame = frame.copy()
    record: dict = {"total": 0, "matches": [], "policy": (
        "Only the matched substring is replaced, with [redacted-<pattern>]. The cell "
        "is otherwise untouched and the source master is not modified."
    )}

    ids = frame["recipe_id"] if "recipe_id" in frame.columns else pd.Series(frame.index)

    for column in frame.columns:
        if column in PII_EXEMPT_COLUMNS or frame[column].dtype != object:
            continue
        series = frame[column]
        for name, pattern in PII_PATTERNS.items():
            if name == "credit_card":
                # Over-fires on decimal quantities; the release verifier applies the
                # anchored version. Redaction stays conservative and skips it.
                continue
            hits = series.fillna("").astype(str).str.contains(pattern, regex=True, na=False)
            if not hits.any():
                continue
            for rid in ids[hits].tolist():
                record["matches"].append(
                    {"column": column, "recipe_id": int(rid), "pattern": name}
                )
            record["total"] += int(hits.sum())
            series = series.astype(str).str.replace(
                pattern, f"[redacted-{name}]", regex=True
            ).where(frame[column].notna())
        frame[column] = series

    return frame, record


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, default=MASTER_CSV)
    ap.add_argument("--out", type=Path, default=REPO_ROOT / "data" / "corpus")
    args = ap.parse_args()

    if not args.source.exists():
        print(f"FATAL: master not found: {args.source}", file=sys.stderr)
        return 1

    args.out.mkdir(parents=True, exist_ok=True)

    print(f"reading  {args.source}  ({args.source.stat().st_size / 1e6:.0f} MB)")
    df = pd.read_csv(args.source, low_memory=False)
    print(f"  {len(df):,} rows x {len(df.columns)} columns")

    if len(df) != EXPECTED_SOURCE_RECIPES:
        print(
            f"FATAL: expected {EXPECTED_SOURCE_RECIPES:,} source rows, got {len(df):,}. "
            "Either the master changed or release_config.py is stale — resolve "
            "before releasing.",
            file=sys.stderr,
        )
        return 1

    # 2026-08-29: `nut_indb_frac` is MISNAMED in the master. It was documented as the
    # share of dish calories sourced from "INDB India-curated foods", but the FCT's
    # `source` labels `INDB-US` / `INDB-UK` are themselves misattributed: the two
    # spreadsheets carry `primarysource` = `usda` (54 rows) and `ukfct` (144 rows).
    # There is NO Indian composition data in the table -- it is 7,847 USDA plus 144 UK
    # CoFID. Publishing a column whose name asserts India-grounding would repeat the
    # retracted "IFCT-grounded" claim.
    #
    # The quantity itself is real and worth keeping: it is the share of calories drawn
    # from the supplementary tables rather than USDA SR Legacy. Renamed on publish only;
    # the master is not rewritten.
    if "nut_indb_frac" in df.columns:
        df = df.rename(columns={"nut_indb_frac": "nut_suppl_fct_frac"})
        print("renamed nut_indb_frac -> nut_suppl_fct_frac (see DATASHEET: no INDB data exists)")

    # A2, 2026-08-29. Same rename-on-publish pattern, for a safety column this time.
    #
    # `Allergens_filled` is superseded by `Allergens_v2` and was shipping beside it with no
    # marker saying so. It is the worse column in every respect that matters:
    #
    #   * 12 real classes, not 16 -- coconut, asafoetida, fenugreek and tamarind, this
    #     workspace's own declared South Asian extension, are absent entirely
    #   * 129 distinct values in the published frame, because some rows are still COMMA
    #     separated (`dairy,mustard`) where v2 is semicolon-only and has 18
    #   * un-normalised tokens survive: `dairy` alongside `milk`, `peanuts` alongside `peanut`
    #   * none of the later fixes: celery 501 vs 2,403, tree_nuts 29,140 vs 31,750,
    #     shellfish 3,397 vs 3,854
    #
    # It is renamed rather than dropped so a v1-era claim stays reproducible, but the name
    # now says what it is. A consumer scanning the schema for "the allergen column" can no
    # longer land on the fail-open one by accident, which is exactly how it stayed unnoticed.
    if "Allergens_filled" in df.columns:
        df = df.rename(columns={"Allergens_filled": "Allergens_v1_superseded"})
        print("renamed Allergens_filled -> Allergens_v1_superseded "
              "(12 of 16 classes, comma-encoded; use Allergens_v2)")

    # ------------------------------------------------------------------ exclusions
    if EXCLUDED_RECIPE_IDS:
        drop = df["recipe_id"].isin(EXCLUDED_RECIPE_IDS)
        for rid, reason in EXCLUDED_RECIPE_IDS.items():
            present = "present" if (df["recipe_id"] == rid).any() else "ALREADY ABSENT"
            print(f"excluding recipe_id={rid} ({present})")
            print(f"  reason: {reason}")
        df = df[~drop].reset_index(drop=True)
        print(f"  {len(df):,} rows remain")

    # D4.1: licence-driven source exclusions. These rows are not ours -- they came from
    # upstream datasets under NonCommercial / ShareAlike terms that would propagate to
    # the whole release. The master keeps them; this is a publication filter.
    if EXCLUDED_SOURCE_SITES and "SourceSite" in df.columns:
        before = len(df)
        for site, reason in EXCLUDED_SOURCE_SITES.items():
            n = int((df["SourceSite"] == site).sum())
            print(f"excluding SourceSite={site}: {n:,} rows")
            print(f"  reason: {reason}")
        df = df[~df["SourceSite"].isin(EXCLUDED_SOURCE_SITES)].reset_index(drop=True)
        print(f"  removed {before - len(df):,} rows; {len(df):,} remain")

    if len(df) != EXPECTED_RECIPES:
        print(
            f"FATAL: after exclusions expected {EXPECTED_RECIPES:,} rows, "
            f"got {len(df):,}.",
            file=sys.stderr,
        )
        return 1

    present_prose = [c for c in PROSE_COLUMNS if c in df.columns]
    missing_prose = [c for c in PROSE_COLUMNS if c not in df.columns]
    if missing_prose:
        print(f"  note: prose columns not in this master: {missing_prose}")

    # ---------------------------------------------------------- rehydration index
    print("building rehydration index")
    index = pd.DataFrame(
        {
            "recipe_id": df["recipe_id"],
            "URL": df["URL"],
            "SourceSite": df["SourceSite"],
            "Lang": df["Lang"],
        }
    )
    index["text_sha256"] = df[present_prose].apply(prose_digest, axis=1)

    # Not every row came from a scraped page. Rows sourced from pre-existing
    # datasets carry a placeholder URL and cannot be rehydrated by re-fetching;
    # marking them is more honest than letting a user discover it mid-crawl.
    host = index["URL"].fillna("").map(lambda u: urlparse(u).netloc)
    index["rehydratable"] = ~(host.str.endswith(".dataset") | host.eq(""))
    index["source_kind"] = index["rehydratable"].map(
        {True: "scraped_page", False: "derived_dataset"}
    )
    # Which prose fields were actually non-empty, so a rehydrator knows what to expect.
    for col in present_prose:
        index[f"had_{col.lower()}"] = df[col].notna() & (df[col].astype(str).str.strip() != "")

    # ------------------------------------------------------------ structured corpus
    print(f"dropping {len(present_prose)} prose columns: {present_prose}")
    structured = df.drop(columns=present_prose)
    print(f"  {len(structured):,} rows x {len(structured.columns)} columns retained")

    # ------------------------------------------------------------------- redaction
    structured, redactions = redact_pii(structured)
    if redactions["total"]:
        print(f"redacted {redactions['total']} personal-data match(es):")
        for entry in redactions["matches"]:
            print(f"  {entry['column']} row recipe_id={entry['recipe_id']} ({entry['pattern']})")
    else:
        print("redaction: no personal-data matches found")

    # ------------------------------------------------------------------- write out
    for name, frame in (
        ("recipes_structured.parquet", structured),
        ("rehydration_index.parquet", index),
    ):
        path = args.out / name
        table = pa.Table.from_pandas(frame, preserve_index=False)
        pq.write_table(
            table,
            path,
            compression=PARQUET_COMPRESSION,
            compression_level=PARQUET_COMPRESSION_LEVEL,
            row_group_size=PARQUET_ROW_GROUP_SIZE,
        )
        print(f"wrote    {path}  ({path.stat().st_size / 1e6:.1f} MB)")

    # ------------------------------------------------------------------- manifest
    manifest = {
        "corpus_build": EXPECTED_CORPUS_BUILD,
        "source_master": args.source.name,
        "rows": int(len(structured)),
        "excluded_recipe_ids": {str(k): v for k, v in EXCLUDED_RECIPE_IDS.items()},
        "excluded_source_sites": dict(EXCLUDED_SOURCE_SITES),
        "columns_retained": int(len(structured.columns)),
        "columns_withheld": present_prose,
        "column_names": list(structured.columns),
        "rehydratable_rows": int(index["rehydratable"].sum()),
        "non_rehydratable_rows": int((~index["rehydratable"]).sum()),
        "redactions": redactions,
        "withholding_policy": (
            "Prose columns are withheld under the two-tier release model "
            "(paper section 3.5). Their SHA-256 digest is published in "
            "rehydration_index.parquet so reconstructed text can be verified."
        ),
    }
    manifest_path = args.out / "corpus_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"wrote    {manifest_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
