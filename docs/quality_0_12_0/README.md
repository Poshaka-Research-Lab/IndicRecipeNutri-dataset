# 0.12.0 additive evidence layers

Local candidate; public publication is not performed. All 219,384 original recipe IDs, legacy corpus values, graph, benchmark, interaction log and Split_v3 assignments are preserved. DEV means train plus validation (208,290); the other 11,094 rows are the existing test split. No evaluation claim is made from inspecting aggregate test coverage.

| New artifact | Rows | Meaning |
|---|---:|---|
| recipe_quality_v1.parquet | 219,384 | Provisional quality, language support, region strata and audit flags |
| duplicate_crosswalk_v1.parquet | 219,384 | Candidate groups alongside original families/splits; not confirmed equivalence |
| allergen_evidence_v1.parquet | 3,729,528 | Per-recipe/class evidence, legacy status and new status; 17 vocabulary entries |
| allergen_review_candidates_v1.parquet | 144 | Unreviewed name/legacy-label conflicts; no automatic correction |
| item_attributes_v1.parquet | 219,384 | Existing attributes, provenance and rating-count bins |
| nutrition_evidence_v1.parquet | 219,384 | Estimator assumptions and basis diagnostics |
| interactions_v5/users.parquet | 50,000 | Fictional preferences in a new user namespace |
| interactions_v5/interactions.parquet | 1,000,000 | Synthetic choices; 16 train and 4 test events per user |
| interactions_v5/generator_truth/choice_probabilities.parquet | 1,000,000 | Oracle mechanism output; exclude from normal model inputs |

Quality artifacts live under `data/quality/`; generator artifacts live under `data/interactions_v5/`. Each build has a manifest with input/code/configuration/output hashes. Quality rules are `quality-v1-draft-2-audit-aligned`, explicitly provisional. No raw instruction text or local rendered item cards are exported.

The quality rule reproduces the supplied DEV audit's 36,402 text-insufficiency flags. It is not a human correctness judgment or the full frozen K006 physical-state classifier. Unsupported method languages produce UNKNOWN in actionable fields. There are 70 candidate duplicate groups spanning legacy splits (468 rows); no recipe was reassigned. Report these conflicts when evaluating a consumer.

Read [allergen evidence](ALLERGEN_EVIDENCE.md), [item cards](ITEM_CARD.md), [nutrition evidence](NUTRITION_EVIDENCE.md), [generator v5](GENERATOR_V5.md), [Goa source diagnostics](GOA_SOURCE_DIAGNOSTIC.md), and [model/source trace](MODEL_AND_SOURCE_TRACE.md). Full schemas can be read directly from Parquet; closed quality domains are enforced by `scripts/quality_contract.py`.

## Acceptance and use boundaries

Engineering acceptance checks keys, digests, legacy preservation, rule consistency and deterministic reproduction. It is separate from independent semantic validation. The full release verifier requires all new layers and fails on missing/stale artifacts. Nutrition and item-card values are recomputed for comparison from published inputs. Generator full replay is a separate recorded check.

DS-7 permits including non-text flags subject to source-terms verification. Passing a private source-reader gate does not itself establish permission for public distribution. A per-source publication determination remains required before remote publication; the local candidate makes no blanket legal clearance claim. DS-9 IFCT retention uses the owner's confirmation of permission, not an independently inspected grant. See [third-party terms](../THIRD_PARTY_TERMS.md).

No clinical safety, certification, regional causal effect, nutrient accuracy or real-user recommendation improvement follows from these checks. Historical K006 pins and results are unchanged; adopting this version downstream requires an explicit new study version.


## Execution plans and local evidence

The scope and detailed execution plans are also stored in `docs/DATASET_0.12.0_PLAN.md` and `docs/DATASET_0.12.0_GOAL_EXECUTION_PLAN.md`; the G1-G23 disposition and reproduction instructions sit beside them. Their run-ledger, audit-intake and receipt references identify the method workspace at `D:/Research Drive/METHOD_IndicRecipeNutri_ACTIVE/docs`, which is retained separately. These snapshots record the pre-integration state; current integration identity is recorded in that run ledger and Git history.
