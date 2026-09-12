import sys
import unittest
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from split_contract import validate_split_frames


class SplitContractTests(unittest.TestCase):
    def setUp(self):
        self.recipes = pd.DataFrame({"recipe_id": [17, 93, 105], "Split_v3": ["train", "test", "val"],
                                     "Title_normalized": ["rice", "dal", "roti"]})
        self.nodes = pd.DataFrame({"node_id": ["recipe::105", "recipe::17", "recipe::93"],
                                  "type": ["recipe"] * 3, "split": ["val", "train", "test"]})
        self.wide = self.recipes.assign(dup_family_id=[1, 2, 3])

    def test_noncontiguous_reordered_ids(self):
        self.assertEqual(validate_split_frames(self.recipes, self.nodes, self.wide), [])

    def test_legacy_graph_split_is_rejected(self):
        self.nodes.loc[0, "split"] = "train"
        self.assertTrue(any("disagree" in p for p in validate_split_frames(self.recipes, self.nodes, self.wide)))

    def test_missing_graph_recipe_is_rejected(self):
        self.assertTrue(any("IDs differ" in p for p in validate_split_frames(self.recipes, self.nodes.iloc[:2], self.wide)))

    def test_casefolded_title_crossing_is_rejected(self):
        self.recipes.loc[1, "Title_normalized"] = " RICE "
        self.assertTrue(any("title groups" in p for p in validate_split_frames(self.recipes, self.nodes, self.wide)))

    def test_duplicate_family_crossing_is_rejected(self):
        self.wide.loc[1, "dup_family_id"] = 1
        self.assertTrue(any("duplicate families" in p for p in validate_split_frames(self.recipes, self.nodes, self.wide)))

    def test_missing_split_does_not_fall_back(self):
        self.recipes.loc[0, "Split_v3"] = None
        self.assertTrue(any("invalid" in p for p in validate_split_frames(self.recipes, self.nodes, self.wide)))

    def test_wide_disagreement_is_rejected(self):
        self.wide.loc[0, "Split_v3"] = "test"
        self.assertTrue(any("narrow and wide" in p for p in validate_split_frames(self.recipes, self.nodes, self.wide)))


if __name__ == "__main__":
    unittest.main()
