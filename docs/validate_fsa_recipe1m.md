# Validation Report: FSA Traffic Light Band Logic

This report documents the validation of our FSA traffic light band logic against the ground-truth classifications in the Recipe1M+ dataset, as required by Milestone 7 (gate P2).

> ### ⚠️ What this report does and does not cover
>
> It validates the **per-100 g band function** — the code that turns a nutrient density into
> green/amber/red. That function is not the only thing determining the `fsa_*` columns that
> ship.
>
> Since the V17 pass, a **per-portion red override** also applies: a recipe whose *serving*
> exceeds the FSA per-portion red bounds (fat 21.0 g, saturates 6.0 g, sugars 27.0 g, salt
> 1.8 g, for portions greater than 100 g) is marked red for that nutrient regardless of its per-100 g
> band. Measured in the published payload: **88,266 cells across 55,312 recipes (25.2% of the
> corpus)** carry a light set this way rather than by the logic validated below. The override
> is monotone — it can only move a cell *toward* red, never away from it.
>
> So: **`fsa_*_pre_portion` is the column this report validates. `fsa_*` is what ships**, and
> for a quarter of the corpus the two differ. `fsa_portion_override_applied` marks the
> affected rows and `fsa_portion_g` records the portion size used. See
> `docs/DATA_DICTIONARY.md`.

## Validation Protocol
*   **Dataset:** Recipe1M+ dataset, consisting of **51,235 recipes** with both ground-truth FSA classifications and calculated nutrient values per 100 g. That count is the one recorded in `docs/weights_validation_dishlevel.json`.
*   **Evaluation:** Evaluated our band classification logic against Recipe1M+'s thresholds (older FSA revision) and current guidelines.

## Threshold Revision Differences

There is a version mismatch between the older FSA revision implemented in the published Recipe1M+ labels and the current guidance implemented in our v15 master database:

| Nutrient | Bound Type | Recipe1M+ (Older FSA) | Ours (Current FSA) |
|---|---|---|---|
| **Fat** | High Threshold | **20.0 g** | **17.5 g** |
| **Sugars** | High Threshold | **15.0 g** | **22.5 g** |
| **Saturates** | High Threshold | 5.0 g | 5.0 g |
| **Salt** | High Threshold | 1.5 g | 1.5 g |

All other boundaries (low thresholds for fat <= 3g, saturates <= 1.5g, sugars <= 5g, salt <= 0.3g) are identical between revisions.

## Agreement under Matched Thresholds

When evaluated using the matching older FSA thresholds to align with the Recipe1M+ ground truth, our band logic yields a perfect **100.000% agreement** across all classes:

| Nutrient | Agreement Rate | Status |
|---|---:|---|
| **Saturates** | 100.00000% | matches reference |
| **Salt** | 100.00000% | matches reference |
| **Fat** | 100.00000% | matches reference |
| **Sugars** | 100.00000% | matches reference |
| **Overall (All 4 Match)** | **100.00000%** | **all four agree** |

## Conclusions

1.  **No disagreement with the reference implementation, on this data.** Holding the
    thresholds equal, our band function reproduces Recipe1M+'s published labels on all
    51,235 recipes, including at the boundaries. That is the strongest available evidence
    that the arithmetic, the rounding and the inclusive/exclusive edges match.

    It is **not** proof of zero bugs, and the earlier wording of this line ("proves our
    classification code contains zero calculation, rounding, or boundary-handling bugs")
    claimed more than the experiment can deliver. Agreement between two implementations of
    the same rule is silent about anything both get wrong, and the test exercises only the
    inputs Recipe1M+ happens to contain — it says nothing about nutrient values outside that
    range, about missing or null inputs, or about the per-portion override above, which has
    no reference implementation to be compared against at all.

2.  **Deliberate standard:** We implement the **current UK FSA guidance**, which is why the
    shipped bands differ from Recipe1M+'s where the two revisions disagree (fat and sugars).
    The agreement figures above are therefore measured under *matched* thresholds, and are a
    test of the code, not of the standard.

3.  **Version note.** This report was written against the v12 master and the threshold table
    above was checked again at v15; the band logic and the thresholds are unchanged between
    them. The corpus generation it now describes is the published payload, 219,386 rows.
