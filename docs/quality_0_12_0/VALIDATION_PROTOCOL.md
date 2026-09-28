# Proposed independent validation protocol

Status: proposal for VAL-1; no reference labels have been collected or independent error rates measured by this update. Engineering fixtures and exact audit-count agreement are not reference validation. The existing K006 investigator-confirmed, AI-assisted audit has its own provenance and must not silently become a new independent test set.

## Freeze and populations

Before drawing a sample, freeze candidate commit, input and rule hashes, definitions, exclusion policy, analyst roles and acceptance targets. Develop rules on DEV only. Keep the existing test split locked for study evaluation; creating descriptive sidecars does not authorize tuning on its outcomes.

Use separate tasks: instruction completeness/end state/intermediates; allergen evidence ambiguity and name conflicts; candidate duplicate equivalence. Nutrition accuracy needs actual reference masses/composition and cannot be evaluated by asking a reviewer whether an inferred number looks plausible. Diet certification needs admissible documentary evidence.

## Sampling proposal

Use a DEV probability sample for population estimates, stratified by source site, language support and region stratum where feasible. Fix allocation and seed before access to labels, retain each unit's inclusion probability, and report source/language cells too small for a stable estimate. Do not treat the corpus's recipe counts as representative population food prevalence.

Use a separately reported diagnostic sample to cover every quality output class, ambiguous carrier type, legacy/status conflict, unsupported language and cross-split duplicate group. Review the 144 ALL name-conflict candidates only under the applicable split-access policy; the DEV subset can be investigated without treating test candidates as development evidence. Diagnostic oversampling does not yield an unweighted corpus error rate.

Select the total sample size from the chosen endpoint and uncertainty target before annotation. For illustration only, 149 independent randomly selected predicted-admissible items with zero errors gives the one-sided exact 95% binomial upper bound `1 - 0.05**(1/149)`, approximately 2%. This does not estimate recall, does not cover all regional/language strata, and is not directly valid for a clustered or unequal-probability design. A weighted/clustered design requires its own variance calculation. This example is not an adopted acceptance threshold or a statement that 149 reviews are sufficient for the release.

## Annotation and disagreement

Two reviewers independently see permitted local source evidence and written definitions, blinded to rule outputs and each other's judgments. Record label, abstention, evidence locator, reviewer identifier, timestamp and provenance. Do not replace unavailable source text with a model-generated instruction. Reviewers must be competent in the item's language; otherwise mark language-unassessed.

Adjudicate disagreements with a recorded rationale after independent labels are frozen. Keep original labels, adjudication and missing-evidence outcomes. AI assistance, if used, must be declared and evaluated as such; it cannot be described as independent human-only labeling. Keep private text local and release only permitted structured evidence and aggregates.

## Endpoints and decisions

Report class-wise confusion matrices, abstention/UNKNOWN rates, coverage, precision and recall with denominators and uncertainty. Recall needs a sample that includes predicted negatives. Report weighted population results separately from diagnostic findings. Cluster-aware uncertainty should account for source/family correlation; do not pool heterogeneous sources merely to obtain narrow intervals.

For allergens, distinguish lexical presence, text ambiguity, inferred absence and any externally verified absence. Do not label lexical-rule agreement as food safety. For duplicates, estimate pair/group precision on adjudicated evidence; cross-split candidates alone do not prove leakage. Never move historical splits to improve a reported score.

VAL-1 still needs reviewer availability, permitted local evidence access, endpoint/risk target and annotation budget. DS-2 final rule adoption follows the review results or an explicitly documented decision to distribute provisional annotations. Until then all current rules remain provisional. Any rule change invalidates affected generation and validation receipts and requires a new version plus repeat checks.
