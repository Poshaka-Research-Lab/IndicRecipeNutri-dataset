# Third-party layers and their terms

The knowledge graph fuses external resources. Each is redistributable only to the
extent its own licence permits, and the combined graph is released only to that extent.

> **Status: unverified. This file is a release gate.** Every row below is `⟨TBD⟩`
> until the licence text has been read and recorded. Nothing here is asserted from
> memory, and no licence name is guessed. Until this table is completed, treat the
> knowledge-graph layers derived from these sources as **not cleared for
> redistribution**.

| layer | used for | licence | redistribution of derived data | verified |
|---|---|---|---|---|
| **IFCT 2017** (Indian Food Composition Tables) | nutrient grounding, per-100g values | `⟨TBD⟩` | `⟨TBD⟩` | ☐ |
| **FlavorDB** | `FlavorCompound` nodes (1,641), `has_compound` / `shares_flavor` edges | `⟨TBD⟩` | `⟨TBD⟩` | ☐ |
| **FoodOn** | `FoodOnClass` nodes (408), `grounded_as` / `is_a` edges | `⟨TBD⟩` | `⟨TBD⟩` | ☐ |
| **RecipeDB NER training data** | CRF ingredient tagger | `⟨TBD⟩` | `⟨TBD⟩` | ☐ |

## Upstream recipe datasets — found during the 0.1.0 build, not in the paper's list

4,807 of the 224,002 published recipes (2.1%) did not come from a scraped page. They came from
pre-existing datasets and carry a placeholder URL, so they cannot be rehydrated by
re-fetching. They are flagged `source_kind = "derived_dataset"` in
`data/corpus/rehydration_index.parquet`.

These are **additional third-party sources that the paper's section 3.5 does not name**,
and their terms gate the release exactly as the four layers above do.

| upstream dataset | `SourceSite` | recipes | licence | redistribution | verified |
|---|---|---:|---|---|---|
| 3A2M / RecipeNLG-derived Indian subset | `3a2m_indian` | 3,803 | `⟨TBD⟩` | `⟨TBD⟩` | ☐ |
| IndB | `indb` | 973 | `⟨TBD⟩` | `⟨TBD⟩` | ☐ |
| RecipeNLG (Indian subset) | `recipenlg_indian` | 30 | `⟨TBD⟩` | `⟨TBD⟩` | ☐ |
| indori | `indori` | 1 | `⟨TBD⟩` | `⟨TBD⟩` | ☐ |

## What to record for each

1. The licence identifier, or the exact terms URL if it is not a standard licence.
2. Whether redistribution of *derived* data (not the source table) is permitted.
3. Whether attribution is required, and in what form.
4. Whether share-alike applies — if any layer is share-alike, CC BY 4.0 on the
   combined graph may be wrong and the licence must be revisited.
5. The date checked and by whom.

## If a layer turns out not to be redistributable

Withhold that layer's nodes and edges from the release and publish the join keys plus
a build script instead, the same pattern used for the recipe prose. Record the
exclusion in `data/kg/EXCLUDED.json`.
