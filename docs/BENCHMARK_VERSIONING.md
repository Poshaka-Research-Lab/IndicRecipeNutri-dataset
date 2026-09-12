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


The two synthetic interaction exports are retained as **historical snapshots**.
Neither is an aligned current-corpus benchmark. Each folder carries `SNAPSHOT.json`
with independently pinned file hashes and `HISTORICAL_MANIFEST.json` with ID
membership, train/test counts and current withdrawal reconciliation. Their data,
existing results and generators remain byte-for-byte unchanged. The source archive
was recovered from inspected local release bytes; the original full-corpus hash is
unknown. Having a generator beside an output does not prove full regeneration from
its original inputs.

| Snapshot | Post-core items | Train pairs | Test pairs | Withdrawn catalogue items | Withdrawn raw interaction rows |
|---|---:|---:|---:|---:|---:|
| Historical v1 | 16,688 | 658,098 | 163,115 | 385 | 20,161 |
| Historical v3 | 16,194 | 654,605 | 162,182 | 12 | 1,087 |

Both train/test files resolve through their user and item remap tables, with no
shared user-item pair across the two splits. These are **interaction splits**, not
recipe `Split_v3` or duplicate-family splits. The raw pre-core interaction logs have
389 distinct withdrawn recipe IDs in v1 and 12 in v3; the post-core item tables have
385 and 12 respectively. These denominators describe different populations. All
recipe IDs missing from today's corpus reconcile to recorded withdrawals.

The historical KG resolves within its own exported entity/relation namespace.
Original learned-feature training scope is not established, so these snapshots do
not support an inductive claim. Use the exact historical files for historical result
comparisons; a new experiment requiring current features needs a separately versioned
aligned dataset and fresh results. Do not silently join withdrawn historical items
to current features or relabel old results as current.
