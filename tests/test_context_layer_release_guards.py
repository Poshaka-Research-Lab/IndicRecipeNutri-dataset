"""0.11.0 context-layer guards: the digest suppression is named, shape-scoped and pattern-scoped,
and the four source-authored text columns are the only new length exemptions."""
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import verify_release as verifier

SHA = 'a' * 20 + '4111111111111111' + 'b' * 28          # 64 hex, holds a 16-digit run
LINK = 'link::' + '4111111111111111'              # 16 hex, all digits
TABLES = {('data/cultural_context/occasion_registry.parquet', 'source_text_sha256'): SHA,
          ('data/cultural_context/dietary_rules.parquet', 'source_text_sha256'): SHA,
          ('data/cultural_context/dietary_rules.parquet', 'note_text_sha256'): SHA,
          ('data/cultural_context/context_tag_links.parquet', 'link_uid'): LINK}


class ContextLayerGuardTests(unittest.TestCase):
    def scan(self, values, *, column, path):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); target = root / path; target.parent.mkdir(parents=True)
            pd.DataFrame({column: values}).to_parquet(target, index=False)
            with patch.object(verifier, 'failures', []), patch.object(verifier, 'notes', []):
                verifier.check_pii(root)
                return verifier.failures.copy(), verifier.notes.copy()

    def test_declared_pairs_are_exactly_the_four(self):
        self.assertEqual(set(verifier.CONTEXT_DIGEST_COLUMNS), set(TABLES))

    def test_valid_digests_pass_with_a_note(self):
        for (path, column), value in TABLES.items():
            with self.subTest(path=path, column=column):
                self.assertRegex(value, re.compile(verifier.PII_PATTERNS['credit_card']))
                failures, notes = self.scan([value, None], column=column, path=path)
                self.assertEqual(failures, [])
                self.assertTrue(any('validated context-layer digest' in n for n in notes))

    def test_other_shapes_in_the_same_column_still_fail(self):
        for (path, column), value in TABLES.items():
            for bad in [value[:-1], value.upper(), value + ' x', 'card 4111 1111 1111 1111']:
                with self.subTest(path=path, column=column, bad=bad):
                    failures, _ = self.scan([value, bad], column=column, path=path)
                    self.assertTrue(any('matches credit_card' in f for f in failures))

    def test_same_value_elsewhere_is_not_exempt(self):
        for path, column in [('data/cultural_context/context_citations.parquet', 'source_text_sha256'),
                             ('data/historical_snapshot/recipe_id_crosswalk.parquet', 'link_uid'),
                             ('data/cultural_context/occasion_registry.parquet', 'other_sha256')]:
            with self.subTest(path=path, column=column):
                failures, _ = self.scan([SHA], column=column, path=path)
                self.assertTrue(any('matches credit_card' in f for f in failures))

    def test_other_patterns_still_scan_declared_columns(self):
        path, column = 'data/cultural_context/context_tag_links.parquet', 'link_uid'
        failures, _ = self.scan([LINK, 'someone@example.org'], column=column, path=path)
        self.assertTrue(any('matches email' in f for f in failures))

    def test_length_exemptions_added_are_the_four_source_text_columns(self):
        added = verifier.LENGTH_EXEMPT - {'IngredientsList', 'HealthConditions', 'checks', 'lenses',
                                          'Ingredients_recovered'}
        self.assertEqual(added, {'registry_note', 'date_rule_text', 'rule_note', 'sect_variants_json'})


if __name__ == '__main__':
    unittest.main()
