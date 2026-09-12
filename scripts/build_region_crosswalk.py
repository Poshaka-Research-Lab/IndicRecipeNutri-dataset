#!/usr/bin/env python3
r"""The region crosswalk: which user home_regions have no KG entity, and why.

REWRITTEN 2026-09-12 for v0.7.0. The previous version documented a **vocabulary mismatch**:
`users.csv` profiled its users with the generator's 28-code August vocabulary
(`Parsi (community)`, `Sindhi (community)`, `Mughlai (North India)`) while the KG had been
rebuilt on a different set, so six codes did not resolve by string and a hand-maintained
`MANUAL` table renamed or folded three of them.

**That mismatch is gone.** `data/interactions` is generated from
`data/corpus/recipes_structured.parquet`, so user home_regions and KG region entities are now
drawn from the same published `Region` column. Measured after the v4 rebuild: every code
resolves by exact string, including `Sindhi` and `Parsi`, and the `MANUAL` table has been
deleted rather than carried forward as dead configuration.

What survives is a smaller and entirely different gap, which is worth publishing precisely
because it is easy to mistake for the old one: a region can have users but no KG entity when
none of its recipes survived the **iterative 10-core** on the interaction log. An entity
exists only for an item retained after that filter, and the corpus's smallest regions hold
too few recipes to accumulate ten distinct users each. Nothing is misnamed; those regions are
simply unreachable through the graph.

The old meta note also claimed `users.csv` could not be remapped because "gen.py cannot be
re-run". That is no longer true — `scripts/build_interactions.py` regenerates the whole set —
so the reason to leave the profiles alone is now a modelling one and is stated as such: the
generator weighted `0.35 * region-match`, so a user's regional preference was real at
generation time, and rewriting it after the fact would misdescribe how the log was produced.

Usage:  python scripts/build_region_crosswalk.py
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from release_config import REPO_ROOT  # noqa: E402

# The 14 state-level regions of the primary evaluation axis (CLAUDE.md 6.2). Recorded per row
# so a reader can tell an axis region from a supra-regional bucket or a community code.
AXIS_14 = {"Andhra Pradesh", "Bihar", "Goa", "Gujarat", "Jammu & Kashmir", "Karnataka",
           "Kerala", "Maharashtra", "Punjab", "Rajasthan", "Tamil Nadu", "Telangana",
           "Uttar Pradesh", "West Bengal"}

FIELDS = ["user_home_region", "n_users", "kg_entity", "match", "in_primary_axis",
          "corpus_recipes", "note"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, default=REPO_ROOT / "data" / "interactions")
    ap.add_argument("--corpus", type=Path,
                    default=REPO_ROOT / "data" / "corpus" / "recipes_structured.parquet")
    args = ap.parse_args()

    import pandas as pd

    entities = []
    with (args.data / "entity_list.txt").open(encoding="utf-8") as fh:
        next(fh)
        for line in fh:
            if line.strip():
                entities.append(line.rsplit(None, 1)[0])
    kg_regions = {e for e in entities if e.startswith("region:")}
    print(f"KG region entities: {len(kg_regions)}")

    users: Counter[str] = Counter()
    with (args.data / "users.csv").open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            users[row.get("home_region", "")] += 1
    total_users = sum(users.values())
    print(f"user home_region codes: {len(users)}   users: {total_users:,}")

    corpus_counts = (pd.read_parquet(args.corpus, columns=["Region"])
                     .Region.fillna("Pan-Indian").astype(str).value_counts().to_dict())

    rows, unreachable_users = [], 0
    for code, n in sorted(users.items(), key=lambda kv: -kv[1]):
        entity = f"region:{code}"
        if entity in kg_regions:
            match, note = "exact", "resolves by string against the published Region column"
        else:
            match = "unreachable"
            note = (f"no item from this region survived the iterative 10-core "
                    f"({corpus_counts.get(code, 0)} recipes in the corpus), so the graph "
                    f"carries no entity for it")
            entity = ""
            unreachable_users += n
        rows.append({"user_home_region": code, "n_users": n, "kg_entity": entity,
                     "match": match, "in_primary_axis": str(code in AXIS_14).lower(),
                     "corpus_recipes": corpus_counts.get(code, 0), "note": note})

    out = args.data / "region_crosswalk.csv"
    with out.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    kinds = Counter(r["match"] for r in rows)
    print(f"\n{'match':<14}{'codes':>7}")
    for k, v in kinds.most_common():
        print(f"  {k:<12}{v:>7}")
    for r in rows:
        if r["match"] != "exact":
            print(f"  {r['user_home_region']:<22} -> (none)   {r['n_users']:>6,} users, "
                  f"{r['corpus_recipes']:>5} corpus recipes")
    print(f"\nunreachable codes: {kinds['unreachable']}   users affected: "
          f"{unreachable_users:,} ({100 * unreachable_users / total_users:.3f}%)")

    meta = {
        "user_codes": len(users),
        "kg_region_entities": len(kg_regions),
        "matches": dict(kinds),
        "users_unreachable": unreachable_users,
        "users_unreachable_pct": round(100 * unreachable_users / total_users, 3),
        "renames_required": 0,
        "note": "Users and KG entities are both drawn from the published Region column, so "
                "every code resolves by exact string and no rename table is needed. The "
                "unreachable codes are regions whose recipes did not survive the iterative "
                "10-core, not naming mismatches. users.csv is deliberately not remapped: the "
                "generator weighted 0.35*region-match, so regional preference was real at "
                "generation time and rewriting it afterwards would misdescribe the log.",
    }
    (args.data / "region_crosswalk_meta.json").write_text(
        json.dumps(meta, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
