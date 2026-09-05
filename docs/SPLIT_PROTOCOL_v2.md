# Split Protocol (v2)

This document describes the Grouped Stratified Split (v2) protocol implemented in the v15 master database, as required by Milestone 3.

## The Problem with Split v1
*   **Data Leakage:** Identical titles (duplicate recipe names) spanned across different splits (train/test/val), introducing severe data leakage.
*   **Imbalanced Regions:** The test partition had zero rows for some small regions like `East India` and `Himachal Pradesh`, preventing robust testing.
*   **Reproducibility Gap:** The partition logic was undocumented and unseeded.

## Split v2 Specification
*   **Grouping Column:** `Title_normalized` (empty/null titles are treated as unique singletons to keep them independent). This ensures that no recipe with the same normalized name spans across partitions.
*   **Stratification Column:** `Region_v5` (normalized J&K spelling collapses to 27 values). This ensures every region retains representative test and val mass.
*   **Proportion:** 90% Train · 5% Val · 5% Test (mapped from 20 StratifiedGroupKFold splits).
*   **Split Map:** Folds 0-17 map to `train`, Fold 18 maps to `val`, Fold 19 maps to `test`.
*   **Random Seed:** `42` (with shuffling enabled).

## Verification Results
*   **Data Leakage:** 0 groups span partitions.
*   **Regional Stratification:** Every state-level region (including minor ones) is represented proportionally.
