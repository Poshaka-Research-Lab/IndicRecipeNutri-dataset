"""Independent allergen and diet audit over the released corpus.

The allergen flags in `allergens_v8` are produced by the same labelling pass that the
diet labels and the benchmark gold sets come from. Checking any of them against the
others therefore measures internal consistency, not correctness. This script provides
the independent leg: it matches the *parsed ingredient list* against an allergen
ingredient lexicon and reports where the flag disagrees.

Two directions are reported and they are not symmetric. Per the workspace guardrail on
allergen handling, a false negative — allergen present in the ingredients, flag says
absent — is the direction that matters and is reported as the headline. A false
positive is recorded but is an acceptable cost.

Lexicon hits are review candidates, not confirmed defects; an ingredient lexicon
over-fires and the negative-phrase list that suppresses plant substitutes is not
exhaustive. Every rate below is therefore an upper bound on the defect, and the
sampled examples are given so a reader can judge the precision themselves.

Usage:  python scripts/audit_corpus.py [--out PATH]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from release_config import (  # noqa: E402
    LEXICAL_EVIDENCE,
    NEGATIVE,
    REPO_ROOT,
)

# Diet labels that are incompatible with a dairy or egg ingredient.
DIET_CONFLICTS = {
    "Vegan": ["milk", "egg", "fish", "shellfish"],
    "Vegetarian": ["fish", "shellfish"],
    "Eggetarian": ["fish", "shellfish"],
}


def lexical_mask(text: pd.Series, allergen: str) -> pd.Series:
    """True where the ingredient text names the allergen, after stripping negatives."""
    pattern = LEXICAL_EVIDENCE[allergen]
    negative = NEGATIVE.get(allergen)
    cleaned = (
        text.str.replace(negative, " ", case=False, regex=True) if negative else text
    )
    return cleaned.str.contains(pattern, case=False, regex=True, na=False)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=REPO_ROOT / "data" / "corpus")
    args = ap.parse_args()

    corpus = pd.read_parquet(
        REPO_ROOT / "data" / "corpus" / "recipes_structured.parquet",
        columns=["recipe_id", "RecipeName", "Diet", "IngredientsList"],
    )
    allergens = pd.read_parquet(REPO_ROOT / "data" / "enrichment" / "allergens_v8.parquet")
    df = corpus.merge(allergens, on="recipe_id", how="left")
    text = df["IngredientsList"].fillna("")

    report: dict = {
        "method": (
            "The parsed IngredientsList is matched against an allergen ingredient "
            "lexicon after removing plant-substitute phrasings (e.g. 'almond milk', "
            "'peanut butter'). The result is compared with the has_<allergen> flag in "
            "allergens_v8. Lexicon hits are review candidates, not confirmed defects, "
            "so every rate is an upper bound."
        ),
        "asymmetry": (
            "False negatives (ingredient present, flag absent) are the direction that "
            "matters for allergen safety and are reported as the headline. False "
            "positives are recorded but are an acceptable cost."
        ),
        "corpus_rows": int(len(df)),
        "allergens": {},
        "diet_conflicts": {},
    }

    print(f"corpus: {len(df):,} rows\n")
    print(f"{'allergen':<12} {'lexical':>9} {'flagged':>9} {'FN':>7} {'FN rate':>9}")
    print("-" * 50)

    for allergen in sorted(LEXICAL_EVIDENCE):
        col = f"has_{allergen}"
        if col not in df.columns:
            report["allergens"][allergen] = {"note": f"no column {col}"}
            continue

        lex = lexical_mask(text, allergen)
        flag = df[col].fillna(False).astype(bool)
        fn = lex & ~flag
        fp = flag & ~lex

        examples = df.loc[fn, ["recipe_id", "RecipeName"]].head(15)
        entry = {
            "lexical_present": int(lex.sum()),
            "flagged_present": int(flag.sum()),
            "false_negatives": int(fn.sum()),
            "false_negative_rate_of_lexical": (
                round(int(fn.sum()) / int(lex.sum()), 4) if lex.sum() else None
            ),
            "false_positives_flag_only": int(fp.sum()),
            "false_negative_examples": [
                {"recipe_id": int(r.recipe_id), "name": str(r.RecipeName)}
                for r in examples.itertuples()
            ],
        }
        report["allergens"][allergen] = entry
        rate = entry["false_negative_rate_of_lexical"]
        print(
            f"{allergen:<12} {entry['lexical_present']:>9,} {entry['flagged_present']:>9,} "
            f"{entry['false_negatives']:>7,} {rate:>8.2%}" if rate is not None else
            f"{allergen:<12} {entry['lexical_present']:>9,} {entry['flagged_present']:>9,} "
            f"{entry['false_negatives']:>7,} {'n/a':>9}"
        )

    # ------------------------------------------------------------- diet conflicts
    print(f"\n{'diet':<14} {'rows':>9} {'conflicting':>12} {'rate':>8}  conflicting ingredient")
    print("-" * 68)
    for diet, forbidden in DIET_CONFLICTS.items():
        in_diet = df["Diet"].eq(diet)
        if not in_diet.any():
            continue
        per_allergen = {}
        any_conflict = pd.Series(False, index=df.index)
        for allergen in forbidden:
            if allergen not in LEXICAL_EVIDENCE:
                continue
            conflict = in_diet & lexical_mask(text, allergen)
            per_allergen[allergen] = int(conflict.sum())
            any_conflict |= conflict

        examples = df.loc[any_conflict, ["recipe_id", "RecipeName", "Diet"]].head(15)
        report["diet_conflicts"][diet] = {
            "rows_with_label": int(in_diet.sum()),
            "conflicting_rows": int(any_conflict.sum()),
            "rate": round(int(any_conflict.sum()) / int(in_diet.sum()), 4),
            "by_allergen": per_allergen,
            "examples": [
                {"recipe_id": int(r.recipe_id), "name": str(r.RecipeName)}
                for r in examples.itertuples()
            ],
        }
        rate = report["diet_conflicts"][diet]["rate"]
        detail = ", ".join(f"{k}={v:,}" for k, v in per_allergen.items())
        print(
            f"{diet:<14} {int(in_diet.sum()):>9,} {int(any_conflict.sum()):>12,} "
            f"{rate:>7.2%}  {detail}"
        )

    out = args.out / "ALLERGEN_AUDIT.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nwrote    {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
