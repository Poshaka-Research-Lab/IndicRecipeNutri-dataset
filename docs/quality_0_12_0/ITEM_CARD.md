# Existing-attribute item card

DS-10 implementation version `irn-item-card-0.12.0-v1` provides `data/quality/item_attributes_v1.parquet` and a local-only `item_card.render_local_card(recipe, attrs)` text view. All 219384 source ID/attribute rows, dtypes and nulls were compared exactly by key. No new spice/popularity source is invented.

The structured view carries existing SpiceLevel, SpiceLevel_src, HealthGrade, RatingCount, RatingAverage, Region and Cuisine. Added fields: rating_count_bin (`unknown`, `zero`, `1_9`, `10_99`, `100_plus`), spice_is_rule_inferred and cuisine_generic_or_missing. Missing ratings never become zero. Bins are fixed descriptive ranges, not optimized on outcomes. HealthGrade remains a dataset label, not an independently validated health effect.

The local renderer shows title, ingredients and selected attribute values with their limitations. It is not materialized or committed as ID/title pairs. Its allowlist excludes hidden generator quality, oracle rank, noise and exposure, even when supplied in the input object. Remote submission of private text is not part of this workflow.

A separate generator may use these public structured attributes. It must keep the old interaction log unchanged and record its own version, seeds, mechanism and validation. Item-card availability by itself does not establish a model-performance improvement.
