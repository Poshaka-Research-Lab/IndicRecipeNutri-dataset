#!/usr/bin/env python3
r"""Generate `data/interactions/` — the single synthetic interaction benchmark.

Supersedes `data/synthetic_interactions/` (v1) and `data/synthetic_interactions_v3/` (v3),
which were two independent simulations that could not be merged: their remapped ID spaces
collide (user 0 rated recipe 4489 in v1 and recipe 121171 in v3; only 2 of ~16,000 item
entries agree), so concatenating them would invent users who rated across two catalogues and
would destroy both the 10-core property and the zero-leakage guarantee. One coherent set can
only come from regeneration, which is what this script is.

WHAT CHANGED FROM `gen.py`, and why each change is a fix rather than a preference.

1. SOURCE IS THE PUBLISHED CORPUS, NOT A RETRIEVAL-SIDE CSV.
   gen.py read `retrieval/recipe_attrs.csv` on another machine. That table predates the
   withdrawals and still carries 801 rows that left the corpus, which is why v1 and v3 had
   to be PINNED at 385/385/20,161 and 12/12/1,087 withdrawn references. Reading
   `data/corpus/recipes_structured.parquet` makes "zero withdrawn references" true by
   construction rather than by audit, and the assertion at the end enforces it.

2. THE GLYCEMIC TERM WAS DEAD IN BOTH PUBLISHED GENERATIONS — IT READ THE WRONG COLUMN.
   gen.py mapped `GlycemicLoad` through {'low':1.0,'medium':0.5,'high':0.0}. Measured
   2026-09-12: that column is ~98.6% NUMERIC in both recipe_attrs.csv (v1's source) and
   recipe_attrs_v15.csv (v3's), and holds not one 'low'/'medium'/'high' value. So `.map()`
   returned NaN for every row, `.fillna(0.5)` made gl_score a CONSTANT, and the `diabetic`
   profile (15% of users) silently reduced to HealthGrade alone. The published datasheet's
   "diabetic→low glycemic/grade A-B" describes a term that never operated in either release.
   The categorical column it wanted was sitting directly beside it, named `gl_bucket`.
   FIX: map `gl_bucket`, which IS published (labels.parquet and recipes_structured.parquet)
   and is 98.62% exactly low/medium/high. Its bands are the corpus's own and coincide with
   the conventional dietetic ones — measured boundaries low 0–10, medium 10–20, high
   20–232.11 — so this restores gen.py's intended semantics rather than substituting a
   threshold of my own. The remaining 1.38% carry no bucket and sit at the neutral midpoint,
   which is honest at 1.38% of rows where it was not at 100%. The guard below fails the
   build if the mapping ever silently stops matching again.

3. DIET NORMALISATION FAILED OPEN ON A HARD CONSTRAINT.
   gen.py's norm_diet() returns 'Vegetarian' for anything it does not recognise. The corpus
   carries 731 recipes with Diet == 'unknown', so those entered the Vegan, Vegetarian and
   Eggetarian candidate pools. Worse, the stats audit re-used norm_diet(), so
   `diet_violation_vegan_on_nonvegan` reported 0 while it was happening — a green check over
   the exact rows it should have caught. Dietary law is a hard constraint (CLAUDE.md 4.3).
   FIX: an undeclared diet is its own class and is excluded from EVERY pool, and the audit
   below reads the RAW published Diet column so it can actually fail.

4. THE ZONE MAP WAS KEYED TO A VOCABULARY THE CORPUS NO LONGER USES.
   gen.py's zone sets name 'Sindhi (community)', 'Parsi (community)' and
   'Mughlai (North India)'. The published corpus uses 'Sindhi' and 'Parsi' and contains no
   'Mughlai (North India)' at all, so those codes fell through to zone 'O' and lost their
   regional affinity silently. The sets below are built against the 27 codes actually
   present.

5. IDS ARE REAL `recipe_id`s, NOT POSITIONAL INDICES.
   gen.py selected candidates as positional indices into the dataframe and wrote them into a
   column named `recipe_id`. Everything downstream — item_list.txt, entity_list.txt and the
   static-id gate — then reads that column as though it held corpus recipe ids. This script
   maps position -> recipe_id explicitly before anything is written.

6. PATHS AND SEED ARE ARGUMENTS.
   gen.py hardcoded '/tmp/bench/synth50' and '/mnt/user-data/uploads/...', which is the
   stated reason the pins were never retired (verify_release.py:487). Nothing here is
   machine-specific.

Usage:
    python scripts/build_interactions.py --out data/interactions
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from release_config import REPO_ROOT, all_withdrawn_ids  # noqa: E402

# The four declared diet classes. Anything else is undeclared and is not servable to a
# user with a dietary restriction.
DECLARED = ("Vegetarian", "Vegan", "Non-Vegetarian", "Eggetarian")
UNDECLARED = "undeclared"

# Zones over the 27 Region codes the PUBLISHED corpus actually uses.
SOUTH = {"Tamil Nadu", "Kerala", "Karnataka", "Andhra Pradesh", "Telangana", "South India"}
NORTH = {"Punjab", "North India", "Rajasthan", "Uttar Pradesh", "Jammu & Kashmir",
         "Himachal Pradesh", "Uttarakhand"}
EAST = {"West Bengal", "Bihar", "Odisha", "Assam", "East India", "Nagaland", "Manipur"}
WEST = {"Maharashtra", "Gujarat", "Goa", "Sindhi", "Parsi", "West India"}

NEEDED = ["recipe_id", "Diet", "Region", "HealthGrade", "gl_bucket", "GlycemicLoad_numeric",
          "Nut_Sodium", "Nut_SaturatedFat", "Nut_Calories", "RatingCount",
          "SpiceLevel", "Course"]


def norm_diet(value: object) -> str:
    """Fail CLOSED: only an explicit, recognised declaration yields a restricted class."""
    if not isinstance(value, str):
        return UNDECLARED
    t = value.strip().lower()
    if t in ("non-vegetarian", "non vegetarian", "nonvegetarian"):
        return "Non-Vegetarian"
    if t == "vegan":
        return "Vegan"
    if t == "eggetarian":
        return "Eggetarian"
    if t == "vegetarian":
        return "Vegetarian"
    return UNDECLARED


def zone_of(region: str) -> str:
    if region in SOUTH:
        return "S"
    if region in NORTH:
        return "N"
    if region in EAST:
        return "E"
    if region in WEST:
        return "W"
    return "O"


def pctl(series: pd.Series) -> np.ndarray:
    """Within-corpus percentile rank; missing values sit at the midpoint."""
    return pd.to_numeric(series, errors="coerce").rank(pct=True).fillna(0.5).values


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", type=Path,
                    default=REPO_ROOT / "data" / "corpus" / "recipes_structured.parquet")
    ap.add_argument("--out", type=Path, default=REPO_ROOT / "data" / "interactions")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--users", type=int, default=50_000)
    ap.add_argument("--hotc", type=int, default=18_000)
    ap.add_argument("--zipf-exp", type=float, default=0.35)
    ap.add_argument("--gamma-exp", type=float, default=0.6)
    args = ap.parse_args()

    np.random.seed(args.seed)
    args.out.mkdir(parents=True, exist_ok=True)

    print(f"reading {args.corpus}")
    df = pd.read_parquet(args.corpus, columns=NEEDED).reset_index(drop=True)
    n_recipes = len(df)
    print(f"recipes: {n_recipes:,}")

    # ---- position -> real recipe_id, established once and used for every emitted id
    recipe_id = df["recipe_id"].astype("int64").values
    if len(set(recipe_id)) != n_recipes:
        raise SystemExit("corpus recipe_id is not unique; refusing to build")

    # ---- diet, fail-closed
    diet_arr = np.array([norm_diet(v) for v in df["Diet"].values])
    undeclared_n = int((diet_arr == UNDECLARED).sum())
    print(f"diet classes: " + ", ".join(
        f"{k}={int((diet_arr == k).sum()):,}" for k in DECLARED))
    print(f"undeclared (excluded from every pool): {undeclared_n:,}")

    region = df["Region"].fillna("Pan-Indian").astype(str).values
    zone_arr = np.array([zone_of(r) for r in region])
    unzoned = sorted({r for r, z in zip(region, zone_arr) if z == "O"} - {"Pan-Indian"})
    if unzoned:
        print(f"NOTE region codes with no zone: {unzoned}")

    # ---- static feature arrays
    grade_num = df["HealthGrade"].map({"A": 5, "B": 4, "C": 3, "D": 2, "E": 1})
    grade_score = ((pd.to_numeric(grade_num, errors="coerce").fillna(3) - 1) / 4.0).values

    # FIX 2: map the CATEGORICAL bucket gen.py meant to read. Low glycemic load scores high.
    gl_mapped_series = (df["gl_bucket"].astype(str).str.strip().str.lower()
                        .map({"low": 1.0, "medium": 0.5, "high": 0.0}))
    gl_mapped = int(gl_mapped_series.notna().sum())
    gl_score = gl_mapped_series.fillna(0.5).values
    print(f"glycemic buckets mapped: {gl_mapped:,}/{n_recipes:,} "
          f"({gl_mapped / n_recipes * 100:.2f}%)  — gen.py mapped 0.00% of them")
    if gl_mapped < n_recipes * 0.5:
        raise SystemExit(
            "gl_bucket mapped under half the corpus, so the glycemic term is effectively "
            "constant again — the exact defect this build exists to fix. Refusing to build.")
    sodium_p = pctl(df["Nut_Sodium"])
    satfat_p = pctl(df["Nut_SaturatedFat"])
    cal_p = pctl(df["Nut_Calories"])

    rc = pd.to_numeric(df["RatingCount"], errors="coerce").fillna(0).values
    pop = np.log1p(rc)
    pop = pop / pop.max() if pop.max() > 0 else pop

    rank = np.random.permutation(n_recipes)
    base = 1.0 / np.power(rank + 1.0, args.zipf_exp)
    q = base * (1.0 + 2.0 * pop)
    q = np.where(rank < args.hotc, q, q * 5e-4)
    q = np.maximum(q, 1e-12)
    logq = np.log(q)

    spice = df["SpiceLevel"].values
    spice_r = np.array([{"mild": 0, "medium": 1, "hot": 2}.get(s, -1) for s in spice])
    course = df["Course"].fillna("Unknown").astype(str).values
    grade_letter = df["HealthGrade"].fillna("NA").astype(str).values
    spice_letter = df["SpiceLevel"].fillna("NA").astype(str).values

    # ---- candidate pools. FIX 3: undeclared is in NO pool.
    is_declared = diet_arr != UNDECLARED
    pool_mask = {
        "Vegan": diet_arr == "Vegan",
        "Vegetarian": np.isin(diet_arr, ["Vegetarian", "Vegan", "Eggetarian"]),
        "Eggetarian": np.isin(diet_arr, ["Vegetarian", "Vegan", "Eggetarian"]),
        "Non-Vegetarian": is_declared,
    }
    pool_idx = {k: np.where(v)[0] for k, v in pool_mask.items()}
    for k, v in pool_idx.items():
        print(f"  pool {k:<16} {len(v):>8,}")
    pool_q = {k: (q[i] / q[i].sum()) for k, i in pool_idx.items()}

    region_to_idx: dict[str, list[int]] = {}
    for i, r in enumerate(region):
        region_to_idx.setdefault(r, []).append(i)
    region_to_idx = {k: np.array(v) for k, v in region_to_idx.items()}

    # ---- users
    nu = args.users
    present = list(region_to_idx.keys())
    counts = {r: len(region_to_idx[r]) for r in present}
    non_pan = [r for r in present if r != "Pan-Indian"]
    sq = np.array([np.sqrt(counts[r]) for r in non_pan])
    sq = sq / sq.sum() * 0.75
    home_regions = ["Pan-Indian"] + non_pan
    home_p = np.array([0.25] + list(sq))
    home_p = home_p / home_p.sum()
    home_region = np.random.choice(home_regions, size=nu, p=home_p)
    for ri, r in enumerate(present):
        if not (home_region == r).any():
            home_region[ri] = r

    diet_u = np.random.choice(list(DECLARED), nu, p=[0.40, 0.15, 0.35, 0.10])
    health_u = np.random.choice(["general", "diabetic", "heart_lowsodium", "weight_loss"],
                                nu, p=[0.60, 0.15, 0.15, 0.10])
    spice_u = np.random.choice(["mild", "medium", "hot"], nu, p=[0.20, 0.45, 0.35])
    age_u = np.random.choice(["18-25", "26-35", "36-50", "51+"], nu, p=[0.25, 0.35, 0.25, 0.15])

    sigma = 0.75

    def sample_counts(mu: float, seed: int) -> np.ndarray:
        rs = np.random.RandomState(seed)
        x = rs.lognormal(mean=mu, sigma=sigma, size=nu)
        return np.clip(np.round(x), 5, 200).astype(int)

    mu = 2.55
    for _ in range(40):
        m = sample_counts(mu, 1).mean()
        if abs(m - 20) < 0.15:
            break
        mu += (20 - m) * 0.03
    n_inter = sample_counts(mu, 99)
    print(f"mu {mu:.3f}  mean interactions/user {n_inter.mean():.2f}  total {n_inter.sum():,}")

    users = pd.DataFrame({
        "user_id": np.arange(nu), "home_region": home_region, "diet": diet_u,
        "health_profile": health_u, "spice_pref": spice_u, "age_band": age_u,
        "n_interactions": n_inter,
    })
    users.to_csv(args.out / "users.csv", index=False)

    # ---- interactions
    w_region, w_health, w_spice, w_pop, temp = 0.35, 0.20, 0.15, 0.10, 0.3
    sp_rank_u = {"mild": 0, "medium": 1, "hot": 2}
    date_start = datetime(2016, 1, 1)
    span = (datetime(2026, 6, 30) - date_start).days
    raw_t = np.array([1, 2, 4, 16, 72], float)
    norm_t = raw_t / raw_t.sum()

    rows_u, rows_i, rows_r, rows_d = [], [], [], []
    rng = np.random.RandomState(2024)

    for u in range(nu):
        dclass = diet_u[u]
        base_pool = pool_idx[dclass]
        hr = home_region[u]
        n = int(n_inter[u])
        parts = []
        rmatch = region_to_idx.get(hr)
        if rmatch is not None:
            rm = rmatch[pool_mask[dclass][rmatch]]
            if len(rm) > 400:
                rw = q[rm] / q[rm].sum()
                rm = rng.choice(rm, 400, replace=True, p=rw)
            if len(rm):
                parts.append(rm)
        parts.append(rng.choice(base_pool, max(2500, n * 15), replace=True, p=pool_q[dclass]))
        cand = np.unique(np.concatenate(parts))
        n = min(n, len(cand))

        rreg = region[cand]
        rz = zone_arr[cand]
        uz = zone_of(hr)
        region_score = np.where(rreg == hr, 1.0,
                        np.where(rreg == "Pan-Indian", 0.5,
                        np.where((rz == uz) & (uz != "O"), 0.5, 0.1)))
        hp = health_u[u]
        if hp == "diabetic":
            health = 0.5 * gl_score[cand] + 0.5 * grade_score[cand]
        elif hp == "heart_lowsodium":
            health = 0.4 * (1 - sodium_p[cand]) + 0.3 * (1 - satfat_p[cand]) + 0.3 * grade_score[cand]
        elif hp == "weight_loss":
            health = 0.7 * (1 - cal_p[cand]) + 0.3 * grade_score[cand]
        else:
            health = grade_score[cand]
        ur = sp_rank_u[spice_u[u]]
        sr = spice_r[cand]
        spice_match = np.where(sr < 0, 0.3,
                       np.where(sr == ur, 1.0,
                       np.where(np.abs(sr - ur) == 1, 0.5, 0.3)))
        aff = (w_region * region_score + w_health * health + w_spice * spice_match
               + w_pop * pop[cand] + rng.normal(0, 0.15, len(cand)))
        z = aff / temp + args.gamma_exp * logq[cand]
        z -= z.max()
        p = np.exp(z)
        p /= p.sum()
        chosen = rng.choice(len(cand), size=n, replace=False, p=p) if n < len(cand) \
            else np.arange(len(cand))
        ch_idx = cand[chosen]
        ch_aff = aff[chosen]

        order = np.argsort(-ch_aff)
        m = len(order)
        ratings = np.empty(m, int)
        cuts = [(int(round(norm_t[4] * m)), 5), (int(round(norm_t[3] * m)), 4),
                (int(round(norm_t[2] * m)), 3), (int(round(norm_t[1] * m)), 2)]
        pos_ = 0
        for cnt, val in cuts:
            ratings[order[pos_:pos_ + cnt]] = val
            pos_ += cnt
        ratings[order[pos_:]] = 1

        days = rng.randint(0, span + 1, m)
        dstr = np.array([(date_start + timedelta(days=int(d))).strftime("%Y-%m-%d") for d in days])
        o2 = np.argsort(days)
        rows_u.append(np.full(m, u))
        rows_i.append(ch_idx[o2])          # positional; mapped to recipe_id below
        rows_r.append(ratings[o2])
        rows_d.append(dstr[o2])
        if (u + 1) % 10_000 == 0:
            print(f"  {u + 1:,}/{nu:,} users")

    pos_idx = np.concatenate(rows_i)
    inter = pd.DataFrame({
        "user_id": np.concatenate(rows_u),
        "recipe_id": recipe_id[pos_idx],   # FIX 5: real corpus ids
        "rating": np.concatenate(rows_r),
        "date": np.concatenate(rows_d),
    })
    inter.to_csv(args.out / "interactions.csv", index=False)
    print(f"interactions: {len(inter):,}")

    # ---- 10-core over positives, then a per-user temporal 80/20 split
    keep = pd.DataFrame({"user_id": inter.user_id.values, "recipe_id": inter.recipe_id.values,
                         "date": inter.date.values})[inter.rating.values >= 4]
    core = 10
    while True:
        uc = keep.user_id.value_counts()
        ic = keep.recipe_id.value_counts()
        before = len(keep)
        keep = keep[keep.user_id.isin(uc[uc >= core].index)
                    & keep.recipe_id.isin(ic[ic >= core].index)]
        if len(keep) == before:
            break
    print(f"post-10core: {len(keep):,} positives, {keep.user_id.nunique():,} users, "
          f"{keep.recipe_id.nunique():,} items")

    keep = keep.sort_values(["user_id", "date"]).reset_index(drop=True)
    test_rows: list[int] = []
    for _, g in keep.groupby("user_id", sort=False):
        idx = g.index.values
        ntest = min(max(1, int(round(len(idx) * 0.2))), len(idx) - 1)
        test_rows.extend(idx[-ntest:])
    mask = np.ones(len(keep), bool)
    mask[test_rows] = False
    train, test = keep[mask], keep[~mask]
    print(f"train {len(train):,}  test {len(test):,}")

    u_ids = sorted(keep.user_id.unique())
    i_ids = sorted(keep.recipe_id.unique())
    u_remap = {o: i for i, o in enumerate(u_ids)}
    i_remap = {o: i for i, o in enumerate(i_ids)}

    def write_map(name: str, ids: list, remap: dict) -> None:
        with (args.out / name).open("w", encoding="utf-8", newline="\n") as fh:
            fh.write("org_id remap_id\n")
            for o in ids:
                fh.write(f"{o} {remap[o]}\n")

    write_map("user_list.txt", u_ids, u_remap)
    write_map("item_list.txt", i_ids, i_remap)

    def write_ui(name: str, frame: pd.DataFrame) -> dict:
        d: dict[int, list[int]] = {}
        for uid, iid in zip(frame.user_id.values, frame.recipe_id.values):
            d.setdefault(u_remap[uid], []).append(i_remap[iid])
        with (args.out / name).open("w", encoding="utf-8", newline="\n") as fh:
            for uid in sorted(d):
                fh.write(str(uid) + " " + " ".join(map(str, d[uid])) + "\n")
        return d

    train_d = write_ui("train.txt", train)
    test_d = write_ui("test.txt", test)
    leak = sum(len(set(v) & set(train_d.get(k, ()))) for k, v in test_d.items())
    print(f"train/test leakage: {leak}")

    # ---- attribute KG
    relations = [("has_region", 0), ("has_diet", 1), ("has_course", 2),
                 ("has_healthgrade", 3), ("has_spice", 4)]
    with (args.out / "relation_list.txt").open("w", encoding="utf-8", newline="\n") as fh:
        fh.write("org_id remap_id\n")
        for name, rid in relations:
            fh.write(f"{name} {rid}\n")

    pos_of = {int(r): i for i, r in enumerate(recipe_id)}
    ent_org = [f"item:{o}" for o in i_ids]
    attr_node: dict[str, int] = {}
    next_id = len(i_ids)

    def node(val: str) -> int:
        nonlocal next_id
        if val not in attr_node:
            attr_node[val] = next_id
            ent_org.append(val)
            next_id += 1
        return attr_node[val]

    triples = []
    for o in i_ids:
        i = pos_of[int(o)]
        h = i_remap[o]
        triples.append((h, 0, node(f"region:{region[i]}")))
        triples.append((h, 1, node(f"diet:{diet_arr[i]}")))
        if course[i] != "Unknown":
            triples.append((h, 2, node(f"course:{course[i]}")))
        if grade_letter[i] != "NA":
            triples.append((h, 3, node(f"grade:{grade_letter[i]}")))
        if spice_letter[i] != "NA":
            triples.append((h, 4, node(f"spice:{spice_letter[i]}")))

    with (args.out / "entity_list.txt").open("w", encoding="utf-8", newline="\n") as fh:
        fh.write("org_id remap_id\n")
        for i, name in enumerate(ent_org):
            fh.write(f"{name} {i}\n")
    with (args.out / "kg_final.txt").open("w", encoding="utf-8", newline="\n") as fh:
        for h, r, t in triples:
            fh.write(f"{h} {r} {t}\n")
    print(f"kg: {len(triples):,} triples over {len(ent_org):,} entities")

    # ---- audits. FIX 3: read the RAW Diet column, never norm_diet, so this can fail.
    raw_diet = pd.Series(df["Diet"].astype(str).values, index=recipe_id)
    merged = inter.merge(users[["user_id", "diet"]], on="user_id")
    merged["rdiet"] = raw_diet.loc[merged.recipe_id.values].values
    vegan_bad = int(((merged.diet == "Vegan") & (merged.rdiet != "Vegan")).sum())
    veg_bad = int((merged.diet.isin(["Vegetarian", "Eggetarian"])
                   & (merged.rdiet == "Non-Vegetarian")).sum())
    undeclared_served = int((~merged.rdiet.isin(DECLARED)).sum())

    withdrawn = set(all_withdrawn_ids())
    wd_inter = int(inter.recipe_id.isin(withdrawn).sum())
    wd_items = len(set(i_ids) & withdrawn)
    print(f"\naudit  vegan-on-non-vegan {vegan_bad}   veg-on-non-veg {veg_bad}   "
          f"undeclared served {undeclared_served}")
    print(f"audit  withdrawn recipes referenced: {wd_items} items / {wd_inter} rows")

    for label, value in (("vegan_on_nonvegan", vegan_bad), ("veg_on_nonveg", veg_bad),
                         ("undeclared_served", undeclared_served),
                         ("withdrawn_items", wd_items), ("withdrawn_rows", wd_inter)):
        if value:
            raise SystemExit(f"REFUSING TO PUBLISH: {label} = {value}, expected 0")

    counts_per_user = inter.user_id.value_counts()
    ach = inter.rating.value_counts(normalize=True).sort_index()
    stats = {
        "version": "v4",
        "generator": "scripts/build_interactions.py",
        "seed": args.seed,
        "source": str(args.corpus.relative_to(REPO_ROOT)).replace("\\", "/"),
        "source_recipes": int(n_recipes),
        "hotc": args.hotc, "zipf_exp": args.zipf_exp, "gamma_exp": args.gamma_exp,
        "n_users": int(nu),
        "n_items_total_rated": int(inter.recipe_id.nunique()),
        "n_interactions_total": int(len(inter)),
        "n_positives_pre_10core": int((inter.rating >= 4).sum()),
        "n_positives_post_10core": int(len(keep)),
        "n_users_post_10core": int(keep.user_id.nunique()),
        "n_items_post_10core": int(len(i_ids)),
        "n_train": int(len(train)), "n_test": int(len(test)),
        "rating_hist_achieved": {int(k): round(float(v), 4) for k, v in ach.items()},
        "rating_hist_target_normalized": {i + 1: round(float(norm_t[i]), 4) for i in range(5)},
        "per_user_count_percentiles": {str(p): float(np.percentile(counts_per_user.values, p))
                                       for p in (1, 5, 25, 50, 75, 90, 95, 99)},
        "per_user_count_mean": round(float(counts_per_user.mean()), 3),
        "region_coverage_users": {k: int(v) for k, v in users.home_region.value_counts().items()},
        "n_regions_with_recipes": len(present),
        "n_regions_covered_by_users": int(users.home_region.nunique()),
        "diet_split_users": {k: float(v) for k, v in users.diet.value_counts(normalize=True).round(4).items()},
        "recipes_with_undeclared_diet_excluded": undeclared_n,
        "n_kg_triples": len(triples), "n_kg_entities": len(ent_org), "n_kg_relations": 5,
        "train_test_leakage": int(leak),
        "diet_violation_vegan_on_nonvegan": vegan_bad,
        "diet_violation_veg_on_nonveg": veg_bad,
        "diet_undeclared_served": undeclared_served,
        "withdrawn_recipe_items": wd_items,
        "withdrawn_recipe_interaction_rows": wd_inter,
        "recipe_id_space": "corpus recipe_id (not positional index)",
        "glycemic_term": "gl_bucket low/medium/high mapped to 1.0/0.5/0.0",
        "glycemic_buckets_mapped": gl_mapped,
    }
    (args.out / "stats.json").write_text(json.dumps(stats, indent=2) + "\n",
                                         encoding="utf-8", newline="\n")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
