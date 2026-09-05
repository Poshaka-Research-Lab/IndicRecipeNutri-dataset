"""Single source of truth for the release contract.

Both the builders (`build_*.py`) and the validator (`verify_release.py`) import from
here, so the licence guard and the expected counts cannot drift apart.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# The allergen token set is declared ONCE, in `D:\datasets\allergen_taxonomy.py`, and
# imported everywhere. Before 2026-09-04 it was written out by hand in 26 files; four of
# them carried `ghee` and the rest did not, which shipped a release whose graph declares 17
# allergen classes and whose tables declare 16. `paths.bootstrap()` would do this insert
# too, but this module is imported by the validator as well as the builders and must not
# depend on the working tree being importable, so the insert is explicit and minimal.
sys.path.insert(0, os.environ.get("DATASETS_ROOT", r"D:\datasets"))
import allergen_taxonomy as _AT  # noqa: E402

# --------------------------------------------------------------------------- paths

# Root of the *source* tree the release is built from. Overridable so the builders
# can run on a machine where the working corpus lives somewhere else.
SOURCE_ROOT = Path("D:/datasets/scraped_indian_recipes")

REPO_ROOT = Path(__file__).resolve().parent.parent

MASTER_CSV = SOURCE_ROOT / "data" / "MASTER_indian_recipes_enriched.csv"
KG_DIR = SOURCE_ROOT / "data" / "kg"
RETRIEVAL_DIR = SOURCE_ROOT / "retrieval"
BENCH_SYNTH_DIR = SOURCE_ROOT.parent / "bench_synth"

# --------------------------------------------------------------- the licence guard

# Columns that carry copyrightable prose from the source pages. Paper section 3.5:
# "Raw copyrighted prose is not redistributed." These MUST NOT appear in any
# published artefact. `verify_release.py` fails the build if one is found.
#
# `Ingredients` is the raw scraped ingredient string and is excluded; `IngredientsList`
# is the *parsed* list, which section 3.5 explicitly places in the redistributable
# tier ("parsed ingredients, quantities").
PROSE_COLUMNS = [
    "Description",
    "Instructions",
    "Ingredients",
    "Keywords",
    "Enrich_Log",
    # Not prose - a pre-edit BACKUP of IngredientsList, kept in the master so the 2026-09-01
    # title-evidence pass is reversible. It duplicates a column that IS published, so
    # shipping it doubles the text for no benefit. Withheld here rather than exempted from
    # the length check: the guard was right to flag it.
    "IngredientsList_pretitle",
    # Same shape: a pre-clean BACKUP of IngredientsList kept for reversibility of the
    # 2026-09-01 format repairs. Duplicates a published column; withheld.
    "IngredientsList_preclean",
    # Two more of the same shape, 2026-09-05. `_prefused` is the pre-V19 list (before the
    # 1,408 fused Latin+Indic words were split) and `_pregloss` the pre-V20 list (before
    # 1,043 redundant Indic glosses were dropped). Both are kept in the master so those
    # passes stay reversible, and both duplicate a column that IS published, so shipping
    # them doubles the text for no benefit. The licence length guard flagged them as "prose
    # under another name" and it was right — the same call it made about the two above.
    #
    # `IngredientsList_src_script` is deliberately NOT here. It is the same *shape* but a
    # different *thing*: decision D-2 publishes it as provenance, it is sparse (49 rows),
    # and it is the one column that legitimately holds non-Latin text once M29 is closed.
    "IngredientsList_prefused",
    "IngredientsList_pregloss",
    "RecipeName_preclean",
    # Third of the same shape, 2026-09-02: the pre-translation backup from the V9 Indic
    # pass, kept in the master so the translation is reversible. Caught by the licence
    # guard's length check at 786 chars — the guard was right, as it was the previous two
    # times. The pattern is now established: any `IngredientsList_*` backup duplicates a
    # published column and doubles the text for no consumer benefit.
    "IngredientsList_pre_v9",
]

# Prose columns are hashed into the rehydration index so a user who re-fetches the
# source page can verify they reconstructed the same text we measured.
REHYDRATION_KEY_COLUMNS = ["recipe_id", "URL", "SourceSite", "Lang"]

# --------------------------------------------------------------- expected invariants

# Every figure below is read from an artefact in the source tree, never asserted from
# memory. `kg_stats.json` is the authority for the KG counts; the corpus count is the
# row count of the v15 master.
# Rows present in the working master.
# 2026-09-01: 224,003 -> 220,191. The V7 pass withdrew 3,812 rows that were never recipe
# pages -- 2,314 WordPress /tag/ and /category/ archive listings, 821 single-food commodity
# records, 465 image-attachment pages, 135 shop product pages, 111 glossary/article/listicle
# pages, 1 other. Every one was read individually by an adjudicating agent and survived an
# adversarial pass that refuted 125 others; 35 more were spared at the point of removal
# because the page they were a secondary view OF did not survive. Withdrawn records are kept
# in full at `scraped_indian_recipes/data/MASTER_nonrecipe_quarantine_v7.csv`; the decision
# record is `scraped_indian_recipes/data/_docs/V7_NONRECIPE_2026-09-01.md`.
# 2026-09-01 (recheck): 220,191 -> 220,188. All 3,812 withdrawn rows were read individually
# by a third reader whose default was RESTORE; 3,809 upheld, 3 restored, and 6 archive
# listings the rule had never seen (/recipe_difficulty/ was absent from its taxonomy
# pattern) were withdrawn. Record: v7_recheck_meta.json.
# 2026-09-02 (V8 grihshobha): 220,188 -> 219,387 (-801). The whole of SourceSite=grihshobha.
# The scraper never located an ingredient list there: what it captured was the page's
# navigation bar plus the words of the title —
#     Murgin's Yogurt -> ['ऑडियो स्टोरी', 'कुक बुक', 'Login', 'yogurt']
# — on all 801 rows, including the 102 with no nav chrome, which are title-token echoes by
# the same mechanism. 96% fall below the 3-ingredient threshold and 91 have zero real items,
# yet every one carried a non-null Nut_Calories computed from those words and 105 claimed
# Nut_Tier C. `badlist_nav` was 0 on all 801 because the navigation detector matched English
# menu words only — a Devanagari nav bar walked straight past it and the rows cleared every
# gate in the build. The detector now carries Indic nav vocabulary; the withdrawal is the
# rows it should have caught. Full records: MASTER_grihshobha_quarantine_v8.csv.
EXPECTED_SOURCE_RECIPES = 219_387

# Rows withdrawn from the published release. The master is not modified; the exclusion
# is applied by every builder and enforced by the verifier, so it is reversible by
# deleting an entry here and rebuilding.
EXCLUDED_RECIPE_IDS = {
    211731: (
        "Withdrawn at the maintainer's request. Its IngredientsList contained no "
        "ingredients at all - the scrape captured the source site's sidebar "
        "navigation, with the site owner's email address attached. One of 101 rows "
        "from SourceSite=savorytales with the same scrape defect; the other 100 "
        "carry no personal data and are retained, flagged in quarantine_list."
    ),
}

# --------------------------------------------------- V7 non-recipe withdrawal
#
# Rows that were never recipe pages -- image-attachment pages, HTTP error pages, WordPress
# /tag/ and /category/ archive listings, online-shop product pages, single-food commodity
# records, listicles and non-food articles. Unlike EXCLUDED_RECIPE_IDS above, these are
# REMOVED FROM THE MASTER, not filtered at build time, so they are already absent from
# EXPECTED_SOURCE_RECIPES and must NOT be subtracted again.
#
# The list is still loaded here for one reason: `verify_release.py` scans every published
# artefact for these ids, so a rebuild from a stale master -- the one way a withdrawn row
# could come back -- fails loudly instead of silently republishing it.
#
# Full records are preserved in
# `scraped_indian_recipes/data/MASTER_nonrecipe_quarantine_v7.csv`; the decision record is
# `scraped_indian_recipes/data/_docs/V7_NONRECIPE_2026-09-01.md`.
_WITHDRAWN_JSON = SOURCE_ROOT / "data" / "nonrecipe_withdrawn_v7.json"


def _load_withdrawn() -> dict:
    """Load the withdrawn-id list, and FAIL if it is missing rather than returning {}.

    The first version returned an empty dict when the file was absent, which is a fail-open
    in a guard: `verify_release.check_exclusions` would then scan for nothing, report
    "0 withdrawn recipe(s) absent from all published artefacts", and pass. The one scenario
    the guard exists to catch - a rebuild from a stale tree where the withdrawal never
    happened - is exactly the scenario in which this file goes missing.

    A source-less checkout that cannot reach SOURCE_ROOT at all is a legitimate case, so it
    has an explicit opt-out rather than a silent one.
    """
    import json
    import os
    if not _WITHDRAWN_JSON.exists():
        if os.environ.get("INDICRECIPE_ALLOW_NO_WITHDRAWN_LIST") == "1":
            return {}
        raise FileNotFoundError(
            f"{_WITHDRAWN_JSON} is missing. The V7 pass withdrew rows from the master, and "
            f"this list is what stops a stale rebuild republishing them - an empty list "
            f"would make the exclusion check pass vacuously. Restore the file, or set "
            f"INDICRECIPE_ALLOW_NO_WITHDRAWN_LIST=1 if this really is a checkout with no "
            f"source tree."
        )
    with _WITHDRAWN_JSON.open(encoding="utf-8") as fh:
        return {int(k): str(v) for k, v in json.load(fh).items()}


WITHDRAWN_NONRECIPE_IDS = _load_withdrawn()

# --------------------------------------------------- V8 grihshobha withdrawal
#
# ADDED 2026-09-04, after finding all 801 of these rows in 21 PUBLISHED enrichment tables
# while the master held none of them.
#
# The V8 pass (2026-09-02) withdrew the whole of SourceSite=grihshobha: the scraper never
# located an ingredient list there, so what it captured was the page's navigation bar plus
# the words of the title. Every one of the 801 nevertheless carried a non-null
# `Nut_Calories` computed from those words, and 105 claimed `Nut_Tier C`. Publishing them
# is the exact outcome the withdrawal existed to prevent.
#
# WHY IT WAS MISSED, which is the part worth keeping: `check_exclusions` was written
# against two hard-coded populations and a third was added to the corpus without being
# added to it. Nothing in the build knew this set existed. The registry below exists so
# that cannot recur -- see `ALL_WITHDRAWN_IDS` and `check_unregistered_quarantines`.
_GRIHSHOBHA_CSV = SOURCE_ROOT / "data" / "MASTER_grihshobha_quarantine_v8.csv"


def _load_grihshobha() -> dict:
    """Same fail-loud contract as `_load_withdrawn`: a missing list must not read as an
    empty one, because an empty list makes the exclusion check pass vacuously."""
    import csv
    import os
    if not _GRIHSHOBHA_CSV.exists():
        if os.environ.get("INDICRECIPE_ALLOW_NO_WITHDRAWN_LIST") == "1":
            return {}
        raise FileNotFoundError(
            f"{_GRIHSHOBHA_CSV} is missing. The V8 pass withdrew 801 rows from the master; "
            f"this list is what stops a rebuild republishing them. Restore the file, or "
            f"set INDICRECIPE_ALLOW_NO_WITHDRAWN_LIST=1 if this really is a checkout with "
            f"no source tree."
        )
    with _GRIHSHOBHA_CSV.open(encoding="utf-8", newline="") as fh:
        return {
            int(row["recipe_id"]): "V8 grihshobha: ingredient list was the page navigation bar"
            for row in csv.DictReader(fh)
            if row.get("recipe_id", "").strip().isdigit()
        }


WITHDRAWN_GRIHSHOBHA_IDS = _load_grihshobha()

# THE REGISTRY. Every population that must never appear in a published artefact, in one
# place, so adding a fourth is one line here rather than an edit to each consumer that
# happens to remember. `build_enrichment.py` and `verify_release.py` both read this.
#
# Keep the human-readable name: it is what the failure message prints, and "801 rows from
# an unnamed set" is not an actionable error.
WITHDRAWAL_SETS = {
    "build-time exclusion (PII)": EXCLUDED_RECIPE_IDS,
    "V7 non-recipe withdrawal": WITHDRAWN_NONRECIPE_IDS,
    "V8 grihshobha withdrawal": WITHDRAWN_GRIHSHOBHA_IDS,
}


def all_withdrawn_ids() -> dict:
    """recipe_id -> reason, across every registered withdrawal population."""
    out: dict = {}
    for ids in WITHDRAWAL_SETS.values():
        out.update(ids)
    return out


def unregistered_quarantine_files() -> list:
    """Quarantine files in the source tree that no registered set covers.

    A withdrawal nobody wired up is precisely the defect found on 2026-09-04, so the build
    looks for the shape of the mistake rather than trusting that it will be remembered.
    Matching is deliberately crude -- any `*quarantine*.csv` under `data/` -- because a
    false alarm here costs one line in KNOWN_QUARANTINE_FILES and a miss costs a release.
    """
    # Files that ARE registered withdrawals, plus files that look like withdrawals and are
    # not. Every entry in the second group carries the measurement that settles it, taken
    # 2026-09-04 -- an allow-list without evidence is just a way of turning a red gate green.
    known = {
        # --- registered withdrawal populations -------------------------------------
        _GRIHSHOBHA_CSV.name,                       # 801 ids, 0 in master, 0 published
        "MASTER_nonrecipe_quarantine_v7.csv",       # 3,815 ids, 0 in master, 0 published
        # --- not id-keyed withdrawals ----------------------------------------------
        # No `recipe_id` column at all, so there is nothing for an id scan to check.
        "MASTER_junk_quarantine.csv",
        "MASTER_junk_quarantine2.csv",
        "MASTER_junk_quarantine3.csv",
        # --- superseded backup -----------------------------------------------------
        # The pre-recheck copy of the V7 set: 3,812 ids, of which exactly 3 are back in the
        # master. Those 3 are the rows the V7 recheck RESTORED, which is independent
        # corroboration of `v7_recheck_meta.json` rather than a leak. The live V7 file
        # above supersedes it.
        "MASTER_nonrecipe_quarantine_v7.pre_recheck.bak.csv",
        # --- historical, not a release withdrawal ----------------------------------
        # 10,963 ids, of which 9,705 are STILL IN THE MASTER and published -- they were
        # quarantined for review and restored, so this is a review log, not a withdrawal.
        # The 1,258 that are absent from the master were checked individually: all 1,258
        # are covered by a registered set above, and none appears in any published
        # artefact. Verified, not assumed.
        "MASTER_v5_quarantine.csv",
    }
    data_dir = SOURCE_ROOT / "data"
    if not data_dir.is_dir():
        return []
    return sorted(
        p.name for p in data_dir.glob("*quarantine*.csv") if p.name not in known
    )


# D4.1 REVERSED 2026-08-29 -- the four upstream-dataset sources are RETAINED.
#
# They were briefly excluded to strip NonCommercial terms from the release. Decision
# reversed: the recipes stay. The licence follows the contents rather than the contents
# following the licence, so `data/` is CC BY-NC-SA 4.0 again (see LICENSE-DATA).
#
# What they are, on the evidence, so nobody has to re-derive it:
#   3a2m_indian      3,803  synthetic URLs (3a2m.dataset); source text_corpora/3A2M
#   yummly           2,923  synthetic URLs (yummly.whatscooking); source
#                           cultural/yummly_whats_cooking/{train,test}.json
#   foodcom          2,628  real food.com URLs; source datasets/foodcom/foodcom.zip
#   recipenlg_indian    30  synthetic URLs (recipenlg.dataset); source datasets/recipenlg
# None has a scraper URL list, and CLAUDE.md 6.1 names them as primary corpora.
#
# Keeping the mechanism (empty) so re-excluding is a one-line change, not a rewrite.
EXCLUDED_SOURCE_SITES = {}
EXPECTED_EXCLUDED_BY_SITE = 0

# Rows actually published.
EXPECTED_RECIPES = (EXPECTED_SOURCE_RECIPES - len(EXCLUDED_RECIPE_IDS)
                    - EXPECTED_EXCLUDED_BY_SITE)
# Raised 2026-08-29 by A1/A3/C1.1. Was 225_661 / 6_131_947. Do not lower these back without
# reading TODO_PENDING_2026-08-29.md: the old figures are the signature of the KG being built
# from the superseded `Allergens_filled` column, which carried only 12 of the 16 declared
# allergen classes.
#
#   nodes  +5   4 new allergen classes (coconut, asafoetida, fenugreek, tamarind)
#              + 1 `allergen::unknown` sentinel, so an unassessed recipe is distinguishable
#                from an assessed-and-clean one in the graph as well as on the node flag.
#   edges  +105,699   contains_allergen 299,941 -> 405,624, which now reconciles EXACTLY,
#                     per class, against the corpus `Allergens_v2` column;
#                     + 10 `derived_from` edges (coconut-oil -> coconut and nine more,
#                     seven of whose parents are declared allergens).
# 2026-08-30 (P6): 227,239 -> 227,223 (-16). Exactly the 16 vocabulary tokens dropped
# because they NEVER appear after a quantity in 224,003 recipes (`cover`, `completely`,
# `television`, `toddlers` ...). Ingredient nodes 1,005 -> 990; the other 1 is a foodclass
# that lost its only member.
# 2026-09-01 (V7 non-recipe withdrawal): 227,223 -> 223,409 (-3,814). Reconciled exactly by
# rebuilding the graph from `master + quarantine` -- the corpus as it stood before the
# withdrawal -- with the same builder, and diffing:
#   recipe      -3,812   the withdrawn rows, one node each
#   ingredient      -2   `gajak` and `prepacks`, which existed ONLY inside withdrawn rows.
#                        `gajak` is a real sesame brittle and its loss is a genuine (small)
#                        vocabulary cost; `prepacks` was never an ingredient.
# No other node type moved.
# 2026-09-01 (recheck): 223,409 -> 223,406 (-3), exactly the net recipe change
# (+3 restored, -6 newly withdrawn). Ingredient nodes unchanged at 988; no other node type
# moved.
# 2026-09-02 (R6 flag integrity): 223,406 -> 223,407 (+1). ONE node, and naming it is the
# reconciliation:
#
#   diet::unknown   +1   the sentinel for the 731 recipes whose IngredientsList is empty
#
# R6 set `Diet = "unknown"` on those rows, which had been labelled from no evidence at all —
# 657 of them as Vegan, the most permissive value. `diet_tags("unknown")` matches no rule, so
# without a sentinel those rows would carry NO has_diet edge and an unassessed recipe would
# be indistinguishable from one the builder failed on. That is the reading the allergen path
# forbids in build_kg_v3.py's own A3 comment ("Dropping it made 1,091 unassessed recipes
# indistinguishable from assessed-and-clean -- Codex CXC 80-2020 forbids exactly that"), so
# the diet axis now does what the allergen axis already did.
#
# EXPECTED_KG_EDGES is UNCHANGED at 6,270,620, which is the check that this is a sentinel and
# not a new fact: the 731 has_diet edges moved to diet::unknown rather than disappearing.
# Verified: 731 edges with tail == "diet::unknown", and no other node type moved.
#
# The sentinel is excluded from benchmark query generation
# (retrieval/structural/make_eval_queries.py) — it clears the >=5-member threshold and would
# otherwise add two meaningless queries, "unknown recipes" and "unknown recipes without
# <allergen>", taking the benchmark from 68 to 70.
#
# 2026-09-02 (V8 withdrawal + V10 ghee): 223,407 -> 222,607 (-800). Two movements, and they
# are the whole delta:
#
#   recipe          -801   the withdrawn grihshobha rows, one node each
#   allergen::ghee    +1   the 17th token's node
#                   ------
#                    -800  exactly
#
# No other node family moved: ingredient stays 988, compound 1,601, foodclass 377,
# cuisine 53, occasion 44, healthtag 30, region 27.
# MOVED 2026-09-05: 222,607 -> 222,578, delta -29 -- exactly P6's dropped ingredient nodes.
# Nothing else moved: the corpus row count is unchanged at 219,387 (219,386 published).
EXPECTED_KG_NODES = 222_578
# 2026-08-30: 6,307,080 -> 6,321,106 (+14,026). Every edge accounted for, none unexplained:
#   for_occasion  +10,045  the duplicate-family merge filled 6,114 `Occasion` values, and
#                          Occasion is multi-valued, so rows expand to more edges
#   has_diet       +2,092  D1/D2 relabels (2,939 -> Non-Vegetarian, 3,285 Vegan -> Vegetarian)
#   in_context     +1,963  the merge filled 1,833 `DietaryContext` values
#   has_health_tag    -74  knock-on from the diet and per-100g corrections
# Do not raise this constant without an equivalent per-relation reconciliation. The guard
# caught this change correctly; it is meant to make an unexplained drift stop the build.
# 2026-08-30 (P6): 6,321,106 -> 6,320,665 (-441), fully reconciled per relation:
#   has_ingredient  -373   edges from the 16 dropped tokens
#   rich_in          -67   nutrient edges those nodes carried
#   grounded_as       -1   one FoodOn grounding
# No other relation moved. If a future drop shifts a relation not on this list, that is
# the signal the guard exists for - reconcile before raising the constant.
# 2026-08-31 (allergen lexicon v14): 6,320,665 -> 6,350,250 (+29,585).
#   contains_allergen  +29,585   and NO other relation moved.
# Matches the 29,861 label additions in the master less the withdrawn PII row and rows
# whose class edge already existed. v14 is additive by assertion - 0 labels removed -
# and it cut the human-measured false negatives from 118 to 36 (69.5% recovered).
# 2026-09-01 (M4 title evidence): 6,350,250 -> 6,353,348 (+3,098), reconciled:
#   has_ingredient     +3,083  the 3,544 added lines, less those whose node already existed
#   contains_allergen      +7  new allergen labels from title evidence
#   pairs_with             +5  PMI recomputed over the new edges
#   shares_flavor          +3  same
# Added lines carry `(from title, quantity unknown)`. Asserted ABSENT from
# ingredients_weights.parquet and ingredients_nutrition.parquet - an unquantified line must
# never acquire a phantom weight. per-100g medians moved 168 -> 160 on touched rows only.
# Re-run 2026-09-01 with the blend/substitute exclusions added to the title-evidence pass:
# 6,353,348 -> 6,353,264 (-84). 109 fewer recipes touched (3,452 -> 3,343) because titles
# like `Chicken Masala Powder` and `Red Indian Fish Masala` name a SEASONING for a meat,
# not the meat. Gate M18 caught the first version as 58 new strict-veg contradictions;
# with the exclusions it is back to 0.
# 2026-09-01 (format cleaning F1/F3/F4): 6,353,264 -> 6,354,211 (+947), and only two
# relations moved, both UP:
#   has_ingredient  +860  fraction normalisation and the unit-spacing repair made that
#                         many more ingredient tokens parseable - the cleaning EXPOSED
#                         ingredients, it did not lose any
#   pairs_with        +3  PMI recomputed over the new edges
# Every repair passed the five-check negative-test harness first: no allergen class and no
# vocabulary token lost a row, whitespace-only where declared, idempotent, inside its
# declared share window, and a provably-untouchable control set left byte-identical.
# 2026-09-01 (V7 non-recipe withdrawal): 6,354,211 -> 6,270,633 (-83,578). Reconciled per
# relation against a rebuild of the pre-withdrawal corpus, not estimated:
#   has_ingredient     -20,845        is_course          -3,812
#   has_health_tag     -20,213        from_region        -3,812
#   suitable_for       -14,677        in_cuisine         -3,812
#   cooked_by           -6,957        for_occasion         -330
#   contains_allergen   -4,903        in_context            -71
#   has_diet            -4,036        rich_in                -9
#                                     ---------------------------
#                                     pass-1 subtotal   -83,477
# The remaining -101 is the pass-2 pairing and flavour layers (pairs_with, shares_flavor,
# has_compound, grounded_as) recomputed over the smaller corpus, which is expected: PMI and
# co-occurrence are functions of the corpus, and two ingredient nodes left it.
#
# The three mandatory relations are the check that the delta IS the withdrawal and nothing
# else: in_cuisine, is_course and from_region each carry exactly one edge per row, and each
# fell by exactly 3,812 -- 224,003 -> 220,191.
# 2026-09-01 (recheck): 6,270,633 -> 6,270,560 (-73), reconciled per relation with NO
# residual - the 6 withdrawn archive stubs carried more ingredient and allergen edges than
# the 3 restored recipes:
#   has_ingredient -28   cooked_by         -7   in_cuisine  -3
#   contains_allergen -8 has_health_tag    -6   is_course   -3
#   suitable_for   -7    for_occasion      -6   from_region -3
#   has_diet       -2                           = -73 exactly
# in_context and rich_in did not move. The three mandatory one-edge-per-row relations each
# fell by exactly 3, which is the check that the delta IS the net row change.
#
# 2026-09-02 (allergen lexicon R5): 6,270,560 -> 6,270,620 (+60). ONE relation moved, which
# is itself the check: R5 touched exactly one corpus column the KG reads, `Allergens_v2`,
# which feeds `contains_allergen` and nothing else. `suitable_for` is built from
# HealthConditions, not from allergens, so it must not move - and did not.
#
#   contains_allergen  +118 gained  -58 lost  = +60 net, measured over the 220,187 RELEASED
#                                               recipe ids, residual exactly 0
#     gained: gluten 54, tree_nuts 34, peanut 5, milk 4, sesame 4, asafoetida 3, egg 3,
#             soy 3, coconut 2, fenugreek 2, sulphites 2, tamarind 1, fish 1
#     lost  : shellfish 58 -- every one the `oyster mushroom` retraction, enumerated and
#             asserted row by row in apply_allergen_r5.py
#   every other relation: 0
#
# The gains close fail-opens (chestnut was sitting IN the tree_nuts exclusion list; the
# ancient wheats were absent from the gluten pattern). The 58 losses are false positives:
# `oysters?` is a DIRECT shellfish term and nothing excluded the fungus, so 55 mushroom
# recipes carried a shellfish label, one of them a vegan soup. Record:
# scraped_indian_recipes/data/allergen_r5_meta.json.
# 2026-09-02 (V8 withdrawal + R9 + V9 + V10): 6,270,620 -> 6,295,077 (+24,457). Reconciled
# per relation with NO residual. The withdrawal and the additions pull in opposite
# directions, so the decomposition matters more than usual:
#
#   contains_allergen  +33,361   = +33,538 ghee (V10, the 17th token on 33,538 rows)
#                                  +   546 R9: rows flipped none_detected -> unknown. A
#                                          `none_detected` row emits NO edge; an `unknown`
#                                          row emits one to the allergen::unknown sentinel,
#                                          so withdrawing an absence-claim CREATES an edge.
#                                  +    35 V9: classes found once Indic text was translated
#                                  -   758 grihshobha's own allergen edges
#
#   ...and every other relation fell by the withdrawn rows' share:
#     has_ingredient -1,463   has_health_tag -2,484   suitable_for   -383
#     cooked_by      -1,253   has_diet         -858   for_occasion    -58
#     in_context         -2   shares_flavor      -1   pairs_with       +1 (PMI recomputed
#                                                                        over a corpus two
#                                                                        ingredient nodes
#                                                                        smaller)
#     is_course / in_cuisine / from_region  -801 EACH
#
# Those last three are the check that the delta IS the withdrawal: they carry exactly one
# edge per row, and each fell by exactly 801.
# 2026-09-04 (V14 lexicon fixes L-1/L-5/L-6): 6,295,077 -> 6,295,101, +24. Reconciled to
# ZERO residual before this literal was touched, because a constant raised on inspection is
# how a real regression gets absorbed:
#
#   +27  contains_allergen edges for real classes
#          fish       +12   L-1: `catfish` did not fire; recipe 403 "Catfish Masala"
#                            asserted none_detected with ["catfish", ...] as ingredient 1
#          milk        +9   L-6 added 11 (`curds` had never fired in any version of the
#                            lexicon) and L-5 removed 2 (`chena` = elephant yam, not cheese)
#          coconut     +2 · sulphites +2 · egg +1 · tree_nuts +1
#   -3   `allergen::unknown` sentinel edges
#          179135, 201592, 201783 were unassessed and now carry a real class, so they left
#          the sentinel. All three are fully readable rows (unreadable_items = 0).
#   +0   every non-allergen relation
#   ----
#   +24  observed
# 2026-09-05 (V15/T5): 6,295,101 -> 6,294,706, -395. Reconciled to ZERO residual:
#   -395  contains_allergen -> mustard, one per dropped label
#     +0  every other allergen class
#     +0  every non-allergen relation
#
# The tadka/tempering blend rule was removed after a 100-row adjudication put its precision
# at 23/99 = 23.2% (Wilson 95% [16.0%, 32.5%]), against a threshold of 0.30 pre-registered
# before the sample was drawn. It labelled recipes mustard from a TECHNIQUE word while their
# own ingredient lists named cumin, hing, pepper or cashew -- overriding stated information
# rather than inferring unstated. The 124 rows whose INSTRUCTIONS name mustard were kept;
# the other 395 dropped. Record: scraped_indian_recipes/data/t5_mustard_removal_meta.json.
# MOVED AGAIN 2026-09-05 (V16 / L-4): 6,294,706 -> 6,294,719, delta +13.
#
# Reconciled to ZERO residual before this literal was touched, because a constant raised on
# inspection is how a real regression gets absorbed. The +13 is exactly the 13 class
# assertions V16 added across 12 rows, and every one is a per-class match:
#
#     sulphites  +6   ghee  +2   gluten  +2   asafoetida  +2   peanut  +1
#     +0         every other class, and every non-allergen relation
#
# V16 scans the raw `Ingredients` field alongside the parsed `IngredientsList`. It is not a
# new evidence channel -- it is the SAME source text read without the lossy comma split --
# so the union is strictly more faithful than either alone. L-4's original premise ("the
# parser drops food nouns") did not survive tracing: extract_jsonld.py:85 does no parsing,
# and the whole allergen exposure is 12 rows (0.005%). Record:
# scraped_indian_recipes/data/l4_raw_ingredients_v16_meta.json.
# MOVED 2026-09-05 (V18-V23 + P6): 6,294,719 -> 6,292,041, delta -2,678.
#
#     +337   allergen edges. V19 splits +7, V22 misspelled mustard +12, V23 ISSUE-15 +322 --
#            341 real class assertions MINUS 4 sentinel edges freed by rows that moved off
#            `unknown` on gaining their first real class. Verified per class.
#      -57   ingredient edges from the text passes (V18 withdrawal, V19 splits, V20 gloss).
#   -2,958   P6: 29 ingredient nodes dropped and every edge incident to them. MEASURED by
#            rebuilding the KG once with the pre-P6 ingredient_map and once with the post-P6
#            map -- 222,608/6,295,013 vs 222,579/6,292,055 -- rather than inferred.
#
# The -57 is the one term obtained by subtraction rather than observation. Measuring it would
# mean reverting the master to its pre-V18 state and rebuilding; it is recorded as derived so
# nobody later reads the reconciliation as three measurements when it is two and a remainder.
# MOVED 2026-09-05 (V24/V25 romanisation): 6,292,041 -> 6,292,116, delta +75.
#
#    +26   allergen edges: 27 class assertions (gluten +16, coconut +3, sulphites +3,
#          tamarind +3, milk +1, ghee +1) minus 1 sentinel edge freed by a row moving off
#          `unknown`. Measured per class against the master.
#    +49   has_ingredient: a translated word now matches the controlled vocabulary, where the
#          Devanagari matched nothing. Measured by importing `ings_of` from build_kg_v3 and
#          running it over MASTER_pre_romanise.bak.csv and the current master --
#          1,779,395 -> 1,779,444 -- rather than inferred.
#
# BOTH terms are measured; unlike the previous move there is no remainder. 143 rows changed
# ingredient count and some went DOWN, because translating a word can merge it with an
# English one already present and the vocabulary dedupes.
# MOVED 2026-09-05 (V26, complete translation): 6,292,116 -> 6,292,304, delta +188.
#
#    +35   allergen: 37 class assertions minus 2 sentinel edges freed. sulphites +23 is the
#          largest single movement of the romanisation effort -- the carriers are raisins,
#          dried fruit and vinegar, written as किशमिश / ಒಣದ್ರಾಕ್ಷಿ / કિસમિસ / വിനാഗിരി.
#          `unidecode` gives `kishamisha`, which the lexicon cannot read; `raisins` it can.
#   +153   has_ingredient: a translated word matches the controlled vocabulary where a
#          transliteration matched nothing. Measured with build_kg_v3's own `ings_of` over
#          MASTER_pre_retranslate.bak.csv and the current master (1,779,444 -> 1,779,597).
#
# Both terms measured; no remainder.
EXPECTED_KG_EDGES = 6_292_304
# --------------------------------------------------------------- allergen taxonomy
# 17 declared classes: the 16-token taxonomy (CLAUDE.md 6.3 — FALCPA 9 + South Asian 5 +
# EU FIC 2) plus `ghee`, a derivative marker added 2026-09-02. The TAXONOMY is still 16;
# the 17th token identifies one milk derivative and always co-occurs with `milk`.
#
# The South Asian five are an INVESTIGATOR-DEFINED extension, not a regulator-derived one --
# FSSAI's mandatory list is eight items and excludes all five. Stated here so the constant
# cannot be read as inheriting regulatory authority it does not have.
# Every token, its provenance (including the FSSAI qualification on the South Asian
# five) and the ghee-is-not-a-17th-allergen reasoning now live in the module, so they
# travel to all 26 former declaration sites instead of to this one.
DECLARED_ALLERGENS = set(_AT.TOKENS)

# Not a 17th class. The ABSENCE of an assessment, which under Codex CXC 80-2020 must never
# read as "no allergen present". Published as both a node flag and a sentinel edge.
UNASSESSED_TOKEN = _AT.UNASSESSED

# 2026-08-30 (P6): 68 -> 67. Exactly one `diet+ingredient` query (6 -> 5) lost its subject
# when the 16 zero-quantity-share tokens left the vocabulary. Every other template is
# unchanged: ingredient 12, diet 7, diet+allergenfree 7, course 6, cuisine 6, condition 12,
# diet+nutrient 12. A drop in any OTHER template would mean the vocabulary change reached
# further than intended - reconcile before raising this.
# 2026-09-01 (V7 non-recipe withdrawal): 67 -> 68, and the SET churned by 15 out / 16 in.
# Both are consequences of the corpus shrinking, not of a defect, and the reason is in
# `make_eval_queries_nx.py`:
#
#   * `rel_values()` selects target values whose recipe-count falls in [lo, hi], sorts by
#     count DESC, then takes an even STRIDE of `limit` of them. Removing 3,812 recipes moves
#     every ingredient's count, so both which values sit inside the window and where the
#     stride lands change. Hence "recipes with kokum" out, "recipes with lemongrass" in.
#   * `add()` drops any query with fewer than 3 relevant items. One more query clears that
#     guard than before -- "Jain recipes with roast" lands on exactly 3 -- which is the whole
#     of the 67 -> 68 move.
#
# The gold set is therefore NOT stable across corpus changes, and that is worth stating
# rather than hiding behind a constant: it is regenerated from the KG on every rebuild, so a
# result measured against one generation is not comparable to a result measured against
# another. Recorded in the V7 decision record.
#
# Noted while reconciling, NOT a regression: the ingredient vocabulary the generator draws
# from still contains non-ingredients and typos. The new set has `separated`, `liners`,
# `filet`; the old one had `crystals`, `capsicm`, `tatse`. Same class of noise before and
# after, and a P6-style vocabulary-hypothesis job rather than a benchmark one.
# 2026-09-02: 68 -> 67. ONE template moved — `diet+ingredient` 6 -> 5 — because a pairing
# fell below the generator's `len(relevant) >= 3` gold-set guard after the 801-row grihshobha
# withdrawal. Every other template is unchanged: ingredient 12, diet 7, diet+allergenfree 7,
# course 6, cuisine 6, condition 12, diet+nutrient 12.
#
# The query TEXT churns more than the count does, and that is expected rather than alarming:
# the generator selects by frequency banding, so a corpus that lost 801 rows and gained a
# token reshuffles which terms sit in each band. `recipes with chenna` left and
# `Diabetic-Friendly recipes without ghee` arrived — the 17th token being exercised by the
# benchmark, which is the point of adding it.
#
# The `diet::unknown` sentinel remains excluded from generation (see EXPECTED_KG_NODES): it
# clears the >=5-member threshold and would otherwise add two queries asking a retriever to
# return the recipes whose diet could not be assessed.
EXPECTED_BENCHMARK_QUERIES = 67
EXPECTED_CORPUS_BUILD = "v15"

# --------------------------------------------------------------------- release identity

DATASET_VERSION = "0.3.0"
CONCEPT_TITLE = "IndicRecipeNutri"

# --------------------------------------------------------------------------- parquet

PARQUET_COMPRESSION = "zstd"
PARQUET_COMPRESSION_LEVEL = 9

# Explicit row groups. A single group over 220k rows forces a full-table read for
# any column selection and is poor form in a published dataset.
PARQUET_ROW_GROUP_SIZE = 50_000

# ------------------------------------------------------------------------- PII sweep

# Applied to every string column of every published artefact by `verify_release.py`.
# A hit is a build failure, not a warning: section 3.5 promises a PII pass.
PII_PATTERNS = {
    "email": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    "phone_intl": r"\+\d{1,3}[\s-]?\d{6,14}\b",
    "phone_in": r"\b(?:0|91|\+91)?[\s-]?[6-9]\d{9}\b",
    # Anchored so it cannot fire on a decimal ("8.300000000000001 g") or on a long
    # digit run inside a URL slug. Neither is a card number.
    "credit_card": r"(?<![\d.\-])(?:\d[ -]?){13,16}(?![\d.])",
}

# Columns exempt from the PII sweep, with the reason. `URL` carries source identifiers
# by design (section 3.5 requires per-recipe source attribution); numeric-looking
# nutrition fields trip the credit-card pattern.
PII_EXEMPT_COLUMNS = {
    "URL": "source attribution required by section 3.5",
    "url": "same, on the knowledge-graph node table",
    "text_sha256": "hex digest, not free text",
    "recipe_id": "identifier, not free text",
    "Ingredients_recovered": "raw scraped ingredient text containing external links and IDs",
}

# ------------------------------------------------------- allergen audit lexicons

# Lexical evidence for each allergen, matched against the *parsed* ingredient list.
# This is the independent leg of the audit: the flag columns and the gold sets share a
# provenance, so agreement between them is a consistency check, not evidence of
# correctness. `NEGATIVE` removes the plant-substitute phrasings that make a bare
# "milk" match useless ("almond milk" in a vegan recipe is not dairy).
LEXICAL_EVIDENCE = {
    "milk": (
        r"\b(?:milk|curd|yogurt|yoghurt|dahi|paneer|panir|ghee|butter|cream|khoya|"
        r"mawa|khoa|malai|cheese|buttermilk|chenna|rabri)\b"
    ),
    "gluten": r"\b(?:wheat|maida|atta|semolina|sooji|rava|barley|rye|seitan|bread|pasta)\b",
    "mustard": r"\b(?:mustard|sarson|rai|kasundi)\b",
    "tree_nuts": r"\b(?:almond|cashew|walnut|pistachio|pecan|hazelnut|badam|kaju|akhrot)\b",
    "sesame": r"\b(?:sesame|til|tahini|gingelly)\b",
    "peanut": r"\b(?:peanut|groundnut|moongphali)\b",
    "soy": r"\b(?:soy|soya|tofu|edamame|tempeh)\b",
    "fish": r"\b(?:fish|anchovy|tuna|salmon|pomfret|rohu)\b",
    "shellfish": r"\b(?:prawn|shrimp|crab|lobster|squid|clam|mussel)\b",
    "egg": r"\b(?:egg|anda|albumen)\b",
    "coconut": r"\b(?:coconut|nariyal|khopra|thengai|kobbari|kopra)\b",
    "tamarind": r"\b(?:tamarind|imli|puli|chinch|chintapandu)\b",
    "fenugreek": r"\b(?:fenugreek|methi|kasuri\s+methi|vendhayam|menthulu)\b",
    "asafoetida": r"\b(?:asafoetida|hing|perungayam|inguva|kayam)\b",
    "celery": r"\b(?:celery)\b",
    "sulphites": r"\b(?:sulphite|sulfite|sulphur\s+dioxide|sulfur\s+dioxide)\b",
    # Added 2026-09-04. Its absence is why `Diabetic-Friendly recipes without ghee` (256
    # gold recipes) shipped with BOTH audit legs null -- leg A had no column and leg B had
    # no pattern, so nothing checked that gold set at all.
    #
    # WRITTEN HERE BY HAND, from the corpus, and deliberately NOT imported from
    # `allergen_lexicon_v14.DIRECT["ghee"]`. Leg B exists to be a second opinion; sourcing
    # it from the lexicon that produced the flags would leave the audit with two legs
    # sharing one blind spot. For a vernacular vocabulary this small the two statements
    # inevitably look similar -- the independence that matters is that neither is DERIVED
    # from the other, so an edit to one does not silently propagate to the other.
    #
    # Note `milk` above already matches `ghee` and `butter`. That is correct and is not a
    # substitute for this entry: it answers "does this recipe contain milk", not "does this
    # recipe contain ghee", and the ghee query asks the second question.
    "ghee": r"\b(?:ghee|ghi|clarified\s+butter|tup+a|neyyi|ney|ghrita|ghruta)\b",
}

# Phrases that must be REMOVED FROM THE TEXT before the lexicon is applied, because
# they contain an allergen token without being that allergen. They are stripped rather
# than used to veto the row: a recipe listing both "coconut milk" and "panir" must
# still register the panir.
NEGATIVE = {
    "milk": (
        r"\b(?:almond|soy|soya|coconut|oat|cashew|rice|hemp|peanut|flax|walnut|"
        r"macadamia|pea)[\s-]*milk\b"
        r"|\b(?:peanut|almond|cashew|nut|sunflower|sesame|seed|coconut|apple|"
        r"cocoa|shea)[\s-]*butter\b"
        r"|\bbutter(?:nut|\s*squash|\s*beans?|\s*lettuce|\s*paper|fly)\b"
        r"|\b(?:coconut|cashew|soy|oat)[\s-]*(?:cream|yogurt|yoghurt|curd|cheese)\b"
        r"|\bcream(?:\s*of\s*tartar|\s*style\s*corn)\b"
    ),
    "tree_nuts": r"\b(?:water\s*chestnut|nutmeg|coconut|butternut)\b",
    "gluten": r"\b(?:buck\s*wheat|buckwheat|gluten[\s-]*free)\b",
    "egg": r"\b(?:egg\s*plant|eggless|egg[\s-]*free)\b",
    "soy": r"\b(?:soy[\s-]*free)\b",
}

# The KEYS of the two dicts above are part of the declared vocabulary even though their
# VALUES are independent evidence. Asserted rather than derived, so a typo'd or retired
# token cannot sit in the audit unnoticed -- which is exactly how `ghee` came to have a
# benchmark query and no way to check it.
_bad = sorted(set(LEXICAL_EVIDENCE) - set(_AT.TOKENS))
assert not _bad, f"LEXICAL_EVIDENCE names undeclared allergen token(s): {_bad}"
_bad = sorted(set(NEGATIVE) - set(_AT.TOKENS))
assert not _bad, f"NEGATIVE names undeclared allergen token(s): {_bad}"
del _bad
