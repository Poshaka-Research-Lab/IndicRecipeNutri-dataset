# Benchmark generations and comparisons

`data/benchmark/eval_queries.jsonl` now retains 67 fixed question definitions and
refreshes their labels from the full current knowledge graph. Its labels are silver graph assertions, not independent human
judgments. The task is transductive. Some vocabulary selected by frequency bands
is malformed; success on this file does not establish culinary relevance.

`BENCHMARK_MANIFEST.json` pins the exact query file and graph edge file. Compare
system variants only against the same query and relevance generation. In the
12 September source recovery/parser batch, the generator selected 12 new query
texts and retired 11. Only diet-plus-ingredient changed count (5 to 6); the
remaining seven template counts and all shared-query relevance sets stayed equal.
That intermediate 68-query generation cannot be scored interchangeably with the old 67.
The subsequent alias pass reselected questions again. This is why frequency-based
discovery no longer controls the default benchmark.

`fixed_silver_v1` preserves the frozen question text, templates and order. Stable
query IDs derive from text and template. `eval_queries_protocol.json` records all
relevance-set changes from the historical baseline. Relevant IDs are sorted
deterministically, withdrawn IDs are excluded, and unknown/unassessed allergen
records cannot enter allergen-absence gold sets. Nutrient ranking excludes nonfinite
values. If a question loses support, it remains present with `insufficient_gold`;
it is never silently replaced by an easier question. The caps remain 300 relevant
IDs, or 50 for nutrient-ranked questions. For allergen constraints, filtering follows
the historical first-300 diet-member sampling rule.

`silver_regression_v1.jsonl` preserves the prior 67-query file byte for byte; its
digest is independently pinned in `release_config.py`. Its companion JSON records
its origin and limitations. This is a historical regression fixture, not a claim
that its labels remain correct after future corpus corrections. Do not overwrite
it during graph rebuilds, and do not use it as evidence for current allergen safety.

The independent relevance pilot, cultural review, human adjudication and locked
feature ablations specified by the database improvement plan remain outstanding.
Neither of these silver generations supplies those missing judgments.


`data/interactions/` is a **single** synthetic interaction benchmark, regenerated from
the published corpus by `scripts/build_interactions.py`. It is simulated behaviour and
is not an aligned human benchmark.

It replaces two retired exports, `synthetic_interactions/` (v1) and
`synthetic_interactions_v3/`. They were **not merged**, because they could not be: they
were independent simulations whose remapped id spaces collide, so concatenating them
would have invented users rating across two catalogues and destroyed both the 10-core
property and the zero-leakage guarantee. Both remain at the `v0.6.0` tag and its DOI for
reproducing results published against them.

| Generation | Post-core items | Train pairs | Test pairs | Withdrawn catalogue items | Withdrawn raw interaction rows |
|---|---:|---:|---:|---:|---:|
| **Current (v4)** | 16,567 | 657,610 | 162,956 | **0** | **0** |
| Retired v1 (`v0.6.0`) | 16,688 | 658,098 | 163,115 | 385 | 20,161 |
| Retired v3 (`v0.6.0`) | 16,194 | 654,605 | 162,182 | 12 | 1,087 |

**The zeros are structural, not audited.** Generating from `data/corpus/` means a
withdrawn recipe cannot be selected. The retired sets could only ever be *declared*
clean at a pinned count, because their generator hardcoded another machine's paths and
could not be re-run; that pin is now retired along with them.

Do not join either retired set to the current one. Their `recipe_id` column held
dataframe row offsets rather than corpus ids, so the id spaces are not comparable even
where the numbers overlap.

Train and test resolve through the user and item remap tables with no shared user-item
pair. These are **interaction splits**, not recipe `Split_v3` or duplicate-family
splits. The attribute KG resolves within its own exported entity/relation namespace, and
learned-feature training scope is not established, so this benchmark supports no
inductive claim.
