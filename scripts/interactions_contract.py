"""Structural contract for `data/interactions` — the current synthetic benchmark.

Replaces `synthetic_history_contract.py`, which staged two FROZEN historical generations
(`synthetic_interactions/` v1 and `synthetic_interactions_v3/`) and pinned their
`SNAPSHOT.json` digests. Both directories were retired in v0.7.0: they were independent
simulations whose remapped id spaces collide, so they could not be merged, and neither could
be brought up to date because their generator hardcoded another machine's paths.

WHY THERE IS NO SNAPSHOT PIN HERE. A frozen artefact needs its bytes pinned because nothing
else can regenerate it. `data/interactions` is regenerable — `scripts/build_interactions.py`
rebuilds it from the published corpus — and every one of its files already carries a digest
in `checksums/SHA256SUMS`, which `check_checksums` verifies in both directions. A second
byte-pin would duplicate that and would have to be hand-updated on every rebuild, which is
how a pin drifts into a rubber stamp.

So this contract checks STRUCTURE and SAFETY, the things a digest cannot see:

  * id maps are well-formed and injective in both directions
  * the item and entity namespaces agree (`item:<org_id>` <-> the same remap id)
  * every KG triple resolves to a known entity and relation
  * both splits reference only known users and items, and do not overlap
  * every referenced recipe is live in the published corpus and none is withdrawn
  * NO USER WITH A DIETARY RESTRICTION IS SERVED AN INCOMPATIBLE OR UNDECLARED RECIPE
  * `stats.json` describes the files that are actually present

The diet check is here rather than only in the generator on purpose. `build_interactions.py`
audits itself and refuses to write, but a generator's self-audit is not a release gate: it
does not run when someone edits a published file by hand, and CLAUDE.md records what happens
to gates nobody runs. Dietary law is a hard constraint, so it is verified at release time
against the corpus, independently of the code that produced the artefact.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

DIRNAME = "interactions"

REQUIRED = (
    "interactions.csv", "users.csv", "stats.json",
    "train.txt", "test.txt", "kg_final.txt",
    "user_list.txt", "item_list.txt", "entity_list.txt", "relation_list.txt",
)

# Only these four are declarations. Anything else is undeclared and is not servable to a
# user who has a dietary restriction.
DECLARED = ("Vegetarian", "Vegan", "Non-Vegetarian", "Eggetarian")
# user diet -> the recipe diets they may be served
COMPATIBLE = {
    "Vegan": {"Vegan"},
    "Vegetarian": {"Vegetarian", "Vegan", "Eggetarian"},
    "Eggetarian": {"Vegetarian", "Vegan", "Eggetarian"},
    "Non-Vegetarian": set(DECLARED),
}


def id_map(path: Path) -> dict[int, str]:
    """The final field is a remap ID; names may contain spaces."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].split() != ["org_id", "remap_id"]:
        raise ValueError(f"invalid ID-map header: {path.name}")
    result: dict[int, str] = {}
    originals: set[str] = set()
    for line in lines[1:]:
        if not line.strip():
            continue
        original, remapped = line.rsplit(None, 1)
        remapped = int(remapped)
        if remapped in result or original in originals:
            raise ValueError(f"duplicate map identity: {path.name}")
        result[remapped] = original
        originals.add(original)
    return result


def read_split(path: Path, users: dict, items: dict) -> tuple[set, int]:
    pairs: set[tuple[int, int]] = set()
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        user, *rated = map(int, line.split())
        if user not in users or any(item not in items for item in rated):
            raise ValueError(f"split references an unknown remapped user/item id: {path.name}")
        count += len(rated)
        pairs.update((user, item) for item in rated)
    return pairs, count


def validate_interactions(root: Path) -> list[str]:
    """Return a list of problems; empty means the contract holds."""
    from release_config import all_withdrawn_ids

    root = Path(root)
    folder = root / "data" / DIRNAME
    if not folder.exists():
        return [f"data/{DIRNAME}/ is missing"]

    missing = [n for n in REQUIRED if not (folder / n).exists()]
    if missing:
        return [f"data/{DIRNAME}/ is missing {', '.join(sorted(missing))}"]

    problems: list[str] = []
    try:
        items = id_map(folder / "item_list.txt")
        users = id_map(folder / "user_list.txt")
        entities = id_map(folder / "entity_list.txt")
        relations = id_map(folder / "relation_list.txt")
    except ValueError as exc:
        return [str(exc)]

    for remapped, rid in items.items():
        if entities.get(remapped) != "item:" + rid:
            problems.append("item/entity map namespace disagreement at remap id "
                            f"{remapped}: entity is {entities.get(remapped)!r}, "
                            f"expected {'item:' + rid!r}")
            break

    triples = pd.read_csv(folder / "kg_final.txt", sep=r"\s+", header=None,
                          names=["head", "rel", "tail"])
    if (not triples["head"].isin(entities).all()
            or not triples["tail"].isin(entities).all()
            or not triples["rel"].isin(relations).all()):
        problems.append("kg_final.txt references an unknown entity or relation remap id")

    try:
        train, n_train = read_split(folder / "train.txt", users, items)
        test, n_test = read_split(folder / "test.txt", users, items)
    except ValueError as exc:
        return problems + [str(exc)]

    overlap = len(train & test)
    if overlap:
        problems.append(f"train and test share {overlap:,} user/item pairs; expected 0")

    # ---- every referenced recipe must be live in the published corpus
    corpus = pd.read_parquet(root / "data" / "corpus" / "recipes_structured.parquet",
                             columns=["recipe_id", "Diet"])
    live = set(corpus.recipe_id.astype("int64"))
    withdrawn = set(all_withdrawn_ids())

    item_ids = {int(v) for v in items.values()}
    inter = pd.read_csv(folder / "interactions.csv",
                        usecols=["user_id", "recipe_id", "rating"])
    inter_ids = set(inter.recipe_id.astype("int64"))

    for label, ids in (("item_list.txt", item_ids), ("interactions.csv", inter_ids)):
        gone = ids - live
        if gone:
            problems.append(f"{label} references {len(gone):,} recipe ids absent from the "
                            f"published corpus, e.g. {sorted(gone)[:5]}")
        hit = ids & withdrawn
        if hit:
            problems.append(f"{label} references {len(hit):,} WITHDRAWN recipe ids, "
                            f"e.g. {sorted(hit)[:5]}")

    # ---- the hard constraint, checked against the corpus rather than the generator
    diet_of = dict(zip(corpus.recipe_id.astype("int64"), corpus.Diet.astype(str)))
    profiles = pd.read_csv(folder / "users.csv", usecols=["user_id", "diet"])
    user_diet = dict(zip(profiles.user_id.astype("int64"), profiles.diet.astype(str)))

    served_undeclared = 0
    violations: dict[str, int] = {}
    for uid, rid in zip(inter.user_id.astype("int64"), inter.recipe_id.astype("int64")):
        rdiet = diet_of.get(rid)
        if rdiet not in DECLARED:
            served_undeclared += 1
            continue
        allowed = COMPATIBLE.get(user_diet.get(uid, ""), set(DECLARED))
        if rdiet not in allowed:
            key = f"{user_diet.get(uid)} user served {rdiet} recipe"
            violations[key] = violations.get(key, 0) + 1

    if served_undeclared:
        problems.append(
            f"{served_undeclared:,} interactions serve a recipe whose Diet is not one of "
            f"{DECLARED}. An undeclared diet is not a permissive one: it must be excluded "
            f"from every pool, not defaulted into Vegetarian.")
    for key, n in sorted(violations.items(), key=lambda kv: -kv[1]):
        problems.append(f"dietary hard-constraint violated: {n:,} rows where a {key}")

    # ---- stats.json must describe the files that are present
    import json
    stats = json.loads((folder / "stats.json").read_text(encoding="utf-8"))
    for key, actual in (("n_train", n_train), ("n_test", n_test),
                        ("n_items_post_10core", len(items)),
                        ("n_users_post_10core", len(users)),
                        ("n_interactions_total", len(inter)),
                        ("n_kg_triples", len(triples)),
                        ("n_kg_entities", len(entities))):
        if key in stats and int(stats[key]) != int(actual):
            problems.append(f"stats.json {key} says {stats[key]:,} but the files hold "
                            f"{actual:,}")
    if stats.get("train_test_leakage", 0) != 0 or overlap:
        problems.append("stats.json declares nonzero train/test leakage")

    return problems
