#!/usr/bin/env python3
r"""ST1 / S-1 - split the 243-column monolith into six narrow tables plus a long history.

THE PROBLEM THIS SOLVES
-----------------------
Measured 2026-08-30 on the master: only **44 of 208 columns were content**. 36 were shadow
backups (`_orig`, `_uncorrected`, `_predensity`), 28 were boolean "we did a fix" markers,
and **58 of those 64 shipped to consumers**. Eight of the booleans were allergen build steps
alone, and nothing in the schema said which was current.

The schema was growing with the number of mistakes we had corrected. The 27 open items,
fixed the old way, would have taken it to roughly 278 columns with content still at 44 -
this session alone added 11 before the migration.

The audit trail is worth keeping: the three per-100g generations genuinely differ (current
vs `_predensity` on 195,731 rows). **It is not worth keeping as columns in the table a
consumer reads.** So it moves to rows.

THE SHAPE
---------
    corpus/recipes.parquet             identity, text, timing, source
    corpus/nutrition.parquet           the 34 `Nut_*` as supplied
    corpus/nutrition_derived.parquet   per100g_*, fsa_*, DV_*, glycemic, and their basis
    corpus/labels.parquet              Diet, Region, Cuisine, Course, Spice, Occasion,
                                       HealthGrade - each beside its `*_src` provenance
    corpus/allergens.parquet           LONG: one row per (recipe, allergen), so `unknown`
                                       is a first-class value rather than a sentinel string
    corpus/quality.parquet             badlist_*, has_*, contradiction and family flags
    provenance/field_history.parquet   LONG: recipe_id, field, generation, value
    provenance/builds.json             build_id -> date, script, row count

Every table is keyed on `recipe_id`. A fix from here on adds ROWS to `field_history`, not
columns to anything.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.environ.get("DATASETS_ROOT", r"D:\datasets"))
import paths as _paths  # noqa: E402
import allergen_taxonomy as _AT  # noqa: E402

_paths.bootstrap()
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd  # noqa: E402

OUT = r"D:\datasets\IndicRecipeNutri-dataset\data"

ID = "recipe_id"

RECIPES = ["recipe_id", "RecipeName", "Title_normalized", "URL", "SourceSite", "Lang",
           "Lang_base", "Servings", "Servings_num", "PrepTimeMins", "CookTimeMins",
           "TotalTimeMins", "StepCount", "Difficulty", "RatingAverage", "RatingCount",
           "IngredientsList", "Ingredients", "Description_Source", "Ingredients_Source",
           "source_licence", "source_terms_url", "Split_v2", "Split_v1_leaky"]

LABELS = ["recipe_id", "Diet", "Diet_prior", "Region", "region_src", "region_normalised",
          "Cuisine", "cuisine_scope", "out_of_scope", "Course", "SpiceLevel",
          "SpiceLevel_src", "Occasion", "DietaryContext", "CookingMethod", "HealthGrade",
          "HealthConditions", "gl_bucket", "GlycemicLoad_numeric", "diet_v13",
          "diet_meat_class"]

QUALITY = ["recipe_id", "has_instructions", "has_ingredients", "has_rating",
           "diet_contradicts_ingredients", "contains_pork", "contains_beef",
           "contains_poultry", "contains_fish", "contains_alcohol", "contains_gelatin",
           "sulphites_possible", "sulphites_possible_src", "nonveg_corrected",
           "mojibake_fixed", "qty_source", "ing_weight_confident_frac", "nut_indb_frac",
           "confident_coverage", "dup_family_id", "dup_family_size", "is_family_primary",
           "family_filled"]

SHADOW = re.compile(r"(_orig|_uncorrected|_predensity)$")
BUILD_FLAG = re.compile(
    r"^(allergens_(tn_fix|celery_fix|lexgap_fix|lexv9_fix|title_fix|title_src|rescan_v10|"
    r"sesame_v11|failclosed_broken|inferred|src|encoding_fixed|sa5_src))$"
    r"|^(atwater_fixed|region_corrected|region_inferred|energy_capped_v3|"
    r"SpiceLevel_inferred|nutrition_estimated|nutrition_est_method|gl_hg_inferred|"
    r"course_inferred|cuisine_inferred|cookingmethod_inferred|cookingmethod_normalised|"
    r"micros_estimated|occasion_inferred|dcx_inferred|allergens_filled|"
    r"diet_contradiction_recomputed_v9|per100g_density_corrected|per100g_v13|"
    r"allergens_lexgap_fix|Enrich_Log)$", re.I)

BUILD_ID = "v15-2026-09-01"



def _hist_frame(ids, field, generation, values):
    """One history row per changed field.

    Numeric history goes in `value_num`, text in `value_str`. Storing everything as text
    made a PII scanner read floats like `361.09404018234` as Indian phone numbers - 141
    false positives on the first run. Keeping the type is both more honest and quieter.
    """
    num = pd.to_numeric(values, errors="coerce")
    is_num = num.notna()
    return pd.DataFrame({ID: ids.values, "field": field, "generation": generation,
                         "value_num": num.where(is_num).values,
                         "value_str": values.where(~is_num).astype("string").values})


def main() -> int:
    print(f"reading {_paths.MASTER}", flush=True)
    df = pd.read_csv(_paths.MASTER, low_memory=False)

    # The master is the working copy; the RELEASE is a filtered view of it. Reading the
    # master directly skips that filter, and on the first run this shipped the withdrawn
    # PII row into three of the new tables. verify_release caught it. Apply the exclusions
    # here, at the boundary, rather than trusting that the master never contains one.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from release_config import (EXCLUDED_RECIPE_IDS, EXCLUDED_SOURCE_SITES,
                                PROSE_COLUMNS)
    before = len(df)
    if EXCLUDED_RECIPE_IDS:
        df = df[~df[ID].astype("int64", errors="ignore").isin(set(EXCLUDED_RECIPE_IDS))]
    if EXCLUDED_SOURCE_SITES and "SourceSite" in df.columns:
        df = df[~df["SourceSite"].isin(set(EXCLUDED_SOURCE_SITES))]
    df = df.reset_index(drop=True)
    print(f"release exclusions applied: {before - len(df)} row(s) withheld "
          f"({sorted(EXCLUDED_RECIPE_IDS)})")

    # The two-tier release model withholds the prose columns entirely - they are the
    # copyright-bearing text AND the place free-text PII hides. The first run of this
    # migration republished all four through the `leftover` catch-all, and verify_release
    # found emails in 26 Instructions rows and phone numbers in 18 more. A catch-all that
    # sweeps up unassigned columns must never be allowed to sweep up withheld ones.
    present_prose = [c for c in PROSE_COLUMNS if c in df.columns]
    if present_prose:
        df = df.drop(columns=present_prose)
        print(f"prose columns withheld ({len(present_prose)}): {present_prose}")
    n = len(df)
    cols = list(df.columns)
    print(f"rows {n:,}   columns {len(cols)}")

    def take(names):
        return [c for c in names if c in df.columns]

    nutrition = [ID] + [c for c in cols if c.startswith("Nut_") and not SHADOW.search(c)]
    derived = [ID] + [c for c in cols
                      if (c.startswith(("per100g_", "fsa_", "DV_"))
                          or c in ("grams_per_serving_v3", "serving_basis_v3",
                                   "atwater_relerr", "ProteinPct", "CarbPct", "FatPct"))
                      and not SHADOW.search(c)]

    assigned = set(take(RECIPES)) | set(nutrition) | set(derived) | set(take(LABELS)) \
        | set(take(QUALITY))
    shadow_cols = [c for c in cols if SHADOW.search(c)]
    flag_cols = [c for c in cols if BUILD_FLAG.search(c) and c not in assigned]
    allergen_cols = [c for c in cols if c.lower().startswith("allergens")]
    leftover = [c for c in cols
                if c not in assigned and c not in shadow_cols and c not in flag_cols
                and c not in allergen_cols]

    print(f"\n  recipes            {len(take(RECIPES)):>4}")
    print(f"  nutrition          {len(nutrition):>4}")
    print(f"  nutrition_derived  {len(derived):>4}")
    print(f"  labels             {len(take(LABELS)):>4}")
    print(f"  quality            {len(take(QUALITY)):>4}")
    print(f"  -> field_history   {len(shadow_cols) + len(flag_cols):>4}  "
          f"({len(shadow_cols)} shadow + {len(flag_cols)} build flags)")
    print(f"  allergens (long)   {len(allergen_cols):>4} source columns")
    if leftover:
        print(f"  unassigned         {len(leftover):>4}  -> appended to recipes: {leftover[:8]}"
              f"{' ...' if len(leftover) > 8 else ''}")

    os.makedirs(os.path.join(OUT, "corpus"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "provenance"), exist_ok=True)

    written = {}

    def write(name, columns, sub="corpus"):
        t = df[columns].copy()
        pth = os.path.join(OUT, sub, f"{name}.parquet")
        t.to_parquet(pth, index=False)
        written[name] = {"rows": len(t), "cols": len(t.columns),
                         "mb": round(os.path.getsize(pth) / 1e6, 1)}
        print(f"    wrote {name+'.parquet':<30}{len(t):>9,} x {len(t.columns):<4} "
              f"{written[name]['mb']:>6.1f} MB")

    print("\nwriting:")
    write("recipes", take(RECIPES) + leftover)
    write("nutrition", nutrition)
    write("nutrition_derived", derived)
    write("labels", take(LABELS))
    write("quality", take(QUALITY))

    # ── allergens, long ───────────────────────────────────────────────────
    # Imported, not restated. This list held 16 tokens while the master and the KG held
    # 17, which published a long table and a `has_*` block with no `ghee` in them at all --
    # a consumer filtering "no ghee" on the tables got nothing while the graph returned
    # 33,538 recipes. It is the writer of BOTH tabular allergen surfaces, so it was the
    # single most costly place for this list to be out of date.
    CLASSES = list(_AT.TOKENS)
    src = df["Allergens_v2"].fillna("").astype(str)
    rows = []
    for rid, blob in zip(df[ID], src):
        toks = {t.strip() for t in re.split(r"[;,]", blob) if t.strip()}
        if not toks or "unknown" in toks:
            # FIXED 2026-09-02. This emitted ONE row with a literal `*` as the allergen
            # name, which put a 17th member into a dimension the release declares as 16 and
            # made those 1,131 recipes vanish from every per-class filter: a query for
            # `allergen == 'peanut'` returned 219,056 recipes, not 220,187, with the missing
            # 1,131 being exactly the unassessed ones. Silently dropping the rows that are
            # NOT KNOWN to be safe is the fail-open direction Codex CXC 80-2020 forbids.
            # Sixteen explicit `unassessed` rows keep the table a true cross product and
            # make `unassessed` reachable per class, as this function's docstring intended.
            for c in CLASSES:
                rows.append((rid, c, "unassessed"))
            continue
        if toks == {"none_detected"}:
            for c in CLASSES:
                rows.append((rid, c, "absent"))
            continue
        for c in CLASSES:
            rows.append((rid, c, "present" if c in toks else "absent"))
    al = pd.DataFrame(rows, columns=[ID, "allergen", "status"])
    pth = os.path.join(OUT, "corpus", "allergens.parquet")
    al.to_parquet(pth, index=False)
    written["allergens"] = {"rows": len(al), "cols": 3,
                            "mb": round(os.path.getsize(pth) / 1e6, 1)}
    print(f"    wrote {'allergens.parquet':<30}{len(al):>9,} x 3    "
          f"{written['allergens']['mb']:>6.1f} MB   (long form)")
    print(f"      status: {al['status'].value_counts().to_dict()}")

    # ── field history, long ───────────────────────────────────────────────
    hist = []
    for c in shadow_cols:
        m = SHADOW.search(c)
        gen = m.group(1).lstrip("_")
        field = c[: m.start()]
        s = df[c]
        keep = s.notna() & (s.astype(str).str.strip() != "")
        if not keep.any():
            continue
        hist.append(_hist_frame(df.loc[keep, ID], field, gen, s[keep]))
    for c in flag_cols:
        s = df[c]
        keep = s.notna() & ~s.astype(str).str.lower().isin(["false", "0", "", "nan", "none"])
        if not keep.any():
            continue
        hist.append(_hist_frame(df.loc[keep, ID], c, "build_flag", s[keep]))
    fh = pd.concat(hist, ignore_index=True) if hist else pd.DataFrame(
        columns=[ID, "field", "generation", "value_num", "value_str"])
    fh["build_id"] = BUILD_ID
    pth = os.path.join(OUT, "provenance", "field_history.parquet")
    fh.to_parquet(pth, index=False)
    written["field_history"] = {"rows": len(fh), "cols": 5,
                                "mb": round(os.path.getsize(pth) / 1e6, 1)}
    print(f"    wrote {'field_history.parquet':<30}{len(fh):>9,} x 5    "
          f"{written['field_history']['mb']:>6.1f} MB   (long form)")
    print(f"      {fh['field'].nunique()} distinct fields, generations: "
          f"{fh['generation'].value_counts().to_dict()}")

    # ── gate: every id resolves ───────────────────────────────────────────
    print("\nGATE: referential integrity")
    base = set(df[ID].astype(str))
    ok = True
    for name in ("recipes", "nutrition", "nutrition_derived", "labels", "quality"):
        t = pd.read_parquet(os.path.join(OUT, "corpus", f"{name}.parquet"), columns=[ID])
        d = set(t[ID].astype(str))
        same = (len(t) == n) and (d == base)
        print(f"  {name:<20}{len(t):>9,} rows   ids match: {same}")
        ok &= same
    for name, sub in (("allergens", "corpus"), ("field_history", "provenance")):
        t = pd.read_parquet(os.path.join(OUT, sub, f"{name}.parquet"), columns=[ID])
        orphan = set(t[ID].astype(str)) - base
        print(f"  {name:<20}{len(t):>9,} rows   orphans: {len(orphan)}")
        ok &= not orphan
    assert ok, "referential integrity failed"
    print("  PASS")

    json.dump({BUILD_ID: {"date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                          "script": "migrate_schema.py",
                          "rows": n, "source_columns": len(cols),
                          "tables": written,
                          "note": "S-1 split. 64 build-history columns moved to "
                                  "field_history rows. A future fix adds rows, not columns."}},
              open(os.path.join(OUT, "provenance", "builds.json"), "w", encoding="utf-8"),
              indent=2)

    tot = sum(v["cols"] for k, v in written.items() if k not in ("allergens", "field_history"))
    print(f"\n  {len(cols)} monolith columns -> {tot} across five keyed tables "
          f"+ 2 long tables")
    print(f"  build history: {len(shadow_cols) + len(flag_cols)} columns -> {len(fh):,} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
