"""Build the redistributable corpus tier from the working master.

Produces two artefacts under `data/corpus/`:

  recipes_structured.parquet   the v11 master with every prose column removed
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
    EXPECTED_RECIPES,
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

    if len(df) != EXPECTED_RECIPES:
        print(
            f"FATAL: expected {EXPECTED_RECIPES:,} rows, got {len(df):,}. "
            "Either the master changed or release_config.py is stale — resolve "
            "before releasing.",
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
        "columns_retained": int(len(structured.columns)),
        "columns_withheld": present_prose,
        "column_names": list(structured.columns),
        "rehydratable_rows": int(index["rehydratable"].sum()),
        "non_rehydratable_rows": int((~index["rehydratable"]).sum()),
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
