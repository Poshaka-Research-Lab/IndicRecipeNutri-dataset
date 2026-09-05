#!/usr/bin/env python3
r"""Stamp the unit registry onto the published Parquet schemas, and emit docs/UNITS.json.

Before this, 0 of 236 Arrow fields carried metadata and every pandas column metadata entry
was null, so no unit was readable by any tool. A consumer opening
`recipes_structured.parquet` had to guess — and `per100g_sodium` (mg) sits beside
`per100g_salt` (g), differing by 400x under an identical name pattern.

Two outputs, because two kinds of consumer:
  * Arrow FIELD metadata on the parquet — what pandas/polars/duckdb/HuggingFace read
  * docs/UNITS.json — what a person or an indexing service reads, plus the DV reference

Rewriting the parquet preserves the data exactly: the table is read, its schema is replaced
with an identically-typed schema carrying metadata, and the row count and every column's
non-null count are asserted unchanged before the file is replaced.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from column_units import COLUMN_UNITS, DV_REFERENCE, undeclared  # noqa: E402
from release_config import REPO_ROOT  # noqa: E402

TARGETS = [
    "data/corpus/recipes_structured.parquet",
    "data/kg/kg_nodes.parquet",
]


def stamp(path: Path) -> dict:
    table = pq.read_table(path)
    before_rows = table.num_rows
    before_nn = {n: table.column(n).null_count for n in table.column_names}

    fields, stamped = [], 0
    for f in table.schema:
        decl = COLUMN_UNITS.get(f.name)
        if decl is None:
            fields.append(f)
            continue
        md = {
            b"unit": str(decl["unit"]).encode(),
            b"basis": str(decl["basis"]).encode(),
            b"basis_note": str(decl["basis_note"]).encode(),
        }
        if decl.get("domain"):
            md[b"domain"] = json.dumps(decl["domain"]).encode()
        fields.append(f.with_metadata(md))
        stamped += 1

    schema_md = dict(table.schema.metadata or {})
    schema_md[b"units_registry"] = b"scripts/column_units.py"
    schema_md[b"dv_reference"] = json.dumps(DV_REFERENCE["standard"]).encode()
    new = table.cast(pa.schema(fields, metadata=schema_md))

    assert new.num_rows == before_rows, "row count changed"
    for n in new.column_names:
        assert new.column(n).null_count == before_nn[n], f"{n} null count changed"

    tmp = path.with_suffix(".units.tmp")
    pq.write_table(new, tmp, compression="snappy")
    shutil.move(str(tmp), str(path))
    return {"file": str(path.relative_to(REPO_ROOT)), "columns": len(table.column_names),
            "stamped": stamped, "rows": before_rows}


def main() -> int:
    results, gaps = [], {}
    for rel in TARGETS:
        p = REPO_ROOT / rel
        if not p.exists():
            print(f"absent, skipped: {rel}")
            continue
        schema = pq.read_schema(p)
        numeric = [n for n, t in zip(schema.names, schema.types)
                   if str(t) in ("double", "int64", "float", "int32")]
        missing = undeclared(numeric)
        if missing:
            gaps[rel] = missing
        r = stamp(p)
        results.append(r)
        print(f"{rel}: stamped {r['stamped']}/{r['columns']} fields, "
              f"{r['rows']:,} rows preserved")
        if missing:
            print(f"    {len(missing)} numeric column(s) with NO declaration: "
                  f"{', '.join(missing[:8])}")

    out = REPO_ROOT / "docs" / "UNITS.json"
    json.dump({
        "what": "Unit, basis and physical domain for every dimensioned column in the "
                "IndicRecipeNutri release. Authoritative over column NAMES where the two "
                "disagree — see grams_per_serving_v3, whose name declares the wrong basis.",
        "generated_by": "scripts/stamp_units.py from scripts/column_units.py",
        "how_units_were_established": "The build never recorded them. Each was derived from "
                                      "median magnitude against physiological range on "
                                      "2026-09-02, and the derivation is in each column's "
                                      "basis_note so it can be checked rather than trusted. "
                                      "The two that were TBD were resolved on 2026-09-05 "
                                      "from the builder rather than from magnitude: "
                                      "Nut_VitaminA is ug RAE (FDC nutrient 1106) and "
                                      "Nut_Folate is TOTAL folate (FDC 1177), not DFE — so "
                                      "DV_Folate, which divides by the 400 ug DFE Daily "
                                      "Value, is not a DFE percentage. Both carry a caveat "
                                      "for the 2.5% of composition rows drawn from the INDB "
                                      "spreadsheets, whose headers state no vitamer basis.",
        "unit_vocabulary": {
            "kcal": "kilocalories", "g": "grams", "mg": "milligrams",
            "ug": "micrograms", "min": "minutes", "%": "percent",
            "1": "dimensionless ratio or count",
        },
        "watch_out": [
            "per100g_sodium is mg/100g; per100g_salt is g/100g. Same prefix, 400x apart.",
            "ProteinPct/CarbPct/FatPct are percent of ENERGY, not of mass.",
            "grams_per_serving_v3 is a whole-dish weight despite its name.",
            "DV_* are percentages of US FDA 2016 Daily Values, not an Indian reference "
            "intake. ICMR-NIN 2020 RDAs differ.",
        ],
        "dv_reference": DV_REFERENCE,
        "columns": {k: v for k, v in sorted(COLUMN_UNITS.items())},
        "undeclared_numeric_columns": gaps,
        "files_stamped": results,
    # newline="\n" is load-bearing: docs/*.json is `text eol=lf` in .gitattributes and this
    # file's digest is pinned. Written with the platform default it is CRLF here and LF on a
    # Linux checkout, so --strict-checksums passes locally and fails on the runner.
    }, open(out, "w", encoding="utf-8", newline="\n"), indent=1)
    print(f"\nwrote {out.relative_to(REPO_ROOT)}  ({len(COLUMN_UNITS)} declarations)")
    if gaps:
        print("\nNUMERIC COLUMNS WITH NO UNIT — the gate will fail on these:")
        for f, cs in gaps.items():
            print(f"  {f}: {cs}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
