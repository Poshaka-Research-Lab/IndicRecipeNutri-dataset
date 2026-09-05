#!/usr/bin/env python3
"""L3 - semantic PII scan over the PUBLISHED text, with a run artefact.

The paper states a PII pass removed author names and personal anecdotes. Pattern-based
redaction (email / phone / card) runs in build_corpus.py and is evidenced. The semantic
half had no artefact, which is what this produces.

Two facts shape the scope, and the first one does most of the work:

1. **Personal anecdotes are not published at all.** build_corpus.py drops the five prose
   columns (Description, Instructions, Ingredients, Keywords, Enrich_Log). Anecdotes live
   in prose, so the risk is structurally removed rather than mitigated -- there is nothing
   to scan. Only a rehydrating user re-fetching the source page sees them, and at that
   point they are reading the publisher's own page under the publisher's own terms.

2. **Names survive in `RecipeName`**, which IS published: "Vijay's Favourite Paneer Sabzi",
   "Amma's Sambar". These are a genuine residue.

The distinction that matters for whether a name is personal data here:

   a public figure's name attached to their own published recipe (a cookbook author,
   a site owner) is attribution, not a privacy problem -- and section 3.5 REQUIRES
   per-recipe source attribution.

   a private individual named in a title ("my neighbour Sunita's pickle") is different.

This script does not attempt to make that call automatically. It surfaces candidates with
enough context for a human to, and writes the counts either way so the claim in the paper
can be checked instead of trusted.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Possessive constructions are the realistic carrier of a personal name in a recipe title.
POSSESSIVE = re.compile(r"\b([A-Z][a-z]{2,15})(?:'s|'S|â€™s|’s)\b")

# Kinship terms are the strongest signal of a PRIVATE individual rather than a brand.
KINSHIP = re.compile(
    r"\b(amma|ammas|maa|mom|mum|mummy|nani|dadi|aji|patti|thatha|paati|"
    r"grandma|grandmother|mother|aunt|aunty|chachi|mami|bhabhi|didi)\b", re.I)

# Names that are the SITE or a published author -- attribution, not PII.
KNOWN_PUBLISHERS = {
    "sanjeev", "kapoor", "nisha", "madhulika", "tarla", "dalal", "hebbar", "hebbars",
    "archana", "manjula", "raks", "kamala", "vahchef", "bhavna", "nishamadhulika",
    "ranveer", "brar", "kunal", "kapur", "vikas", "khanna", "madhur", "jaffrey",
}


def main() -> int:
    src = REPO / "data" / "corpus" / "recipes_structured.parquet"
    print(f"reading {src}")
    df = pd.read_parquet(src)
    print(f"  {len(df):,} rows x {df.shape[1]} cols")

    text_cols = [c for c in df.columns if df[c].dtype == object]
    print(f"  object columns published: {len(text_cols)}")

    prose = {"Description", "Instructions", "Ingredients", "Keywords", "Enrich_Log"}
    still = sorted(prose & set(df.columns))
    print(f"  prose columns still present: {still or 'NONE (dropped at build time)'}")

    titles = df["RecipeName"].fillna("").astype(str)
    poss = titles.str.extract(POSSESSIVE, expand=False)
    has_poss = poss.notna()
    kin = titles.str.contains(KINSHIP, regex=True, na=False)

    cand = poss.dropna().str.lower()
    known = cand.isin(KNOWN_PUBLISHERS)

    print(f"\npossessive name in RecipeName : {int(has_poss.sum()):,}")
    print(f"  of those, a known publisher : {int(known.sum()):,}  (attribution, not PII)")
    print(f"  remaining candidates        : {int((~known).sum()):,}")
    print(f"kinship term in RecipeName    : {int(kin.sum()):,}")

    top = cand[~known].value_counts().head(20)
    print("\ntop non-publisher possessive tokens:")
    for name, c in top.items():
        print(f"   {name:<18} {c:>6,}")

    sample = df.loc[has_poss & ~df.index.isin(cand[known].index), ["recipe_id", "RecipeName"]].head(25)
    print("\n25 candidate titles for human review:")
    for _, r in sample.iterrows():
        print(f"   {str(r['RecipeName'])[:70]}")

    report = {
        "scanned_rows": int(len(df)),
        "prose_columns_present": still,
        "prose_columns_withheld": sorted(prose),
        "possessive_name_titles": int(has_poss.sum()),
        "known_publisher_titles": int(known.sum()),
        "review_candidates": int((~known).sum()),
        "kinship_term_titles": int(kin.sum()),
        "top_tokens": {k: int(v) for k, v in top.items()},
        "note": (
            "Anecdotes are not published: the five prose columns are dropped at build "
            "time, so the semantic PII surface is RecipeName plus structured fields "
            "only. A publisher's own name on their own recipe is attribution and is "
            "required by section 3.5; a private individual's is not. This scan does not "
            "make that call automatically and the candidate list needs human review."
        ),
    }
    out = REPO / "data" / "corpus" / "PII_SEMANTIC_SCAN.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
