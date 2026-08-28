"""Stage the retrieval benchmark and the synthetic interaction log.

The benchmark is the 66-query silver set with knowledge-graph-derived gold sets. Its
gold sets are templated from the KG, which is the mechanism a prior audit found could
admit contradictory members into an allergen-free gold set. This script therefore does
not merely copy the file: it recomputes a contamination report for every constraint
query and writes it alongside, so the defect is visible in the release rather than
discovered by a reader.

The synthetic interaction log is copied wholesale; it is synthetic, so no licence or
PII question arises, but its datasheet travels with it.

Usage:  python scripts/build_benchmark.py [--out PATH]
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from release_config import (  # noqa: E402
    BENCH_SYNTH_DIR,
    LEXICAL_EVIDENCE,
    NEGATIVE,
    EXPECTED_BENCHMARK_QUERIES,
    REPO_ROOT,
    RETRIEVAL_DIR,
)

SYNTH_FILES = [
    "interactions.csv",
    "users.csv",
    "kg_final.txt",
    "train.txt",
    "test.txt",
    "user_list.txt",
    "item_list.txt",
    "entity_list.txt",
    "relation_list.txt",
    "stats.json",
    "baseline_results.json",
    "DATASHEET.md",
    "DISTRIBUTION_REPORT.md",
    "gen.py",
    "baselines.py",
]

# "<Diet> recipes without <allergen>" — the query family whose gold sets are derived
# from the allergen columns and are therefore auditable for contradiction.
CONSTRAINT_RE = re.compile(r"^(?P<diet>.+?) recipes without (?P<allergen>\w+)$")

# Allergen token in the query -> the boolean column in allergens_v8 that contradicts it.
ALLERGEN_COLUMN = {
    "milk": "has_milk",
    "gluten": "has_gluten",
    "mustard": "has_mustard",
    "tree_nuts": "has_tree_nuts",
    "sesame": "has_sesame",
    "peanut": "has_peanut",
    "soy": "has_soy",
    "fish": "has_fish",
    "shellfish": "has_shellfish",
    "egg": "has_egg",
    "fenugreek": "has_fenugreek",
    "asafoetida": "has_asafoetida",
    "tamarind": "has_tamarind",
    "coconut": "has_coconut",
}


def audit_gold_sets(
    queries: list[dict], allergens: pd.DataFrame, corpus: pd.DataFrame
) -> dict:
    """Audit every allergen-constraint gold set on two independent legs.

    Leg A (flag) asks whether the allergen flag contradicts the query. It shares a
    provenance with the gold sets, so it can only detect internal inconsistency.

    Leg B (lexical) asks whether the *parsed ingredient list* names the allergen. It
    is independent of the flags and is the leg that matters. Its hits are candidates
    for review, not confirmed defects: an ingredient lexicon over-fires.
    """
    by_id = allergens.set_index("recipe_id")
    ingredients = corpus.set_index("recipe_id")["IngredientsList"].fillna("")
    names = corpus.set_index("recipe_id")["RecipeName"].fillna("")

    rows, total_gold, total_flag, total_lex = 0, 0, 0, 0
    per_query = []

    for q in queries:
        m = CONSTRAINT_RE.match(q["query"])
        if not m:
            continue
        rows += 1
        allergen = m.group("allergen")
        ids = [int(r.split("::")[1]) for r in q["relevant"] if r.startswith("recipe::")]

        entry: dict = {"query": q["query"], "allergen": allergen, "gold_n": len(ids)}

        col = ALLERGEN_COLUMN.get(allergen)
        if col and col in by_id.columns:
            flag_bad = int(by_id.reindex(ids)[col].fillna(False).astype(bool).sum())
            entry["flag_contradicting"] = flag_bad
            entry["flag_rate"] = round(flag_bad / len(ids), 4) if ids else None
            total_flag += flag_bad
        else:
            entry["flag_contradicting"] = None
            entry["flag_rate"] = None
            entry["note_flag"] = f"no allergen column for '{allergen}'"

        pattern = LEXICAL_EVIDENCE.get(allergen)
        if pattern:
            text = ingredients.reindex(ids).fillna("")
            negative = NEGATIVE.get(allergen)
            if negative:
                # Strip the non-allergen phrasings, then match. Stripping rather than
                # vetoing means a row carrying both "coconut milk" and "panir" is still
                # caught on the panir.
                text = text.str.replace(negative, " ", case=False, regex=True)
            hit = text.str.contains(pattern, case=False, regex=True, na=False)
            lex_ids = [int(i) for i in text.index[hit]]
            entry["lexical_candidates"] = len(lex_ids)
            entry["lexical_rate"] = round(len(lex_ids) / len(ids), 4) if ids else None
            entry["lexical_examples"] = [
                {"recipe_id": i, "name": str(names.get(i, ""))} for i in lex_ids[:10]
            ]
            total_lex += len(lex_ids)
        else:
            entry["lexical_candidates"] = None
            entry["lexical_rate"] = None
            entry["note_lexical"] = f"no ingredient lexicon for '{allergen}'"

        per_query.append(entry)
        total_gold += len(ids)

    return {
        "method": {
            "leg_a_flag": (
                "Each gold-set member is looked up in allergens_v8; it contradicts the "
                "query if the corresponding has_<allergen> flag is true. NOT independent "
                "of the gold sets — both derive from the allergen labelling."
            ),
            "leg_b_lexical": (
                "Each gold-set member's parsed IngredientsList is matched against an "
                "allergen ingredient lexicon, minus plant-substitute phrasings. "
                "Independent of the flags. Hits are review candidates, not confirmed "
                "defects."
            ),
        },
        "queries_audited": rows,
        "gold_entries_audited": total_gold,
        "flag_contradicting_total": total_flag,
        "flag_overall_rate": round(total_flag / total_gold, 4) if total_gold else None,
        "lexical_candidates_total": total_lex,
        "lexical_overall_rate": round(total_lex / total_gold, 4) if total_gold else None,
        "per_query": per_query,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=REPO_ROOT / "data")
    args = ap.parse_args()

    bench_out = args.out / "benchmark"
    synth_out = args.out / "synthetic_interactions"
    bench_out.mkdir(parents=True, exist_ok=True)
    synth_out.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------- benchmark
    src = RETRIEVAL_DIR / "eval_queries.jsonl"
    if not src.exists():
        print(f"FATAL: missing {src}", file=sys.stderr)
        return 1

    queries = [json.loads(line) for line in src.open(encoding="utf-8") if line.strip()]
    if len(queries) != EXPECTED_BENCHMARK_QUERIES:
        print(
            f"FATAL: expected {EXPECTED_BENCHMARK_QUERIES} queries, got {len(queries)}",
            file=sys.stderr,
        )
        return 1

    shutil.copy2(src, bench_out / "eval_queries.jsonl")
    print(f"copied   eval_queries.jsonl  ({len(queries)} queries)")

    allergen_path = REPO_ROOT / "data" / "enrichment" / "allergens_v8.parquet"
    if not allergen_path.exists():
        print(
            "FATAL: run build_enrichment.py first — the gold-set audit needs "
            "allergens_v8.parquet",
            file=sys.stderr,
        )
        return 1

    corpus_path = REPO_ROOT / "data" / "corpus" / "recipes_structured.parquet"
    if not corpus_path.exists():
        print("FATAL: run build_corpus.py first — the lexical leg needs the corpus", file=sys.stderr)
        return 1

    allergens = pd.read_parquet(allergen_path)
    corpus = pd.read_parquet(
        corpus_path, columns=["recipe_id", "RecipeName", "IngredientsList"]
    )
    report = audit_gold_sets(queries, allergens, corpus)
    (bench_out / "GOLD_SET_AUDIT.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )

    print(
        f"audited  {report['queries_audited']} constraint queries, "
        f"{report['gold_entries_audited']:,} gold entries"
    )
    print(
        f"  leg A (flag, not independent): {report['flag_contradicting_total']:,} "
        f"({report['flag_overall_rate']:.2%})"
    )
    print(
        f"  leg B (lexical, independent):  {report['lexical_candidates_total']:,} "
        f"({report['lexical_overall_rate']:.2%})"
    )
    for r in sorted(
        (r for r in report["per_query"] if r["lexical_rate"] is not None),
        key=lambda r: -r["lexical_rate"],
    ):
        print(
            f"    {r['query']:48s} {r['lexical_candidates']:>4}/{r['gold_n']:<4} "
            f"{r['lexical_rate']:6.2%}"
        )

    # -------------------------------------------------------- synthetic interactions
    for name in SYNTH_FILES:
        s = BENCH_SYNTH_DIR / name
        if not s.exists():
            print(f"FATAL: missing {s}", file=sys.stderr)
            return 1
        shutil.copy2(s, synth_out / name)
    total = sum((synth_out / n).stat().st_size for n in SYNTH_FILES)
    print(f"copied   {len(SYNTH_FILES)} synthetic-interaction files ({total / 1e6:.1f} MB)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
