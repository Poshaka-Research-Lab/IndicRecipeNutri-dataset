#!/usr/bin/env python3
r"""R2 - the region crosswalk. Makes the user/KG vocabulary mismatch explicit.

`users.csv` profiles 50,000 synthetic users with `home_region` drawn from the **28-code**
vocabulary the generator used in August. The KG was rebuilt on **14 primary state-level
regions + 10 marked supra-regional buckets = 24 entities**. Six user codes do not resolve
by string, and four of those have no target at all:

    Parsi (community)      -> region_supra:Parsi          (renamed)
    Sindhi (community)     -> region_supra:Sindhi         (renamed)
    Mughlai (North India)  -> region_supra:North_India    (folded; a culinary lineage, not
                                                           a geography - CLAUDE.md 6.2)
    Uttarakhand            -> (none)   8 recipes, below --min_per_region
    Manipur                -> (none)   1 recipe
    West India             -> (none)   3 recipes

The generator weighted `0.35 * region-match`, so those users' region preference was real at
generation time and is unreachable now. **Remapping `users.csv` was rejected**: it would
change a file that `interactions.csv`, `train.txt` and `test.txt` were built against, and
the generator cannot be re-run. A crosswalk states the mismatch instead of erasing it.
"""
from __future__ import annotations

import csv
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.environ.get("DATASETS_ROOT", r"D:\datasets"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = r"D:\datasets\IndicRecipeNutri-dataset"
SI = os.path.join(ROOT, "data", "synthetic_interactions")

AXIS_14 = {"Andhra Pradesh", "Bihar", "Goa", "Gujarat", "Jammu & Kashmir", "Karnataka",
           "Kerala", "Maharashtra", "Punjab", "Rajasthan", "Tamil Nadu", "Telangana",
           "Uttar Pradesh", "West Bengal"}

# explicit, reviewed mappings for the codes that do not match by string
MANUAL = {
    "Parsi (community)":     ("region_supra:Parsi",       "renamed", "community code"),
    "Sindhi (community)":    ("region_supra:Sindhi",      "renamed", "community code"),
    "Mughlai (North India)": ("region_supra:North_India", "folded",
                              "culinary lineage, not a geography (CLAUDE.md 6.2)"),
}


def safe(x: str) -> str:
    return "_".join(str(x).split())


def main() -> int:
    ents = []
    with open(os.path.join(SI, "entity_list.txt"), encoding="utf-8") as fh:
        next(fh)
        for line in fh:
            parts = line.split()
            if parts:
                ents.append(parts[0])
    kg_regions = {e for e in ents if e.startswith(("region:", "region_supra:"))}
    print(f"KG region entities: {len(kg_regions)}  "
          f"(primary {sum(1 for e in kg_regions if e.startswith('region:'))}, "
          f"supra {sum(1 for e in kg_regions if e.startswith('region_supra:'))})")

    users = Counter()
    with open(os.path.join(SI, "users.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            users[r.get("home_region", "")] += 1
    print(f"user home_region codes: {len(users)}   users: {sum(users.values()):,}")

    rows, unresolved_users = [], 0
    for code, n in sorted(users.items(), key=lambda kv: -kv[1]):
        if code in MANUAL:
            ent, kind, note = MANUAL[code]
            if ent not in kg_regions:
                ent, kind, note = "", "unreachable", note + "; target absent from the KG"
        else:
            prim = f"region:{safe(code)}"
            supra = f"region_supra:{safe(code)}"
            if prim in kg_regions:
                ent, kind, note = prim, "exact", "primary 14-region axis"
            elif supra in kg_regions:
                ent, kind, note = supra, "exact", "supra-regional / community bucket"
            else:
                ent, kind, note = "", "unreachable", "below --min_per_region; no KG entity"
        if not ent:
            unresolved_users += n
        rows.append({"user_home_region": code, "n_users": n, "kg_entity": ent,
                     "match": kind, "in_primary_axis": str(code in AXIS_14).lower(),
                     "note": note})

    out = os.path.join(SI, "region_crosswalk.csv")
    with open(out, "w", encoding="utf-8", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=["user_home_region", "n_users", "kg_entity",
                                            "match", "in_primary_axis", "note"])
        wr.writeheader()
        wr.writerows(rows)

    kinds = Counter(r["match"] for r in rows)
    print(f"\n{'match':<14}{'codes':>7}")
    for k, v in kinds.most_common():
        print(f"  {k:<12}{v:>7}")
    print(f"\nunreachable codes: {kinds['unreachable']}   "
          f"users affected: {unresolved_users:,} ({100*unresolved_users/sum(users.values()):.2f}%)")
    for r in rows:
        if r["match"] != "exact":
            print(f"  {r['user_home_region']:<24} -> {r['kg_entity'] or '(none)':<28} "
                  f"{r['match']:<12} {r['n_users']:>6,} users")

    meta = {"user_codes": len(users), "kg_region_entities": len(kg_regions),
            "matches": dict(kinds), "users_unreachable": unresolved_users,
            "note": "users.csv deliberately NOT remapped: interactions.csv, train.txt and "
                    "test.txt were built against its id space and gen.py cannot be re-run."}
    json.dump(meta, open(os.path.join(SI, "region_crosswalk_meta.json"), "w",
                         encoding="utf-8"), indent=2)
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
