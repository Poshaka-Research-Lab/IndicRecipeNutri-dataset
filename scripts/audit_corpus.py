r"""Second-lexicon consistency check over the released corpus. NOT an accuracy measurement.

⚠️ CORRECTED 2 September 2026. This file previously called itself "the independent leg"
and described every rate it printed as "an upper bound on the defect". Both claims were
wrong, and in the dangerous direction: they made a corpus whose held-out pilot found a
36.88% raw false-negative rate publish per-class false-negative rates of 0.02%–0.2%.

WHAT IT ACTUALLY DOES
    It re-scans `IngredientsList` with a SECOND term list (`LEXICAL_EVIDENCE` in
    release_config.py) and reports where that disagrees with the shipped flags, which came
    from a FIRST term list (lexicons/allergen_lexicon_v14.py). Two term lists, written by
    the same author from the same intuitions. Where they agree, this file reports zero
    defects — including where they are both wrong.

WHY THAT IS NOT INDEPENDENCE — demonstrated, not asserted
    On 2 September 2026 the R5 pass fixed eight concrete blind spots in the first lexicon.
    Every one of them is ALSO invisible to the second lexicon used here:

        chestnut (a FALCPA tree nut)      -> BLIND       spelt, farro, kamut, einkorn -> BLIND
        mava / kova (khoya spellings)     -> BLIND       oyster mushroom (a false +ve) -> BLIND

    Before R5, 93 corpus rows named chestnut and carried no tree-nut label. This audit
    reported the tree_nuts false-negative rate as 0.0002. It was not an upper bound on
    anything; it was the rate at which two lists that share a blind spot notice each other.
    `known_blind_spots` in the emitted JSON re-runs that probe on every build, so the file
    states its own blindness instead of leaving a reader to discover it.

T12 DIAGNOSTIC -- CORRECTED 2026-09-12
    The returned pilot contains 794 rows: TP 202, FP 38, FN 118, TN 433,
    and 3 unclear. The predicted-positive stratum has 240 rows, not 202.
    Its zero false negatives follow from selection on predicted presence;
    they cannot establish sensitivity or a false-negative confidence bound.
    Raw FNR 118/320 is conditional on this draw and these returned labels.
    Reviewer independence and population inclusion weights are not established.
    No corpus-wide rate or direction of bias is inferred.

BOTH DIRECTIONS COST SOMETHING
    A false negative is the catastrophic direction and stays the headline. But this file
    used to say false positives are "an acceptable cost", which the workspace guardrail
    explicitly qualified on 28 August 2026: at per-user volume they are not free — the
    medication-safety literature reports 85–98% override rates, and an alerting channel
    people learn to dismiss inverts the safety mechanism. R5 removed 55 recipes wrongly
    labelled `shellfish` because `oyster mushroom` matched `oysters?`; one was a vegan soup.

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
    SOURCE_ROOT,
)
import allergen_surface  # noqa: E402

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


# The eight blind spots the R5 pass fixed in the LABELLING lexicon on 2026-09-02. Each is a
# real food that the labelling lexicon could not see; the point of re-testing them here is
# that the AUDIT lexicon cannot see them either, so this file reported a false-negative rate
# of ~0 for exactly the rows that carried the defect. Re-run on every build so the claim
# stays measured rather than remembered — and so that fixing LEXICAL_EVIDENCE later shows up
# here as the count falling, rather than being silently forgotten.
BLIND_SPOT_PROBE = [
    ("tree_nuts", "1 cup Chestnuts (Roasted)", "Castanea is a FALCPA tree nut"),
    ("tree_nuts", "2 cups chestnuts", "same"),
    ("gluten", "whole grain spelt flour", "spelt is wheat"),
    ("gluten", "pearled farro", "farro is wheat"),
    ("gluten", "1 cup kamut", "kamut is wheat"),
    ("gluten", "einkorn flour", "einkorn is wheat"),
    ("milk", "Kova/Mava(unsweetened) 300 gm", "mava/kova are khoya spellings"),
    ("shellfish", "250 grams Oyster Mushrooms", "FALSE-POSITIVE direction: a fungus"),
]


def blind_spot_probe() -> list[dict]:
    """Does the AUDIT lexicon see the foods the labelling lexicon was blind to?"""
    out = []
    for allergen, text, note in BLIND_SPOT_PROBE:
        sees = bool(lexical_mask(pd.Series([text]), allergen).iloc[0])
        out.append({
            "allergen": allergen, "text": text, "note": note,
            "audit_lexicon_blind": not sees,
        })
    return out


def t12_diagnostic():
    """Recompute the diagnostic from returned labels, keeping input identities."""
    import hashlib
    import importlib.util
    helper = SOURCE_ROOT / 'data/lexicons/t12_scoring_contract.py'
    spec = importlib.util.spec_from_file_location('t12_release_scoring', helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    folder = helper.parent / 'T12'
    returned = folder / 'T12_pilot_RETURNED.tsv'
    key = folder / 'T12_pilot_800_WITH_KEY.tsv'
    annotations = pd.read_csv(returned, sep='\t', keep_default_na=False)
    labels = pd.read_csv(key, sep='\t', keep_default_na=False)
    report, pairs = module.score_tables(annotations, labels)
    report['positive_stratum_n'] = int(labels.stratum.eq('positive').sum())
    report['positive_stratum_interpretation'] = (
        'Selection on predicted presence precludes false negatives in this stratum; '
        'zero FN here is not a sensitivity estimate or confidence bound.')
    report['inputs'] = {str(p.relative_to(SOURCE_ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in (returned, key, helper)}
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=REPO_ROOT / "data" / "corpus")
    args = ap.parse_args()

    corpus = pd.read_parquet(
        REPO_ROOT / "data" / "corpus" / "recipes_structured.parquet",
        columns=["recipe_id", "RecipeName", "Diet", "IngredientsList"],
    )
    # D-4, 2026-09-04: the release has ONE allergen surface. See allergen_surface.py.
    allergens = allergen_surface.load_wide(REPO_ROOT)
    df = corpus.merge(allergens, on="recipe_id", how="left")
    text = df["IngredientsList"].fillna("")

    blind = blind_spot_probe()
    n_blind = sum(1 for b in blind if b["audit_lexicon_blind"])

    report: dict = {
        "WHAT_THIS_IS_NOT": (
            "NOT an accuracy measurement, and the rates below are NOT upper bounds on the "
            "allergen defect. This is a consistency check between two term lists written by "
            "the same author. Where both are blind to the same food it reports zero defects. "
            "For the returned-label diagnostic and its limits see T12_MEASURED below."
        ),
        "T12_MEASURED": t12_diagnostic(),
        "method": (
            "The parsed IngredientsList is re-scanned with LEXICAL_EVIDENCE (release_config"
            ".py) after removing plant-substitute phrasings (e.g. 'almond milk', 'peanut "
            "butter'), and compared with the has_<allergen> flag derived from "
            "data/corpus/allergens.parquet, which came "
            "from lexicons/allergen_lexicon_v14.py. Disagreement between the two lists is "
            "what is counted. Agreement is NOT evidence of correctness."
        ),
        "known_blind_spots": {
            "probe": "the eight blind spots the R5 pass fixed in the labelling lexicon on "
                     "2026-09-02, re-tested here against the AUDIT lexicon on every build",
            "audit_lexicon_blind_on": n_blind,
            "of": len(blind),
            "detail": blind,
            "reading": "every case this audit is blind to is a case where it will report a "
                       "false-negative rate of zero while the corpus carries the defect",
        },
        "asymmetry": (
            "A false negative (ingredient present, flag absent) is the catastrophic "
            "direction and is the headline. False positives are NOT free: per the workspace "
            "guardrail as qualified 2026-08-28, at per-user volume they train a user to "
            "dismiss the channel (85-98% override rates in the medication-safety "
            "literature), which inverts the safety mechanism. R5 removed 55 recipes wrongly "
            "labelled shellfish on `oyster mushroom`, one of them a vegan soup."
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
            # How much of the labelled population this audit's own lexicon can even SEE.
            # `false_negative_rate_of_lexical` is a rate over the rows this lexicon matched,
            # so it says nothing about the rows it cannot match at all. When coverage is far
            # below 1.0 the near-zero FN rate is measuring a narrow slice, and at 0.0 the
            # class is entirely unaudited while still printing a clean-looking row.
            "audit_lexicon_coverage_of_flagged": (
                round(int((lex & flag).sum()) / int(flag.sum()), 4) if flag.sum() else None
            ),
            "unaudited_flagged_rows": int((flag & ~lex).sum()),
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
    out.write_text(json.dumps(report, indent=2) + '\n', encoding="utf-8", newline='\n')
    print(f"\nwrote    {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
