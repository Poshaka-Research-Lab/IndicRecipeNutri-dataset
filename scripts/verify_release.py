"""Pre-release gate. Fails the build rather than publishing a defective record.

Checks, in order of what they protect:

  1. Licence      no withheld prose column, by stem, in any published artefact;
                  no free-text column that looks like prose smuggled under a new name
  2. Integrity    row counts, KG node/edge counts, benchmark query count
  3. Privacy      PII pattern sweep over every string column
  4. Checksums    SHA256SUMS matches what is on disk
  5. Disclosure   the audit artefacts a release is required to carry are present

A release that cannot pass this should not be tagged. Every failure names the file and
the reason; nothing is a warning that can be scrolled past.

Usage:  python scripts/verify_release.py [--strict-checksums]
Exit:   0 all checks passed, 1 one or more failed
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))
from release_config import (  # noqa: E402
    EXCLUDED_RECIPE_IDS,
    EXPECTED_BENCHMARK_QUERIES,
    DECLARED_ALLERGENS,
    EXPECTED_KG_EDGES,
    EXPECTED_KG_NODES,
    UNASSESSED_TOKEN,
    EXPECTED_RECIPES,
    PII_EXEMPT_COLUMNS,
    PII_PATTERNS,
    PROSE_COLUMNS,
    REPO_ROOT,
    WITHDRAWN_NONRECIPE_IDS,
    WITHDRAWAL_SETS,
    all_withdrawn_ids,
    unregistered_quarantine_files,
)
from build_enrichment import prose_stem  # noqa: E402

# Imported for INCLUDE_DIRS / INCLUDE_FILES only, so the checksum COVERAGE check below
# tests the same scope the manifest is written over. Two hand-kept copies of that scope
# would drift, and the drift would be silent in the safe direction-looking way.
import make_checksums as mk  # noqa: E402

# A published string column whose values run this long is prose by any other name.
# `IngredientsList` is a parsed JSON array and is legitimately long, so it is exempt.
PROSE_LENGTH_THRESHOLD = 400
LENGTH_EXEMPT = {"IngredientsList", "HealthConditions", "checks", "lenses", "Ingredients_recovered"}

REQUIRED_ARTEFACTS = [
    "data/corpus/recipes_structured.parquet",
    "data/corpus/rehydration_index.parquet",
    "data/corpus/corpus_manifest.json",
    "data/corpus/ALLERGEN_AUDIT.json",
    "data/kg/kg_nodes.parquet",
    "data/kg/kg_edges.parquet",
    "data/kg/kg_stats.json",
    "data/benchmark/eval_queries.jsonl",
    "data/benchmark/GOLD_SET_AUDIT.json",
    "docs/DATASHEET.md",
    "docs/PROVENANCE.md",
    "docs/TAKEDOWN.md",
    "docs/THIRD_PARTY_TERMS.md",
    "LICENSE-DATA",
    "LICENSE-CODE",
    "CITATION.cff",
    ".zenodo.json",
]

failures: list[str] = []
notes: list[str] = []


def fail(check: str, detail: str) -> None:
    failures.append(f"[{check}] {detail}")


def published_parquet(root: Path) -> list[Path]:
    return sorted(p for p in (root / "data").rglob("*.parquet"))


# ------------------------------------------------------------------ 1. licence guard


def check_licence(root: Path) -> None:
    for path in published_parquet(root):
        schema = pq.read_schema(path)
        offending = [c for c in schema.names if prose_stem(c) in PROSE_COLUMNS]
        if offending:
            fail(
                "licence",
                f"{path.relative_to(root)} publishes withheld prose column(s) {offending}",
            )

    # Content-level check: a long free-text column under an innocent name.
    for path in published_parquet(root):
        schema = pq.read_schema(path)
        str_cols = [
            n
            for n, t in zip(schema.names, schema.types)
            if str(t) in ("string", "large_string") and n not in LENGTH_EXEMPT
        ]
        if not str_cols:
            continue
        sample = pd.read_parquet(path, columns=str_cols).head(5000)
        for col in str_cols:
            longest = sample[col].astype(str).str.len().max()
            if pd.notna(longest) and longest > PROSE_LENGTH_THRESHOLD:
                fail(
                    "licence",
                    f"{path.relative_to(root)} column '{col}' has values up to "
                    f"{int(longest)} chars — prose under another name? Add to "
                    f"LENGTH_EXEMPT with a reason, or withhold it.",
                )


# --------------------------------------------------------------------- 2. integrity


def check_integrity(root: Path) -> None:
    corpus = root / "data" / "corpus" / "recipes_structured.parquet"
    if corpus.exists():
        n = pq.read_metadata(corpus).num_rows
        if n != EXPECTED_RECIPES:
            fail("integrity", f"corpus has {n:,} rows, expected {EXPECTED_RECIPES:,}")
    else:
        fail("integrity", "corpus parquet missing")

    stats_path = root / "data" / "kg" / "kg_stats.json"
    if stats_path.exists():
        stats = json.loads(stats_path.read_text(encoding="utf-8"))
        for name, expected, actual in (
            ("nodes", EXPECTED_KG_NODES, stats.get("nodes")),
            ("edges", EXPECTED_KG_EDGES, stats.get("edges")),
        ):
            if actual != expected:
                fail("integrity", f"kg_stats {name}={actual}, expected {expected}")
        for name, key in (("kg_nodes.parquet", "nodes"), ("kg_edges.parquet", "edges")):
            p = root / "data" / "kg" / name
            if p.exists() and pq.read_metadata(p).num_rows != stats.get(key):
                fail(
                    "integrity",
                    f"{name} has {pq.read_metadata(p).num_rows:,} rows, "
                    f"kg_stats says {stats.get(key):,}",
                )
    else:
        fail("integrity", "kg_stats.json missing")

    bench = root / "data" / "benchmark" / "eval_queries.jsonl"
    if bench.exists():
        n = sum(1 for line in bench.open(encoding="utf-8") if line.strip())
        if n != EXPECTED_BENCHMARK_QUERIES:
            fail("integrity", f"benchmark has {n} queries, expected {EXPECTED_BENCHMARK_QUERIES}")
    else:
        fail("integrity", "benchmark missing")


# ----------------------------------------------------------------------- 3. privacy


def check_pii(root: Path) -> None:
    compiled = {k: re.compile(v) for k, v in PII_PATTERNS.items()}
    for path in published_parquet(root):
        schema = pq.read_schema(path)
        str_cols = [
            n
            for n, t in zip(schema.names, schema.types)
            if str(t) in ("string", "large_string") and n not in PII_EXEMPT_COLUMNS
        ]
        if not str_cols:
            continue
        df = pd.read_parquet(path, columns=str_cols)
        for col in str_cols:
            series = df[col].dropna().astype(str)
            if series.empty:
                continue
            for name, rx in compiled.items():
                # credit_card over-fires on numeric id strings; only flag when the
                # column is not otherwise numeric-looking.
                hits = series.str.contains(rx, regex=True, na=False)
                if hits.any():
                    n = int(hits.sum())
                    example = series[hits].iloc[0][:80]
                    if name == "credit_card" and series.str.fullmatch(r"[\d.eE+-]*").mean() > 0.9:
                        notes.append(
                            f"pii: {path.relative_to(root)}:{col} '{name}' suppressed "
                            f"({n} hits) — column is numeric"
                        )
                        continue
                    fail(
                        "privacy",
                        f"{path.relative_to(root)} column '{col}' matches {name} "
                        f"in {n} row(s), e.g. {example!r}",
                    )


# --------------------------------------------------------------------- 4. checksums


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_checksums(root: Path, strict: bool) -> None:
    manifest = root / "checksums" / "SHA256SUMS"
    if not manifest.exists():
        if strict:
            fail("checksums", "SHA256SUMS missing — run scripts/make_checksums.py")
        else:
            notes.append("checksums: SHA256SUMS missing (not strict)")
        return
    bad = 0
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, rel = line.split(None, 1)
        target = root / rel.strip()
        if not target.exists():
            fail("checksums", f"listed but missing: {rel.strip()}")
            bad += 1
        elif sha256(target) != digest:
            fail("checksums", f"digest mismatch: {rel.strip()}")
            bad += 1
    # The loop above walks the MANIFEST, so it can only catch a listed file that changed
    # or vanished. A file ADDED to the payload after the last make_checksums.py run is
    # invisible to it: it ships, unverified, and the gate stays green. That is exactly how
    # docs/RELEASING.md entered the payload on 2026-09-05 with no digest. So walk the other
    # direction too, over the same scope make_checksums.py writes.
    listed = {line.split(None, 1)[1].strip()
              for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip()}
    on_disk = set()
    for d in mk.INCLUDE_DIRS:
        on_disk |= {p.relative_to(root).as_posix()
                    for p in (root / d).rglob("*") if p.is_file()}
    on_disk |= {f for f in mk.INCLUDE_FILES if (root / f).exists()}
    for rel in sorted(on_disk - listed):
        fail("checksums", f"published but not in SHA256SUMS: {rel} — run scripts/make_checksums.py")
        bad += 1

    # CRLF IN AN eol=lf FILE IS A CHECKSUM BUG THAT ONLY SHOWS UP ON THE RUNNER.
    # `.gitattributes` normalises source and docs to LF. A file authored on Windows with
    # default newline translation is CRLF in the working tree, LF in the object store, and
    # LF again on a Linux checkout -- one byte shorter per line than the digest recorded from
    # the working copy. `--strict-checksums` then passes here and fails in CI, which is the
    # worst place to find it. Thirteen files were in that state on 2026-09-05.
    lf_exts = {".md", ".py", ".yml", ".yaml", ".cff"}
    for rel in sorted(listed):
        p = root / rel
        suf = Path(rel).suffix
        # `data/**/*.json` is `-text` (stored verbatim); docs/*.json is not.
        normalised = suf in lf_exts or (suf == ".json" and not rel.startswith("data/"))
        if not normalised or not p.exists():
            continue
        if b"\r\n" in p.read_bytes():
            fail("checksums", f"CRLF in an eol=lf file: {rel} — its digest was taken from the "
                             f"working copy, but a fresh checkout delivers LF and will not match")
            bad += 1

    if not bad:
        notes.append(f"checksums: all {len(listed)} entries match, every published file under "
                     f"{'/, '.join(mk.INCLUDE_DIRS)}/ is covered, and no eol=lf file carries CRLF")


# -------------------------------------------------------------------- 5. disclosure


def check_exclusions(root: Path) -> None:
    """No withdrawn recipe may survive anywhere in the published payload.

    Populations come from `release_config.WITHDRAWAL_SETS`, NOT from a list written out
    here. This function used to name two sets explicitly, a third was added to the corpus
    without being added to this line, and on 2026-09-04 all 801 rows of that third set were
    found in 21 published enrichment tables while the master held none. Reading the registry
    means a new withdrawal is wired in one place instead of remembered in several.

    Each set is checked separately so the failure says WHICH withdrawal leaked; "801 rows
    from an unnamed set" is not an actionable error.
    """
    stray = unregistered_quarantine_files()
    if stray:
        fail(
            "exclusion",
            f"quarantine file(s) not covered by any registered withdrawal set: {stray}. "
            f"A withdrawal nobody wired up is how 801 rows shipped on 2026-09-04. Add the "
            f"set to release_config.WITHDRAWAL_SETS, or to KNOWN_QUARANTINE_FILES if it is "
            f"genuinely not a release withdrawal.",
        )

    withdrawn = all_withdrawn_ids()
    if not withdrawn:
        return

    node_ids = {f"recipe::{rid}" for rid in withdrawn}

    for path in published_parquet(root):
        schema = pq.read_schema(path)
        cols = [c for c in ("recipe_id", "node_id", "head", "tail") if c in schema.names]
        if not cols:
            continue
        df = pd.read_parquet(path, columns=cols)
        for col in cols:
            if col == "recipe_id":
                hit = df[col].isin(withdrawn)
            else:
                hit = df[col].isin(node_ids)
            if hit.any():
                fail(
                    "exclusion",
                    f"{path.relative_to(root)} still references excluded recipe(s) "
                    f"in column '{col}': {int(hit.sum())} row(s)",
                )

    bench = root / "data" / "benchmark" / "eval_queries.jsonl"
    if bench.exists():
        for line in bench.open(encoding="utf-8"):
            if not line.strip():
                continue
            query = json.loads(line)
            leaked = node_ids.intersection(query.get("relevant", []))
            if leaked:
                fail(
                    "exclusion",
                    f"benchmark query {query['query']!r} cites excluded {sorted(leaked)}",
                )

    notes.append(
        "exclusion: "
        + " + ".join(f"{len(ids)} {name}" for name, ids in WITHDRAWAL_SETS.items())
        + " absent from all published artefacts"
    )


def check_static_id_lists(root: Path) -> None:
    """Withdrawn recipes may not be referenced by the STATIC benchmark artefacts either.

    `check_exclusions` above scans published *.parquet. `data/synthetic_interactions/` is
    plain text and CSV, so it was outside every scan -- and after the V7 withdrawal
    (2026-09-01) it still referenced recipes that had left the corpus. All three gate suites
    were green while it did. That is the failure mode CLAUDE.md names: a gate that does not
    cover the path that broke.

    This check is COLUMN-AWARE on purpose. A regex sweep for withdrawn ids over these files
    reports `user_list.txt` and `train.txt` as offenders, which is wrong -- those hold user
    ids and REMAPPED ids that merely collide numerically with a recipe id. Only the columns
    named below actually carry a `recipe_id`.

    The counts are PINNED, not waived. `bench_synth/gen.py` is a static generator whose
    paths point at another machine (`/mnt/user-data/uploads/...`), so it cannot be re-run
    here, and regenerating a synthetic benchmark would invalidate the published
    `baseline_results.json`. That is a decision, not a side effect, and it is filed as
    TODO_VERIFICATION V9.5. Until then the artefact is DECLARED as pinned to the
    pre-withdrawal corpus at exactly these counts, and any drift -- a further withdrawal, a
    partial regeneration -- fails the build instead of passing silently.
    """
    si = root / "data" / "synthetic_interactions"
    if not si.exists() or not WITHDRAWN_NONRECIPE_IDS:
        return

    # file -> (column holding a recipe_id, separator, id prefix to strip, pinned row count)
    #
    # `entity_list.txt` was MISSED by the first version of this check, and the miss is worth
    # recording: its ids are written `item:11`, not `11`, so a numeric read of the column
    # silently coerced every value to NaN and matched nothing. It carries the same 315
    # withdrawn references as item_list.txt. A prefixed identifier defeats a numeric test
    # without erroring - the same shape as the plural fail-open in the meat lexicon.
    #
    # The other id-bearing files in this directory are NOT recipe ids and are correctly
    # absent: relation_list.txt and user_list.txt are relations and users, and kg_final.txt,
    # train.txt and test.txt carry REMAPPED ids that merely collide numerically.
    PINNED = {
        "item_list.txt": ("org_id", r"\s+", "", 315),
        "entity_list.txt": ("org_id", r"\s+", "item:", 315),
        "interactions.csv": ("recipe_id", ",", "", 16_699),
    }
    for name, (col, sep, prefix, pinned) in PINNED.items():
        path = si / name
        if not path.exists():
            fail("static-ids", f"{path.relative_to(root)} missing")
            continue
        df = pd.read_csv(path, sep=sep, engine="python")
        if col not in df.columns:
            fail("static-ids", f"{name} has no '{col}' column; the pin cannot be checked")
            continue
        vals = df[col].astype(str)
        if prefix:
            vals = vals[vals.str.startswith(prefix)].str.slice(len(prefix))
        n = int(pd.to_numeric(vals, errors="coerce")
                .isin(WITHDRAWN_NONRECIPE_IDS).sum())
        if n != pinned:
            fail(
                "static-ids",
                f"{name}: {n:,} rows reference a withdrawn recipe, pinned at {pinned:,}. "
                "The synthetic benchmark is declared pinned to the PRE-withdrawal corpus "
                "(TODO_VERIFICATION V9.5); a change to this number means it was partly "
                "regenerated or another withdrawal landed. Reconcile, do not re-pin.",
            )
    notes.append(
        f"static-ids: synthetic_interactions is pinned to the pre-withdrawal corpus - "
        f"{', '.join(f'{v[3]:,} in {k}' for k, v in PINNED.items())}, against "
        f"{len(WITHDRAWN_NONRECIPE_IDS):,} withdrawn recipes. Declared, counted and "
        f"filed as V9.5; not silently tolerated. The pins are absolute row counts, so a "
        f"change to the withdrawal set that touches these files fails the build."
    )



def check_licence_tiers(root: Path) -> None:
    """Report where the CC BY-NC-SA layer sits. Informational since 2026-08-29 (evening).

    This used to FAIL the release if FlavorDB-derived nodes appeared in `data/kg/`, because
    the core graph was deliberately kept free of NonCommercial and ShareAlike obligations.
    That constraint was lifted on instruction: everything is included, and licensing is
    settled at publication with stated limitations.

    So the check no longer blocks — but it still REPORTS, because the consequence is a fact
    about how the licences compose and not a matter of taste:

        FlavorDB is CC BY-NC-SA. Merged into `data/kg/`, NonCommercial and ShareAlike
        propagate to the ENTIRE knowledge graph. A consumer can no longer take the core
        alone and treat it as CC BY 4.0.

    A guard that silently stopped guarding would be worse than no guard, which is why this
    prints the position on every run rather than disappearing.
    """
    import pandas as pd

    nodes = root / "data" / "kg" / "kg_nodes.parquet"
    edges = root / "data" / "kg" / "kg_edges.parquet"
    n_comp = n_edge = 0
    if nodes.exists():
        df = pd.read_parquet(nodes, columns=["node_id", "type"])
        n_comp = int((df["type"] == "compound").sum())
    if edges.exists():
        df = pd.read_parquet(edges, columns=["rel"])
        n_edge = int(df["rel"].isin(["has_compound", "shares_flavor"]).sum())

    if n_comp or n_edge:
        notes.append(
            f"licence-tiers: core carries {n_comp:,} FlavorDB `compound` nodes and "
            f"{n_edge:,} has_compound/shares_flavor edges. data/ was ALREADY CC BY-NC-SA 4.0 "
            "(the 9,384 upstream recipes), so the top-level licence is unchanged -- what is "
            "given up is SEPARABILITY: data/kg/ can no longer be lifted out free of "
            "FlavorDB's 3.0 terms. Intended since 2026-08-29; LICENSE-DATA states it")
    else:
        notes.append("licence-tiers: core is free of FlavorDB-derived nodes and edges")

    flavour_dir = root / "data" / "kg_flavor"
    if flavour_dir.exists() and not (flavour_dir / "LICENSE").exists():
        fail("licence-tiers",
             "data/kg_flavor/ exists without its own LICENSE -- the NC-SA boundary is "
             "unstated, which is worse than not shipping the layer at all")


def check_kg_allergens(root: Path) -> None:
    """C3 — the graph's allergen edges must reconcile with the corpus column.

    Written 2026-08-29 because nothing checked this and the consequence was a fail-open.
    The builder sourced `contains_allergen` from `Allergens_filled`, superseded and carrying
    only 12 of the 16 declared classes, so `coconut` (36,745 rows), `asafoetida` (29,252),
    `fenugreek` (19,909) and `tamarind` (12,148) had NO edges in the published graph at all.
    98,054 allergen labels existed in the corpus and were invisible to every KG consumer.

    Both release gates passed the whole time. They passed because neither looked here.

    Four assertions, each closing one way the defect could return:

      1. every declared class has a node -- catches a source column losing classes
      2. per-class edge counts equal the corpus column exactly -- catches a partial or
         stale rebuild, which a total-only check would miss
      3. `unknown` is representable -- an unassessed recipe must be distinguishable from an
         assessed-and-clean one (Codex CXC 80-2020: never assume an allergen is absent)
      4. the two encodings of (3) agree -- the node flag and the sentinel edge record the
         same fact twice, which is a deliberate redundancy and therefore a drift risk
    """
    kg_nodes = root / "data" / "kg" / "kg_nodes.parquet"
    kg_edges = root / "data" / "kg" / "kg_edges.parquet"
    corpus = root / "data" / "corpus" / "recipes_structured.parquet"
    if not (kg_nodes.exists() and kg_edges.exists() and corpus.exists()):
        notes.append("kg-allergens: skipped, tables not present")
        return

    import collections

    import pandas as pd

    nodes = pd.read_parquet(kg_nodes, columns=["node_id", "type", "name", "allergen_assessed"])
    edges = pd.read_parquet(kg_edges, columns=["head", "rel", "tail"])
    src_col, dst_col = "head", "tail"

    # 1. every declared class present
    graph_classes = set(nodes.loc[nodes["type"] == "allergen", "name"]) - {UNASSESSED_TOKEN}
    missing = DECLARED_ALLERGENS - graph_classes
    if missing:
        fail("kg-allergens",
             f"{len(missing)} declared allergen class(es) have no node in the published "
             f"graph: {sorted(missing)}. This is the A1 defect: a recipe carrying one of "
             "these in the corpus has no edge expressing it, so a filter reads it as safe.")
    unexpected = graph_classes - DECLARED_ALLERGENS
    if unexpected:
        fail("kg-allergens",
             f"allergen node(s) outside the declared 16: {sorted(unexpected)}. Extend the "
             "taxonomy deliberately or fix the source column.")

    # 2. per-class reconciliation against the corpus
    ca = edges[edges["rel"] == "contains_allergen"]
    graph_counts = collections.Counter(
        str(d).split("::", 1)[1] for d in ca[dst_col]
    )
    col = pd.read_parquet(corpus, columns=["Allergens_v2"])["Allergens_v2"]
    corpus_counts: collections.Counter = collections.Counter()
    for cell_value in col.fillna("").astype(str):
        for token in cell_value.split(";"):
            token = token.strip()
            if token and token != "none_detected":
                corpus_counts[token] += 1
    disagree = {
        k: (graph_counts.get(k, 0), corpus_counts.get(k, 0))
        for k in set(graph_counts) | set(corpus_counts)
        if graph_counts.get(k, 0) != corpus_counts.get(k, 0)
    }
    if disagree:
        detail = ", ".join(f"{k}: graph {g:,} vs corpus {c:,}" for k, (g, c) in sorted(disagree.items()))
        fail("kg-allergens",
             f"contains_allergen does not reconcile with Allergens_v2 per class -- {detail}. "
             "A total-only check would hide this; the classes must match one by one.")

    # 3 + 4. `unknown` representable, and the two encodings agree
    sentinel = {str(s) for s in ca.loc[ca[dst_col] == f"allergen::{UNASSESSED_TOKEN}", src_col]}
    flagged = set(nodes.loc[nodes["allergen_assessed"] == False, "node_id"].astype(str))  # noqa: E712
    if not sentinel and not flagged:
        fail("kg-allergens",
             "no recipe is marked unassessed, by either the `allergen_assessed` flag or an "
             f"`allergen::{UNASSESSED_TOKEN}` edge. Unassessed rows exist in the corpus, so "
             "they are being published as indistinguishable from assessed-and-clean.")
    if sentinel != flagged:
        only_edge, only_flag = len(sentinel - flagged), len(flagged - sentinel)
        fail("kg-allergens",
             f"the two unassessed encodings disagree: {only_edge:,} recipe(s) carry the "
             f"sentinel edge but not the flag, {only_flag:,} the reverse. They record one "
             "fact twice and have drifted.")

    notes.append(
        f"kg-allergens: all {len(DECLARED_ALLERGENS)} classes present, "
        f"{int(len(ca)):,} contains_allergen edges reconcile per class with Allergens_v2, "
        f"{len(flagged):,} recipes marked unassessed by both encodings"
    )


def check_disclosure(root: Path) -> None:
    for rel in REQUIRED_ARTEFACTS:
        if not (root / rel).exists():
            fail("disclosure", f"required artefact missing: {rel}")

    # A release must not silently drop the audit findings.
    audit = root / "data" / "corpus" / "ALLERGEN_AUDIT.json"
    if audit.exists():
        data = json.loads(audit.read_text(encoding="utf-8"))
        # CORRECTED 2026-09-02. This note used to read "worst allergen false-negative rate
        # is <x> at <n>% (upper bound)". It was neither the worst nor an upper bound: the
        # rate is computed only over rows the AUDIT lexicon matched, and that lexicon is
        # blind to whole classes. Reporting the highest rate while a class sits at 0%
        # coverage put the reassuring number in the gate output and hid the alarming one.
        # 2026-09-05 (T1): the "28.2%" that stood here could not be reproduced. Both
        # scored pilot files carry 794 rows, not the n=394 it cited, and recomputing
        # from T12_pilot_SCORED_v2.tsv gives 118/320 = 36.88%. Three figures were in
        # circulation and the release published the most favourable of them. What is
        # published now is the positive-stratum result (the only one the sample size
        # supports) plus an explicit withholding of the corpus rate.
        allergens = {a: e for a, e in data.get("allergens", {}).items() if isinstance(e, dict)}
        blind = data.get("known_blind_spots", {})
        uncovered = sorted(
            (
                (a, e.get("audit_lexicon_coverage_of_flagged"),
                 e.get("unaudited_flagged_rows") or 0)
                for a, e in allergens.items()
                if e.get("audit_lexicon_coverage_of_flagged") is not None
                and e["audit_lexicon_coverage_of_flagged"] < 0.6
            ),
            key=lambda x: x[1],
        )
        unaudited_total = sum(e.get("unaudited_flagged_rows") or 0 for e in allergens.values())
        worst = max(
            ((a, e.get("false_negative_rate_of_lexical") or 0) for a, e in allergens.items()),
            key=lambda x: x[1], default=None,
        )
        if worst:
            notes.append(
                f"disclosure: ALLERGEN_AUDIT is a two-lexicon consistency check, NOT an "
                f"accuracy measurement. The held-out T12 pilot (n=794) confirmed "
                f"0 false negatives in 202 positive-stratum rows (95% upper bound 1.87%); "
                f"its raw 36.88% figure is a 50%-hard-negative draw and over-estimates the "
                f"corpus by construction; the corpus-level rate is WITHHELD — it rested on "
                f"10 rows per class. Highest disagreement rate is "
                f"{worst[0]} at {worst[1]:.2%}, computed only over rows the audit lexicon "
                f"matched."
            )
        if uncovered:
            notes.append(
                "disclosure: the audit lexicon covers under 60% of flagged rows for "
                + ", ".join(f"{a} ({c:.0%})" for a, c, _ in uncovered)
                + f" — {unaudited_total:,} flagged rows are not audited at all, so a low "
                  "rate for those classes is not evidence of anything"
            )
        if blind.get("audit_lexicon_blind_on"):
            notes.append(
                f"disclosure: the audit lexicon is blind to "
                f"{blind['audit_lexicon_blind_on']} of {blind.get('of')} known blind-spot "
                f"probes (the foods the R5 pass fixed in the labelling lexicon) — it shares "
                f"the blind spots of the lexicon it is checking"
            )


def check_units(root: Path) -> None:
    """Every dimensioned column must declare its unit where a machine can read it.

    Added 2026-09-02. Before it, 0 of 236 Arrow fields carried metadata and no unit was
    declared anywhere — while `per100g_sodium` (mg) sat beside `per100g_salt` (g) under an
    identical name pattern, 400x apart. This is a hard check, not a note: an undeclared
    numeric column is how that ambiguity got in, and a new one must not be able to ship.
    """
    import pyarrow.parquet as pq

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from column_units import COLUMN_UNITS, undeclared

    NUMERIC = ("double", "int64", "float", "int32", "int16", "float32")
    targets = [
        root / "data" / "corpus" / "recipes_structured.parquet",
        root / "data" / "kg" / "kg_nodes.parquet",
    ]
    total = stamped = 0
    for p in targets:
        if not p.exists():
            continue
        schema = pq.read_schema(p)
        numeric = [n for n, t in zip(schema.names, schema.types) if str(t) in NUMERIC]
        missing = undeclared(numeric)
        total += len(numeric)
        stamped += sum(1 for f in schema if f.metadata and b"unit" in f.metadata)
        if missing:
            fail("units",
                 f"{p.relative_to(root)}: {len(missing)} numeric column(s) declare no unit "
                 f"— {', '.join(missing[:6])}" + (" …" if len(missing) > 6 else ""))
        unstamped = [n for n, f in zip(schema.names, schema)
                     if n in COLUMN_UNITS and not (f.metadata and b"unit" in f.metadata)]
        if unstamped:
            fail("units",
                 f"{p.relative_to(root)}: {len(unstamped)} declared column(s) carry no "
                 f"field metadata — run scripts/stamp_units.py")
    if total:
        notes.append(
            f"units: {stamped} of {total} dimensioned columns carry machine-readable unit "
            f"metadata; docs/UNITS.json is the human-readable registry. Two units remain "
            f"genuinely unresolved and say TBD: Nut_VitaminA (ug RAE vs ug retinol) and "
            f"Nut_Folate (total vs DFE) — both affect DV_* quotients"
        )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=REPO_ROOT)
    ap.add_argument("--strict-checksums", action="store_true")
    args = ap.parse_args()

    print(f"verifying {args.root}\n")
    check_licence(args.root)
    check_integrity(args.root)
    check_pii(args.root)
    check_exclusions(args.root)
    check_static_id_lists(args.root)
    check_units(args.root)
    check_checksums(args.root, args.strict_checksums)
    check_disclosure(args.root)
    check_licence_tiers(args.root)
    check_kg_allergens(args.root)

    for note in notes:
        print(f"  note  {note}")

    if failures:
        print(f"\nFAILED — {len(failures)} problem(s):\n")
        for f in failures:
            print(f"  {f}")
        return 1

    print("\nPASSED — licence, integrity, privacy, checksums, disclosure, kg-allergens")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
