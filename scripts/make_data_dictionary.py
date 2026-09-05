"""Generate docs/DATA_DICTIONARY.md from the published Parquet schemas.

Generated rather than hand-written so it cannot drift from the data. Column meanings
are not invented: where the working master documents no meaning, the description
column is left empty.

Usage:  python scripts/make_data_dictionary.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from release_config import REPO_ROOT  # noqa: E402

# DISCOVERED, not listed (changed 2026-09-02). This was a hardcoded list of four, so the
# dictionary documented 4 of the 45 published Parquet tables and 428 of 726 columns had no
# entry at all — a consumer opening any of the other 41 files had nothing to read. A
# hand-maintained list of tables drifts exactly the way a hand-maintained dictionary does,
# which is the reason this file is generated in the first place.
def _tables() -> list[str]:
    root = REPO_ROOT / "data"
    return sorted(
        str(p.relative_to(REPO_ROOT)).replace("\\", "/")
        for p in root.rglob("*.parquet")
    )


# Rows to sample when a table is too large to load whole. kg_edges alone is 6.2M rows, and
# the dictionary needs its schema and a representative value, not all of it.
BIG_ROWS = 500_000

# Unit and basis come from the single registry (scripts/column_units.py) rather than being
# restated here, so the dictionary cannot disagree with the Arrow field metadata stamped on
# the parquet. Before 2026-09-02 the dictionary declared no unit for any column, while
# per100g_sodium (mg) sat beside per100g_salt (g).
try:
    from column_units import COLUMN_UNITS  # noqa: E402
except Exception:                                     # pragma: no cover
    COLUMN_UNITS = {}


def unit_cell(col: str) -> str:
    d = COLUMN_UNITS.get(col)
    if not d:
        return ""
    u = d["unit"]
    u = "" if u == "1" else f"`{u}`"
    b = d.get("basis")
    dom = d.get("domain")
    bits = [x for x in (u, f"per {b}" if b and b != "row" else "",
                        f"[{dom[0]}, {dom[1]}]" if dom and dom[1] is not None else "") if x]
    return " ".join(bits)


# A2, 2026-08-29. A generated dictionary cannot drift from the data, but it also cannot say
# which of two similarly-named columns to trust. Both allergen columns shipped for weeks with
# identical-looking rows, and the plainer name was the broken one -- a schema scan is exactly
# how a consumer picks a column, so the warning has to live in the schema table itself.
#
# Keep these short: one sentence, and only where reading the wrong column changes an answer.
COLUMN_NOTES = {
    # ---- added 2026-09-02 by the standardisation recheck. Each is a case where a consumer
    # reading the obvious column gets a wrong answer, and the note is the only thing that
    # would tell them. Same rationale as the allergen pair below.
    "Lang": "⚠ **Do not filter on this.** BCP-47 with region subtags mixed with bare ISO "
            "639-1, so `Lang == 'en'` returns 122,569 rows and misses 85,090 more "
            "(`en-US` 79,581, `en-GB` 5,508) — **41% of the English corpus.** "
            "Use `Lang_base`.",
    "Lang_base": "**Use this for language filtering.** ISO 639-1 primary subtag only; "
                 "`Lang_base == 'en'` returns all 207,659 English rows.",
    "Split_v2": "⚠ **Leaks.** Groups on `Title_normalized` without case-folding and ignores "
                "`dup_family_id`: 2,223 groups straddle a boundary, so **11.9% of the test "
                "set has a near-duplicate in train**. Any Recall@K / NDCG@K on it is "
                "inflated. Use `Split_v3`.",
    "Split_v3": "**Use this split.** Connected components over case-folded title AND "
                "`dup_family_id`; 0 groups span a boundary. Seed 20260902.",
    "per100g_sodium": "**MILLIGRAMS** per 100 g — unlike every other `per100g_` mass column, "
                      "which are grams. `per100g_salt` beside it is grams, so the two differ "
                      "by 400x. See `docs/UNITS.json`.",
    "per100g_salt": "**GRAMS** per 100 g, and exactly `per100g_sodium * 0.0025` on every row "
                    "where both exist — it carries no independent information.",
    "grams_per_serving_v3": "⚠ **The name is wrong.** This is a WHOLE-DISH weight (median "
                            "705 g), not one serving. Divide by `Servings_num` for a "
                            "per-serving figure.",
    "atwater_fixed": "⚠ **Misnamed:** flags rows the Atwater check IDENTIFIED, not rows it "
                     "repaired — `Nut_Calories == Nut_Calories_orig` on all of them. "
                     "`atwater_recomputed` is the column that means what this one says.",
    "atwater_recomputed": "True where `Nut_Calories` actually differs from "
                          "`Nut_Calories_orig` (3,626 rows).",
    "fsa_n_labelled": "How many of the four FSA lights are set. The denominator for "
                      "`fsa_n_red` / `fsa_n_green`, which is not 4 everywhere.",
    "per100g_macrosum_implausible": "True where protein+carb+fat exceeds 100 g per 100 g "
                                    "(12,110 rows, max 880). Values are NOT clipped — the "
                                    "upstream `grams_per_serving_v3` is wrong on these rows.",
    "nutrient_subcomponent_violation": "True where saturated fat exceeds total fat, or sugar "
                                       "or fibre exceeds carbohydrate (2,570 rows). Left "
                                       "unclipped: which side is wrong is not decidable here.",
    "macro_pct_unfounded": "True where the 13/40/44 macro-percent trio appeared on a row with "
                           "no macros to compute it from. Those Pct values are nulled.",
    "allergen_tier": "Evidence tier per asserted class. `inherited` means the class came from "
                     "an earlier lexicon generation and carries no evidence in the current "
                     "scan. Empty on `unknown` (unassessed) rows.",
    "Allergens_v2": "**Authoritative.** All 17 declared classes — the 16-token taxonomy "
                    "plus `ghee`, a derivative marker that ALWAYS co-occurs with `milk` "
                    "and never replaces it; `;`-separated. "
                    "`unknown` means NOT ASSESSED -- treat as unsafe, never as clean.",
    "Allergens_v1_superseded": "⚠ **Superseded, do not use for safety.** 12 of the 16 classes "
                               "(no coconut / asafoetida / fenugreek / tamarind), some rows "
                               "comma-separated, un-normalised `dairy` and `peanuts` tokens. "
                               "Retained only so a v1-era claim stays reproducible.",
    "allergen_assessed": "False = allergens were never assessed for this recipe. Mirrors the "
                         "`allergen::unknown` edge; the two are asserted to agree.",
    "allergens_title_src": "Semicolon list of classes labelled from the recipe TITLE rather "
                           "than the ingredient text — weaker evidence, kept separable on purpose.",
    "allergens_title_fix": "True where the title channel added at least one class (4,052 rows).",
    "allergens_lexv9_fix": "True where the v9 lexicon pass added a class (316 rows: panir/panner, "
                           "`ground nut`, crabs/squids/clams plurals).",
    "diet_contradicts_ingredients": "True where the declared `Diet` conflicts with a labelled "
                                    "allergen or a meat term. Advisory: the row is NOT auto-corrected.",
}


def cell(value: object) -> str:
    text = str(value)[:40]
    return text.replace("|", r"\|").replace("\n", " ").replace("\r", " ")


def main() -> int:
    out: list[str] = [
        "# Data dictionary",
        "",
        "Generated by `scripts/make_data_dictionary.py` from the published Parquet",
        "schemas — not hand-maintained, so it cannot drift from the data.",
        "",
        "Counts are over the full table. The example is the first non-null value and is",
        "illustrative only. Column *meanings* are deliberately absent where the working",
        "master documents none; they are not guessed.",
        "",
        "Prose columns (`Description`, `Instructions`, `Ingredients`, `Keywords`,",
        "`Enrich_Log`) are withheld from every table below — see `DATASHEET.md`.",
    ]

    tables = _tables()
    out += ["", f"Covering **all {len(tables)} published Parquet tables**.", ""]
    for rel in tables:
        path = REPO_ROOT / rel
        if not path.exists():
            print(f"skip (missing): {rel}")
            continue
        import pyarrow.parquet as pq
        nrows = pq.read_metadata(path).num_rows
        if nrows > BIG_ROWS:
            df = pd.read_parquet(path).head(BIG_ROWS)
            sampled = f" (statistics from the first {BIG_ROWS:,} rows)"
        else:
            df = pd.read_parquet(path)
            sampled = ""
        out += [
            "",
            f"## `{rel}`",
            "",
            f"{nrows:,} rows x {len(df.columns)} columns - "
            f"{path.stat().st_size / 1e6:.1f} MB{sampled}",
            "",
            "| column | type | unit / basis | non-null | distinct | example | note |",
            "|---|---|---|---:|---:|---|---|",
        ]
        for col in df.columns:
            series = df[col]
            non_null = int(series.notna().sum())
            try:
                distinct = format(int(series.nunique(dropna=True)), ",")
            except TypeError:
                distinct = "n/a"
            values = series.dropna()
            example = cell(values.iloc[0]) if len(values) else ""
            out.append(
                f"| `{col}` | {series.dtype} | {unit_cell(col)} | {non_null:,} | "
                f"{distinct} | {example} | {COLUMN_NOTES.get(col, '')} |"
            )
        print(f"  {rel}: {len(df.columns)} columns")

    # ---- payload manifest ---------------------------------------------------------
    # Added 2026-09-02: 33 of the 90 files under data/ were named in no published document,
    # so a consumer could not tell what they were, whether they were inputs or outputs, or
    # which of two similarly-named directories to use. Listing every file is cheap and
    # cannot drift; the KINDS map explains the ones whose purpose is not obvious from the
    # path, and anything unmapped is shown as `⟨undescribed⟩` so the gap is visible rather
    # than silent.
    KINDS = {
        ".parquet": "columnar table — documented above",
        ".jsonl": "one JSON object per line",
        ".csv": "delimited text",
        ".txt": "plain-text id or triple list",
        ".json": "metadata / manifest",
        ".md": "prose",
        ".py": "generator kept beside its output so the artefact is reproducible",
    }
    NOTES = {
        "data/synthetic_interactions": "⚠ **v1, superseded.** Pinned to the PRE-withdrawal "
                                       "corpus: its `item_list.txt` and `interactions.csv` "
                                       "reference recipe ids withdrawn by the V7 pass. Kept "
                                       "so a v1-era result stays reproducible; do not build "
                                       "on it.",
        "data/synthetic_interactions_v3": "**Use this one.** Rebuilt against the current "
                                          "corpus.",
        "data/kg_flavor": "FlavorDB-derived flavour layer, `CC BY-NC-SA 3.0`. Note the same "
                          "content is ALSO inside `data/kg/`, so taking the core graph "
                          "alone does not avoid FlavorDB's terms.",
        "data/provenance": "per-field change history across builds.",
    }
    files = sorted((p for p in (REPO_ROOT / "data").rglob("*") if p.is_file()),
                   key=lambda p: str(p).lower())
    out += ["", "---", "", "## Every published file",
            "", f"All {len(files)} files under `data/`, so nothing ships undescribed.", ""]
    last_dir = None
    for p in files:
        rel = str(p.relative_to(REPO_ROOT)).replace("\\", "/")
        d = rel.rsplit("/", 1)[0]
        if d != last_dir:
            note = NOTES.get(d, "")
            out += ["", f"### `{d}/`" + (f" — {note}" if note else ""), "",
                    "| file | size | kind |", "|---|---:|---|"]
            last_dir = d
        kind = KINDS.get(p.suffix, "⟨undescribed⟩")
        out.append(f"| `{rel.rsplit('/', 1)[-1]}` | {p.stat().st_size / 1e6:.2f} MB | "
                   f"{kind} |")
    print(f"  payload manifest: {len(files)} files")

    target = REPO_ROOT / "docs" / "DATA_DICTIONARY.md"
    # newline="\n": this file is `text eol=lf` in .gitattributes and its digest is pinned in
    # checksums/SHA256SUMS. The platform default makes it CRLF here and LF in the object
    # store, so --strict-checksums passes locally and fails on the Linux runner.
    with target.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(out) + "\n")
    print(f"wrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
