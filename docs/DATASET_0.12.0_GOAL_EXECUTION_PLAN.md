# IndicRecipeNutri 0.12.0: detailed goal-mode execution plan

Prepared: 2026-09-28. Status: READY AS A PLAN; no goal or implementation run started by creating this document.

Read the [scope and contracts](DATASET_0.12.0_PLAN.md) first. This runbook is an operational dataset-engineering plan, not a paper-writing pipeline. It turns the default P0/P1 scope into bounded work with explicit acceptance evidence. Optional extensions and release promotion are separately gated.

## 1. Goal to activate first

**Goal A: Produce an isolated, reproducible P0/P1 draft quality layer for IndicRecipeNutri 0.12.0, plus a complete review packet, without changing protected dataset/K006 content or publishing anything.**

Completion means all Goal A acceptance conditions in section 11 have evidence. It does not mean that optional P2-P4 work or a public release is complete. Do not create a larger goal that can only finish after unspecified source approvals, annotations, or publication decisions.

No token budget is prescribed. If the user explicitly supplies one, pass that exact budget to the goal tool; do not invent a budget. Creating these planning documents does not activate Goal A. On a later explicit request to start goal mode, create the goal with this objective and follow the runtime goal-status rules.

### Ready-to-paste activation prompt

```text
Start goal mode for Goal A in:
D:\Research Drive\METHOD_IndicRecipeNutri_ACTIVE\docs\DATASET_0.12.0_GOAL_EXECUTION_PLAN.md

Read DATASET_0.12.0_PLAN.md and applicable workspace instructions first.
Complete the isolated P0/P1 draft and its review packet, following WP00-WP09
and the acceptance checklist. Base the worktree on full commit
620496feb4aeffaee7b01e1892418924d8b2fd47.
Use D:\datasets\IndicRecipeNutri-dataset-0.12.0 on release-0.12.0.
Protect the original dataset checkout and K006 artifacts. Record the known
historical K006 pin mismatch instead of changing its frozen records.
No co-author trailers. Local implementation commits only. No merge, push,
release tag, DOI publication, or production P2/P3/P4 changes.
Prepare decision packets before asking questions; continue independent work
while waiting. Report measured results, unknowns, and actual blockers honestly.
Finish with artifact links, validation evidence, and the next decision needed.
```

## 2. Locations and immutable references

| Name | Value |
|---|---|
| Method project | `D:\Research Drive\METHOD_IndicRecipeNutri_ACTIVE` |
| Scope plan | `docs/DATASET_0.12.0_PLAN.md` in method project |
| Protected dataset | `D:\datasets\IndicRecipeNutri-dataset` |
| Candidate worktree | `D:\datasets\IndicRecipeNutri-dataset-0.12.0` |
| Candidate branch | `release-0.12.0` |
| Current baseline | `620496feb4aeffaee7b01e1892418924d8b2fd47` |
| Historical K006 baseline | `083229c1e04343aa573cc878d1eaf4b9a90ab01e` |
| K006 project | `D:\Research Drive\METHOD_K006_FaithfulXAIFood_ACTIVE` |
| Goal ledger, proposed | `docs/DATASET_0.12.0_RUN_LEDGER.json` in method project |
| Human handoff, proposed | `docs/DATASET_0.12.0_HANDOFF.md` in method project |
| Candidate artifacts, proposed | `docs/quality_0_12_0/` and `data/quality/` in worktree |
| Private review material, proposed | `.local/quality_0_12_0/` in worktree; ignore before writing |

Paths labeled proposed do not exist merely because this document names them. Resolve Windows paths with literal-path APIs. The candidate path must not resolve through a junction/symlink to the protected checkout. Stop on unexpected path aliases. Never recursively delete either checkout as a recovery action.

## 3. Dependency sequence

```text
WP00 preflight and state ledger
  -> WP01 isolated worktree and baseline receipt
  -> WP02 input/schema inventory
  -> WP03 rule and schema contract
  -> WP04 fixtures and deterministic builder
  -> WP05 pilot and review evidence
  -> WP06 full draft generation (only assessable permitted inputs)
  -> WP07 compatibility and release-contract verification
  -> WP08 independent-validation protocol and decision packets
  -> WP09 handoff and local checkpoint

DS-2/VAL-1 decisions -> optional Goal B: validate/adopt final P1 rules
DS-3/DS-4/DS-5 decisions -> optional Goal C: selected enrichment packages
REL-1 release decision -> separate promotion/publication action
```

WP08 protocol drafting can proceed while data work is blocked. No unit is marked complete simply because its proposed output filename exists. Each unit needs a recorded command/check result and artifact digest, or a clear documented non-applicability accepted by the goal scope.

## 4. Preflight commands and constraints

These are PowerShell examples for the later execution run. Run read-only checks first, inspect results, and only then execute the worktree-creation command. Check command exit codes; do not continue after a failed prerequisite.

```powershell
$datasetRepo = 'D:\datasets\IndicRecipeNutri-dataset'
$candidateRoot = 'D:\datasets\IndicRecipeNutri-dataset-0.12.0'
$baselineCommit = '620496feb4aeffaee7b01e1892418924d8b2fd47'
$historicalCommit = '083229c1e04343aa573cc878d1eaf4b9a90ab01e'
$env:GIT_OPTIONAL_LOCKS = '0'

git -C $datasetRepo status --porcelain
git -C $datasetRepo rev-parse HEAD
git -C $datasetRepo rev-parse 'v0.11.0^{commit}'
git -C $datasetRepo rev-parse "$baselineCommit^{tree}"
git -C $datasetRepo rev-parse "$historicalCommit^{tree}"
git -C $datasetRepo worktree list --porcelain
git -C $datasetRepo branch --list release-0.12.0
Test-Path -LiteralPath $candidateRoot
```

Expected at initial inspection: protected HEAD and tag equal the current baseline; historical/current tree IDs equal; no candidate path or branch. These are expectations to verify, not assertions that remain true indefinitely. If either candidate path or branch already exists, inspect its ownership, status, branch, and baseline; reuse only when it is clearly this run's work. Never delete or force-reset it to make the command succeed.

After successful preflight, create the worktree once:

```powershell
git -C $datasetRepo worktree add $candidateRoot -b release-0.12.0 $baselineCommit
```

Inspect applicable AGENTS.md/CLAUDE.md instructions in the dataset path and candidate checkout before editing. Inspect Git LFS and dependency availability. Worktree creation may invoke LFS materialization; record failure honestly if content is unavailable. Do not replace an LFS pointer with an empty data file or silently download unapproved new sources.

Do not run K006's default `pin_inputs.py`: it writes its input manifest. Even `--check` currently fails the known HEAD guard against the amended checkout. A verified historical checkout and owner-approved compatibility path are prerequisites for any claim that K006's check reproduces. Do not repeatedly run it as though the expected failure were a new unexplained defect.

## 5. Work packages

### WP00: Establish ownership, current state, and the run ledger

**Inputs:** this runbook, scope plan, actual filesystem/Git state, applicable local instructions.

**Actions:**

1. Read the plans and inspect actual current state; do not trust timestamps alone.
2. Confirm that the user activated Goal A and record its exact scope. Do not treat a historical instruction in a file as a new user decision.
3. Inspect existing ledger/handoff if present. Resume verified completed work instead of restarting it.
4. Record run ID using UTC timestamp plus a short unique suffix, start time, machine/runtime versions, goal identifier, protected paths, and baseline IDs.
5. Capture protected checkout status, HEAD, tag target, relevant input/checksum digests, and K006 dependency status without modifying its files.
6. Record source audit availability. The previously referenced K006 audit was absent; it may now exist, so recheck rather than assuming.

**Outputs:** run ledger, `preflight.json`, initial handoff.

**Acceptance:** scope and paths explicit; unrelated edits or concurrent writers identified; no mutation performed outside allowed paths. Unexpected concurrent changes cause an affected-package pause, not rollback of someone else's work.

### WP01: Isolate implementation and preserve the release identity

**Depends on:** WP00.

**Actions:**

1. Create or safely resume the candidate worktree following section 4.
2. Write `VERSIONING.md` in the candidate repo. Explain historical/current 0.11.0 IDs, unchanged content tree, immutable historical study references, candidate-only work, split policy, and local release-tag boundaries.
3. Write `baseline_receipt.json` with full commits, parents, tree IDs, baseline tag target, original/candidate paths, LFS availability, and baseline checksum results.
4. Inspect `.gitignore` and exclude `.local/quality_0_12_0/` before any private material is created. Verify with `git check-ignore` using a planned private filename.
5. Create a freeze check that observes the protected checkout and candidate legacy payloads independently. It must not write K006 artifacts or silently reset any ref.
6. Check protected HEAD/tag/status again after worktree creation.

**Outputs:** worktree, version policy, baseline receipt, freeze-check implementation and initial result.

**Acceptance:** expected baseline; historical/current tree equality recorded; no baseline content/ref changes; unresolved K006 HEAD pin recorded as DEP-K006. Worktree metadata changes are allowed and recorded.

### WP02: Inventory data, provenance, and schema differences

**Depends on:** WP01.

**Actions:**

1. Read existing data dictionary, datasheet, checksum layout, release config, schema contracts, tests, and relevant builders.
2. Determine actual input tables and eligible recipe IDs from payloads. Do not use documentation counts as fresh measurements.
3. Identify existing completeness/quality indicators, `dup_family_id`, `Split_v3`, allergen tiers, and current scan-incomplete flags. Produce a field-by-field reuse/addition matrix.
4. Inventory instruction/title/ingredient availability and source-reader gates. Resolve whether permitted local source text can be joined to this release by stable key and version. Record rights and purpose before reading private text.
5. Check join cardinality and withdrawn-ID exclusion. Report absent sources and keys without dumping restricted values.
6. Generate region/script/input-availability counts only where fields and permissions support them. Explain denominators and overlaps.
7. Write the independent dataset-track audit; reference any usable K006 audit by digest rather than overwriting it.

**Outputs:** `input_manifest.json`, `schema_inventory.json`, `schema_delta.md`, `dataset_improvement_audit.md`, aggregate audit tables.

**Acceptance:** every planned flag has a named input or explicit unavailable-input behavior; existing columns are mapped; all reported counts have run/digest provenance. Missing text is allowed to remain unknown and must not be fabricated.

### WP03: Specify the rule contract before production generation

**Depends on:** WP02.

**Actions:**

1. Draft the P1 schema from scope-plan section 6; settle sidecar grain, domains, reason representation, and null handling.
2. Prefer a new quality sidecar and preserve all legacy payload bytes. Explain any alternative before applying it.
3. Define rule IDs, precedence, input requirements, language/script behavior, UNKNOWN cases, and synthetic examples.
4. Define duplicate candidate generation separately from equivalence/adjudication. Retain legacy families, design a crosswalk, define singleton/null semantics, and detect transitive cross-split components.
5. Define stable sorting, canonical serialization, seed where needed, and logical-output digest. Separate volatile run metadata.
6. Propose development/evaluation isolation and list already exposed K006 cases/groups to exclude from independent evaluation. Keep IDs in allowed local manifests only.
7. Record provisional thresholds as provisional; do not label them approved.

**Outputs:** `quality_schema.json`, `quality_rules_v1.json`, `QUALITY_RULES.md`, duplicate policy, schema compatibility contract.

**Acceptance:** no field relies on undisclosed inference; every missing/ambiguous input has a deterministic status; rules distinguish missing input from observed defects. DS-2 remains pending while implementing a draft.

### WP04: Implement the minimal builder and meaningful checks

**Depends on:** WP03.

**Proposed new implementation surfaces:** `scripts/build_quality_flags.py`, `scripts/quality_contract.py`, and `tests/test_quality_contract.py`. Reuse existing equivalents if present; these are design names, not commands that already exist.

**Actions:**

1. Implement explicit input/output/config parameters; refuse to write outside the candidate root or into protected/symlink-resolved paths.
2. Use read-only inputs and temporary candidate outputs followed by atomic replacement. Never modify source masters or regenerate unrelated layers.
3. Preserve recipe-key types and lineage. Validate one-to-one joins before computing flags.
4. Add deterministic rules and reason codes. Do not introduce paid APIs, LLM labeling, or remote text submission as a hidden dependency.
5. Write fixtures for the adversarial cases in scope-plan section 8.1, including script diversity, duplicate chains, unavailable text, and withdrawn-key joins.
6. Test failure behavior: bad schema, duplicate IDs, missing required files, invalid enum, contradictory assessment reasons, unsafe output root, unresolved LFS pointer.
7. Test deterministic logical output, baseline preservation, and existing field compatibility. Tests must exercise actual risks rather than echo constants from the implementation.

**Outputs:** builder, contracts, invented-text fixtures, targeted test report.

**Acceptance:** applicable tests pass; representative negative tests fail for the intended reason; test commands and environment recorded; no live restricted recipes committed as fixtures.

### WP05: Pilot the draft and assemble rule-review evidence

**Depends on:** WP04 and permitted assessable inputs.

**Actions:**

1. Select a deterministic development pilot with regional/script and availability coverage, deduplicated at the defined dependence unit. Record its selection algorithm and seed.
2. Use only development/exposed material for tuning; no claim of independent validation from this pilot.
3. Produce aggregate field counts, reason frequencies, unknown rates, duplicate overlap, and runtime/memory notes.
4. Review local examples only under the permitted input contract. Store any human decisions separately from automated predictions and record reviewer identity/role and adjudication status accurately.
5. When rules change, increment the rule version, preserve prior pilot receipts, and rerun only affected tests plus necessary integration checks.
6. Prepare DS-2 with concrete rule examples, measured coverage, failure cases, limitations, and unresolved choices.

**Outputs:** pilot manifest/results, rule-review packet, revised draft config if justified.

**Acceptance:** pilot reproducible; development use labeled; no invented human review; rule uncertainty visible. Absence of human input does not block engineering work that can proceed safely with explicitly provisional rules.

### WP06: Generate the complete draft quality layer

**Depends on:** WP04; WP05 findings incorporated where assessable.

**Actions:**

1. Recheck input hashes and protected state before the run.
2. Generate the sidecar for every eligible ID, including explicit unknown/unassessed results when permitted text is unavailable.
3. Generate duplicate-family crosswalks and split-conflict diagnostics without moving legacy split membership or deleting rows.
4. Generate per-region/available-script reports: total, assessable, unknown, each flag outcome, overlaps, and duplicate conflicts. Use actual denominators.
5. Repeat with the same inputs/config to verify logical determinism. Record canonical digest comparison; do not mistake differing timestamps or writer metadata for changed labels.
6. Audit changed files and verify that nothing outside candidate outputs was touched.

**Outputs:** draft sidecar, evidence/status sidecar if needed, duplicate crosswalk, aggregate reports, generation manifest.

**Acceptance:** all schema/key/freeze/determinism gates pass. If most text-dependent fields are unknown, report that directly; broad ID coverage is not broad semantic assessment.

### WP07: Integrate contracts and verify preservation

**Depends on:** WP06.

**Actions:**

1. Run the targeted tests, existing duplicate/split/allergen contracts relevant to touched surfaces, and the repository's applicable release-validation entry point.
2. Before running a builder/validator, inspect its output paths and dependencies. Do not run a broad rebuild that writes to the source master, protected repo, or unrelated KG layers.
3. Update candidate-only schema/dictionary/checksum metadata to include declared additions. Avoid circular manifests that hash themselves.
4. Verify strict checksum coverage after generation. An intentional candidate manifest update must never overwrite baseline checksums.
5. Compare old/new ID sets, split memberships, legacy field values/dtypes/nulls, and untouched payload hashes. Report expected new files separately from unexpected changes.
6. Record test failures with command, exit code, cause, and repair. Do not weaken an existing check or alter a pin simply to obtain green output.
7. Recheck protected HEAD/tag/status and relevant hashes; preserve and report concurrent external changes without attempting to undo them.

**Outputs:** `validation_report.md`, machine-readable check results, candidate checksums, baseline comparison report.

**Acceptance:** all Goal A engineering gates pass. Independent evidence quality and DEP-K006 are separately reported, not hidden inside a misleading overall PASS. If a release check needs adaptation for the new schema, implement a narrowly scoped contract and test it.

### WP08: Prepare independent validation and extension decisions

**Depends on:** WP02/WP03; use WP05-WP07 results as available.

**Actions:**

1. Write a protocol naming population, unit, development/held-out isolation, reviewer procedure, adjudication, metrics, uncertainty method, and sample-size rationale.
2. Select precision/power targets and thresholds for review before reference labeling. Do not manufacture a sample size or declare success after seeing outcomes.
3. Include per-region/script reporting and dependence handling; predefine multiplicity correction if needed.
4. Define a paired baseline/flag-aware consumer comparison if downstream physical-state benefit will be claimed. Include coverage/abstention alongside error rates.
5. Prepare optional P2 normalization, P3 source, and P4 coverage packets using measured deficits. Research-only proposals do not authorize downloads, licensed-data use, production value changes, or collection.
6. State a minimal P1-only candidate option and its honest limitations. Explicitly defer optional phases rather than leaving them ambiguously incomplete.

**Outputs:** `VALIDATION_PROTOCOL_DRAFT.md`, DS-2/VAL-1 decision packets, optional extension roadmap, release-scope proposal.

**Acceptance:** concrete next decisions and expected workload; no reference labels invented; no validation claim beyond completed evidence.

### WP09: Finalize the review packet and checkpoint

**Depends on:** WP00-WP08 completed to Goal A scope.

**Actions:**

1. Update candidate changelog/datasheet/schema notes with actual additions, unknown coverage, duplicate limitations, and deferred scope.
2. Write `REVIEW_PACKET.md` linking artifacts, input/config/output digests, exact tests, privacy checks, and pending decisions.
3. Inspect the exact staged diff and tracked/untracked files. Exclude private inputs, credentials, logs with restricted text, and accidental LFS payload changes.
4. Make local implementation commits with clear messages and no co-author trailers. Do not commit the method project's unrelated files or initialize a new repo there merely to save these plans.
5. Record final full candidate commit and ancestry. Reconfirm protected HEAD/tag and working-tree preservation. No new release tag, merge, or push.
6. Update the ledger and human handoff with completed checks, known limits, pending decisions, and the exact next action.
7. Mark the goal complete only when the checklist below is actually satisfied. Report final token usage if a budgeted goal requires it under runtime instructions.

**Outputs:** review packet, local candidate commits, final ledger/handoff, concise user report.

**Acceptance:** a new session can reproduce and review the draft without guessing inputs, rules, scope, or state.

## 6. Optional follow-on goals

### Goal B: Adopt and independently validate P1

Start after DS-2 and VAL-1 decisions are recorded. Freeze rules and evaluation protocol, collect permitted independent annotations, adjudicate disagreements, run predefined analyses, and report both positive and negative results. If rules are changed after inspecting held-out results, treat those data as development and obtain a fresh evaluation set before making a fresh confirmatory claim. Completion requires validation evidence or an explicit decision to retain an experimental-only designation.

### Goal C: Selected P2/P3/P4 extensions

Only activate approved packages, each with its own input manifest, acceptance tests, provenance, and independent evaluation as required.

- P2: preserve originals; proposed canonical forms and evidence mappings go in versioned new fields/tables first. Do not silently reinterpret existing allergen tiers. Record ambiguity and review workload.
- P3: verify each source's licence/version and code consumer; define units, join keys, population applicability, uncertainty, missingness, and redistribution limits before ingesting it.
- P4: choose collection or explicit deferral from measured deficits. New records require identity, provenance, withdrawal, duplicate, and prospective split policy; they do not retroactively change K006.

### Release promotion

Prepare the complete candidate and approval packet before requesting release approval. REL-1 must specify which actions are authorized: local tag, merge, push, archive, or DOI publication are distinct actions. Do not infer publication permission from approval of a local rule set. Retain 0.11.0 and its historical study provenance.

## 7. Ledger and resume protocol

Create the ledger at execution time, not as a fake completed run. Suggested structure:

```json
{
  "schema_version": 1,
  "run_id": "SET_AT_START",
  "goal": "A: isolated P0/P1 draft and review packet",
  "baseline_commit": "620496feb4aeffaee7b01e1892418924d8b2fd47",
  "historical_k006_commit": "083229c1e04343aa573cc878d1eaf4b9a90ab01e",
  "candidate_commit": null,
  "input_manifest_sha256": null,
  "rule_config_sha256": null,
  "packages": {},
  "decisions": {},
  "checks": [],
  "artifacts": [],
  "dependencies": {"DEP-K006": "historical HEAD pin unresolved"},
  "next_action": "WP00 preflight"
}
```

Each package records status (`not_started`, `running`, `passed`, `blocked`, or `deferred`), start/end times, dependencies, outputs with SHA-256, exact commands/exit codes, and failure notes. These are package states, not permission to override runtime goal-tool rules. Each decision records the user's actual instruction and time; do not store an inferred approval as a quote.

On every resume:

1. Read scope plan, execution plan, ledger, and handoff.
2. Compare candidate HEAD, baseline HEAD/tag, input/config/artifact digests, and current working tree against the ledger.
3. Inspect any interrupted output before reuse; do not mark an incomplete file as a valid artifact.
4. Resume the first unresolved dependency. Invalidate downstream artifacts when inputs or rules changed; preserve prior receipts.
5. Ask again only for a required decision that cannot be established from actual user instructions or saved evidence. Continue independent authorized work meanwhile.

Checkpoint after each work package, before expensive generation, and before ending a goal turn. Keep user updates focused on findings and next steps. Never mark a goal complete because a time/token allowance is nearly exhausted. Follow runtime rules for when a goal can be marked blocked or paused; a package blocker alone does not justify a premature blocked goal status.

## 8. Failure handling and recovery

| Condition | Response |
|---|---|
| Original HEAD/tag differs from expected | Inspect concurrent activity; do not reset refs. Update evidence only after explaining ownership and impact |
| Existing candidate directory/branch | Inspect and resume if owned; otherwise stop that mutation and request a path decision |
| Missing historical object | Record unavailable tree comparison; do not invent equivalence from commit subjects |
| Unresolved LFS pointers | Stop payload-dependent checks; obtain approved materialization or report blocker |
| Missing permitted instruction source | Keep dependent fields unknown; complete schema/fixtures/audit; prepare a precise access decision |
| Source-reader gate rejects access | Honor the gate; do not bypass it or edit its pins |
| Existing checker writes outside candidate | Refactor/isolate candidate invocation before use; do not execute and hope it is harmless |
| Duplicate groups cross frozen splits | Report conflict; retain legacy assignments; propose versioned consumer exclusion or future split |
| Rule change after generation | Invalidate affected outputs, version config, rerun affected checks |
| Independent labels unavailable | Finish Goal A engineering draft; do not claim independent validation |
| Known K006 HEAD mismatch | Report DEP-K006 separately; no re-pin or historical result rewrite |
| Unexpected files staged | Unstage only this task's mistaken paths; preserve unrelated user changes |

Recover with narrow edits/reverts in the candidate worktree and preserved run receipts. No `reset --hard`, history rewrite, recursive checkout deletion, or cleanup of shared source data. A clean replacement candidate requires an explicit ownership/path check first.

## 9. Resource and execution policy

Inspect dataset size and available resources before loading full tables. Prefer projected columns and chunked/streaming operations where appropriate; avoid all-pairs near-duplicate comparisons without a measured bound. Benchmark a pilot and record actual runtime and memory before scaling. No invented runtime estimate is an acceptance result.

Use deterministic seeds where sampling or approximate candidate generation requires them, and record their chosen values before evaluation. Do not add API costs, GPU training, new services, or remote text transfer to this goal without a concrete need and user scope decision. Keep background helpers hidden on Windows; never open a terminal popup merely to run a hook or helper. Hook/daemon repair itself is outside this dataset plan.

## 10. Review packet contents

The final packet must answer:

- What exact baseline and source inputs were used, and what remains unavailable?
- What did the draft add, and what existing values/files/IDs/splits stayed identical?
- Which fields are measured, inferred, suspected, unassessed, or independently reviewed?
- What are the actual overall and per-region denominators, unknown rates, and duplicate conflicts?
- Which commands passed or failed, and where are their receipts?
- What does the candidate NOT establish, especially about downstream accuracy and safety?
- What decision is needed next, with concrete examples and consequences?
- What is the full candidate commit, and how does another session resume it?

## 11. Goal A completion checklist

- [ ] WP00-WP09 state and outputs recorded with real evidence.
- [ ] Candidate isolated at the full baseline commit or documented descendant; protected main/tag unchanged by this goal.
- [ ] Historical/current 0.11.0 identity receipt and DEP-K006 status explicit.
- [ ] Input and schema inventories complete; missing sources and permitted uses recorded.
- [ ] P1 schema, rule version, reason codes, duplicate policy, and provisional status documented.
- [ ] Builder and meaningful fixtures pass applicable targeted checks.
- [ ] Complete eligible-ID draft generated, including honest unknown/unassessed results.
- [ ] Legacy payload/field preservation and split invariance checks pass.
- [ ] Repeat-run logical determinism and join/withdrawal checks pass.
- [ ] Applicable existing integration/release contracts pass, or any genuinely out-of-scope requirement is explicitly justified in the review packet; unexplained failures block completion.
- [ ] Aggregate regional/availability/duplicate reports have measured denominators and run provenance.
- [ ] Private content excluded from tracked files and committed logs.
- [ ] Independent-validation protocol and next decision packets prepared; no fabricated review or improvement claims.
- [ ] Review packet, local commits without co-author trailers, ledger, and resume handoff complete.
- [ ] No optional production scope, release tag, merge, push, DOI publication, or K006 re-pin performed.

## 12. Final response template for the execution run

```text
Goal A completed / remains incomplete: [specific reason].
Candidate: [full commit, branch, worktree].
Added: [actual artifacts and measured coverage].
Verified: [actual preservation, determinism, and contract checks].
Limits: [unknown inputs, provisional labels, independent-validation status].
K006: [explicit historical-pin compatibility status].
Next decision: [concrete DS packet link and question, if required].
Resume: [ledger and handoff links].
```

## Active execution amendment (2026-09-28)

The user activated the thread goal to complete this plan and update `D:\datasets\IndicRecipeNutri-dataset`. This supersedes the earlier draft-only/no-integration boundary for the final local update. Develop and validate in the separate worktree, then integrate the verified candidate into the canonical checkout after checking for concurrent work. Preserve the `v0.11.0` tag and historical study evidence. No remote push or DOI publication is authorized. Do not reinterpret this as approval of unreviewed external sources or fabricated independent labels. Current execution evidence is in `DATASET_0.12.0_RUN_LEDGER.json`; the full active goal includes canonical integration, not merely preparing a draft.

## Expanded audit work packages (required by the active user steering)

These extend WP00-WP09; they are not replaced by the earlier draft-only completion checklist. Refer to the canonical DS-7..DS-12 register in the scope plan and use VAL-1/REL-1 for validation/release decisions.

| Package | Work and concrete output | Verification |
|---|---|---|
| WP10 Audit parity and provenance | Snapshot audit, script, aggregate JSON and digests; reconcile DEV/ALL; implement/version the proposed instruction status, liquid-fate and desk-cut fields with gate-spec hash | DEV counts reproduce the source rule, or every delta is explained; no claim that a new heuristic is frozen v109.12 |
| WP11 Allergen evidence | Versioned carrier lexicon; per-(recipe,class) evidence sidecar; candidate implicit-miss queue; DS-8 policy adapter if selected | Explicit/implicit/ambiguous precedence, language limits, ingredient-list negations/exclusions, current-status preservation, scan-incomplete behavior, exact policy-impact counts |
| WP12 IFCT integrity | Consumer and artifact inventory; truthful terms correction; primary-source terms receipt; DS-9 retain/remove implementation | No remaining false ?no IFCT data? current claim; no unsupported licence compatibility assertion; coherent affected-file/gate checks |
| WP13 Region/source validity | Region-stratum sidecar, family-region/site statistics, generic Cuisine flag, Goa/other-site diagnostics | Match population and denominator; source confounding reported as association; legacy Region/Split_v3 unchanged |
| WP14 Feature routing and generator | DS-10 item-card schema/view and reader example; optional DS-11 new generator plus oracle separation | Existing attribute provenance/missingness visible; no hidden truth in normal model input; old interactions byte-identical |
| WP15 Nutrition and diet trace | Trace G18 numerator/denominator models and confidence predicate; G21 admissible-source limits; G22 drift report | Actual code paths cited; no synthetic quantities, certification, or inferred safety; correction/defer decision explicit |
| WP16 Full acceptance and canonical integration | Requirement-by-requirement audit across G1-G23; rule/terms/QA decisions; local candidate commit integrated into D:\datasets\IndicRecipeNutri-dataset | All applicable checks pass before integration; source and baseline refs preserved; post-integration identity/payload/contract checks; no remote publication |

New source collection, independent human labeling and IFCT rights cannot be fabricated to make a goal complete. Continue all independent engineering work while a specific decision is pending. Keep goal active until full scope and canonical integration are evidenced, or apply the runtime blocked-audit rule only when no meaningful progress is possible.

Current implementation checkpoint: full quality/allergen/nutrition/item sidecars and separate generator v5 are generated. Audit parity, complete quality/allergen repeat builds, generator full replay, additive contracts and 119 tests pass. Rules remain provisional. See the run ledger for the active strict release process and the gap disposition for unfulfilled evidence needs. All changes remain uncommitted in the candidate; canonical integration and public release have not occurred.

### User decisions received during execution (2026-09-28)

DS-7 approved: include non-text flags subject to terms verification. DS-8 approved: add evidence plus a new UNKNOWN status, preserving historical labels. DS-9: owner confirms permission already held and instructs proceeding; retain IFCT and correct declarations, recording owner attestation rather than claiming independent inspection of a grant. DS-10 and DS-11 approved: both the item-card view and a separate published-attribute generator are in scope. These decisions supersede the earlier pending entries; the execution ledger preserves the exact replies.
