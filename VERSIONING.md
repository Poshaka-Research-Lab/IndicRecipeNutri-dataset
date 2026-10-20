# Dataset version policy

0.11.0 is preserved by local tag `v0.11.0` at `620496feb4aeffaee7b01e1892418924d8b2fd47`. The historical K006 commit is `083229c1e04343aa573cc878d1eaf4b9a90ab01e`. Removal of a co-author trailer changed the commit ID; their tree and parent were verified identical. Historical study records must not be silently re-pinned.

0.12.0 is preserved by local tag `v0.12.0` at `ea32232c1f8fd8084457149ee2fda7033bca6089`.

0.13.0 is preserved by local tag `v0.13.0`. It rebuilds the release on data version v19 (master `e3f89628`); historical 0.12.0 identifiers (`irn-allergen-evidence-0.12.0-v1`, `docs/quality_0_12_0/`) keep their names.

0.12.0 is developed on `release-0.12.0`. The active user goal authorizes a final local integration into the canonical dataset checkout after validation. It does not authorize a remote push or DOI publication. Existing recipe IDs, legacy fields and Split_v3 remain immutable during P1. New quality annotations are generated sidecars; new duplicate evidence is reported without moving legacy splits. New recipes/corrections require an explicit scope decision.

Reproduce the source manifest, rule digest and logical-output digest. Private recipe text remains local. A candidate is not independent validation. All commits omit co-author trailers. Retain prior release tags and evidence.
