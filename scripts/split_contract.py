"""Validate the published Split_v3 contract by stable recipe ID, offline."""
from pathlib import Path
import pandas as pd

SPLIT_COLUMN = "Split_v3"
SPLIT_VALUES = {"train", "val", "test"}


def validate_split_frames(recipes, nodes, wide=None):
    """Return actionable violations; never join by row position or silently fall back."""
    problems = []
    required = {"recipe_id", SPLIT_COLUMN, "Title_normalized"}
    missing = required - set(recipes.columns)
    if missing:
        return [f"recipes missing columns: {sorted(missing)}"]
    if recipes.recipe_id.isna().any() or recipes.recipe_id.duplicated().any():
        return ["recipes contain null or duplicate recipe_id"]
    if not recipes[SPLIT_COLUMN].isin(SPLIT_VALUES).all():
        problems.append("recipes contain missing/invalid Split_v3 values")
    title = recipes.Title_normalized.fillna("").astype(str).str.strip().str.casefold()
    groups = recipes.assign(_title=title).loc[title.ne("")].groupby("_title")[SPLIT_COLUMN].nunique()
    crossed = int(groups.gt(1).sum())
    if crossed:
        problems.append(f"{crossed} case-folded title groups span Split_v3 boundaries")
    if not {"node_id", "type", "split"} <= set(nodes.columns):
        return problems + ["graph missing node_id/type/split"]
    graph = nodes.loc[nodes.type.eq("recipe"), ["node_id", "split"]].copy()
    if graph.node_id.isna().any() or graph.node_id.duplicated().any():
        return problems + ["graph recipe nodes contain null or duplicate IDs"]
    expected = recipes[["recipe_id", SPLIT_COLUMN]].copy()
    expected["node_id"] = "recipe::" + expected.recipe_id.astype(str)
    joined = expected.merge(graph, on="node_id", how="outer", indicator=True, validate="one_to_one")
    missing_ids = int(joined._merge.ne("both").sum())
    if missing_ids:
        problems.append(f"{missing_ids} recipe IDs differ between corpus and graph")
    mismatched = int((joined._merge.eq("both") & joined[SPLIT_COLUMN].ne(joined['split'])).sum())
    if mismatched:
        problems.append(f"{mismatched} graph split values disagree with Split_v3")
    if wide is not None:
        if wide.recipe_id.isna().any() or wide.recipe_id.duplicated().any():
            return problems + ["wide corpus contains null or duplicate recipe_id"]
        z = recipes[["recipe_id", SPLIT_COLUMN]].merge(
            wide[["recipe_id", SPLIT_COLUMN]], on="recipe_id", how="outer",
            suffixes=("_recipe", "_wide"), indicator=True, validate="one_to_one")
        bad = z._merge.ne("both") | z[SPLIT_COLUMN + "_recipe"].ne(z[SPLIT_COLUMN + "_wide"])
        if bad.any():
            problems.append(f"{int(bad.sum())} split/ID disagreements between narrow and wide corpus")
        if "dup_family_id" not in wide:
            problems.append("wide corpus lacks dup_family_id for leakage check")
        else:
            family = wide.dropna(subset=["dup_family_id"]).groupby("dup_family_id")[SPLIT_COLUMN].nunique()
            if family.gt(1).any():
                problems.append(f"{int(family.gt(1).sum())} duplicate families span Split_v3 boundaries")
    return problems


def validate_release_splits(root: Path):
    return validate_split_frames(
        pd.read_parquet(root / "data/corpus/recipes.parquet", columns=["recipe_id", SPLIT_COLUMN, "Title_normalized"]),
        pd.read_parquet(root / "data/kg/kg_nodes.parquet", columns=["node_id", "type", "split"]),
        pd.read_parquet(root / "data/corpus/recipes_structured.parquet", columns=["recipe_id", SPLIT_COLUMN, "dup_family_id"]),
    )
