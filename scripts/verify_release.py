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
    EXPECTED_TAXONOMY_HASH,
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
import allergen_taxonomy as _AT  # noqa: E402

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


def check_authorship(root: Path) -> None:
    """`.zenodo.json` and `CITATION.cff` name the same people.

    WHY THIS EXISTS. `.zenodo.json` listed one author while the published 0.3.0 record
    carried three -- the co-authors had been added by hand on Zenodo and never written back
    to the repository. Publishing 0.4.0 regenerated the record from the repo metadata and
    DROPPED THEM, silently, into a permanent DOI. Nothing failed; the release was green.

    Attribution is not a cosmetic field, and a metadata file that disagrees with the record
    it generates is the same class of defect as a count that disagrees with its payload.
    This compares surnames rather than exact strings, because the two formats spell a name
    differently by design (`Dr. Santosh P. Borde` vs family/given plus `name-prefix`).
    """
    zen = root / ".zenodo.json"
    cff = root / "CITATION.cff"
    if not zen.exists() or not cff.exists():
        return
    creators = json.loads(zen.read_text(encoding="utf-8")).get("creators", [])
    if not creators:
        fail("authorship", ".zenodo.json declares no creators")
        return
    # Surname = the longest alphabetic token that is not an honorific or an initial.
    def surnames(names: list[str]) -> set[str]:
        out = set()
        for n in names:
            toks = [t.strip(".,") for t in re.split(r"[,\s]+", n) if t.strip(".,")]
            toks = [t for t in toks if t.lower() not in {"dr", "prof", "mr", "ms", "mrs",
                                                         "shri", "smt"} and len(t) > 1]
            if toks:
                # By POSITION, not by length. "Hemprasad Y. Badgujar" picks "Hemprasad" on a
                # longest-token rule, which is exactly how the first version of this check
                # failed. `Family, Given` -> before the comma; `Given M. Family` -> last.
                out.add((toks[0] if "," in n else toks[-1]).lower())
        return out

    zen_names = surnames([c.get("name", "") for c in creators])
    cff_text = cff.read_text(encoding="utf-8")
    cff_names = {m.lower() for m in re.findall(r"^\s*-?\s*family-names:\s*\"?([^\"\n]+)\"?",
                                               cff_text, re.M)}
    cff_names = {n.strip().lower() for n in cff_names}

    if zen_names != cff_names:
        fail("authorship",
             f".zenodo.json and CITATION.cff name different people — "
             f"only in .zenodo.json: {sorted(zen_names - cff_names) or 'none'}; "
             f"only in CITATION.cff: {sorted(cff_names - zen_names) or 'none'}. "
             f"The published record is generated from .zenodo.json, so a disagreement here "
             f"means the DOI will credit a different author list than the repository does.")
        return
    missing_aff = [c.get("name") for c in creators if not c.get("affiliation")]
    if missing_aff:
        notes.append(f"authorship: {len(creators)} creators agree across .zenodo.json and "
                     f"CITATION.cff; {len(missing_aff)} carry no affiliation ({', '.join(missing_aff)})")
    else:
        notes.append(f"authorship: {len(creators)} creators, agreeing across .zenodo.json and "
                     f"CITATION.cff, all with affiliations — "
                     f"{', '.join(c['name'] for c in creators)}")


def check_metadata_figures(root: Path) -> None:
    """No large number in the citation metadata may contradict the payload.

    `.zenodo.json`'s description and `CITATION.cff`'s abstract are the text a reader sees
    FIRST -- on the Zenodo landing page, in the citation, in every index that harvests the
    record -- and neither is regenerated by anything. Both spent 0.4.0 and 0.4.1 describing
    220,187 recipes, 223,406 nodes, 6,270,560 edges and a 68-query benchmark, none of which
    had been true for three releases, and the DOI carries that text permanently.

    The rule is deliberately mechanical rather than clever: every comma-formatted integer of
    four digits or more in that prose must be a figure the payload actually has. Small
    numbers (17 node types, 42-nutrient schema) are left alone -- they are not counts of
    rows and do not go stale the same way.
    """
    allowed = {
        f"{EXPECTED_RECIPES:,}", f"{EXPECTED_KG_NODES:,}", f"{EXPECTED_KG_EDGES:,}",
        f"{len(all_withdrawn_ids()):,}",
        # Figures that legitimately appear and are not payload counts.
        "50,000",       # synthetic users
        "990,273",      # synthetic ratings
        "9,384",        # retained upstream NC/NC-SA recipes
        "214,579", "4,807",   # rehydratable split
        "1,274",        # unassessed recipes
    }
    for rel in (".zenodo.json", "CITATION.cff"):
        p = root / rel
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        for num in set(re.findall(r"\b\d{1,3}(?:,\d{3})+\b", text)):
            if num not in allowed:
                fail("metadata-figures",
                     f"{rel} states '{num}', which is not a current payload figure. The "
                     f"citation text is what a reader sees first and the DOI carries it "
                     f"permanently, so a stale count here outlives the release that made "
                     f"it. Current: {EXPECTED_RECIPES:,} recipes, {EXPECTED_KG_NODES:,} "
                     f"nodes, {EXPECTED_KG_EDGES:,} edges.")
    if not any(f.startswith("[metadata-figures]") for f in failures):
        notes.append("metadata-figures: every large number in .zenodo.json and CITATION.cff "
                     "matches the payload")


def check_taxonomy_vendored() -> None:
    """The allergen taxonomy this checkout actually imported is the one it should have.

    Self-contained ON PURPOSE. Gate M27 compares the canonical file to its copies, but that
    needs both visible at once and so only runs on the authoring machine. This compares the
    imported payload to a digest pinned in `release_config.py`, which works on a clone that
    has never seen the datasets root -- a reviewer's, CI's, or a Zenodo depositor's.

    Until 2026-09-06 the import itself could not succeed off this machine at all, so nothing
    downstream of it had ever run anywhere else.
    """
    got = _AT.source_hash()
    if got != EXPECTED_TAXONOMY_HASH:
        fail("taxonomy",
             f"allergen taxonomy payload hash {got} != pinned {EXPECTED_TAXONOMY_HASH}. The "
             f"vendored copy has drifted from the canonical file, or the taxonomy changed "
             f"without the pin moving — run `_admin/scripts/gen_release_taxonomy.py`.")
        return
    notes.append(f"taxonomy: {len(_AT.TOKENS)} tokens, payload hash {got}, matches the pin — "
                 f"verified without needing the datasets root")


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

    `check_exclusions` above scans published *.parquet. `data/interactions/` is plain text
    and CSV, so it was outside every scan -- and after the V7 withdrawal (2026-09-01) its
    predecessor still referenced recipes that had left the corpus. All three gate suites were
    green while it did. That is the failure mode CLAUDE.md names: a gate that does not cover
    the path that broke.

    This check is COLUMN-AWARE on purpose. A regex sweep for withdrawn ids over these files
    reports `user_list.txt` and `train.txt` as offenders, which is wrong -- those hold user
    ids and REMAPPED ids that merely collide numerically with a recipe id. Only the columns
    named below actually carry a `recipe_id`.

    THE PINS ARE GONE, AND THAT IS THE POINT (2026-09-12, v0.7.0).

    This check used to DECLARE two directories as pinned to the pre-withdrawal corpus at
    exactly 385 / 385 / 20,161 and 12 / 12 / 1,087 withdrawn references. The justification
    was that `gen.py` hardcoded `/mnt/user-data/uploads/...` and so could not be re-run, and
    that regenerating would invalidate the published `baseline_results.json`. Both premises
    have been retired: `scripts/build_interactions.py` regenerates the set from the PUBLISHED
    corpus with no machine-specific path, and `scripts/build_interaction_baselines.py`
    recomputes the baselines against it.

    So the expected count is ZERO, not a declared number. A pinned nonzero count can only
    ever assert "this artefact is stale in exactly the way we already knew"; zero asserts
    that the artefact and the corpus agree. Generating from `data/corpus/` makes that true
    by construction rather than by audit, and the generator refuses to write its output if
    the audit does not come back clean.
    """
    si = root / "data" / "interactions"
    if not si.exists():
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
    #
    # Tested against `all_withdrawn_ids()`, never one population. The 2026-09-06 version used
    # `WITHDRAWN_NONRECIPE_IDS` -- V7 only -- while the registry existed precisely so a
    # population could not be added without every consumer seeing it, and it missed 70 / 70 /
    # 3,462 V8 grihshobha references as a direct result. The registry is the whole set or the
    # check is worth nothing.
    withdrawn_all = set(all_withdrawn_ids())
    EXPECTED = {
        "interactions": {
            "item_list.txt": ("org_id", r"\s+", "", 0),
            "entity_list.txt": ("org_id", r"\s+", "item:", 0),
            "interactions.csv": ("recipe_id", ",", "", 0),
        },
    }
    for subdir, files in EXPECTED.items():
        base = root / "data" / subdir
        if not base.exists():
            continue
        for name, (col, sep, prefix, pinned) in files.items():
            path = base / name
            if not path.exists():
                fail("static-ids", f"{path.relative_to(root)} missing")
                continue
            # Hand-parsed rather than read_csv: v3's entity_list.txt has a row with an extra
            # field, which makes the python engine raise ParserError and would take the whole
            # check down over one malformed line.
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            if not lines:
                fail("static-ids", f"{subdir}/{name} is empty")
                continue
            header = re.split(sep, lines[0].strip())
            if col not in header:
                fail("static-ids",
                     f"{subdir}/{name} has no '{col}' column; the pin cannot be checked")
                continue
            idx = header.index(col)
            n = 0
            for line in lines[1:]:
                parts = re.split(sep, line.strip())
                if len(parts) <= idx:
                    continue
                v = parts[idx]
                if prefix:
                    if not v.startswith(prefix):
                        continue
                    v = v[len(prefix):]
                try:
                    if int(v) in withdrawn_all:
                        n += 1
                except ValueError:
                    continue
            if n != pinned:
                fail(
                    "static-ids",
                    f"{subdir}/{name}: {n:,} rows reference a withdrawn recipe, expected "
                    f"{pinned:,}. The interaction benchmark is generated FROM the published "
                    f"corpus by scripts/build_interactions.py, so a withdrawn id cannot "
                    f"appear unless the artefact is stale or a withdrawal landed after it "
                    f"was built. Regenerate it — do not pin the number.",
                )
    notes.append(
        f"static-ids: data/interactions references ZERO of the {len(withdrawn_all):,} "
        f"withdrawn recipes, across every withdrawal population. This supersedes the v0.6.0 "
        f"declaration, which PINNED two directories at 385 / 385 / 20,161 and 12 / 12 / "
        f"1,087 because their generator hardcoded another machine's paths and could not be "
        f"re-run. scripts/build_interactions.py regenerates from data/corpus/, so agreement "
        f"with the corpus is structural now rather than declared."
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
                f"accuracy measurement. T12 returned labels are a stratified diagnostic; "
                f"zero FN among selected predicted-positive rows does not measure sensitivity. "
                f"Reviewer independence and population weights are unverified; no corpus "
                f"rate is claimed. Highest disagreement rate is "
                f"{worst[0]} at {worst[1]:.2%}, computed only over rows the audit lexicon "
                f"matched."
            )
        # `sulphites` is reported separately from `uncovered`, because lumping them together
        # says the wrong thing. The other classes were under-covered by a fixable defect --
        # the audit patterns were singular and `\b`-anchored, so `\bcashew\b` never matched
        # `cashews`; fixing that on 2026-09-06 took peanut 37%->93%, tree_nuts 45%->93%,
        # shellfish 39%->89%, egg 49%->87%, gluten 53%->75%. `sulphites` is not that: leg B
        # asks whether a recipe DECLARES a sulphite, while leg A labels from a CARRIER rule
        # (vinegar, raisins, wine, dried fruit). A home recipe never names the additive, so
        # the coverage is 0 by construction and will stay 0. Giving leg B a carrier list
        # would make it agree with leg A on leg A's own theory and report that as
        # corroboration, which is worse than reporting nothing.
        structural = [(a, c, n) for a, c, n in uncovered if a == "sulphites"]
        uncovered = [(a, c, n) for a, c, n in uncovered if a != "sulphites"]
        if uncovered:
            notes.append(
                "disclosure: the audit lexicon covers under 60% of flagged rows for "
                + ", ".join(f"{a} ({c:.0%})" for a, c, _ in uncovered)
                + f" — {unaudited_total:,} flagged rows are not audited at all, so a low "
                  "rate for those classes is not evidence of anything"
            )
        for a, _c, n in structural:
            notes.append(
                f"disclosure: {a} is NOT INDEPENDENTLY AUDITABLE from ingredient text and is "
                f"reported as such rather than as 0% coverage. Leg B asks whether the recipe "
                f"declares the additive; leg A labels it from a carrier rule (vinegar, "
                f"raisins, wine, dried fruit), which is where sulphites actually occur. "
                f"Recipes do not name it, so all {n:,} flagged rows are unmatched by "
                f"construction. Adding carriers to leg B would manufacture agreement on leg "
                f"A's own theory — the audit says nothing about this class, deliberately."
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
            f"metadata; docs/UNITS.json is the human-readable registry. The two former TBDs "
            f"are resolved from the builder: Nut_VitaminA is ug RAE (FDC 1106), Nut_Folate is "
            f"TOTAL folate (FDC 1177). DV_Folate is suppressed with an unavailable basis "
            f"and preserved historical values. 2.5% of composition rows use supplemental "
            f"US/UK tables with unstated folate basis"
        )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=REPO_ROOT)
    ap.add_argument("--strict-checksums", action="store_true")
    args = ap.parse_args()

    print(f"verifying {args.root}\n")
    check_licence(args.root)
    check_integrity(args.root)
    from benchmark_contract import validate_benchmark
    for problem in validate_benchmark(args.root):
        fail('benchmark-version', problem)
    from interactions_contract import validate_interactions
    interaction_problems = validate_interactions(args.root)
    for problem in interaction_problems:
        fail('interactions', problem)
    if not interaction_problems:
        notes.append("interactions: id maps injective, item/entity namespaces agree, KG and "
                     "both splits resolve, no train/test overlap, every referenced recipe "
                     "live and none withdrawn, and no restricted-diet user served an "
                     "incompatible or undeclared recipe")
    from split_contract import validate_release_splits
    try:
        split_problems = validate_release_splits(args.root)
    except (KeyError, ValueError, OSError) as exc:
        split_problems = [f"cannot validate canonical split: {exc}"]
    for problem in split_problems:
        fail("split-v3", problem)
    if not split_problems:
        notes.append("split-v3: graph and both corpus views agree by recipe ID; no case-folded title or duplicate-family boundary crossings")
    check_pii(args.root)
    check_exclusions(args.root)
    check_static_id_lists(args.root)
    check_units(args.root)
    check_authorship(args.root)
    check_metadata_figures(args.root)
    check_taxonomy_vendored()
    check_checksums(args.root, args.strict_checksums)
    check_disclosure(args.root)
    from build_release_facts import check as check_current_facts
    for stale_path in check_current_facts(args.root):
        fail("release-facts", f"{stale_path} differs from current payload; run scripts/build_release_facts.py")
    check_licence_tiers(args.root)
    check_kg_allergens(args.root)
    from edge_evidence import validate_release_evidence
    try:
        evidence_problems = validate_release_evidence(args.root)
    except (KeyError, ValueError, OSError) as exc:
        evidence_problems = [f"cannot validate edge evidence: {exc}"]
    for problem in evidence_problems:
        fail("edge-evidence", problem)
    if not evidence_problems:
        notes.append("edge-evidence: unique typed-triple keys, valid JSON attributes, all assertions reference live triples")
    from source_recovery_contract import validate_release_source_recovery
    for problem in validate_release_source_recovery(args.root):
        fail('source-recovery', problem)
    from allergen_tier_contract import validate_release_tiers
    for problem in validate_release_tiers(args.root):
        fail('allergen-tiers', problem)
    from nutrition_contract import validate_release_nutrition_alias, validate_release_folate
    nutrition_problems = validate_release_nutrition_alias(args.root)
    for problem in nutrition_problems:
        fail("nutrition-provenance", problem)
    if not nutrition_problems:
        notes.append("nutrition-provenance: canonical supplemental FCT calorie fraction agrees across wide and quality tables")
    for problem in validate_release_folate(args.root):
        fail('folate-basis', problem)
    from flavor_contract import validate_release_flavor
    flavor_problems = validate_release_flavor(args.root)
    for problem in flavor_problems:
        fail("flavor-contract", problem)
    if not flavor_problems:
        notes.append("flavor-contract: CID identities, crosswalk ambiguity and optional tables reproduce from core evidence")

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
