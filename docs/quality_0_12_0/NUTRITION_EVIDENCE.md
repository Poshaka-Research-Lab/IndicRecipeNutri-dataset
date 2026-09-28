# Nutrition estimator evidence

The new sidecar exposes existing estimator assumptions without changing nutrients, grams, per100g values or threshold decisions. G9/G10 still require independent portion/density reference evidence before accuracy claims. G18's numerator/denominator model mismatch is not repaired by relabeling an estimator as accurate.

Inputs are projected from recipes_structured, ingredients_weights and ingredients_nutrition. Every current occurrence key is matched, occurrence grams agree across the two ingredient tables, and the published ing_weight_confident_frac is reproduced within 1e-12. This agreement does not establish agreement with the historical whole-dish denominator used in per100g calculations.

The sidecar contains line counts, assumed C/D/E lines, flat20 E lines, untiered/unassessed lines, A/B line fraction, estimated A/B mass fraction, partial available-energy A/B fraction, original basis fields, and the existing per100g_confident AND fraction>=0.8 predicate. Empty denominators stay null. Partial energy denominators are explicitly disclosed. No mass is invented for the 609 ALL untiered rows with missing grams.

Measured DEV: 167115/208290 recipes have assumed-weight lines; 141338 have flat20 lines; 81270 satisfy the existing high-confidence predicate; 689 have no occurrence rows; 585 occurrence rows are untiered. These are estimator/construction counts, not measured accuracy. The new sidecar records `not_independently_validated_here` rather than claiming a reference validation.

Authoritative source trace: `scraped_indian_recipes/data/recompute_per100g_v13.py` uses the available declared/alternate weight and sets confidence to good AND NOT use_alt AND NOT clipped. Historical ingredient-density and later exclusion passes narrow the result. The K006 confidence-trace report is supporting historical evidence, not a newly rerun accuracy experiment. Source consumer paths and their hashes must remain in the final provenance packet.
