import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from allergen_tier_contract import validate_row, parse_tiers


class TierContractTests(unittest.TestCase):
    def test_stale_and_missing_tiers_rejected(self):
        for labels, tiers in [('none_detected', 'mustard:blend'), ('milk', ''),
                              ('unknown', 'milk:inherited')]:
            with self.subTest(labels=labels), self.assertRaises(ValueError):
                validate_row(labels, tiers)

    def test_valid_tiers_and_sentinels(self):
        for labels, tiers in [('unknown', None), ('none_detected', ''),
                              ('milk;ghee', 'ghee:direct;milk:derived')]:
            validate_row(labels, tiers)

    def test_invalid_or_duplicate_tier_rejected(self):
        for text in ['milk:direct;milk:inherited', 'milk:made_up', 'made_up:direct', 'milk']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_tiers(text)
