"""Single source of truth for the release contract.

Both the builders (`build_*.py`) and the validator (`verify_release.py`) import from
here, so the licence guard and the expected counts cannot drift apart.
"""

from __future__ import annotations

from pathlib import Path

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
]

# Prose columns are hashed into the rehydration index so a user who re-fetches the
# source page can verify they reconstructed the same text we measured.
REHYDRATION_KEY_COLUMNS = ["recipe_id", "URL", "SourceSite", "Lang"]

# --------------------------------------------------------------- expected invariants

# Every figure below is read from an artefact in the source tree, never asserted from
# memory. `kg_stats.json` is the authority for the KG counts; the corpus count is the
# row count of the v11 master.
# Rows present in the working master.
EXPECTED_SOURCE_RECIPES = 224_003

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

# Rows actually published.
EXPECTED_RECIPES = EXPECTED_SOURCE_RECIPES - len(EXCLUDED_RECIPE_IDS)
EXPECTED_KG_NODES = 227_500 - len(EXCLUDED_RECIPE_IDS)
EXPECTED_KG_EDGES = 6_169_926  # 6,169,941 less the 15 edges of the excluded recipe
EXPECTED_BENCHMARK_QUERIES = 66
EXPECTED_CORPUS_BUILD = "v11"

# --------------------------------------------------------------------- release identity

DATASET_VERSION = "0.1.0"
CONCEPT_TITLE = "IndicRecipeNutri"

# --------------------------------------------------------------------------- parquet

PARQUET_COMPRESSION = "zstd"
PARQUET_COMPRESSION_LEVEL = 9

# Explicit row groups. A single group over 224k rows forces a full-table read for
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
