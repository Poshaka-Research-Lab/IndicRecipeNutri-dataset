# Compound identity migration — local candidate, September 12, 2026

This is an interface change. Compound node IDs now use `compound::<PubChem CID>`.
Recipe, ingredient and other node identities are unchanged. No new release has been
published by this migration; regenerate any derived index that embeds old IDs.

Five legacy labels collapsed distinct chemicals: Borneol, Methyl jasmonate, Phytol,
Sabinene hydrate and Spathulenol. Correct identity restores 6 compound nodes and
15 ingredient-compound associations from the existing source CSV. Core compound
nodes change from 1,601 to 1,607 and has_compound edges from 25,854 to 25,869.
Every other relation count is unchanged. This is an identity repair, not a new
ingredient mapping or validation of the legacy associations.

The generated `data/kg/compound_id_crosswalk.csv` records old IDs, current IDs, CID
and `unique`/`ambiguous` status. It is intentionally one-to-many for collisions.
Do not select the first match. Obtain the intended CID from the original evidence
or mark an old reference unresolved.

```python
import pandas as pd
from scripts.flavor_contract import resolve_legacy_compound
crosswalk = pd.read_csv('data/kg/compound_id_crosswalk.csv', dtype=str)
new_id = resolve_legacy_compound('compound::thiamine', crosswalk)
# Ambiguous or unknown references raise; they are never guessed.
```

The optional flavour layer is generated from the core and edge evidence, rather
than independently from old CSVs. It contains exactly the core's ingredient-CID
associations and only live ingredient endpoints. Its molecular-sharing view also
includes 580 attached assertions: 576 on pairing edges, three on substitution
edges and one on a derivation edge. Use
`scripts.flavor_contract.load_with_flavor` to deduplicate shared topology and retain
both relation types. Keep the original evidence tables for numerical attributes.

Rebuild order: source graph, export (including edge evidence), release graph, stamp
units, flavour view, current facts/docs, checksums, and release verification. The
standard orchestrator performs these dependencies. Historical snapshots keep their
old identifiers; never silently overwrite published experimental outputs.

Known limits: food forms and alias unions still require review; five old source-CSV
associations lack a reconstructed entity witness. The molecule's chemical ID does
not resolve that separate provenance problem.
