#!/usr/bin/env python
"""Stage historical-snapshot mappings and provenance (internal source S2) for IndicRecipeNutri 0.11.0.

Binding spec: docs/INTEGRATION_SCHEMA.md section 6 and configs/integration_schema_v0.11.0.json
(tables `recipe_id_crosswalk`, `snapshot_recipe_meta`; layer manifest
`data/historical_snapshot/SNAPSHOT_MANIFEST.json`).

What this script does
  * Re-verifies the SHA-256 of every input against data/manifests/source_manifest.json,
    destination_baseline_v0.10.0.json and the schema's pinned_inputs, and STOPS (exit 2,
    nothing written) on any mismatch.
  * Builds the crosswalk by an exact `recipe_id` VALUE join (pandas merge, outer,
    validate="one_to_one"). No positional, fuzzy, title, URL or dup_family_id join.
  * Derives null-aware change flags on shared IDs. Snapshot RecipeName / Region /
    dup_family_id values are compared in memory only and are NOT written.
  * Omits every withdrawn ID (release_config EXCLUDED_RECIPE_IDS + vendored V7/V8 lists).
    The PII snapshot-only IDs are recorded as a count only.
  * Records kg_edges.parquet by hash only (not opened as a table).

What this script does NOT do
  * Write anywhere except <staging>/data/historical_snapshot/.
  * Import release_config.py (would write __pycache__ into D:\\datasets); it is parsed with `ast`.
  * Copy any payload column, append recipes, or replace Split_v3.

Deterministic and idempotent: rows sorted by recipe_id, no wall-clock values, JSON with
sorted keys, Parquet written from explicit Arrow schemas without pandas metadata.

Usage:  python -B scripts/stage_historical_snapshot.py [--dry-run]
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# ----------------------------------------------------------------------------- paths
# Machine-local paths are NOT in this file. They come from a private source-map JSON named by
# $INDICRECIPE_CONTEXT_SOURCE_MAP, which is kept outside the release. The shipped provenance
# names the sources only as "internal source S1" / "internal source S2", with commit and hashes.
import os as _os


def _source_map() -> dict:
    p = _os.environ.get("INDICRECIPE_CONTEXT_SOURCE_MAP")
    if not p:
        raise SystemExit("set INDICRECIPE_CONTEXT_SOURCE_MAP to the private source-map JSON "
                         "(it is not part of the release); nothing was read or written")
    return json.loads(Path(p).read_text(encoding="utf-8"))


_MAP = _source_map()
SCHEMA_JSON = Path(_MAP["schema_json"])
SOURCE_MANIFEST = Path(_MAP["source_manifest"])
DEST_BASELINE = Path(_MAP["destination_baseline"])
SOURCE_MANIFEST_KEY = _MAP["sources"]["S2"]["source_manifest_key"]
PROVIDER_USED_BY_KEY = _MAP["sources"]["S2"]["provider_check_used_by_key"]
# SHA-256 of the two binding input manifests, as recorded when they were frozen.
BINDING_MANIFEST_SHA = {
    "source_manifest.json": "cc226a1c191a5364ef387135f3ad5b88baedd86270ed252206e225a457d81415",
    "destination_baseline_v0.10.0.json": "44531e87ca531c3266a70869a6cd7011ebe77574703699e2704e9a4fedf62564",
}

DEST = Path(_MAP["destination"])
S2_ROOT = Path(_MAP["sources"]["S2"]["root"])
S2_REPO_NAME = "internal source S2"
S2_LOGS_COPY = S2_ROOT / _MAP["sources"]["S2"]["logs_copy"]  # + receipt rel path (logs/...)

STAGING_ROOT = Path(_MAP["staging_root"])
OUT_DIR = STAGING_ROOT / "data" / "historical_snapshot"

IMPORT_SCRIPT = "scripts/stage_historical_snapshot.py"  # same path in the integration workspace and in the release
SNAPSHOT_ID = "historical_snapshot_20260914"
COMPARE_COLS = ["recipe_id", "RecipeName", "Region", "dup_family_id",
                "Split_v3", "Split_v2", "Split_v1_leaky"]

ENV = dict(os.environ, GIT_OPTIONAL_LOCKS="0")


class StopError(RuntimeError):
    """A verification failed; nothing may be written."""


# ----------------------------------------------------------------------------- helpers
def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise StopError(msg)


def check_hash(label: str, path: Path, expected: str) -> str:
    require(path.exists(), f"{label}: missing file {path}")
    actual = sha256_file(path)
    require(actual == expected, f"{label}: SHA-256 mismatch {path}\n  expected {expected}\n  actual   {actual}")
    return actual


def git_porcelain(repo: Path) -> str:
    r = subprocess.run(["git", "-C", str(repo), "status", "--porcelain"],
                       capture_output=True, env=ENV)
    require(r.returncode == 0, f"git status failed in {repo}")
    return r.stdout.decode("utf-8", "replace")


def load_json(p: Path) -> dict:
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def excluded_recipe_ids_from_release_config(path: Path) -> set[int]:
    """Parse EXCLUDED_RECIPE_IDS keys with `ast` (never import: that writes __pycache__)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "EXCLUDED_RECIPE_IDS" for t in node.targets):
            require(isinstance(node.value, ast.Dict), "EXCLUDED_RECIPE_IDS is not a dict literal")
            return {int(ast.literal_eval(k)) for k in node.value.keys}
    raise StopError("EXCLUDED_RECIPE_IDS not found in release_config.py")


def null_aware_changed(a: pd.Series, b: pd.Series) -> pd.Series:
    """True where values differ; null==null is unchanged; null vs non-null is changed."""
    an, bn = a.isna(), b.isna()
    both_present = ~an & ~bn
    diff = pd.Series(False, index=a.index)
    diff[both_present] = a[both_present].to_numpy() != b[both_present].to_numpy()
    return (diff | (an ^ bn)).astype(bool)


def write_parquet_deterministic(table: pa.Table, path: Path) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    pq.write_table(table, tmp, compression="snappy", write_statistics=True,
                   use_dictionary=True, row_group_size=1 << 20)
    os.replace(tmp, path)


def write_json_deterministic(obj: dict, path: Path) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, indent=2, sort_keys=True, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


# ----------------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="verify and build, write nothing")
    args = ap.parse_args()

    # --- 0. binding manifests are the frozen ones --------------------------------------
    check_hash("binding source_manifest", SOURCE_MANIFEST, BINDING_MANIFEST_SHA["source_manifest.json"])
    check_hash("binding destination baseline", DEST_BASELINE,
               BINDING_MANIFEST_SHA["destination_baseline_v0.10.0.json"])
    schema = load_json(SCHEMA_JSON)
    src = load_json(SOURCE_MANIFEST)[SOURCE_MANIFEST_KEY]
    base = load_json(DEST_BASELINE)
    require(schema["schema_version"] == "1.1.0", "schema version is not 1.1.0")
    pinned = schema["pinned_inputs"]
    t_xw = schema["tables"]["recipe_id_crosswalk"]
    t_sm = schema["tables"]["snapshot_recipe_meta"]
    man_spec = schema["layer_manifests"]["data/historical_snapshot/SNAPSHOT_MANIFEST.json"]

    # --- 1. destination: clean tree, pinned bytes ---------------------------------------
    porcelain_before = git_porcelain(DEST)
    require(porcelain_before == "", "destination git tree is not clean")
    base_files = {f["rel"] if "rel" in f else f["path"]: f for f in base["files"]} \
        if isinstance(base["files"], list) else base["files"]

    def base_sha(rel: str) -> str:
        e = base_files[rel]
        return e["sha256"] if isinstance(e, dict) else e

    dest_rs_rel = pinned["destination_recipes_structured_0_10_0"]["path"]
    dest_rs_sha = pinned["destination_recipes_structured_0_10_0"]["sha256"]
    require(base_sha(dest_rs_rel) == dest_rs_sha, "schema pin and baseline disagree on recipes_structured")
    check_hash("destination recipes_structured", DEST / dest_rs_rel, dest_rs_sha)
    rc_rel = "scripts/release_config.py"
    check_hash("destination release_config", DEST / rc_rel, base_sha(rc_rel))
    wd_rel = "data/provenance/withdrawn_ids.json"
    check_hash("destination withdrawn_ids", DEST / wd_rel, base_sha(wd_rel))
    recipes_rel = "data/corpus/recipes.parquet"
    check_hash("destination recipes (canonical Split_v3 table)", DEST / recipes_rel, base_sha(recipes_rel))

    # --- 2. source S2: snapshot, excluded asset (hash only), receipts --------------------------
    snap_pin = pinned["s2_snapshot_recipes"]
    src_files = {f["rel"]: f for f in src["files"]}
    require(src_files[snap_pin["path"]]["sha256"] == snap_pin["sha256"],
            "schema pin and source_manifest disagree on the snapshot parquet")
    snap_path = S2_ROOT / Path(snap_pin["path"])
    check_hash("source S2 snapshot recipes_structured", snap_path, snap_pin["sha256"])

    kg_rel = ".local/paper-data-20260914/data/kg/kg_edges.parquet"
    kg_sha = man_spec["excluded_hash_only"]["kg_edges.parquet"]
    require(src_files[kg_rel]["sha256"] == kg_sha, "schema and source_manifest disagree on kg_edges")
    check_hash("source S2 kg_edges (hash only, not opened)", S2_ROOT / Path(kg_rel), kg_sha)

    receipts = []
    receipt_bytes: dict[str, bytes] = {}
    for r in sorted(src["receipts"], key=lambda x: x["rel"]):
        copy = S2_LOGS_COPY / Path(r["rel"])
        check_hash(f"source S2 receipt {r['rel']}", copy, r["head_sha256"])
        receipt_bytes[r["rel"]] = copy.read_bytes()
        receipts.append({
            "rel": r["rel"],
            "sha256": r["head_sha256"],
            "head_commit": src["git"]["head"],
            "head_blob_id": r["head_blob_id"],
            "worktree_status": "deleted (tracked logs/ absent from worktree)",
            "bytes_read_from": "output/code-release-v0.17/" + r["rel"] + " (byte-identical to the HEAD blob)",
        })
    require(src["git"]["head"] == pinned["s2_receipts_head_commit"], "source S2 receipts head commit mismatch")

    snapshot_json = json.loads(receipt_bytes["logs/dataset_current_20260914/snapshot.json"])
    require(snapshot_json["files"]["data/corpus/recipes_structured.parquet"] == snap_pin["sha256"],
            "snapshot.json declared corpus hash != pinned snapshot hash")
    require(snapshot_json["files"]["data/kg/kg_edges.parquet"] == kg_sha,
            "snapshot.json declared kg_edges hash != pinned hash")
    require(snapshot_json["provider_commit"] == snap_pin["declared_provider_commit"],
            "snapshot.json provider commit != schema declared_provider_commit")
    split_counts = json.loads(receipt_bytes["logs/dataset_current_20260914/learned/split_counts.json"])
    agg = man_spec["aggregate_split_counts"]
    require((split_counts["train"], split_counts["validation"], split_counts["test"], len(split_counts["folds"]))
            == (agg["train"], agg["validation"], agg["test"], agg["folds"]),
            "split_counts.json does not match the schema's aggregate source S2 split counts")
    learned_receipt = json.loads(receipt_bytes["logs/dataset_current_20260914/learned/receipt.json"])
    npz_declared = learned_receipt.get("files", learned_receipt).get("split_manifest.npz") \
        if isinstance(learned_receipt.get("files", learned_receipt), dict) else None
    if npz_declared is None:  # search the receipt tree for the key
        def _find(o):
            if isinstance(o, dict):
                for k, v in o.items():
                    if k == "split_manifest.npz":
                        return v
                    x = _find(v)
                    if x:
                        return x
            elif isinstance(o, list):
                for v in o:
                    x = _find(v)
                    if x:
                        return x
            return None
        npz_declared = _find(learned_receipt)
    require(npz_declared == src["split_manifest_npz"]["declared_sha256"], "split_manifest.npz declared hash mismatch")
    npz_on_disk = sorted(str(p.relative_to(S2_ROOT)).replace("\\", "/") for p in S2_ROOT.rglob("split_manifest*.npz"))
    provider_check = json.loads(receipt_bytes["logs/dataset_current_20260914/provider_check.json"])

    # --- 3. withdrawn IDs --------------------------------------------------------------
    pii_ids = excluded_recipe_ids_from_release_config(DEST / rc_rel)
    wd = load_json(DEST / wd_rel)
    v7 = {int(k) for k in wd["v7_nonrecipe"]}
    v8 = {int(k) for k in wd["v8_grihshobha"]}
    withdrawn = pii_ids | v7 | v8
    withdrawn_set_sizes = {"build_time_exclusion_pii": len(pii_ids), "v7_nonrecipe": len(v7),
                           "v8_grihshobha": len(v8), "union": len(withdrawn)}

    # --- 4. load selected columns (payload columns are not read) ------------------------
    cur = pq.read_table(DEST / dest_rs_rel, columns=COMPARE_COLS).to_pandas()
    snp = pq.read_table(snap_path, columns=COMPARE_COLS).to_pandas()
    canon = pq.read_table(DEST / recipes_rel, columns=["recipe_id", "Split_v3"]).to_pandas()
    for name, df in (("current", cur), ("snapshot", snp)):
        require(df["recipe_id"].dtype == "int64", f"{name} recipe_id is not int64")
        require(df["recipe_id"].notna().all(), f"{name} recipe_id has nulls")
        require(df["recipe_id"].is_unique, f"{name} recipe_id has duplicates: ambiguous mapping, build fails")
    # canonical Split_v3 (recipes.parquet) must agree with recipes_structured
    cc = cur[["recipe_id", "Split_v3"]].merge(canon, on="recipe_id", how="outer",
                                              validate="one_to_one", indicator=True, suffixes=("", "_canon"))
    require((cc["_merge"] == "both").all(), "recipes.parquet and recipes_structured ID sets differ")
    require((cc["Split_v3"] == cc["Split_v3_canon"]).all(), "Split_v3 differs between recipes and recipes_structured")
    require(not (set(cur["recipe_id"]) & withdrawn), "destination 0.10.0 contains a withdrawn ID")

    # --- 5. exact recipe_id value join --------------------------------------------------
    j = cur.merge(snp, on="recipe_id", how="outer", validate="one_to_one",
                  suffixes=("_cur", "_snap"), indicator=True)
    both = j[j["_merge"] == "both"]
    cur_only = j[j["_merge"] == "left_only"]
    snap_only = j[j["_merge"] == "right_only"]
    snap_only_ids = set(snap_only["recipe_id"].astype("int64"))
    snap_only_withdrawn = snap_only_ids & withdrawn
    snap_only_retained = snap_only_ids - withdrawn
    snap_only_withdrawn_pii = snap_only_withdrawn & pii_ids
    require(snap_only_withdrawn == snap_only_withdrawn_pii,
            "snapshot-only withdrawn IDs include non-PII withdrawals; schema has no status for them")
    require(not (set(both["recipe_id"]) & withdrawn), "a shared ID is withdrawn")

    # --- 6. recipe_id_crosswalk -------------------------------------------------------
    pv = schema["provenance_columns"]
    prov = {
        "prov_source_repo": S2_REPO_NAME,
        "prov_source_path": snap_pin["path"],
        "prov_source_sha256": snap_pin["sha256"],
        "prov_source_commit": snap_pin["prov_source_commit"],
        "prov_import_script": IMPORT_SCRIPT,
        "prov_schema_version": schema["schema_version"],
    }
    require(re.fullmatch(pv["prov_source_commit"]["regex"], prov["prov_source_commit"]) is not None,
            "prov_source_commit does not match its regex")

    rows = []
    for rid in sorted(both["recipe_id"].astype("int64")):
        rows.append((f"xw::{rid}", rid, rid, "exact_id"))
    for rid in sorted(cur_only["recipe_id"].astype("int64")):
        rows.append((f"xw::{rid}", rid, None, "current_only"))
    for rid in sorted(snap_only_retained):
        rows.append((f"xw::s{rid}", None, rid, "snapshot_only_retained"))
    rows.sort(key=lambda r: (r[1] if r[1] is not None else r[2], r[3]))
    n = len(rows)

    xw_schema = pa.schema([
        pa.field("xw_uid", pa.string(), nullable=False),
        pa.field("recipe_id", pa.int64(), nullable=True),
        pa.field("snapshot_id", pa.string(), nullable=False),
        pa.field("snapshot_recipe_id", pa.int64(), nullable=True),
        pa.field("match_status", pa.string(), nullable=False),
        pa.field("join_key", pa.string(), nullable=False),
        pa.field("identity_semantics", pa.string(), nullable=False),
        pa.field("prov_source_repo", pa.string(), nullable=False),
        pa.field("prov_source_path", pa.string(), nullable=False),
        pa.field("prov_source_sha256", pa.string(), nullable=False),
        pa.field("prov_source_commit", pa.string(), nullable=False),
        pa.field("prov_destination_version", pa.string(), nullable=False),
        pa.field("prov_destination_sha256", pa.string(), nullable=False),
        pa.field("prov_import_script", pa.string(), nullable=False),
        pa.field("prov_schema_version", pa.string(), nullable=False),
    ], metadata={"schema_id": schema["schema_id"], "schema_version": schema["schema_version"],
                 "table": "recipe_id_crosswalk"})
    require(set(xw_schema.names) == set(t_xw["columns"]), "crosswalk columns differ from the schema")
    xw = pa.Table.from_pydict({
        "xw_uid": [r[0] for r in rows],
        "recipe_id": [r[1] for r in rows],
        "snapshot_id": [SNAPSHOT_ID] * n,
        "snapshot_recipe_id": [r[2] for r in rows],
        "match_status": [r[3] for r in rows],
        "join_key": ["recipe_id_value"] * n,
        "identity_semantics": ["same_id_not_same_content"] * n,
        "prov_source_repo": [prov["prov_source_repo"]] * n,
        "prov_source_path": [prov["prov_source_path"]] * n,
        "prov_source_sha256": [prov["prov_source_sha256"]] * n,
        "prov_source_commit": [prov["prov_source_commit"]] * n,
        "prov_destination_version": [schema["base_version"]] * n,
        "prov_destination_sha256": [dest_rs_sha] * n,
        "prov_import_script": [IMPORT_SCRIPT] * n,
        "prov_schema_version": [prov["prov_schema_version"]] * n,
    }, schema=xw_schema)
    match_counts = {k: sum(1 for r in rows if r[3] == k)
                    for k in ("exact_id", "current_only", "snapshot_only_retained")}

    # --- 7. snapshot_recipe_meta -------------------------------------------------------
    b = both.sort_values("recipe_id", kind="mergesort").reset_index(drop=True)
    flags = {
        "split_v3_changed": null_aware_changed(b["Split_v3_snap"], b["Split_v3_cur"]),
        "split_v2_changed": null_aware_changed(b["Split_v2_snap"], b["Split_v2_cur"]),
        "split_v1_leaky_changed": null_aware_changed(b["Split_v1_leaky_snap"], b["Split_v1_leaky_cur"]),
        "recipe_name_changed": null_aware_changed(b["RecipeName_snap"], b["RecipeName_cur"]),
        "region_changed": null_aware_changed(b["Region_snap"], b["Region_cur"]),
        "dup_family_changed": null_aware_changed(b["dup_family_id_snap"], b["dup_family_id_cur"]),
    }
    for c in ("Split_v3_snap", "Split_v2_snap", "Split_v1_leaky_snap"):
        require(b[c].notna().all() and set(b[c]) <= {"train", "val", "test"}, f"{c} has values outside train/val/test")
    m = len(b)
    sm_schema = pa.schema([
        pa.field("recipe_id", pa.int64(), nullable=False),
        pa.field("snapshot_id", pa.string(), nullable=False),
        pa.field("snapshot_split_v3", pa.string(), nullable=False),
        pa.field("snapshot_split_v2", pa.string(), nullable=False),
        pa.field("snapshot_split_v1_leaky", pa.string(), nullable=False),
        *[pa.field(k, pa.bool_(), nullable=False) for k in flags],
        pa.field("snapshot_label_status", pa.string(), nullable=False),
        pa.field("prov_source_repo", pa.string(), nullable=False),
        pa.field("prov_source_path", pa.string(), nullable=False),
        pa.field("prov_source_sha256", pa.string(), nullable=False),
        pa.field("prov_source_commit", pa.string(), nullable=False),
        pa.field("prov_import_script", pa.string(), nullable=False),
        pa.field("prov_schema_version", pa.string(), nullable=False),
    ], metadata={"schema_id": schema["schema_id"], "schema_version": schema["schema_version"],
                 "table": "snapshot_recipe_meta",
                 "snapshot_split_semantics": t_sm["columns"]["snapshot_split_v3"]["semantics"]})
    expected_sm_cols = {c for c, spec in t_sm["columns"].items() if spec.get("present", True)}
    require(set(sm_schema.names) == expected_sm_cols, "snapshot_recipe_meta columns differ from the schema")
    sm = pa.Table.from_pydict({
        "recipe_id": b["recipe_id"].astype("int64").tolist(),
        "snapshot_id": [SNAPSHOT_ID] * m,
        "snapshot_split_v3": b["Split_v3_snap"].tolist(),
        "snapshot_split_v2": b["Split_v2_snap"].tolist(),
        "snapshot_split_v1_leaky": b["Split_v1_leaky_snap"].tolist(),
        **{k: v.tolist() for k, v in flags.items()},
        "snapshot_label_status": ["historical"] * m,
        "prov_source_repo": [prov["prov_source_repo"]] * m,
        "prov_source_path": [prov["prov_source_path"]] * m,
        "prov_source_sha256": [prov["prov_source_sha256"]] * m,
        "prov_source_commit": [prov["prov_source_commit"]] * m,
        "prov_import_script": [IMPORT_SCRIPT] * m,
        "prov_schema_version": [prov["prov_schema_version"]] * m,
    }, schema=sm_schema)
    flag_counts = {k: int(v.sum()) for k, v in flags.items()}
    flag_expected = {k: t_sm["columns"][k]["expected_true"] for k in flags}
    split_v3_changed_ids = sorted(int(x) for x in b.loc[flags["split_v3_changed"], "recipe_id"])
    # snapshot_split_v3 must differ from canonical Split_v3 exactly where the flag is true (SM-03)
    require(((b["Split_v3_snap"] != b["Split_v3_cur"]) == flags["split_v3_changed"]).all(), "SM-03 self-check failed")

    # --- 8. withdrawn-ID guard on the built tables (before anything is written) ---------
    for tname, tbl in (("recipe_id_crosswalk", xw), ("snapshot_recipe_meta", sm)):
        for col in tbl.column_names:
            arr = tbl.column(col).to_pylist()
            if pa.types.is_integer(tbl.schema.field(col).type):
                hit = {v for v in arr if v is not None} & withdrawn
                require(not hit, f"{tname}.{col} contains {len(hit)} withdrawn IDs")
            elif pa.types.is_string(tbl.schema.field(col).type):
                for s in set(arr):
                    toks = {int(t) for t in re.findall(r"(?<![0-9a-f])[0-9]+(?![0-9a-f])", s or "")}
                    require(not (toks & withdrawn), f"{tname}.{col} string token matches a withdrawn ID")

    # --- 9. manifest -------------------------------------------------------------------
    manifest = {
        "schema_id": schema["schema_id"],
        "schema_version": schema["schema_version"],
        "task": "context-layer integration, release 0.11.0",
        "classification": man_spec["classification"],
        "snapshot_id": SNAPSHOT_ID,
        "snapshot_sha256": snap_pin["sha256"],
        "snapshot_source": {
            "repo": S2_REPO_NAME,
            "path": snap_pin["path"],
            "prov_source_commit": snap_pin["prov_source_commit"],
            "in_any_commit": snap_pin["in_any_commit"],
            "rows_read": int(len(snp)),
            "columns_read": COMPARE_COLS,
            "columns_written": ["recipe_id (as recipe_id / snapshot_recipe_id)",
                                "Split_v3", "Split_v2", "Split_v1_leaky (as snapshot_split_*)"],
            "columns_compared_not_written": ["RecipeName", "Region", "dup_family_id"],
        },
        "snapshot_declared": {
            "source": "logs/dataset_current_20260914/snapshot.json @ " + src["git"]["head"],
            "dataset_version": snapshot_json["dataset_version"],
            "provider_commit": snapshot_json["provider_commit"],
            "scope": snapshot_json["scope"],
            "files": snapshot_json["files"],
            "declared_provider_commit_matches_bytes": snap_pin["declared_provider_commit_matches_bytes"],
            "declared_hashes_match_bytes_read": True,
        },
        "destination_version": schema["base_version"],
        "destination_commit": schema["base_commit"],
        "destination_sha256": dest_rs_sha,
        "destination_path": dest_rs_rel,
        "destination_git_clean_before_and_after": True,
        "canonical_split": {"column": "Split_v3", "version": schema["base_version"],
                            "note": "snapshot_split_* are HISTORICAL (0.9.0-era) and never override Split_v3"},
        "join": {"key": "recipe_id (int64) exact value equality",
                 "method": "pandas.merge(how='outer', validate='one_to_one')",
                 "positional_or_fuzzy_joins": "none",
                 "ambiguous_ids": 0,
                 "ambiguity_policy": "build fails if either side has a duplicate recipe_id"},
        "row_counts": {"recipe_id_crosswalk": xw.num_rows, "snapshot_recipe_meta": sm.num_rows,
                       "snapshot_input_rows": int(len(snp)), "destination_rows": int(len(cur))},
        "match_status_counts": match_counts,
        "omitted_withdrawn_snapshot_ids_count": len(snap_only_withdrawn),
        "omitted_withdrawn_snapshot_ids_reason": "build-time exclusion (PII); IDs not written to any staged file",
        "withdrawn_sets_checked": withdrawn_set_sizes,
        "change_flag_counts": flag_counts,
        "change_flag_expected_schema": flag_expected,
        "change_flag_semantics": "null-aware: null==null unchanged, null vs value changed",
        "split_v3_changed_recipe_ids": split_v3_changed_ids,
        "aggregate_split_counts": agg,
        "per_recipe_snapshot_split": man_spec["per_recipe_snapshot_split"],
        "per_recipe_snapshot_split_detail": {
            "declared_file": "split_manifest.npz",
            "declared_sha256": npz_declared,
            "declared_in": "logs/dataset_current_20260914/learned/receipt.json",
            "found_on_disk": npz_on_disk,
        },
        "excluded_hash_only": man_spec["excluded_hash_only"],
        "excluded_hash_only_note": "kg_edges.parquet hash re-verified at staging; file not opened as a table; FlavorDB-derived (CC BY-NC-SA 3.0), not imported",
        "receipts": receipts,
        "receipt_notes": {
            "provider_check.json": {"status": provider_check.get("status"),
                                     "scope": provider_check.get("scope"),
                                     "used_by_consumer": provider_check.get(PROVIDER_USED_BY_KEY)},
        },
        "import_scripts": {
            IMPORT_SCRIPT: {"repo": "integration workspace (private)",
                            "sha256": sha256_file(Path(__file__).resolve())},
        },
        "not_carried": t_sm["not_carried"],
    }
    missing = [k for k in man_spec["required_keys"] if k not in manifest]
    require(not missing, f"manifest missing required keys {missing}")
    man_text = json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False)
    man_toks = {int(t) for t in re.findall(r"(?<![0-9A-Za-z])[0-9]+(?![0-9A-Za-z])", man_text)}
    require(not (man_toks & pii_ids), "manifest contains a PII-withdrawn ID token")
    other_collisions = sorted(man_toks & withdrawn)

    # --- 10. write ---------------------------------------------------------------------
    report = {
        "match_status_counts": match_counts,
        "omitted_withdrawn_snapshot_ids_count": len(snap_only_withdrawn),
        "change_flag_counts": flag_counts,
        "change_flag_expected": flag_expected,
        "split_v3_changed_ids": split_v3_changed_ids,
        "manifest_integer_tokens_colliding_with_nonpii_withdrawn_ids": other_collisions,
        "per_recipe_split_manifest_on_disk": npz_on_disk,
        "provider_check_status": provider_check.get("status"),
    }
    if not args.dry_run:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        write_parquet_deterministic(xw, OUT_DIR / "recipe_id_crosswalk.parquet")
        write_parquet_deterministic(sm, OUT_DIR / "snapshot_recipe_meta.parquet")
        write_json_deterministic(manifest, OUT_DIR / "SNAPSHOT_MANIFEST.json")
        report["written"] = {p.name: sha256_file(p) for p in sorted(OUT_DIR.iterdir()) if p.is_file()}

    porcelain_after = git_porcelain(DEST)
    require(porcelain_after == "", "destination git tree changed during staging")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except StopError as e:
        print(f"STOP: {e}", file=sys.stderr)
        sys.exit(2)
