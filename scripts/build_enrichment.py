"""Convert the enrichment companion tables to Parquet for the release.

Every table is checked against the licence guard before it is written: a column whose
stem matches a withheld prose column (so `Description`, but also `Description_fix`)
aborts the build. Two source tables are excluded outright for exactly that reason and
the exclusion is recorded rather than left silent.

Usage:  python scripts/build_enrichment.py [--source PATH] [--out PATH]
"""

from __future__ import annotations

import argparse
import hashlib
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

IFCT_COMPANIONS = ('recipe_ifct_fraction.parquet', 'ifct_source_profiles.json')
IFCT_SHARE_COLUMNS = ['recipe_id', 'ifct_food_occurrence_count',
    'ifct_energy_available_occurrence_count', 'ifct_computed_energy_kcal',
    'computed_ingredient_energy_kcal', 'energy_available_count', 'fraction_basis',
    'ifct_computed_energy_fraction']


def file_digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def sanitized_ifct_profiles(profiles):
    """Publish component evidence through explicit fields, never recipe/review prose."""
    assertion_fields = ['source_snapshot_sha256', 'source_food_code', 'table',
        'pdf_page_1_based', 'source_tagname', 'mean', 'standard_deviation',
        'value_status', 'unit', 'denominator', 'number_of_regions',
        'regions_are_not_specimen_count', 'extraction_verification', 'source_value_flag']
    component_fields = ['source_tagname', 'target_field', 'unit', 'denominator',
        'value', 'source_standard_deviation', 'status']
    allowed_targets = {'Nut_Protein', 'Nut_Fat', 'Nut_Fiber', 'Nut_Calories'}
    result = {}
    for code, profile in profiles.items():
        if code != profile['source_food_code']:
            raise ValueError('IFCT source profile key mismatch')
        components = profile['target_components']
        if len(components) != 4 or {c['target_field'] for c in components} != allowed_targets:
            raise ValueError('IFCT release requires exactly four compatible components')
        native = profile['native_source']
        item = {key: profile[key] for key in ['version', 'source_food_code',
            'source_manifest_sha256', 'energy_policy']}
        item['native_source'] = {key: native[key] for key in ['source_food_code',
            'source_food_name', 'preparation_basis', 'pdf_page_1_based', 'number_of_regions']}
        item['native_source']['components'] = [
            {key: part[key] for key in assertion_fields if key in part}
            for part in native['components']]
        item['target_components'] = []
        for part in components:
            clean = {key: part[key] for key in component_fields if key in part}
            if part.get('source_assertion') is not None:
                clean['source_assertion'] = {key: part['source_assertion'][key]
                    for key in assertion_fields if key in part['source_assertion']}
            conversion = part.get('conversion')
            clean['conversion'] = None if conversion is None else {
                key: conversion[key] for key in ['policy', 'formula',
                    'source_pdf_page_1_based', 'source_section'] if key in conversion}
            item['target_components'].append(clean)
        item['recipe_match_approved'] = False
        result[code] = item
    # Strict JSON rejects accidental non-finite values without converting unknowns to zero.
    json.dumps(result, allow_nan=False)
    return result


def export_ifct_companions(source, out):
    """Optional coherent IFCT source bundle; return manifest records for released files."""
    present = [(source / name).exists() for name in IFCT_COMPANIONS]
    if not any(present):
        if any((out / name).exists() for name in (*IFCT_COMPANIONS, 'nutrition_source_provenance.json')):
            raise ValueError('Stale IFCT release companions exist without upstream source')
        return []
    if not all(present):
        raise ValueError('IFCT source shares and source profiles must be supplied together')
    manifest_path = source / 'ingredients_nutrition_manifest.json'
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    paths = [source / name for name in IFCT_COMPANIONS] + [manifest_path]
    pins = {path.name: file_digest(path) for path in paths}
    if pins[manifest_path.name] != hashlib.sha256(manifest_bytes).hexdigest():
        raise ValueError('Nutrition source manifest changed during snapshot capture')
    for name in IFCT_COMPANIONS:
        if manifest.get('outputs', {}).get(name) != pins[name]:
            raise ValueError('IFCT companion is not bound by the nutrition manifest: ' + name)
    profiles = sanitized_ifct_profiles(json.loads((source / IFCT_COMPANIONS[1]).read_text(encoding='utf-8')))
    report = manifest.get('ifct', manifest)
    metadata = {key: report[key] for key in ['energy_policy', 'weight_policy',
        'source_manifest_sha256', 'review_registry_sha256', 'active_match_status',
        'human_labels', 'quantity_approvals'] if key in report}
    for key in ['retention_policy', 'retention_factors']:
        if key in manifest: metadata[key] = manifest[key]
    if not profiles or any(p['source_manifest_sha256'] != metadata.get('source_manifest_sha256') for p in profiles.values()):
        raise ValueError('IFCT source profiles and nutrition provenance disagree')
    metadata.update(version='released_ifct_source_provenance_v1', upstream_sha256=pins,
        scope='agent_reviewed_source_identity_partial_estimated_composition',
        fraction_basis='share_of_available_computed_ingredient_energy_not_complete_nutrient_coverage',
        compatible_components=['Nut_Protein', 'Nut_Fat', 'Nut_Fiber', 'Nut_Calories'],
        source_identity_fields=['fct_source', 'fct_food_id'], ifct_fct_idx_required=False)
    frame = pd.read_parquet(source / IFCT_COMPANIONS[0])
    if set(frame.columns) != set(IFCT_SHARE_COLUMNS) or frame.recipe_id.duplicated().any():
        raise ValueError('Unexpected IFCT recipe source-share schema or duplicate recipe')
    frame = frame[IFCT_SHARE_COLUMNS]
    before = len(frame)
    frame = frame[~frame.recipe_id.isin(DROP_IDS)].reset_index(drop=True)
    if pins != {path.name: file_digest(path) for path in paths}:
        raise ValueError('IFCT source companions changed during export')
    frame.to_parquet(out / IFCT_COMPANIONS[0], index=False, compression=PARQUET_COMPRESSION)
    for name, value in [('ifct_source_profiles.json', profiles), ('nutrition_source_provenance.json', metadata)]:
        (out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8', newline='\n')
    return [dict(table=IFCT_COMPANIONS[0], rows=len(frame), columns=len(frame.columns),
        rows_dropped_by_exclusion=before-len(frame)),
        *[dict(metadata=name, sha256=file_digest(out/name)) for name in
            ['ifct_source_profiles.json', 'nutrition_source_provenance.json']]]


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
    # Found by gate M33 again, 2026-09-20 (v0.10.0), and the same defect class as the two above:
    # published False where the master says True, on ONE row. Recipe 160540 is one of the four
    # recipes re-sourced from their own page; the owner took its LABELS into v0.10.0 (decision of
    # 19 Sep, "labels now, text in v0.10.1"), so the master says `nonveg_corrected=True` for what
    # is now "Indian Whitefish and Rice". The enrichment refresh could not carry that across: it is
    # scoped to the 58 corrected recipes and 160540 is not one of them, and `fix11_nonveg.csv` has
    # no writer to regenerate it. Declaring the column master-authoritative is the mechanism this
    # file already uses for exactly this: the builder refreshes it from the master on every
    # rebuild, so it cannot drift again when the v0.10.1 text lands.
    "fix11_nonveg.csv": ["nonveg_corrected"],
}

_MASTER_CACHE: dict = {}

#: Columns that carry a REVIEWED APPLICATION rather than a measurement, per table. A row on a
#: superseded occurrence key that has one of these non-empty is a food-composition or flavour
#: claim bound to an ingredient list that changed.
APPLICATION_COLUMNS = {
    "ingredients_nutrition.parquet": ("ifct_food_review_id", "ifct_food_review_status",
                                      "ifct_source_food_basis"),
}


def occurrence_gate_refusals(name: str, df: "pd.DataFrame"):
    """Refuse to publish a table still carrying an application on a superseded occurrence key.

    Returns a refusal message, or `None`. Loads `_admin/occurrence_gate.py` by absolute path and
    fails CLOSED: if the gate cannot be loaded, the release build stops rather than publishing
    unchecked. Before the guarded source correction is installed the gate is disarmed and this
    returns `None` without touching the frame.
    """
    columns = APPLICATION_COLUMNS.get(name)
    if not columns or "ing_index" not in df.columns:
        return None
    import importlib.util

    adapter_path = REPO_ROOT.parent / "_admin" / "occurrence_gate.py"
    spec = importlib.util.spec_from_file_location("_release_occurrence_gate", str(adapter_path))
    if spec is None or spec.loader is None or not adapter_path.is_file():
        return (f"FATAL: {name}: the occurrence-key supersession gate could not be loaded from "
                f"{adapter_path}; a release may not be published on the grounds that the check "
                "is unavailable.")
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    gate = adapter.gate_module().gate()
    if not gate.armed:
        return None
    present = [c for c in columns if c in df.columns]
    if not present:
        return None
    keys = list(zip(df["recipe_id"].tolist(), df["ing_index"].tolist()))
    carried = []
    for position, key in enumerate(keys):
        if (int(key[0]), int(key[1])) not in gate.old_keys:
            continue
        row = df.iloc[position]
        if any(pd.notna(row[c]) and str(row[c]).strip() for c in present):
            carried.append((int(key[0]), int(key[1])))
    if not carried:
        return None
    return (f"FATAL: {name} still carries {len(carried)} reviewed application(s) on superseded "
            f"occurrence keys, e.g. {carried[:5]}. ing_index is an enumerate() position and the "
            "guarded source correction rewrote those ingredient lists, so publishing this table "
            "would attach a source-food claim to an ingredient that was never reviewed. Rebuild "
            "the enrichment; never re-point an application by reused occurrence index.")


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
        df = apply_nullable_types(name, df)    # AFTER the master overwrite (OD4 v3, review W1-F1)

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

        # Occurrence-key supersession gate.  `ing_index` is an enumerate() position over the
        # ingredient list, so the guarded source correction invalidates every occurrence key it
        # touches.  This table materialises reviewed applications (`ifct_food_review_id`), and
        # copying it verbatim would republish a source-food claim on a key whose ingredient may
        # have changed.  Refuse rather than publish; the fix is to rebuild the enrichment, never
        # to re-point by reused index.  No-op before the correction is installed.
        superseded = occurrence_gate_refusals(name, df)
        if superseded:
            print(superseded, file=sys.stderr)
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

    optional = export_ifct_companions(args.source, args.out)
    written.extend(record for record in optional if 'table' in record)
    metadata = [record for record in optional if 'metadata' in record]
    print(f"\n{len(written)} tables: {total_in / 1e6:.0f} MB total input -> {total_out / 1e6:.0f} MB Parquet")

    (args.out / "ENRICHMENT_MANIFEST.json").write_text(
        json.dumps({"tables": written, "metadata": metadata, "excluded": EXCLUDED}, indent=2), encoding="utf-8"
    )
    print("wrote    ENRICHMENT_MANIFEST.json")
    return 0


# ------------------------------------------------- nullable typed columns (OD4, v0.10.0)
#
# ADDED 2026-09-18 (owner decision; review C18-M3). The v0.10.0 source correction blanks these columns on the
# 58 corrected recipes, whose stored values described the previous dish. pandas reads a blank in an int64
# column as NaN and turns the WHOLE column into float64, and a blank in a bool column turns it into object,
# on which df[df.col] and ~df.col raise. Either would change the published schema for every row. Nullable
# Int64 / boolean keep int64 / bool as the Arrow type and every present value identical; a blank stays null,
# never 0 and never False. A value that is not integral / not boolean is refused, never coerced.
NULLABLE_INTEGER_COLUMNS: dict[str, list[str]] = {
    "renutrition_v3.csv": ["n_ingredients"],
    "fix_cuisine_scope.csv": ["indian_sig"],
    "fix_variants.csv": ["variant_group_id", "variant_index", "variant_count", "dup_of_recipe_id"],
    "quarantine_list.csv": ["n_issues"],
}
NULLABLE_BOOLEAN_COLUMNS: dict[str, list[str]] = {
    "fix11_nonveg.csv": ["animal_in_name", "animal_in_ing", "nonveg_corrected"],
    "fix7_atwater.csv": ["atwater_fixed"],
    "fix_cuisine_scope.csv": ["out_of_scope"],
    # OD4 v3 (review W1-F1): refreshed from the master by apply_master_authority, blank on the 58
    "renutrition_v3.csv": ["energy_capped_v3"],
    "gluten_confidence_v2.csv": ["gluten_declared"],
    "fix14_region.csv": ["region_corrected"],
}
_BOOLEAN_SPELLINGS = {True: True, False: False, "True": True, "False": False}


def apply_nullable_types(name: str, df: "pd.DataFrame") -> "pd.DataFrame":
    """Cast the declared columns to nullable Int64 / boolean, refusing any value that would need coercion."""
    for column in NULLABLE_INTEGER_COLUMNS.get(name, []):
        if column not in df.columns:
            raise KeyError(f"{name}: NULLABLE_INTEGER_COLUMNS names {column!r}, which the table does not have")
        if any(pd.api.types.is_bool(v) for v in df[column].dropna().tolist()):   # OD4 v3, review W1-F3
            raise ValueError(f"{name}.{column}: a boolean in an integer column; refusing to cast it to 1/0")
        values = pd.to_numeric(df[column], errors="raise")
        present = values.dropna()
        if not (present == present.round()).all():
            raise ValueError(f"{name}.{column}: a non-integral value; refusing to truncate it")
        df[column] = values.astype("Int64")
    for column in NULLABLE_BOOLEAN_COLUMNS.get(name, []):
        if column not in df.columns:
            raise KeyError(f"{name}: NULLABLE_BOOLEAN_COLUMNS names {column!r}, which the table does not have")
        present = df[column].dropna().tolist()
        # by TYPE first: unique() would merge 1 into True (1 == True, equal hashes) and let it through
        bad = [v for v in present if not (pd.api.types.is_bool(v) or type(v) is str)]
        bad += [v for v in {v for v in present if type(v) is str} if v not in _BOOLEAN_SPELLINGS]
        if bad:
            raise ValueError(f"{name}.{column}: non-boolean value(s) {bad[:5]}; refusing to coerce them")
        df[column] = df[column].map(lambda v: pd.NA if pd.isna(v) else _BOOLEAN_SPELLINGS[
            v if isinstance(v, str) else bool(v)]).astype("boolean")
    return df

if __name__ == "__main__":
    raise SystemExit(main())
