# Cultural label proposals (0.16.0)

Join `data/cultural_labels/proposals.parquet` or `proposals.csv` to the corpus on
unique `recipe_id`. CSV label columns contain JSON arrays; parse with a JSON
parser. Unlisted IDs are unprocessed. `status=abstain` is not a verified absence
of cultural identity. All rows have `review_status=pending`.

These are source-declaration extraction proposals produced with Claude Opus 5.5
from saved local source fields, followed by exact evidence checks and formatting
recovery. The final unresolved recovery cases were read locally by the assistant;
unsupported claims were removed or abstained. Quote matching does not establish
semantic validity. One recovered response is explicitly marked partial. There
has been no independent semantic validation of this layer. No recipe websites
were fetched for the labelling run. Original quotes and full source evidence
remain private, so the public layer alone cannot reproduce source verification.

Cuisine, administrative state/UT, broad region, community, culinary subregion,
locality and scope have different meanings. No city/state or cuisine/state inference
is supplied. A heuristic filter prioritized possible declarations; it may miss
unknown names. Coverage is selective and is not corpus prevalence.

Keep existing corpus columns as historical annotations. Review proposals before
adopting canonical changes. Fusion maps to indo-fusion under the owner's dataset
definition (Indian mixed with another cuisine); this is a convention, not separate
verification. Indian and Pan-Indian map to indian. International does not establish
non-indian and remains unmapped. Existing indian-adapted values are not disproved
by an Indian source label. The public file preserves the original scope terms.

Core data v21 and graph/splits are unchanged. Do not silently expand cuisine benchmark
cohorts, alter historical splits or evaluate on model-generated labels as ground
truth. Source and cuisine labels are entangled; use publisher-aware evaluation.

Only the allowlisted label arrays, IDs, status, taxonomy and partial flag are
published. No descriptions, quotes, API responses, keys or local paths are published.
The local enriched master CSV is private and is not a GitHub release asset.
