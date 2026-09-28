# Nutrition, diet and historical generator trace

Status: engineering trace completed; independent reference accuracy and certification are not established. Source file digests are in `model_trace_receipt.json`.

## G18: nutrient numerator and weight denominator

The inspected upstream `scraped_indian_recipes/data/recompute_per100g_v13.py` computes per-100 g values as `Nut_X * Servings_num / Wf * 100`. It takes the primary weight from `grams_per_serving_v3`, replaces clipped or missing values with the ingredient-layer total, and retries an implausible energy value using the alternate weight. Its confidence predicate is `good & ~use_alt & ~clipped`. Later integrity passes can clear confidence further.

This is a path/plausibility predicate. It does not establish reference weight or nutrient accuracy. The K006 confidence trace identifies a separate upstream nutrient gram model and whole-dish weight model. Its reported historical comparisons are not new measurements from this release work.

The new nutrition sidecar reproduces the existing A/B ingredient-count fraction and checks the current ingredient weight/nutrition tables against each other. Neither this equality nor a mass-weighted fraction proves that the legacy whole-dish denominator matches the numerator's model. The 0.8 rule remains an estimator rule. G18 is documented and made observable, not repaired by renaming confidence. A future coherent recomputation must version numerator and denominator together and validate them against a permitted independent reference before replacing legacy values.

## G21: no admissible positive diet evidence

The inspected K006 `contracts.py::PASS_ADMISSIBLE_SOURCES` gives halal, kosher and Jain empty positive-source sets. Its `adapters/data.py` supplies violations from the relevant ingredient flags; it does not generate positive certification from the absence of a detected violation. This is an evidence limitation, not a missing-value defect that can be fixed by filling PASS.

No new certification source was collected in this update. Existing cultural-context labels remain inferred and are not converted into certification. UNKNOWN remains appropriate where positive evidence is unavailable. The new synthetic generator does not model dietary restrictions and must not be interpreted as producing suitable menus.

## G22: historical interaction drift

The received K006 audit reports that four served items changed attributes after the legacy log was generated. Their current legacy interaction counts were independently recounted here:

| Recipe ID | Interaction rows |
|---|---:|
| 220860 | 33 |
| 220865 | 44 |
| 220868 | 238 |
| 220902 | 35 |
| Total | 350 |

The historical feature comparison is attributed to `INTERACTION_AUDIT.md`; it was not rerun in this step. That audit identifies generator commit `8260b4d` and generation corpus object beginning `ec49a793` as the reproduction inputs. Current attributes must not be substituted for generation-time oracle features in historical results.

Legacy interactions and their graph stay unchanged. The separate v5 generator pins the new published item-attribute file, configuration and code hashes, and its full 50,000-user/1,000,000-event replay passed. This establishes deterministic mechanism reproduction, not real-user validity or repair of the historical log.
