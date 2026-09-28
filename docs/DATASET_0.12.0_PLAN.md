# IndicRecipeNutri 0.12.0: scope, contracts, and release plan

Updated: 2026-09-28. Owner: dataset track in `METHOD_IndicRecipeNutri_ACTIVE`.
Status: enhanced plan; implementation and release have not started in this session.

This document defines WHAT 0.12.0 should change and what must remain reproducible. The separate [goal-mode execution plan](DATASET_0.12.0_GOAL_EXECUTION_PLAN.md) defines HOW to execute, checkpoint, validate, and resume the work. The [original plan](archive/DATASET_0.12.0_PLAN.before_enhancement_20260928.md) is retained for provenance; its baseline and approval wording are superseded here.

## 1. Baseline and verified facts

| Item | Observed state on 2026-09-28 | Consequence |
|---|---|---|
| Dataset checkout | `D:\datasets\IndicRecipeNutri-dataset`, branch `main` | Treat as protected from further changes by the 0.12.0 task |
| Current 0.11.0 commit | `620496feb4aeffaee7b01e1892418924d8b2fd47` | Base new work on this full ID, not a floating tag |
| Local tag | `v0.11.0` resolves to that commit | Local only; no push performed |
| Historical 0.11.0 commit | `083229c1e04343aa573cc878d1eaf4b9a90ab01e` | K006 still pins this ID |
| Reason for changed ID | User explicitly requested removal of the co-author trailer | Same Git tree and parent were verified after amendment; this is not a dataset-content correction |
| K006 compatibility | `scripts/pin_inputs.py` checks HEAD against the historical ID | Expected HEAD-check failure against current `main`; do not call that a payload failure or claim the check passes |
| 0.12.0 worktree | Not present at inspection | Recheck before creation; never overwrite an existing branch or checkout |
| Improvement audit | Referenced K006 `docs/DATASET_IMPROVEMENT_AUDIT.md` absent at inspection | Produce an independent dataset-track inventory; record absent evidence, not invented counts |
| Project directory | No Git repository found at `METHOD_IndicRecipeNutri_ACTIVE` | Plans live here; future implementation commits belong in the dataset worktree |

Tree equality is evidence about tracked Git objects. It does not replace verification of actual Git LFS payload bytes, local source inputs, or runtime manifests. Record these separately in P0.

### 1.1 K006 freeze compatibility

Do not edit K006's protocol, pins, manifests, labels, scripts, or results as part of this dataset task. Do not automatically substitute the new commit into a historical record. Create a receipt describing old/new IDs, identical tree IDs, and the reason for the metadata amendment.

Dataset-track preparation can continue in isolation. A claim that K006 compatibility is restored requires its owner to choose and validate a repair, such as retaining an old-commit checkout for the historical run or recording a protocol-compliant metadata amendment. Neither action is included in this plan's automatic execution scope. Report this dependency separately from the 0.12.0 data checks.

## 2. Objective and scope

Produce a reproducible candidate release that exposes record quality, duplicate relationships, and uncertainty without changing existing recipe identities, historical split assignments, or existing values during P1.

The default release candidate is **P0 + P1 + the applicable P5 checks**. P2, P3, and P4 are optional extensions requiring a recorded scope decision. The release number does not imply that every listed research gap has been solved. P6 is a separate future study, not an acceptance condition for this dataset task.

[Hypothesis] Explicit quality flags may help a downstream consumer reject unsupported physical-state assignments. This is an evaluation target, not an established improvement. Flags alone change neither consumer behavior nor correctness. Report any reduction in errors together with coverage and abstention costs.

Out of scope by default: nutrition validity claims, clinical or allergen-safe certification, fabricated recipes, synthetic evidence of popularity, changes to frozen K006 analyses, manuscript drafting, remote pushes, DOI publication, and merging into `main`.

## 3. Workspace and change boundaries

- Method documents: `D:\Research Drive\METHOD_IndicRecipeNutri_ACTIVE\docs`.
- Protected baseline: `D:\datasets\IndicRecipeNutri-dataset`.
- Proposed implementation worktree: `D:\datasets\IndicRecipeNutri-dataset-0.12.0`.
- Proposed implementation branch: `release-0.12.0`.
- Baseline full commit: `620496feb4aeffaee7b01e1892418924d8b2fd47`.
- K006 project: `D:\Research Drive\METHOD_K006_FaithfulXAIFood_ACTIVE`, read-only for evidence relevant to this task.

All method-project folders remain directly under `D:\Research Drive`; the implementation worktree belongs beside its dataset repository under `D:\datasets`.

Creating a worktree necessarily adds Git worktree metadata to the shared repository. It must not move `main`, change baseline files, or alter the `v0.11.0` tag. Check status and refs before and after.

Use local commits only when implementing an explicitly started goal. No co-author trailers. Do not amend historical commits again. Do not create or move a `v0.12.0` release tag until release approval. Never force-push. Preserve unrelated work.

## 4. Evidence and gap inventory

Source lead: K006 `docs/DATASET_GAPS_PLAN.md`, cited by the original handoff as commit `87965a2`. Verify the exact source revision before treating it as pinned evidence. Historical K006 sample statistics in the archived plan are leads to inspect; they are not measured 0.12.0 corpus statistics or independent validation results.

| Gap | Workstream | Required evidence/output |
|---|---|---|
| G1 Incomplete or unusable records | P1 completeness | Reproducible reason counts, allowed-input availability, explicit UNKNOWN |
| G2 Final served state not explicit | P1 end-state flag | Text-evidence rule; no final state inferred solely from title |
| G3 Intermediate preparations | P1 intermediate flag | Separate intermediate use from ordinary preparation steps |
| G4 Title/method mismatch and garbling | P1 quality flags | Conservative candidate detection plus review; no silent text repair |
| G5 Text-open silver absence passes the allergen gate | P1 evidence + DS-8 policy | Evidence per recipe/class; quantify absent-to-UNKNOWN impact without claiming verified safety |
| G6 Residual implicit-name candidates | Targeted P2 review | Most mappings already exist; 62 DEV candidates (50 milk, 11 peanut, 1 mustard) require review, not blanket remapping |
| G7 Regional-language/Hinglish strings | P2 lexicon | Script-aware normalization with original values retained |
| G8 Silver inferred absence inflates PASS | Evidence/consumer contract | All audited allergen PASS decisions are silver; absence is not verified safety; distinguish structural diet UNKNOWN |
| G9 Portion weights | P3 references | Source, licence, units, uncertainty, applicable population |
| G10 Liquid density | P3 references | Unit/temperature/ingredient applicability; unmatched remains unknown |
| G11 Existing attributes not routed to models | DS-10 item-card / DS-11 separate generator | Spice/popularity columns exist; distinguish attributes from hidden hotness/noise/exposure; preserve existing synthetic log |
| G12 Thin regional coverage | P4 | Measured regional counts plus collect/defer decision |
| G13 Coarse regional strata | P1 | Declared taxonomy without reassignment of legacy Region |
| G14 Duplicate relationships | P1 | Existing-family reconciliation, new candidate clusters, split-conflict report |
| G15 Frozen-version reproducibility | P0 | Baseline receipt, immutable inputs, version policy |
| G16 Documentation | P5 | Datasheet, schema, limits, release receipt reflecting measured scope |
| G17 Withheld instructions and stale availability flags | P1 / DS-7 | Instruction-derived flags and reproducibility, with no redistributed prose; 103 DEV availability mismatches |
| G18 Different gram models in nutrient numerator/denominator | Nutrition provenance investigation | Trace both models and confidence eligibility; no invented replacement weights |
| G19 Source-site concentration | P1 / DS-12 | Region-by-site diagnostics; Goa and Kerala concentration; no unsupported regional causal claim |
| G20 Undeclared IFCT source values | Priority integrity correction / DS-9 | Actual source declaration, terms evidence, use-path inventory and permission or removal decision |
| G21 No admissible diet PASS source | Evidence-policy documentation | Preserve UNKNOWN for unsupported halal/kosher/Jain claims; no fabricated certification |
| G22 Generator/corpus drift | Generator provenance | Record 4 re-sourced served recipes / 350 historical interaction rows from audit; preserve existing log |
| G23 Generic Cuisine labels | Additive quality annotation | Flag generic/unknown labels without invented regional reassignment |

Audit counts are sourced to the intake below; newly computed counts begin as `TBD_MEASURED`. Every populated count must cite run ID, input-manifest digest, denominator, script version, and output artifact. Missing input is not a zero count.

## 5. Input contract and provenance

Before inspecting recipe text, inventory the authoritative input surfaces and permitted use. Published release documentation states that prose such as Instructions is withheld. K006 has a separate local-source workflow; access there is not proof that this dataset track may export the same content.

Create an input manifest containing: source alias, resolved local path, full revision or content hash, schema, join key, allowed operations, redistribution restrictions, required/optional status, read-only access method, and the decision/evidence supporting use. Public manifests must omit private paths and restricted content when needed.

The candidate source root configured by existing code is `D:/datasets/scraped_indian_recipes`; this is an unverified input candidate, not automatic authorization to rebuild or read every file. Existing source-reader gates must be honored. Read source selection and output paths before running builders: some depend on environment variables or shared modules under `D:\datasets`.

Required checks:

1. Actual data files are present, rather than unresolved LFS pointers; bytes match the applicable baseline checksums.
2. Recipe keys are unique at the intended table grain; joins are audited for missing, duplicate, withdrawn, and extra keys.
3. Source revision matches the declared baseline, or any differences are explicitly recorded; never use an unexplained newer master silently.
4. Unavailable instructions yield `unknown` or `unassessed` and an input reason. A missing published column is not evidence that the original recipe lacked instructions.
5. Titles and recipe text stay local. No committed ID/title pairs, raw excerpts, prompt payloads, or recoverable text in logs. Use invented fixtures for tests. Local review files must be ignored before creation.
6. Withdrawn recipe IDs remain excluded; updates cannot reintroduce them through a join or a duplicate family.

## 6. P1 schema proposal and compatibility

Inspect actual table schemas first. Prefer a new keyed sidecar `data/quality/recipe_quality_v1.parquet` so baseline Parquet files remain byte-identical. This path is a proposed new artifact, not an existing file. If compatibility requires adding columns to a legacy table, document that choice and prove equality of all pre-existing columns by recipe ID, including dtypes and nulls; whole-file hashes will then legitimately differ only for declared candidate files.

The sidecar has exactly one row per eligible corpus recipe ID and no extra IDs. Use a manifest-level schema version and rule-set digest. Stable fields per row include `recipe_id`, the seven proposed fields below, assessment status, and machine-readable reason codes. Keep private review evidence in a separate local file; do not place free-text excerpts in the release table.

| Field | Proposed domain | Semantics and safeguards |
|---|---|---|
| `record_completeness` | `sufficient`, `partial`, `unusable`, `unknown` | Sufficiency for the declared record-quality task, not nutritional completeness; distinguish observed missing/truncated text from unavailable input |
| `end_state_stated` | `yes`, `no`, `unknown` | `no` requires accessible, assessable text without an explicit final state; unknown is not no |
| `is_intermediate` | `yes`, `no`, `unknown` | Flag records whose intended output is an intermediate; ordinary chopping/mixing is insufficient |
| `title_method_mismatch` | `suspected`, `not_detected`, `unknown` | Rule-generated suspicion is not an adjudicated error; not_detected is not proof of agreement |
| `garbled` | `suspected`, `not_detected`, `unknown` | Unicode-aware; unfamiliar scripts, regional words, or code-switching alone never establish garbling |
| `coarse_stratum` | `coarse`, `specific`, `unknown` | Derived from a versioned regional taxonomy; preserve original Region values and report unknown categories |
| `dup_cluster_id` | nullable string | Versioned deterministic cluster identifier; null means unassessed, an assessed singleton gets its own cluster ID |


Companion contract: reason codes must distinguish `input_unavailable`, `input_missing_in_source`, `rule_not_applicable`, `ambiguous`, `assessed`, and `needs_review` where applicable. Do not use one row-level status to obscure per-field missingness. Store per-field reason/status in a normalized evidence sidecar if embedding it would make the primary schema ambiguous.

Rules must be versioned configuration, with input requirements, positive/negative/ambiguous examples, precedence, and an UNKNOWN fallback. Draft thresholds may be explored only on development data and must be labeled provisional. Do not invent or tune thresholds on held-out evaluation labels.

### 6.1 Reconcile existing fields

The current data dictionary already documents `dup_family_id`, `dup_family_size`, `Split_v3`, `allergen_tier`, and `allergen_scan_incomplete`. Existing `allergen_tier_contract.py` accepts `direct`, `derived`, `blend`, and `inherited`; do not replace this with a new vocabulary during P1.

- Map each new field to existing fields and specify whether it adds evidence, summarizes it, or is independent.
- Do not overwrite `dup_family_id` with the new cluster definition. Retain old IDs and emit a crosswalk.
- Do not overwrite `allergen_tier` or reclassify inherited evidence as direct evidence.
- New evidence tiers, if approved in P2, need a versioned separate representation and explicit migration contract.
- Candidate flags must not silently filter rows from legacy release tables or benchmarks.

### 6.2 Duplicate and split policy

Preserve historical `Split_v3` assignments for all existing IDs. Existing documentation describes connected components over titles and duplicate families; verify that claim independently.

New duplicate evidence can connect rows across old splits. Report every resulting cross-split cluster; do not both freeze assignments and claim that stronger clustering automatically guarantees no leakage. Default behavior is to retain historical splits and expose conflicts. A future consumer may use a separately versioned exclusion or split manifest after review. It must never mutate K006's split files.

Duplicate identifiers must be deterministic for a fixed input/rule version. If IDs derive from membership hashes, document that adding a member can change an ID and supply a version-to-version crosswalk. Distinguish exact matches, near-duplicate candidates, and reviewed equivalence. Recipe-title collisions alone do not prove recipe equivalence.

## 7. Work packages and completion evidence

| Phase | Deliverables | Acceptance | Decision boundary |
|---|---|---|---|
| P0 Baseline and isolation | Worktree; version policy; input/schema inventory; old/new commit receipt; freeze checks; run ledger | Full baseline ID verified; protected refs/files unchanged; LFS/source readiness recorded | No fresh approval needed for authorized isolated preparation; K006 pin repair remains separate |
| P1 Draft quality layer | Schema delta; rule config; deterministic sidecar builder; fixtures; duplicate crosswalk; per-region report | IDs/old fields/splits preserved; unknowns explicit; rule tests and repeat-run comparison pass | Draft work allowed on goal activation; DS-2 needed to adopt final rules |
| P2 Optional normalization | Reviewed lexicon; evidence model; provenance; migration and error audit | Original strings preserved; changes traced; unsupported cases unknown | DS-3 before production application |
| P3 Optional sourced attributes | Source registry; adapters; licence and units checks; join audit | Each source verified with a consuming code path; coverage and uncertainty reported | DS-4 per source; proposed sources can be researched first |
| P4 Optional coverage | Measured deficits; collection protocol or explicit deferral | Source/provenance/split policy defined; no fabricated records | DS-5 before collection or changing release population |
| P5 Candidate QA and release preparation | Relevant release checks; documentation; checksum/schema outputs; review packet | All in-scope gates pass; deferred items and K006 compatibility status explicit | Final approval before release tag, merge, push, or publication |
| P6 Future study | Separate protocol on a pinned candidate/release | Independent study decisions and preregistration | Outside this goal |

## 8. Validation design

### 8.1 Engineering acceptance: mandatory for the draft

- Baseline HEAD/tag, tracked-file state, and relevant payload hashes unchanged by this work.
- New sidecar: unique IDs, exact eligible-ID coverage, valid domains, consistent unknown/reason semantics, referential integrity, and no withdrawn records.
- Old fields: exact equality if legacy files are touched; otherwise identical bytes. Include split membership and dtype/null contracts.
- No changes to existing KG, benchmark, interaction, cultural-context, or historical-snapshot payloads in P1 unless explicitly justified as separate scope.
- Determinism: same pinned inputs/config/seed yields the same logical rows and canonical digest. Separate variable run timestamps from deterministic payloads.
- Adversarial fixtures: unavailable instructions, empty source text, placeholder method, incomplete step list, legitimate intermediate, unfamiliar script, ambiguous title, same-title distinct recipes, duplicate chains crossing splits, withdrawn IDs, duplicate join keys.
- Integration: discover the repository's actual release/test entry points before choosing commands. Run applicable existing contracts and strict checksum validation after candidate manifests are generated in the worktree only.

### 8.2 Evidence quality: needed for improvement claims

Write a protocol before sampling or seeing evaluation labels. Define the population, eligible inputs, sampling frame, development/evaluation separation, independent annotation procedure, duplicate-group handling, and primary estimand. Historical K006 error cases can inform development; exclude those exposed cases and related duplicate groups from the independent evaluation frame.

Report per-field detection precision/recall where independent labels support them, uncertainty intervals, reviewer agreement/adjudication, assessed/unknown coverage, and per-region/script slices. Report actual denominators and unassessable exclusions. Determine sample size from a declared precision/power target and available eligible population before labeling; do not invent a convenient fixed n here.

For a physical-state consumer, compare a frozen baseline consumer with an explicitly versioned flag-aware consumer on the same independent sample. Report false-solid errors and admission/abstention coverage together, plus the absolute numbers and paired uncertainty. A selective reduction in admissions is not by itself accuracy improvement. Use duplicate groups as the dependence unit where applicable. Predefine multiplicity handling if testing several primary claims.

P2 allergen validation, if activated, must separately assess explicit/implicit evidence and ambiguity. Detection evaluation does not establish that a food is safe for a person. Empty or inferred-absence evidence never becomes a verified-safe label.

If independent labels or a review budget are unavailable, ship at most a clearly marked draft/experimental annotation candidate after user review; do not claim validated downstream benefit.

## 9. Decision register

| ID | Current state | Concrete review material |
|---|---|---|
| DS-1 Isolated P0 preparation | Planned; execution starts only when user activates the goal | Baseline/preflight receipt; no repeated permission question for routine isolated work |
| DS-2 Adopt P1 rules | Pending | Rule examples, limitations, measured coverage, pilot errors, final schema |
| DS-3 Activate P2 | Pending; excluded from default draft goal | Proposed mappings, migration design, annotation workload and protocol |
| DS-4 Activate each P3 source | Pending; excluded | Verified terms/source/version, fields, join design, consuming code |
| DS-5 Activate P4 | Pending; excluded | Measured deficit report and collect/defer alternatives |
| DS-6 Intended reuse | Default dataset candidate only | A K006 follow-up requires a separate protocol |
| VAL-1 Independent validation design | Pending before reference labeling | Sampling, sample-size rationale, review roles, costs, success criteria |
| REL-1 Release approval | Pending | Full QA packet and explicit list of deferred scope |
| DEP-K006 Metadata compatibility | Unresolved dependency | Original/current IDs and tree receipt; no automatic historical re-pin |

Do not ask for every decision at startup. Prepare concrete reviewable artifacts first and ask only for the next decision that blocks meaningful authorized work. An unanswered question is not approval. Deferrals are explicit scope decisions, never PASS results.

## 10. Release record and completion

A release receipt records full candidate commit, baseline commit/tree, data/config/schema digests, source manifests, changed-file list, row/column deltas, actual test commands and outcomes, measured counts, unresolved risks, and approvals. Changelog distinguishes added annotations from corrected values and new recipes. Datasheet states that legacy silver labels and uncertain inputs remain uncertain.

The first goal completes when P0/P1 draft artifacts and their engineering evidence are ready for review. It does not claim 0.12.0 is released, validated for downstream safety, or compatible with the unchanged K006 HEAD pin. Use the separate execution plan for the exact checklist and restart instructions.

## Active execution amendment (2026-09-28)

The user activated the thread goal to complete this plan and update `D:\datasets\IndicRecipeNutri-dataset`. This supersedes the earlier draft-only/no-integration boundary for the final local update. Develop and validate in the separate worktree, then integrate the verified candidate into the canonical checkout after checking for concurrent work. Preserve the `v0.11.0` tag and historical study evidence. No remote push or DOI publication is authorized. Do not reinterpret this as approval of unreviewed external sources or fabricated independent labels. Current execution evidence is in `DATASET_0.12.0_RUN_LEDGER.json`; the full active goal includes canonical integration, not merely preparing a draft.

## Audit intake and priority correction (2026-09-28; supersedes earlier gap assumptions)

The audit is now available: [received audit snapshot](quality_0_12_0/audit_intake/DATASET_IMPROVEMENT_AUDIT.md), [updated gap snapshot](quality_0_12_0/audit_intake/DATASET_GAPS_PLAN.md), and [source/digest manifest](quality_0_12_0/audit_intake/manifest.json). Its item-level population is **208,290 DEV recipes**; structural ALL counts use **219,384 recipes**. Do not mix these denominators or tune rules to reproduce a desired percentage.

Run `20260928T033454Z_k006-dsaudit-stats_08128afa` reports 36,402 DEV recipes with at least one proposed text-insufficiency flag, and 39.7% for Goa versus 17.5% overall. These are unvalidated rule-hit rates, not measured defect or classifier-error rates. The audit's historical statement that only the committer timestamp changed is incomplete: the co-author trailer was also removed at the user's request; tree equality was verified separately.

Allergen priority is **text-open absence**, not a wholesale missing implicit lexicon: absent plus ambiguous-carrier-only counts are peanut 67,977, sesame 71,228, soy 80,164 on DEV. Most implicit-name hits are already mapped (at least 99.9% in audited classes); review the 62 remaining candidates rather than treating them as confirmed mistakes. The counts of removed PASS decisions must be computed through the actual proposed policy, since existing scan-incomplete/unassessed rows and overlaps matter.

Nutrition still needs work: 80.2% of DEV recipes have an assumed-weight line and 39.0% meet the audited K006 high-confidence predicate. G18 is a construction/provenance issue distinct from collecting new weights. Do not present confidence as validated accuracy.

SpiceLevel and RatingCount already exist. Improve explicit feature routing and provenance, not an unnecessary new source collection. An item card must distinguish inferred spice and missing ratings; an oracle generator-truth sidecar must never enter ordinary model features. Any new generator is a separate log and must keep historical v4 intact.

G20 is a real local integrity contradiction: `ifct_source_profiles.json` contains source profiles while the terms deny IFCT use. Correct the factual declaration and trace every consumer. DS-9 is resolved by owner confirmation of permission and retention; the instrument was not independently inspected. Declaring attribution alone is not permission.

### Canonical audit decisions

The audit owns DS-7 through DS-12. Our earlier independent-validation and release decisions have been renamed **VAL-1** and **REL-1** to remove the collision.

| ID | Decision / action | State |
|---|---|---|
| DS-7 | Include instruction-derived flags in the candidate subject to source-terms verification, or keep them local-only | Approved: include flags subject to terms verification |
| DS-8 | Evidence-only annotation, or new fail-closed status alongside preserved historical labels | Approved: evidence plus new UNKNOWN status; retain legacy labels |
| DS-9 | Retain IFCT with substantiated permission/terms, or remove affected source-derived content through a coherent rebuild | Owner confirms permission already held; retain and declare; grant not independently inspected |
| DS-10 | Existing-attribute item-card view for follow-up use | Approved; implemented item-card view |
| DS-11 | Separate published-attribute synthetic generator | Approved; separate v5 generated and full replay passed; v4 preserved |
| DS-12 | Region-by-source analysis before Goa-specific claims | Included as authorized read-only audit work; no extra permission needed |
| VAL-1 | Independent annotation/evaluation protocol | Pending before collecting reference labels |
| REL-1 | Final promotion/publication | Local canonical integration authorized by active goal; remote publication remains excluded |

Instruction rules need a compatibility layer for the audit's `COMPLETE/MISSING/PLACEHOLDER/NOT_A_METHOD/TRUNCATED` statuses, `liquid_fate_unstated`, `over_desk_cut`, and gate-spec digest. The initial quality-v1 draft prototype is a different exploratory rule, not an implementation of the frozen classifier or a reproduction of the audit. Do not report parity until a DEV-only comparison against the pinned audit rule demonstrates it. Language-unsupported must remain distinct from observed non-method text. Preserve both status/reason evidence and any broad completeness summary explicitly.

Add per-class allergen evidence (`explicit`, `implicit_name`, `ambiguous_carrier`, `text_silent`, `unassessed`) beside legacy statuses, with regex/version provenance and no hidden conversion of uncertain absence to safety. Add region stratum semantics matching the audit: North/South coarse, Pan-Indian/missing unassigned, named primary regions, and descriptive sub-threshold codes. The earlier generic coarse/specific indicator is insufficient by itself.

The full active goal now includes addressing G17-G23 and the corrected G5/G6/G8/G11 priorities, their verifiable outputs or explicit user decisions, and local canonical integration. Completing only the original seven-flag prototype is not completion.

### User decisions received during execution (2026-09-28)

DS-7 approved: include non-text flags subject to terms verification. DS-8 approved: add evidence plus a new UNKNOWN status, preserving historical labels. DS-9: owner confirms permission already held and instructs proceeding; retain IFCT and correct declarations, recording owner attestation rather than claiming independent inspection of a grant. DS-10 and DS-11 approved: both the item-card view and a separate published-attribute generator are in scope. These decisions supersede the earlier pending entries; the execution ledger preserves the exact replies.
