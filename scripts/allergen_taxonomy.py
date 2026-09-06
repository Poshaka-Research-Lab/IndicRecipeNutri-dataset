r"""Single source of truth for the allergen token set.

Written 2026-09-04 after `ghee` was added to four of NINE declaration sites and not the
other five. The result shipped: a release whose knowledge graph carries 17 allergen classes
(33,538 `contains_allergen -> ghee` edges) and whose tabular surfaces carry 16 and no ghee,
past 63 green gates -- because every gate compared one surface against another declaration
that agreed with it. A published benchmark gold set (`Diabetic-Friendly recipes without
ghee`, 256 recipes) shipped with BOTH audit legs null for the same reason.

Precedent: `paths.py`, one directory up, written 2026-08-28 for the same class of failure
(102 files hard-coding a root that had moved). The fix there was a resolver, not a sed. The
fix here is a declaration, not a sed.

WHAT THIS MODULE IS
-------------------
It declares WHICH classes exist.

WHAT IT IS NOT
--------------
It does NOT declare how to recognise them. That is:

  * `scraped_indian_recipes/data/lexicons/allergen_lexicon_v14.py` -- the production
    evidence, the patterns that actually label the corpus; and
  * `IndicRecipeNutri-dataset/scripts/build_benchmark.py::LEXICAL_EVIDENCE` -- an
    INDEPENDENT second opinion, used by leg B of the gold-set audit.

Those two are hand-written, and they must stay hand-written and separate. Deriving
`LEXICAL_EVIDENCE` from the lexicon looks like obvious de-duplication and would be wrong:
leg B stops being a second opinion the moment it shares a source with leg A, and the
benchmark would be left with two legs sharing one blind spot. That is the circularity
`audit_corpus.py` was rewritten to disclose on 2026-09-02.

    The token set is declared ONCE.
    The evidence for each token is written more than once ON PURPOSE.

Gate M27 asserts `set(allergen_lexicon_v14.DIRECT) == set(TOKENS)` -- two independent
statements, one equality check. That check is the reason this module does not simply import
the lexicon and read its keys.

Usage
-----
    import sys, os
    sys.path.insert(0, os.environ.get("DATASETS_ROOT", r"D:\datasets"))
    import allergen_taxonomy as AT

    AT.TOKENS            # 17 -- what may appear in a label
    AT.TAXONOMY_16       # the taxonomy proper; `ghee` is not a member
    AT.has_column("soy") # "has_soy"

`paths.bootstrap()` already puts the datasets root on `sys.path`, so any script that calls
it can `import allergen_taxonomy` with no further plumbing.
"""

from __future__ import annotations

import hashlib
import json

# ---------------------------------------------------------------- the taxonomy

#: FALCPA 9. US Food Allergen Labeling and Consumer Protection Act.
FALCPA_9: tuple[str, ...] = (
    "milk", "egg", "fish", "shellfish", "tree_nuts", "peanut", "gluten", "soy", "sesame",
)

#: INVESTIGATOR-DEFINED, not regulator-derived.
#:
#: FSSAI's mandatory allergen list is eight items and excludes all five of these, and no
#: system in the 2025-26 literature covers them either. CLAUDE.md 6.3 requires this to be
#: stated wherever the five appear, because the earlier wording read as though the set had
#: inherited a regulatory authority it does not have. It is carried HERE, in the module,
#: so the qualification travels to every import site instead of living in one comment that
#: five copies of the list did not have.
#:
#: The justification owed is South Asian clinical-prevalence evidence. Until that citation
#: is attached, this docstring is the disclosure.
SOUTH_ASIAN_5: tuple[str, ...] = (
    "mustard", "fenugreek", "asafoetida", "tamarind", "coconut",
)

#: EU FIC Annex II items carried because the corpus and every gate implement them.
EU_FIC_2: tuple[str, ...] = ("celery", "sulphites")

#: NOT a 17th allergen. A DERIVATIVE MARKER inside the allergen vocabulary, added
#: 2026-09-02 on the researcher's ruling so that ghee is separately filterable -- the
#: annotator dispute blocking the T12 held-out run was whether ghee "counts as milk", and
#: a row can now say both things at once instead of one standing in for the other.
#:
#: IT DOES NOT REPLACE `milk`, and that is the load-bearing part. 33,552 rows name ghee;
#: on 16,790 of them ghee is the ONLY milk evidence in the row, so dropping milk when ghee
#: is present would remove a milk warning from 7.6% of the corpus. Ghee is clarified
#: butter: water and most milk solids are removed, but residual casein remains and allergy
#: guidance does not treat it as milk-free. Gate M26 asserts the co-occurrence.
DERIVATIVE_MARKERS: tuple[str, ...] = ("ghee",)

#: The taxonomy proper -- 16. This is the number to quote when describing the taxonomy.
TAXONOMY_16: tuple[str, ...] = FALCPA_9 + SOUTH_ASIAN_5 + EU_FIC_2

#: What may legitimately appear in an allergen label -- 17. This is the set every
#: declaration site must agree with.
TOKENS: tuple[str, ...] = TAXONOMY_16 + DERIVATIVE_MARKERS

#: A derivative marker implies the class it is derived from. Emitted ALONGSIDE, never
#: INSTEAD OF. Read by gate M26 and by the KG's `derived_from` edges.
DERIVED_FROM: dict[str, str] = {"ghee": "milk"}

#: The ABSENCE of an assessment. Under Codex CXC 80-2020 an operator must "never guess or
#: assume that an allergen is not present", so this must never read as "no allergen
#: present". Not a class, and never a member of TOKENS.
UNASSESSED = "unknown"

#: An assessment that ran and found nothing. Distinct from UNASSESSED, and the distinction
#: is the whole fail-closed design.
NONE_DETECTED = "none_detected"

#: Both sentinels, for sites that need to subtract them from an observed token set.
SENTINELS: frozenset[str] = frozenset({UNASSESSED, NONE_DETECTED})

PROVENANCE: dict[str, str] = {
    **{t: "falcpa9" for t in FALCPA_9},
    **{t: "sa5_investigator_defined" for t in SOUTH_ASIAN_5},
    **{t: "eu_fic2" for t in EU_FIC_2},
    **{t: "derivative_marker" for t in DERIVATIVE_MARKERS},
}

# ---------------------------------------------------------------- accessors


def has_column(token: str) -> str:
    """The boolean flag column for a token: `soy` -> `has_soy`.

    One function so the naming convention is not re-implemented at each site; the
    benchmark's `ALLERGEN_COLUMN` and `migrate_schema`'s wide-table writer disagreed about
    which tokens existed precisely because each built these names for itself.
    """
    if token not in TOKENS:
        raise KeyError(
            f"{token!r} is not a declared allergen token. Extend TOKENS deliberately "
            f"-- do not let an unrecognised token through a safety label."
        )
    return f"has_{token}"


def implies(token: str) -> set[str]:
    """The classes a token asserts, including what it is derived from.

    `implies("ghee") == {"ghee", "milk"}`. Use when expanding a label for a safety
    decision; do NOT use when writing the label, which stays literal.
    """
    out = {token}
    parent = DERIVED_FROM.get(token)
    if parent:
        out.add(parent)
    return out


# ---------------------------------------------------------------- CARE bridge

#: CARE's constraint vocabulary is FALCPA-shaped. CARE keeps a GENERATED copy of this map
#: (`CARE/intent/_taxonomy_generated.py`) rather than importing this module, because CARE
#: must stay runnable standalone.
#:
#: The `ghee -> Dairy` row is decision D-1: ghee maps to the same constraint as milk and is
#: emitted alongside it, never instead of it. The alternative -- a separate `Ghee`
#: constraint -- would split one safety class across two tokens in a system whose intent
#: parser was not built for it.
#:
#: The six tokens with no CARE constraint (mustard, fenugreek, asafoetida, tamarind,
#: coconut, celery, sulphites) are absent because CARE's vocabulary does not carry them,
#: NOT because they are unimportant. A KeyError here would be a fail-open, so callers must
#: use `.get()` and treat a miss as "CARE cannot express this constraint".
CARE_CONSTRAINT: dict[str, str] = {
    "milk": "Dairy",
    "egg": "Eggs",
    "fish": "Fish",
    "shellfish": "Shellfish",
    "tree_nuts": "TreeNuts",
    "peanut": "Peanuts",
    "gluten": "Wheat",
    "soy": "Soy",
    "sesame": "Sesame",
    "ghee": "Dairy",
}

# ---------------------------------------------------------------- integrity


def payload() -> str:
    """The canonical bytes the CARE copy is hashed against.

    Comments and docstrings are excluded ON PURPOSE, so this file's prose can be edited --
    a citation added to the SOUTH_ASIAN_5 note, say -- without breaking a downstream repo
    that has not changed.
    """
    return json.dumps(
        {
            "tokens": list(TOKENS),
            "taxonomy_16": list(TAXONOMY_16),
            "provenance": PROVENANCE,
            "derived_from": DERIVED_FROM,
            "unassessed": UNASSESSED,
            "none_detected": NONE_DETECTED,
            "care": CARE_CONSTRAINT,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def source_hash() -> str:
    """Short digest of `payload()`. Compared against the CARE copy by gate M27."""
    return hashlib.sha256(payload().encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------- self-checks
#
# Cheap invariants, asserted at import so a bad edit fails at the first consumer rather
# than at the next rebuild.

assert len(TAXONOMY_16) == 16, f"taxonomy is {len(TAXONOMY_16)}, not 16"
assert len(TOKENS) == 17, f"token set is {len(TOKENS)}, not 17"
assert len(set(TOKENS)) == len(TOKENS), "duplicate token"
assert set(PROVENANCE) == set(TOKENS), "PROVENANCE and TOKENS disagree"
assert not SENTINELS & set(TOKENS), "a sentinel leaked into TOKENS"
assert all(parent in TOKENS for parent in DERIVED_FROM.values()), "derives from a non-token"
assert set(DERIVED_FROM) == set(DERIVATIVE_MARKERS), "marker without a parent, or vice versa"
assert set(CARE_CONSTRAINT) <= set(TOKENS), "CARE maps a token that is not declared"


if __name__ == "__main__":
    print(f"tokens ({len(TOKENS)}): {', '.join(TOKENS)}")
    print(f"taxonomy ({len(TAXONOMY_16)}): {', '.join(TAXONOMY_16)}")
    print(f"derivative markers: {DERIVED_FROM}")
    print(f"sentinels: {sorted(SENTINELS)}")
    print(f"source_hash: {source_hash()}")
