# Split protocol v3 — current evaluation contract

Use `Split_v3` for new graph and corpus evaluation. The current counts are generated
in `data/provenance/release_facts.json` and `DATASHEET.md`.

The source split builder uses connected components over both case-folded
`Title_normalized` and `dup_family_id`. Grouping is transitive. Empty titles are not
one shared title group. Each component stays in a single partition. Components are
stratified by Region; multi-region groups use their modal region. The source seed is
20260902, with approximate proportions of 90% train, 5% validation and 5% test.
Withdrawals can change published counts without reassigning the retained recipes.

The release verifier requires valid labels, stable-ID parity between graph and both
corpus views, and no crossing case-folded title or duplicate-family groups. It does
not prove that every semantically similar recipe has been detected as a duplicate.

`Split_v2` is historical. Rechecking the September 12 payload found 844 case-folded
title groups and 1,379 duplicate-family groups spanning its partitions. Graph recipe
labels previously used v2: 40,773 differed from v3. These numbers describe that
baseline, not a permissible discrepancy in future releases. Do not silently fall
back to a legacy split when v3 is missing.

Fit learned features on the permitted training data for inductive evaluation.
If the full graph is deliberately accessible, declare the evaluation transductive.
Keep graph-derived silver labels distinct from independently judged relevance.
