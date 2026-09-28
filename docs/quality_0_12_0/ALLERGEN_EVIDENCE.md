# Additive allergen evidence and 0.12.0 status

Policy `irn-allergen-evidence-0.12.0-v1` implements the owner's DS-8 decision: publish evidence beside preserved legacy labels and a separate fail-closed status. It is provisional rule evidence, not independent annotation or a food-safety certificate.

`data/quality/allergen_evidence_v1.parquet` has one row per (recipe_id, allergen), covering the 17 legacy vocabulary entries. Ghee is the legacy derivative marker, not an assertion of a 17th regulatory allergen. `legacy_status` reproduces the old table exactly. No existing corpus value or graph edge is changed.

Evidence kind is explicit, implicit_name, ambiguous_carrier, text_silent or unassessed. Explicit takes precedence over implicit and carrier evidence. Negated names require review. Pattern matching is English-only; unsupported language and invalid/empty ingredient arrays are unassessed. The audit carrier lexicon is retained with a versioned change that inspects alternative clauses separately, so named oil cannot hide an unspecified alternative on the same line.

New status precedence:

1. Legacy present stays present, including incomplete scans.
2. Legacy unassessed, incomplete scans, or unassessed ingredient evidence become unknown.
3. Explicit/implicit name conflicting with legacy absence becomes unknown and enters a review queue; no automatic presence correction.
4. Ambiguous-carrier legacy absence becomes unknown.
5. Remaining absence stays absent with reason `silver_inferred_absence_not_verified_safe`.

Reference consumer `allergen_evidence.decide_constraint` returns FAIL, UNKNOWN, or PASS_SILVER_ONLY. It never returns verified-safe. Frozen K006 code does not consume this sidecar; a follow-up must opt into the new version.

The manifest supplies input/policy digests and separate DEV/heldout and regional counts. Audit-proposal parity is a separate receipt: this policy deliberately differs in language handling, missingness, explicit names, and alternative-clause handling. Do not cite audit carrier-only counts as the number of new UNKNOWNs. Categories overlap and the precedence allocates each output to one status reason.

`allergen_review_candidates_v1.parquet` contains only ID/class candidates and `unreviewed_candidate`, not raw text or attested human labels. These are not confirmed misses. The original audit's 62 implicit candidates and the new policy queue have different definitions; do not equate them.

Reproduction stages: `build_allergen_evidence.py`, `allergen_evidence_contract.py`, then `export_allergen_review_queue.py`. Builders require an isolated root, protected-root path and pinned input manifest; `--help` documents exact arguments. All raw ingredient text is read locally and omitted from outputs. A complete second build reproduced the exact manifest, logical digest and Parquet bytes.
