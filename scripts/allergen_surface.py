r"""The release's ONE allergen surface, and the wide view derived from it.

DECISION D-4, researcher, 2026-09-04: option A -- drop `allergens_v8` from the release and
let `data/corpus/allergens.parquet` be the single allergen surface.

WHY
---
The release carried two allergen surfaces that disagreed with each other:

  data/corpus/allergens.parquet     long form, 3,729,562 rows, 17 classes, derived from the
                                    master's `Allergens_v2` at build time. Agrees with the
                                    knowledge graph on every class with ZERO disagreement.
  data/enrichment/allergens_v8.*    wide `has_<class>` form, 16 classes, no `ghee`, built
                                    from a source CSV that was never rebuilt from the
                                    master. Its flags were 100% consistent with its OWN
                                    `Allergens_v8` label column -- which differed from the
                                    master's `Allergens_v2` on 120,147 of 219,386 rows. It
                                    asserted `sulphites` on 5,118 rows where the corpus says
                                    23,955.

A consumer filtering "no ghee" got 0 rows from one surface and 33,538 from the other, and
every gate passed because each compared one surface against a declaration that agreed with
it.

WHY NOT SIMPLY REFRESH IT
-------------------------
`allergens_v8` also carried `src_<class>` columns recording WHICH channel produced the
evidence -- `ingredient-text`, `kg-edge`, `both`. That cannot be reconstructed from a label
string. Refreshing the flags from the master while leaving `src_*` at the old scan would
have published rows asserting an allergen class with no recorded evidence channel: a worse
defect than the one being fixed. Regenerating `src_*` means re-running the dual-channel SA5
scan, which is a separate piece of work.

So the wide form is DERIVED here, on demand, from the long table. There is one allergen
surface in the release and one derivation of it in the code.

WHAT IS LOST, STATED PLAINLY
----------------------------
The `src_<class>` provenance for the four SA5 classes that had it (fenugreek, asafoetida,
tamarind, coconut) is not published in this release. It described a scan the corpus has
since moved past, so republishing it would have been provenance for the wrong labels. If the
channel breakdown is wanted, re-run the SA5 scan against the current master and publish it
as its own table rather than as columns on a flag table.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, os.environ.get("DATASETS_ROOT", r"D:\datasets"))
import allergen_taxonomy as _AT  # noqa: E402

#: The one published allergen surface, relative to the release repo root.
LONG_PATH = Path("data") / "corpus" / "allergens.parquet"

#: `status` values in the long table. `unassessed` is NOT absence -- under Codex CXC 80-2020
#: an operator must never assume an allergen is not present, so it must not read as False in
#: a safety filter. It is returned separately by `load_wide` for exactly that reason.
PRESENT = "present"
UNASSESSED = "unassessed"


def load_wide(repo_root: Path) -> pd.DataFrame:
    """Return the wide `has_<class>` frame, derived from the long table.

    One row per recipe, one boolean column per declared token, plus `n_allergens` and
    `allergen_unassessed`.

    `has_<class>` is True only where `status == "present"`. An `unassessed` row is NOT
    silently False on the flag alone -- it is False there and True in
    `allergen_unassessed`, so a consumer that ignores the second column gets the
    conservative reading of the first rather than a fabricated absence.
    """
    path = repo_root / LONG_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. It is built by migrate_schema.py and is the release's only "
            f"allergen surface since D-4 (2026-09-04); `allergens_v8.parquet` was dropped."
        )

    long = pd.read_parquet(path)
    present = long[long["status"] == PRESENT]

    # Built by set membership rather than a pivot. A pivot has to invent a value for every
    # (recipe, class) pair that is absent, which means a fillna on an object frame -- and
    # "what does a missing cell mean" is exactly the question a safety flag must not answer
    # implicitly. Membership makes the default explicit: not in the `present` set is False,
    # and `unassessed` is carried separately so False never has to stand for "not checked".
    all_ids = long["recipe_id"].drop_duplicates().sort_values()
    wide = pd.DataFrame(index=pd.Index(all_ids, name="recipe_id"))

    # Every declared token gets a column even if no recipe carries it, so a downstream
    # KeyError cannot depend on the corpus contents. A class with zero rows is a real
    # answer; a missing column is a crash.
    for t in _AT.TOKENS:
        ids = set(present.loc[present["allergen"] == t, "recipe_id"])
        wide[_AT.has_column(t)] = wide.index.isin(ids)

    unassessed = set(long.loc[long["status"] == UNASSESSED, "recipe_id"])
    wide["allergen_unassessed"] = wide.index.isin(unassessed)
    wide["n_allergens"] = wide[[_AT.has_column(t) for t in _AT.TOKENS]].sum(axis=1)

    return wide.reset_index()


def self_test(repo_root: Path) -> list[str]:
    """Invariants a caller can assert. Returns failure strings, empty when clean."""
    out: list[str] = []
    wide = load_wide(repo_root).set_index("recipe_id")
    long = pd.read_parquet(repo_root / LONG_PATH)

    for t in _AT.TOKENS:
        col = _AT.has_column(t)
        if col not in wide.columns:
            out.append(f"{col} missing from the derived wide frame")
            continue
        want = int(((long["allergen"] == t) & (long["status"] == PRESENT)).sum())
        got = int(wide[col].sum())
        if want != got:
            out.append(f"{col}: derived {got:,} != long-table {want:,}")

    if len(wide) != long["recipe_id"].nunique():
        out.append(f"row count {len(wide):,} != {long['recipe_id'].nunique():,} recipes")

    # ghee is a derivative marker and must never appear without milk (gate M26).
    if "has_ghee" in wide.columns and "has_milk" in wide.columns:
        bad = int((wide["has_ghee"] & ~wide["has_milk"]).sum())
        if bad:
            out.append(f"{bad:,} rows carry has_ghee without has_milk")

    return out


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    w = load_wide(root)
    print(f"derived wide frame: {len(w):,} rows x {len(w.columns)} cols")
    print(f"  {sum(1 for c in w.columns if c.startswith('has_'))} has_* columns")
    print(f"  unassessed: {int(w['allergen_unassessed'].sum()):,}")
    fails = self_test(root)
    print("self_test:", "PASS" if not fails else "FAIL")
    for f in fails:
        print("   ", f)
    raise SystemExit(1 if fails else 0)
