#!/usr/bin/env python3
r"""Machine-readable unit and basis declaration for every dimensioned column.

WHY THIS FILE EXISTS
--------------------
Before 2026-09-02 **no unit was declared anywhere a machine could read it**: 0 of the 236
Arrow fields in `recipes_structured.parquet` carried field metadata, every pandas column
metadata entry was `null`, and the 298-row DATA_DICTIONARY table has no unit column. A
consumer had to guess, and two columns in the same family have DIFFERENT units:

    per100g_sodium   milligrams per 100 g
    per100g_salt     GRAMS per 100 g          (= sodium * 0.0025, exactly, on all 155,978 rows)

Guessing wrong there is a 400x error on a sodium figure, in a corpus whose whole point is
nutrition. That is the gap this closes.

HOW THE UNITS WERE ESTABLISHED
------------------------------
The build never recorded them, so they were DERIVED from magnitude against known
physiological ranges, and the derivation is recorded per column in `basis` so a reader can
check the reasoning rather than trust it. Two independent cross-derivations fix the DV
reference, which was also undeclared:

    DV_Protein median 14%  x  50 g   (US FDA 2016 DV) = 7.00 g   vs Nut_Protein median 6.79 g
    DV_Folate  median  7%  x 400 ug  (US FDA 2016 DV) = 28.0 ug  vs Nut_Folate  median 29.36 ug

Both land within a rounding step of the observed median, from different nutrients with
different DV magnitudes, so the reference set is the **US FDA 2016 Daily Values**.

WHERE A UNIT IS GENUINELY UNRESOLVED it is written as the literal string `TBD` with the
question stated, per the workspace convention on unknown values — never a plausible-looking
guess. Two such cases remain and both are real ambiguities in the upstream source, not
oversights here.
"""
from __future__ import annotations

# unit          the physical unit, or "1" for a dimensionless ratio, or "TBD"
# basis         what the value is per: "dish", "100g", "serving", "row", "energy"
# domain        [lo, hi] where a physical bound exists, else None
# basis_note    how the unit was established, or the open question if TBD
U = dict

_G = "g"
_MG = "mg"
_UG = "ug"          # ASCII throughout: this file is read by tooling, not only by people


def _n(unit, note, domain=None):
    return U(unit=unit, basis="dish", domain=domain, basis_note=note)


NUTRIENT_MAGNITUDE = "derived from median magnitude against physiological range 2026-09-02"

COLUMN_UNITS: dict[str, dict] = {
    # ---- energy and macros, per dish -----------------------------------------------
    "Nut_Calories": _n("kcal", f"median 253 kcal/dish; {NUTRIENT_MAGNITUDE}"),
    "Nut_Protein": _n(_G, f"median 6.79 g/dish; {NUTRIENT_MAGNITUDE}"),
    "Nut_Fat": _n(_G, f"median 9.38 g/dish; {NUTRIENT_MAGNITUDE}"),
    "Nut_Carbohydrates": _n(_G, f"median 24.0 g/dish; {NUTRIENT_MAGNITUDE}"),
    "Nut_SaturatedFat": _n(_G, NUTRIENT_MAGNITUDE),
    "Nut_TransFat": _n(_G, NUTRIENT_MAGNITUDE),
    "Nut_PolyunsaturatedFat": _n(_G, NUTRIENT_MAGNITUDE),
    "Nut_MonounsaturatedFat": _n(_G, NUTRIENT_MAGNITUDE),
    "Nut_Fiber": _n(_G, NUTRIENT_MAGNITUDE),
    "Nut_Sugar": _n(_G, NUTRIENT_MAGNITUDE),
    # ---- minerals and vitamins, per dish -------------------------------------------
    "Nut_Sodium": _n(_MG, f"median 342; g would be absurd for a dish; {NUTRIENT_MAGNITUDE}"),
    "Nut_Cholesterol": _n(_MG, f"median 4.74; {NUTRIENT_MAGNITUDE}"),
    "Nut_Potassium": _n(_MG, NUTRIENT_MAGNITUDE),
    "Nut_Calcium": _n(_MG, f"median 61.7; {NUTRIENT_MAGNITUDE}"),
    "Nut_Iron": _n(_MG, f"median 2.37; {NUTRIENT_MAGNITUDE}"),
    "Nut_Magnesium": _n(_MG, NUTRIENT_MAGNITUDE),
    "Nut_Phosphorus": _n(_MG, NUTRIENT_MAGNITUDE),
    "Nut_Zinc": _n(_MG, f"median 0.80; {NUTRIENT_MAGNITUDE}"),
    "Nut_Copper": _n(_MG, f"median 0.14; ug would put a dish at 140 ug, far below "
                          f"typical dietary copper; {NUTRIENT_MAGNITUDE}"),
    "Nut_Manganese": _n(_MG, f"median 0.56; {NUTRIENT_MAGNITUDE}"),
    "Nut_VitaminC": _n(_MG, f"median 2.84; {NUTRIENT_MAGNITUDE}"),
    "Nut_VitaminE": _n(_MG, f"median 0.73, alpha-tocopherol; {NUTRIENT_MAGNITUDE}"),
    "Nut_Thiamin": _n(_MG, f"median 0.11; {NUTRIENT_MAGNITUDE}"),
    "Nut_Riboflavin": _n(_MG, f"median 0.12; {NUTRIENT_MAGNITUDE}"),
    "Nut_Niacin": _n(_MG, f"median 1.08; {NUTRIENT_MAGNITUDE}"),
    "Nut_VitaminK": _n(_UG, f"median 6.08; {NUTRIENT_MAGNITUDE}"),
    "Nut_VitaminB12": _n(_UG, f"median 0.01; {NUTRIENT_MAGNITUDE}"),
    "Nut_Selenium": _n(_UG, f"median 4.62; {NUTRIENT_MAGNITUDE}"),
    "Nut_VitaminB6": _n(_MG, f"pyridoxine is reported in mg in every reference intake "
                             f"(US FDA DV 1.7 mg); {NUTRIENT_MAGNITUDE}"),
    "nut_suppl_fct_frac": U(unit="1", basis="row", domain=[0, 1],
                            basis_note="fraction of the nutrition vector supplied by a "
                                       "supplementary food-composition table, 0-1"),
    "Nut_VitaminD": _n(_UG, f"median 0, p95 1.52; IU would be ~40x larger, so this is "
                            f"micrograms not IU; {NUTRIENT_MAGNITUDE}"),
    # ---- the two genuinely unresolved ones -----------------------------------------
    "Nut_VitaminA": _n(_UG, "MAGNITUDE resolves ug vs IU (median 25.9; IU would be ~10x "
                            "larger). What is NOT resolved is whether it is ug RAE or ug "
                            "retinol: TBD. Check which USDA field the enrichment read "
                            "(VITA_RAE vs VITA_IU vs RETOL). Consequence: RAE and retinol "
                            "differ by up to 12x for plant-source carotenoids, which is most "
                            "of this corpus."),
    "Nut_Folate": _n(_UG, "MAGNITUDE resolves ug (median 29.36). Whether it is total folate "
                          "or ug DFE is TBD, and it matters because DV_Folate divides by the "
                          "400 ug DFE Daily Value: if the numerator is total folate the "
                          "quotient is not a DFE percentage. Check the USDA field read "
                          "(FOL vs FOLDFE)."),
    # ---- per 100 g. NOTE THE TWO DIFFERENT UNITS UNDER ONE PREFIX ------------------
    "per100g_kcal": U(unit="kcal", basis="100g", domain=[0, 900],
                      basis_note="900 kcal/100g is pure fat, the physical ceiling for any "
                                 "food; enforced by gate M17"),
    "per100g_protein": U(unit=_G, basis="100g", domain=[0, 100], basis_note="mass fraction"),
    "per100g_carb": U(unit=_G, basis="100g", domain=[0, 100], basis_note="mass fraction"),
    "per100g_fat": U(unit=_G, basis="100g", domain=[0, 100], basis_note="mass fraction"),
    "per100g_satfat": U(unit=_G, basis="100g", domain=[0, 100], basis_note="mass fraction"),
    "per100g_sugar": U(unit=_G, basis="100g", domain=[0, 100], basis_note="mass fraction"),
    "per100g_fiber": U(unit=_G, basis="100g", domain=[0, 100], basis_note="mass fraction"),
    "per100g_sodium": U(unit=_MG, basis="100g", domain=[0, 100_000],
                        basis_note="MILLIGRAMS per 100 g — NOT grams, unlike every other "
                                   "per100g_ mass column. 110,235 rows exceed 100, which is "
                                   "correct for mg and would be impossible for g."),
    "per100g_salt": U(unit=_G, basis="100g", domain=[0, 100],
                      basis_note="GRAMS per 100 g. Exactly per100g_sodium * 0.0025 on all "
                                 "155,978 rows where both are present (the 2.5 g salt per "
                                 "1 g sodium molar conversion, with the mg->g factor). So "
                                 "the two columns differ in unit AND in scale by 400x."),
    # ---- proportions ---------------------------------------------------------------
    "ProteinPct": U(unit="%", basis="energy", domain=[0, 100],
                    basis_note="percent of ENERGY, not of mass. Medians 11/45/42 sum to 98, "
                               "consistent with an energy split and not with a mass split."),
    "CarbPct": U(unit="%", basis="energy", domain=[0, 100], basis_note="percent of energy"),
    "FatPct": U(unit="%", basis="energy", domain=[0, 100], basis_note="percent of energy"),
    "Nut_MatchCov": U(unit="1", basis="row", domain=[0, 1], basis_note="fraction, 0-1"),
    "Nut_Confidence": U(unit="1", basis="row", domain=[0, 1], basis_note="fraction, 0-1"),
    "confident_coverage": U(unit="1", basis="row", domain=[0, 1], basis_note="fraction, 0-1"),
    "dish_type_agreement": U(unit="1", basis="row", domain=[0, 1], basis_note="fraction, 0-1"),
    "ing_weight_confident_frac": U(unit="1", basis="row", domain=[0, 1],
                                   basis_note="fraction, 0-1"),
    "atwater_relerr": U(unit="1", basis="row", domain=[0, None],
                        basis_note="relative error, dimensionless; not bounded above"),
    # ---- other dimensioned columns -------------------------------------------------
    "PrepTimeMins": U(unit="min", basis="row", domain=[0, None], basis_note="declared in name"),
    "CookTimeMins": U(unit="min", basis="row", domain=[0, None], basis_note="declared in name"),
    "TotalTimeMins": U(unit="min", basis="row", domain=[0, None], basis_note="declared in name"),
    "grams_per_serving_v3": U(unit=_G, basis="dish", domain=[0, None],
                              basis_note="THE NAME IS WRONG: median 705 g is a whole-dish "
                                         "weight, not one serving. Kept for compatibility; "
                                         "the basis declared here is authoritative over the "
                                         "name."),
    "grams_per_serving_predensity": U(unit=_G, basis="dish", domain=[0, None],
                                      basis_note="as grams_per_serving_v3, pre-correction"),
    # V17, 2026-09-05. The portion the FSA per-portion red override was evaluated against.
    # basis="serving" and NOT "dish" -- it is grams_per_serving_v3 DIVIDED by Servings_num,
    # which is the correction that column's own name fails to make. Publishing it is what
    # lets a reader check the override's arithmetic on any row instead of trusting it. NULL
    # where the serving count was unusable (60,519 rows); those rows the override never
    # reached, and a null here is the record of that, not a missing value to be filled.
    "fsa_portion_g": U(unit=_G, basis="serving", domain=[0, None],
                       basis_note="grams_per_serving_v3 / Servings_num — a real per-serving "
                                  "weight, unlike the column it is derived from. Null where "
                                  "Servings_num is outside 1..20, meaning the FSA "
                                  "per-portion rule was not applicable rather than not "
                                  "triggered."),
    "GlycemicLoad_numeric": U(unit="1", basis="serving", domain=[0, None],
                              basis_note="glycemic load is dimensionless by construction"),
    "Servings_num": U(unit="1", basis="row", domain=[1, None], basis_note="count of servings"),
    "RatingAverage": U(unit="1", basis="row", domain=[0, 5],
                       basis_note="0-5 stars for most rows, but 373 rows carry a 0-100 "
                                  "percentage on the same column — see the mixed-scale "
                                  "finding; the domain here is the intended one"),
    "RatingCount": U(unit="1", basis="row", domain=[0, None], basis_note="count"),
    "StepCount": U(unit="1", basis="row", domain=[0, None], basis_note="count"),
    "badlist_n_items": U(unit="1", basis="row", domain=[0, None], basis_note="count"),
    "fsa_n_red": U(unit="1", basis="row", domain=[0, 4], basis_note="count of red lights, 0-4"),
    "fsa_n_green": U(unit="1", basis="row", domain=[0, 4],
                     basis_note="count of green lights, 0-4"),
    "ingredient_items_total": U(unit="1", basis="row", domain=[0, None],
                               basis_note="parsed ingredient items on the row — the "
                                          "denominator for ingredients_unreadable_items"),
    "ingredients_unreadable_items": U(
        unit="1", basis="row", domain=[0, None],
        basis_note="items in a script the allergen lexicon cannot match (Devanagari, "
                   "Bengali, Gurmukhi, Gujarati, Odia, Tamil, Telugu, Kannada, Malayalam, "
                   "Arabic, CJK, Thai, Hangul). Non-zero means an allergen ABSENCE claim on "
                   "this row is not supported — see allergen_scan_incomplete"),
    "fsa_n_labelled": U(unit="1", basis="row", domain=[0, 4],
                        basis_note="how many of the four FSA lights are set on this row — "
                                   "the denominator for fsa_n_red / fsa_n_green, which is "
                                   "not 4 everywhere because light coverage is partial"),
    "dup_family_size": U(unit="1", basis="row", domain=[1, None], basis_note="count"),
    "recipe_id": U(unit="1", basis="row", domain=None, basis_note="identifier, not a quantity"),
    "dup_family_id": U(unit="1", basis="row", domain=None,
                       basis_note="identifier, not a quantity"),
}

# The US FDA 2016 Daily Values every DV_* column is a percentage of. Derived, not assumed —
# see the module docstring for the two independent cross-checks.
DV_REFERENCE = {
    "standard": "US FDA Daily Values, 2016 Nutrition Facts label revision (21 CFR 101.9)",
    "how_established": "derived from the data: DV_Protein median 14% x 50 g = 7.00 g against "
                       "an observed Nut_Protein median of 6.79 g, and DV_Folate median 7% x "
                       "400 ug = 28.0 ug against an observed Nut_Folate median of 29.36 ug. "
                       "Two nutrients, two different DV magnitudes, both consistent.",
    "caveat": "NOT an Indian reference intake. ICMR-NIN 2020 RDAs differ, and for an "
              "India-focused corpus that is a limitation a consumer must know about.",
    "values": {
        "DV_Protein": [50, _G], "DV_Fiber": [28, _G], "DV_Iron": [18, _MG],
        "DV_Calcium": [1300, _MG], "DV_VitaminC": [90, _MG], "DV_VitaminA": [900, _UG],
        "DV_Folate": [400, _UG], "DV_VitaminB12": [2.4, _UG], "DV_VitaminD": [20, _UG],
        "DV_Zinc": [11, _MG],
    },
}
for _c in DV_REFERENCE["values"]:
    COLUMN_UNITS[_c] = U(unit="%", basis="dish", domain=[0, None],
                         basis_note=f"percent of the US FDA 2016 Daily Value "
                                    f"({DV_REFERENCE['values'][_c][0]} "
                                    f"{DV_REFERENCE['values'][_c][1]}); see DV_REFERENCE")

# Shadow families inherit the unit of the column they shadow, so they are declared
# programmatically rather than by hand — 41 columns that would otherwise be 41 chances to
# drift out of step with their parent.
_PRIMARY = dict(COLUMN_UNITS)          # snapshot BEFORE any suffix pass — iterating the live
                                       # dict compounds the suffixes (X_uncorrected_orig) and
                                       # inflated this registry to 600 entries for 96 columns
# `_pre_rN` was added 2026-09-02: the R6/R7/R8 passes preserve prior values under that
# suffix, and the units gate correctly refused the release when ProteinPct_pre_r8 and its
# two siblings shipped undeclared. Keeping the suffix list here — rather than declaring each
# shadow by hand — is what makes a new repair pass inherit its parent's unit automatically.
_SHADOW_SUFFIXES = ("_uncorrected", "_predensity", "_orig",
                    "_pre_r5", "_pre_r6", "_pre_r7", "_pre_r8", "_pre_r9")
for _suffix, _why in (("_uncorrected", "pre-correction value of"),
                      ("_predensity", "pre-density-correction value of"),
                      ("_orig", "original source value of"),
                      ("_pre_r5", "value before the R5 pass of"),
                      ("_pre_r6", "value before the R6 pass of"),
                      ("_pre_r7", "value before the R7 pass of"),
                      ("_pre_r8", "value before the R8 pass of"),
                      ("_pre_r9", "value before the R9 pass of")):
    for _base, _decl in _PRIMARY.items():
        if _base.endswith(_SHADOW_SUFFIXES):
            continue                   # already a shadow; do not stack a second suffix
        _shadow = _base + _suffix
        if _shadow not in COLUMN_UNITS:
            COLUMN_UNITS[_shadow] = dict(_decl, basis_note=f"{_why} {_base}")


# kg_nodes.parquet restates all 32 nutrient columns under a SECOND prefix, `n_Calories`
# beside the corpus's `Nut_Calories`, same quantity and same unit. The duplication is a
# separate finding; declaring the alias here means the KG's copy cannot be read with a
# different unit from the corpus's, which is the failure this registry exists to prevent.
COLUMN_UNITS["glycemic"] = U(
    unit="1", basis="serving", domain=[0, None],
    basis_note="kg_nodes alias of GlycemicLoad_numeric; glycemic load is dimensionless by "
               "construction. Typed as a real number since 2026-09-02 — it previously "
               "shipped as a stringified float using the empty string as a second missing "
               "value beside real nulls, so filtering it required knowing both.")

for _base, _decl in list(_PRIMARY.items()):
    if _base.startswith("Nut_"):
        COLUMN_UNITS.setdefault(
            "n_" + _base[4:],
            dict(_decl, basis_note=f"kg_nodes alias of {_base} — same quantity, same unit; "
                                   f"the duplicate prefix is a schema defect, not a "
                                   f"different measurement"))


def declaration_for(column: str) -> dict | None:
    return COLUMN_UNITS.get(column)


def undeclared(columns) -> list[str]:
    """Numeric columns with no unit declaration. The gate asserts this is empty."""
    return [c for c in columns if c not in COLUMN_UNITS]
