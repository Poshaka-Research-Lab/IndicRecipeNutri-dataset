#!/usr/bin/env python
"""Semantic adapter from the staged context rule layer (internal source S1) to three-state per-item predicates.

Reads ONLY the staged tables written by `stage_cultural_context.py`
(data/cultural_context/occasion_registry.parquet, dietary_rules.parquet). Writes nothing.

Translation (docs/INTEGRATION_SCHEMA.md section 7):

  occasion state (source S1 legacy)           per-item predicate
  -----------------------------           -----------------------
  no occasion declared by the request     NOT_APPLICABLE  (nothing inferred from region,
                                          religion, recipe co-occurrence or corpus Occasion tags)
  EXPLICIT_PROHIBITION  (ABSTAIN)         FAIL for every item + explicit abstention
                                          (kept separate from NO_ELIGIBLE_ITEMS)
  INSUFFICIENT_EVIDENCE (UNDECIDABLE)     UNKNOWN for every item, never PASS
  NO_ADDITIONAL_RESTRICTION (NO_CONSTRAINT) no predicate (NO_CONSTRAINT); not a certification
  EVALUABLE_CONSTRAINT  (SERVE)           FAIL if an excluded tag is evidenced; PASS only if every
                                          relevant tag was assessed from destination evidence;
                                          UNKNOWN otherwise. At 0.11.0 destination_executable is
                                          false for every rule, so this is UNKNOWN for every item.

Deliberate divergence from source S1 `triage._decide_row` (more conservative, never less):
  * An occasion with NO rule is INSUFFICIENT_EVIDENCE unless its registry dietary_status is
    `confirmed_no_constraint`. source S1's strong-evidence/decidable-kind branch is not ported,
    because its calibration (STRONG_EVIDENCE, DECIDABLE_KINDS) is not part of the staged data.
  * A `confirmed_no_constraint` occasion gets the same standing-rule composition as a
    `no_exclusion` rule (source S1 applies standing rules only to the latter).

The API takes a declared occasion uid and optional per-item tag evidence. It has no parameter
for a recipe, its corpus Occasion/DietaryContext labels, a user's region or religion: rule
applicability can therefore never be inferred from co-occurrence.

Usage:  python scripts/context_rule_adapter.py --check   (runs scripts/fixtures/context_rule_adapter_fixtures.json)
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.dont_write_bytecode = True

import pandas as pd

# Inside the released dataset the tables sit beside scripts/; elsewhere, the staging tree.
_RELEASED = Path(__file__).resolve().parent.parent / "data" / "cultural_context"
_STAGING = Path(r"D:\datasets\_staging\IndicRecipeNutri_v0.11.0-candidate\data\cultural_context")
STAGED = _RELEASED if (_RELEASED / "dietary_rules.parquet").exists() else _STAGING
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "context_rule_adapter_fixtures.json"

EVALUABLE = "EVALUABLE_CONSTRAINT"
NO_ADDITIONAL = "NO_ADDITIONAL_RESTRICTION"
PROHIBITION = "EXPLICIT_PROHIBITION"
INSUFFICIENT = "INSUFFICIENT_EVIDENCE"
NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True)
class Outcome:
    occasion_state: str
    item_predicate: str | None          # PASS / FAIL / UNKNOWN / NO_CONSTRAINT / None (not applicable)
    abstain: bool
    governing_rules: tuple = ()
    evidence_tiers: tuple = ()
    hard_constraint_eligible: bool = False   # only a 'sourced' governing rule may be a hard constraint
    required_user_evidence: tuple = ()
    required_item_evidence: tuple = ()
    certifies: bool = False                 # silver conformance is never a certification
    basis: str = ""


class RuleLayer:
    def __init__(self, staged: Path = STAGED, rules_override: pd.DataFrame | None = None):
        self.occ = pd.read_parquet(staged / "occasion_registry.parquet").set_index("occasion_uid")
        rules = rules_override if rules_override is not None else pd.read_parquet(staged / "dietary_rules.parquet")
        self.rules = rules.set_index("rule_uid")
        self.standing = {}
        for uid, r in self.rules.iterrows():
            for rel in (r.standing_for_religions if r.standing_for_religions is not None else []):
                self.standing[rel] = uid

    # -------------------------------------------------------------- rule helpers
    def _tags(self, uid: str) -> set:
        r = self.rules.loc[uid]
        tags = set(r.excludes_tags)
        for other in (r.also_excludes_from_uids if r.also_excludes_from_uids is not None else []):
            tags |= set(self.rules.loc[other].excludes_tags)
        return tags

    def _item(self, uids: list, item_evidence: dict | None) -> str:
        """Per-item value for EVALUABLE_CONSTRAINT. item_evidence: tag -> True/False (assessed), absent = not assessed."""
        if not all(bool(self.rules.loc[u].destination_executable) for u in uids):
            return "UNKNOWN"
        tags = set().union(*(self._tags(u) for u in uids))
        ev = item_evidence or {}
        if "*" in tags or any(ev.get(t) is True for t in tags):
            return "FAIL"
        if all(t in ev and ev[t] is False for t in tags):
            return "PASS"
        return "UNKNOWN"

    def _evaluable(self, uids: list, item_evidence, occ_row, basis) -> Outcome:
        tiers = tuple(self.rules.loc[u].evidence_tier for u in uids)
        req_user = ("sect",) if occ_row is not None and occ_row.sect is not None and occ_row.dietary_rule_uid else ()
        return Outcome(EVALUABLE, self._item(uids, item_evidence), False, tuple(uids), tiers,
                       all(t == "sourced" for t in tiers), req_user,
                       tuple(sorted(set().union(*(self._tags(u) for u in uids)))), False, basis)

    def _standing_or_none(self, occ_row, item_evidence, rule_uid, basis_none) -> Outcome:
        standing = self.standing.get(occ_row.religion)
        if standing is not None:
            s = self.rules.loc[standing]
            if s.rule_class == "narrowing" and bool(s.source_executable):
                return self._evaluable([standing], item_evidence, occ_row,
                                       f"{basis_none}; standing rule {standing} of the occasion's tradition "
                                       "does not lapse and narrows")
        tiers = (self.rules.loc[rule_uid].evidence_tier,) if rule_uid else ()
        return Outcome(NO_ADDITIONAL, "NO_CONSTRAINT", False, (rule_uid,) if rule_uid else (), tiers,
                       False, (), (), False, basis_none + "; no sourced standing rule for this tradition")

    # -------------------------------------------------------------- public
    def decide(self, declared_occasion_uid: str | None, item_evidence: dict | None = None) -> Outcome:
        if declared_occasion_uid is None:
            return Outcome(NOT_APPLICABLE, None, False, basis="no occasion declared by the request")
        if declared_occasion_uid not in self.occ.index:
            return Outcome(INSUFFICIENT, "UNKNOWN", False, basis="occasion not in the registry")
        o = self.occ.loc[declared_occasion_uid]
        uid = o.dietary_rule_uid
        if uid is None:
            if o.dietary_status == "confirmed_no_constraint":
                return self._standing_or_none(o, item_evidence, None, "registry confirms no occasion constraint")
            return Outcome(INSUFFICIENT, "UNKNOWN", False,
                           basis=f"no rule recorded; dietary_status={o.dietary_status}")
        r = self.rules.loc[uid]
        tier = (r.evidence_tier,)
        if r.rule_class == "admits_no_food":
            return Outcome(PROHIBITION, "FAIL", True, (uid,), tier, r.evidence_tier == "sourced",
                           basis="rule admits no food; explicit abstention (not NO_ELIGIBLE_ITEMS)")
        if r.rule_class == "narrowing":
            if not bool(r.source_executable):
                return Outcome(INSUFFICIENT, "UNKNOWN", False, (uid,), tier,
                               basis="rule recorded but not evaluable (source_executable=false)")
            uids = [uid]
            standing = self.standing.get(o.religion)
            also = list(r.also_excludes_from_uids) if r.also_excludes_from_uids is not None else []
            if standing and standing != uid and standing not in also:
                uids.append(standing)  # a standing law composes; it never relaxes the occasion rule
            return self._evaluable(uids, item_evidence, o, "occasion rule narrows")
        if r.rule_class == "no_exclusion":
            return self._standing_or_none(o, item_evidence, uid, f"occasion rule {uid} adds no exclusion")
        raise ValueError(f"unknown rule_class {r.rule_class!r}")


# ------------------------------------------------------------------ fixtures
def run_fixtures() -> int:
    fx = json.loads(FIXTURES.read_text(encoding="utf-8"))
    layer = RuleLayer()
    failures = 0
    for case in fx["cases"]:
        lay = layer
        if case.get("synthetic_destination_executable"):
            rules = pd.read_parquet(STAGED / "dietary_rules.parquet")
            rules["destination_executable"] = True  # in-memory only: exercises the future PASS/FAIL path
            lay = RuleLayer(rules_override=rules)
        out = lay.decide(case["declared_occasion_uid"], case.get("item_evidence"))
        got = {k: getattr(out, k) for k in case["expect"]}
        got = {k: (list(v) if isinstance(v, tuple) else v) for k, v in got.items()}
        ok = got == case["expect"]
        failures += not ok
        print(("PASS " if ok else "FAIL ") + case["id"], "" if ok else f"expected {case['expect']} got {got}")
    # structural guard: the decision API cannot receive recipe/co-occurrence input
    import inspect
    params = list(inspect.signature(RuleLayer.decide).parameters)
    ok = params == ["self", "declared_occasion_uid", "item_evidence"]
    failures += not ok
    print(("PASS " if ok else "FAIL ") + "API-no-cooccurrence-input", params)
    print(f"{len(fx['cases']) + 1 - failures}/{len(fx['cases']) + 1} fixture checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(run_fixtures())
    print(__doc__)
