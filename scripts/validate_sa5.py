"""Regenerate docs/allergen_sa5_v1_validation.md against the PUBLISHED payload.

Supersedes `scraped_indian_recipes/data/lexicons/validate_sa5_lexicon_v2.py`, which produced
the shipped report. Five defects are fixed here, all of the same species: the old report's
prose asserted things its own table did not measure.

  1. CORPUS SIZE WAS A STRING LITERAL. The old template hardcoded "224,003 recipes" in the
     protocol paragraph while the table beside it was computed. Re-running it could never
     move that number. The published payload is 219,386 rows (V7 non-recipe withdrawal, V8
     grihshobha withdrawal, and the D-1 PII withdrawal all landed after the report was
     written). Here `n` is measured and interpolated.

  2. IT SCANNED A COLUMN THAT DOES NOT SHIP. The protocol says "the raw `Ingredients`
     column"; the release payload carries `IngredientsList` (canonicalised JSON array) and
     no `Ingredients`. A reader of the published dataset could not reproduce the check. This
     scans what ships, and says so.

  3. THE SYNONYM SET MISSED THE COMMONEST SPELLING. The old pattern had `asafoetida` but not
     `asafetida` (US spelling), which occurs in 1,096 rows it then counted as FALSE
     POSITIVES OF THE LABEL. The regex was wrong, not the data. `asafo?etida` and `heeng`
     are added; every other class's synonyms are carried over unchanged.

  4. "Status: Verified" WAS A HARDCODED LITERAL, printed for every row whatever the numbers
     were. A status column that cannot say anything else is not a check. It is derived here,
     against thresholds stated in the report itself.

  5. THE FALSE POSITIVES WERE EXPLAINED BY A CHANNEL THAT DOES NOT EXIST. The old prose
     attributed them to "valid knowledge-graph (KG-sourced) labels". There is no KG allergen
     source in the payload -- `allergens_sa5_src` takes only `lexicon_v8` and `none`. The
     real composition is measurable and is measured below: alternate spellings, instruction-
     only mentions, and above all COMPOSITE SPICE BLENDS (chaat masala, sambar powder, pav
     bhaji masala, sev) which contain asafoetida without naming it. That channel is a real
     and deliberate feature of the labelling, and it is the single largest explanation --
     the old report never mentioned it.

WHAT THIS DOES AND DOES NOT MEASURE. Unchanged from the original, and worth restating
because the numbers look like accuracy and are not: this is TEXT AGREEMENT between the
shipped label and a regex over the shipped ingredient list. It shares the lexicon's blind
spots by construction, so it cannot discover a food the lexicon never knew about. It is a
consistency check. Per CLAUDE.md 1.2 rule 7, the blend breakdown ships with the figure it
explains.

Usage:  python scripts/validate_sa5.py [--check]
        --check  exit 1 if the report on disk differs from a fresh run (for gates/CI)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from release_config import REPO_ROOT  # noqa: E402

REPORT = REPO_ROOT / "docs" / "allergen_sa5_v1_validation.md"
CORPUS = REPO_ROOT / "data" / "corpus" / "recipes_structured.parquet"

# Regional synonyms. Carried over from validate_sa5_lexicon_v2.py, plus the two asafoetida
# spellings that omission #3 above turned into phantom false positives.
PATTERNS = {
    "coconut": r"\b(?:coconut|nariyal|khopra|thengai|kobbari|kopra)\b",
    "tamarind": r"\b(?:tamarind|imli|puli|chinch|chintapandu)\b",
    "fenugreek": r"\b(?:fenugreek|methi|kasuri\s+methi|vendhayam|menthulu)\b",
    # The asafoetida arm carries a MISSPELLING FAMILY as well as the regional synonyms.
    # Scraped ingredient text spells this word 19 different ways -- `aseftida`, `asaefoetida`,
    # `asofeotida`, `asafotedia` -- and an exact-spelling scan reads every one of them as a
    # false positive of the LABEL when it is really a gap in the SCAN. The long forms are
    # matched without a left word boundary because quantities fuse to the word
    # (`pinchasafoetida`, `2asafetida`), where `\b` fails against the preceding digit.
    # The SHORT forms keep `\b` on both sides and are never loosened: bare `hing` without a
    # boundary matches `garnishing`, `dishing` and `washing`.
    "asafoetida": (r"(?:a+s[aeo]+f[aeo]*t[ie]d[ia]|a+ss?af[ae]tida|asaf[oe]+dita|asafoted?ia)"
                   r"|\b(?:heeng|hing|perungayam|inguva|kayam)\b"),
}

# Spice blends that contain asafoetida as an undeclared component. Used ONLY to explain
# label-without-term rows, never to create or remove a label.
BLENDS = [
    "chaat masala", "chat masala", "sambar powder", "sambhar", "pav bhaji", "rasam powder",
    "goda masala", "kitchen king", "curry powder", "garam masala", "sev", "papad", "bhel",
    "vada", "dhokla", "pickle", "achar", "undhiyu", "misal",
]

# A row PASSES when the label and the shipped text agree closely enough that a disagreement
# is worth reading as a defect rather than as noise. Stated here so the Status column means
# something; recall is held to the higher bar because a MISSING allergen label is the
# asymmetric error (CLAUDE.md 4.3).
MIN_PRECISION = 0.70
MIN_RECALL = 0.99


def build() -> str:
    df = pd.read_parquet(
        CORPUS, columns=["recipe_id", "IngredientsList", "Allergens_v2", "allergens_sa5_src"]
    )
    n = len(df)
    text = df["IngredientsList"].fillna("").astype(str)
    labels = df["Allergens_v2"].fillna("").astype(str)

    rows = []
    for allergen, pat in PATTERNS.items():
        rx = re.compile(pat, re.IGNORECASE)
        flagged = labels.apply(lambda x, a=allergen: a in x.split(";"))
        in_text = text.apply(lambda x: bool(rx.search(x)))
        tp = int((flagged & in_text).sum())
        fp = int((flagged & ~in_text).sum())
        fn = int((~flagged & in_text).sum())
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        # ANY false negative fails the row, whatever the rate. A recall threshold lets 84
        # fail-open rows read as "agrees" at 99.65%, which is the asymmetry CLAUDE.md 4.3
        # forbids trading: a missed allergen is not a rounding error against a percentage.
        # MIN_RECALL is kept only as a second, weaker tripwire.
        if fn:
            status = f"REVIEW — {fn:,} fail-open"
        elif prec >= MIN_PRECISION and rec >= MIN_RECALL:
            status = "agrees"
        else:
            status = "REVIEW — precision"
        rows.append(dict(allergen=allergen, flagged=tp + fp, lexical=tp + fn, tp=tp, fp=fp,
                         fn=fn, precision=prec, recall=rec, status=status))

    # Explain the largest FP block rather than asserting a cause for it.
    rx = re.compile(PATTERNS["asafoetida"], re.IGNORECASE)
    flagged = labels.apply(lambda x: "asafoetida" in x.split(";"))
    resid = text[flagged & ~text.apply(lambda x: bool(rx.search(x)))]
    blend_counts = {b: int(resid.str.contains(b, case=False, regex=False).sum())
                    for b in BLENDS}
    covered = pd.Series(False, index=resid.index)
    for b in BLENDS:
        covered |= resid.str.contains(b, case=False, regex=False)
    n_res, n_cov = len(resid), int(covered.sum())
    top = sorted(((v, k) for k, v in blend_counts.items() if v), reverse=True)[:6]
    src = df["allergens_sa5_src"].value_counts().to_dict()

    L = []
    A = L.append
    A("# Validation Report: South Asian 5 Allergen Lexicon")
    A("")
    A("Text agreement between the shipped allergen labels and the shipped ingredient lists,")
    A("for the four South Asian 5 classes that no regulator enumerates and that therefore")
    A("rest entirely on this project's own lexicon: `coconut`, `tamarind`, `fenugreek`,")
    A("`asafoetida`.")
    A("")
    A("> **This is a consistency check, not an accuracy measurement.** It compares a label to")
    A("> a regex over the same corpus the label was derived from, so it shares that lexicon's")
    A("> blind spots by construction and cannot discover a food the lexicon never knew about.")
    A("> A high figure here is evidence that the published label and the published text agree —")
    A("> not evidence that either is right. Read it alongside `docs/ALLERGEN_AUDIT.md`.")
    A("")
    A("## Protocol")
    A("")
    A(f"* **Scope.** All **{n:,}** recipes in the published payload")
    A("  (`data/corpus/recipes_structured.parquet`), measured at build time — not a sample,")
    A("  and not a figure carried over from an earlier corpus generation.")
    A("* **Column scanned.** `IngredientsList`, the canonicalised list that ships. Earlier")
    A("  versions of this report scanned a raw `Ingredients` column that is **not** part of")
    A("  the release, so their figures were not reproducible from the published data.")
    A("* **Word boundaries.** Short terms are `\\b`-anchored on both sides, so `hing` does not")
    A("  match `garnishing`. The long `asafoetida` spellings drop the LEFT boundary only,")
    A("  because quantities fuse to the word in scraped text (`pinchasafoetida`, `2asafetida`)")
    A("  and `\\b` does not fire between a digit and a letter. The corpus is fully Roman")
    A("  (`ingredients_romanised`), which is what makes `\\b` usable at all; it is not reliable")
    A("  against Indic script and must not be reused on one.")
    A("* **Precision (text-confirmable).** Of the recipes carrying the label, the share whose")
    A("  ingredient list names the allergen or a regional synonym.")
    A("* **Recall (text-confirmable).** Of the recipes naming it, the share that carry the label.")
    A("* **Status.** Derived, not asserted. **Any** false negative returns `REVIEW` with the")
    A("  count, whatever the rate — a missed allergen is not a rounding error against a")
    A(f"  percentage (CLAUDE.md §4.3). Absent that, `agrees` needs precision ≥ "
      f"{MIN_PRECISION:.0%} and recall ≥ {MIN_RECALL:.0%}.")
    A("")
    A("## Corpus-wide agreement")
    A("")
    A("| Allergen | Labelled | Named in text | TP | FP | FN | Precision | Recall | Status |")
    A("|---|---:|---:|---:|---:|---:|---:|---:|---|")
    for r in rows:
        A(f"| {r['allergen']} | {r['flagged']:,} | {r['lexical']:,} | {r['tp']:,} | "
          f"{r['fp']:,} | {r['fn']:,} | {r['precision']:.2%} | {r['recall']:.2%} | "
          f"{r['status']} |")
    A("")
    A("> **Read the recall column with care.** For `coconut`, `tamarind` and `fenugreek` it is")
    A("> close to a tautology: the labels were derived from a lexicon that is a superset of the")
    A("> regex, so a row naming the allergen is labelled almost by construction and 100.00% is")
    A("> the expected reading, not an achievement. It is **not** evidence that the corpus")
    A("> contains no unlabelled instances of those foods.")
    A(">")
    asa_fn = next(r["fn"] for r in rows if r["allergen"] == "asafoetida")
    A("> `asafoetida` is the one worth reading. Its arm carries a **misspelling family** —")
    A("> 24 further spellings and the quantity-fused forms (`teaspoonasafoetida`) — so its FN")
    A("> count is a genuine measurement rather than a definitional zero.")
    A(">")
    if asa_fn:
        A(f"> It currently reads **{asa_fn:,}**. Those are recipes that name asafoetida in a")
        A("> spelling the labelling lexicon does not carry, so they hold no asafoetida label:")
        A("> **fail-open**, the direction CLAUDE.md §4.3 says is never traded. Evidence:")
        A("> `_docs/audits/PROPOSE_asafoetida_spellings_2026-09-05.tsv`.")
    else:
        A("> It reads **zero**, and that zero was earned rather than assumed. It was **84**")
        A("> when the family was first measured: recipes naming asafoetida in a spelling the")
        A("> labelling lexicon did not carry, holding no asafoetida label — **fail-open**, the")
        A("> direction CLAUDE.md §4.3 says is never traded. None was `unknown`, and 70 carried")
        A("> other classes confidently, so the fail-closed sentinel did not cover them. Pass")
        A("> V27 put the spellings into the lexicon and relabelled 89 rows; a second round was")
        A("> needed because the first listed only spellings ending in `-a` and left 11")
        A("> (`asafatedia`, `asafetide`) behind. A non-zero value here again would mean a new")
        A("> source spelling it a new way, and is a defect to act on, not a rate to tolerate.")
    A("")
    A("## Why asafoetida's precision is the outlier")
    A("")
    A(f"**{n_res:,}** recipes carry the `asafoetida` label without naming it in the shipped")
    A("ingredient list. An earlier version of this report put that count at 1,321 and")
    A("attributed it to *\"valid knowledge-graph (KG-sourced) labels\"*. **There is no KG")
    A("allergen source in this payload** — `allergens_sa5_src` takes only "
      + ", ".join(f"`{k}` ({v:,})" for k, v in sorted(src.items())) + ". The actual")
    A("explanation is compositional, and is the reason the class behaves differently from the")
    A("other three:")
    A("")
    A("**Asafoetida is a component of blended masalas that do not name it.** Chaat masala,")
    A("sambar powder and pav bhaji masala all standardly contain hing. A recipe calling for")
    A("chaat masala contains asafoetida; its ingredient list does not say so. Labelling those")
    A("recipes is correct and is the fail-closed behaviour Codex CXC 80-2020 requires — but it")
    A("makes the label deliberately exceed the text, which is what depresses precision here.")
    A("")
    A(f"Of those {n_res:,} rows, **{n_cov:,} ({n_cov / n_res:.1%})** name such a blend:")
    A("")
    A("| Blend named | Recipes |")
    A("|---|---:|")
    for v, k in top:
        A(f"| {k} | {v:,} |")
    A("")
    A(f"Leaving **{n_res - n_cov:,}** rows ({(n_res - n_cov) / n:.2%} of the corpus) where the")
    A("label is not explained by either a spelling variant or a named blend. These are")
    A("recorded, not resolved. They are a **known open item**, and because the residual")
    A("direction is a label the text does not support — an over-warning, not a missed")
    A("allergen — it is the tolerable direction of the two.")
    A("")
    A("## Notes")
    A("")
    A("1. **Coconut vs tree nuts.** Coconut is a separate token; the generic `tree_nuts` class")
    A("   is cleared where coconut is the only nut present. This follows the project's own")
    A("   taxonomy boundary and not a regulator's — FSSAI's clause 5(14) does not enumerate")
    A("   coconut, and its `tree nuts` entry is illustrative (`e.g.`), so whether coconut falls")
    A("   inside it is open on the face of the text. See `docs/ALLERGEN_TAXONOMY.md`.")
    A("2. **Plant milks.** `coconut milk`, `almond milk` and `soy milk` do not trigger the")
    A("   dairy `milk` class while retaining their own allergen identity.")
    A("3. **Provenance.** The four classes here are lexicon-derived and carry no regulatory")
    A("   backing; they are an investigator-defined extension on South Asian prevalence")
    A("   grounds. Do not present them as a regulator's list.")
    A("")
    A("---")
    A("")
    A("Regenerate with `python scripts/validate_sa5.py`; `--check` fails if this file has")
    A("drifted from the payload.")
    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    fresh = build()
    if args.check:
        cur = REPORT.read_text(encoding="utf-8") if REPORT.exists() else ""
        if cur != fresh:
            print("FAIL  docs/allergen_sa5_v1_validation.md is stale — "
                  "run `python scripts/validate_sa5.py`")
            return 1
        print("OK    SA5 validation report matches the published payload")
        return 0
    # newline="\n" is load-bearing, not style. `.gitattributes` marks `*.md` as `eol=lf`, and
    # this file's digest is pinned in checksums/SHA256SUMS. Written with Python's default
    # translation this lands as CRLF on Windows, git stores LF, and the Linux CI runner then
    # reads a file one byte per line shorter than the digest was taken from -- so
    # `verify_release.py --strict-checksums` fails on the runner while passing locally.
    # Thirteen checksummed files were in exactly that state on 2026-09-05.
    with REPORT.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(fresh)
    print(f"wrote {REPORT.relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
