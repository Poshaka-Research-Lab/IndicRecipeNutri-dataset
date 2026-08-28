# Changelog

Versions follow semver and describe the **release**, not the corpus build. The corpus
build (`v11`) is recorded separately in `data/corpus/corpus_manifest.json` and
`.zenodo.json`.

## [0.1.0] — 2026-08-28

First assembled release. **Pre-release: not citable.** Five gates below are open.

### Added
- Structured corpus: 224,003 recipes × 129 columns, Parquet + zstd (51 MB).
- Rehydration index with source URL, SHA-256 prose digest, and a `rehydratable` flag.
- Knowledge graph: 227,500 nodes / 6,169,941 edges, verified against `kg_stats.json`.
- 23 enrichment companion tables (138 MB CSV → 26 MB Parquet).
- 66-query retrieval benchmark with a two-leg gold-set audit.
- Synthetic interaction log: 50,000 users, 990,273 ratings, with its datasheet.
- Datasheet, data dictionary, provenance, third-party terms, takedown policy.
- Build, audit and verification scripts; tag-driven release workflow.

### Fixed
- **Knowledge-graph Parquet re-encoded.** The working `kg_nodes.parquet` and
  `kg_edges.parquet` were written by pyarrow 25 with size statistics that pyarrow 19
  cannot read at all ("Repetition level histogram size mismatch") — a reader on an
  older Arrow could not have opened the graph. Re-encoded through the release's own
  writer. No value changed; the counts were re-verified afterwards.

### Privacy
- **One redaction applied.** An email address in the `IngredientsList` of
  `recipe_id 211731` is replaced with `[redacted-email]` in the published artefact.
  Only the matched substring changes; the working master is untouched and the
  redaction is reapplied on every build. Recorded in `corpus_manifest.json`.
  `verify_release.py` re-sweeps the written files and now passes.

### Known defects — measured, published, not fixed
- Allergen false negatives, upper bounds: sesame 9.39%, tree_nuts 6.36%,
  shellfish 5.61%, soy 5.46%, peanut 3.62%, mustard 3.13%, egg 2.35%, fish 1.89%,
  milk 1.85%, gluten 1.79%. See `data/corpus/ALLERGEN_AUDIT.json`.
- Diet-label conflicts: 3,042 `Vegan` rows (3.30%) name a dairy, egg, fish or
  shellfish ingredient. Largest cluster is paneer: 216 paneer recipes labelled `Vegan`,
  169 with `has_milk = False`.
- Benchmark: 14 of 289 gold-set members (4.84%) for *"Vegan recipes without milk"* are
  paneer dishes. The other five constraint queries show no lexical conflict.
- **101 `savorytales` rows carry sidebar navigation instead of ingredients**, all
  wrongly flagged `has_ingredients = True`. Already present in the published
  quarantine list; not repaired here. The redacted email sat in the first of them.

### Open gates for 1.0.0
1. **Third-party terms unverified** — IFCT 2017, FlavorDB, FoodOn, RecipeDB NER, plus
   four upstream recipe datasets found during this build (3a2m, IndB, RecipeNLG,
   indori; 4,807 rows). If any is share-alike, CC BY 4.0 on the graph is wrong.
2. **Semantic PII pass has no run artefact.** Pattern-based redaction is now done and
   recorded, but author names and personal anecdotes are not pattern-matchable and the
   pass the paper describes is still unevidenced.
3. **Split protocol undocumented.** Do not describe the train/test/val split as
   random, temporal or cold-start until the assignment rule is established.
4. **No collection timestamps** in the published schema, though the paper states they
   are retained per recipe.
5. **Ingredient vocabulary (1,205) and graph ingredient nodes (1,199) differ by six**,
   cause unestablished.
