import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from quality_rules import observe, observe_audit_aligned, candidate_clusters
from build_quality_flags import validate_output_root, canonical_digest
from quality_contract import validate_frames
import quality_audit_patterns as audit_patterns
import quality_audit_rules as audit_rules


class QualityRulesTests(unittest.TestCase):
    def row(self, rid=1, **kw):
        return dict(recipe_id=rid, Title_normalized='Example soup', IngredientsList='["water", "carrot", "salt"]',
                    Region='Goa', Lang_base='en', dup_family_id=None, **kw)

    def test_unavailable_is_not_missing_or_negative(self):
        result = observe(self.row(), None, False)
        self.assertEqual(result['record_completeness'], 'unknown')
        self.assertEqual(result['end_state_stated'], 'unknown')
        self.assertEqual(result['record_completeness_reason'], 'input_unavailable')
        result = observe(self.row(), '', True)
        self.assertEqual(result['record_completeness'], 'partial')
        self.assertEqual(result['record_completeness_reason'], 'input_missing_in_source')

    def test_non_english_is_not_garbled(self):
        row = self.row()
        row.update(Lang_base='hi', Title_normalized='\u0926\u093e\u0932')
        result = observe(row, '\u092a\u0915\u093e\u090f\u0901\u0964', True)
        self.assertEqual(result['record_completeness'], 'unknown')
        self.assertEqual(result['record_completeness_reason'], 'language_not_supported')
        self.assertEqual(result['garbled'], 'not_detected')

    def test_mixing_dough_is_not_final_intermediate_evidence(self):
        result = observe(self.row(), 'Mix the dough. Bake until crisp. Serve the finished bread.', True)
        self.assertEqual(result['is_intermediate'], 'no')
        result = observe(self.row(), 'Mix the ingredients. Reserve for the filling.', True)
        self.assertEqual(result['is_intermediate'], 'yes')

    def test_clusters_are_order_invariant_and_transitive(self):
        rows = [self.row(i) for i in [1, 2, 3]]
        rows[0]['IngredientsList'] = '[]'
        rows[1].update(dup_family_id=5, IngredientsList='[]')
        rows[2].update(dup_family_id=5, Title_normalized='Other dish', IngredientsList='[]')
        ids, _ = candidate_clusters(rows)
        reversed_ids, _ = candidate_clusters(list(reversed(rows)))
        self.assertEqual(ids, reversed_ids)
        self.assertEqual(len(set(ids.values())), 1)
        with self.assertRaisesRegex(ValueError, 'Duplicate recipe'):
            candidate_clusters([rows[0], rows[0]])

    def test_digest_is_row_order_independent(self):
        frame = pd.DataFrame({'recipe_id': [1, 2], 'value': ['unknown', 'yes']})
        self.assertEqual(canonical_digest(frame), canonical_digest(frame.iloc[::-1]))

    def test_protected_output_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            with self.assertRaisesRegex(ValueError, 'protected'):
                validate_output_root(root, root)
            with self.assertRaises(ValueError):
                validate_output_root(root / 'nested', root)

    def test_contract_rejects_missing_schema_and_missing_ids(self):
        corpus = pd.DataFrame({'recipe_id': [1, 2]})
        self.assertTrue(validate_frames(pd.DataFrame({'recipe_id': [1]}), corpus))

    def test_audit_dependency_hashes_match_received_run(self):
        self.assertEqual(audit_patterns.gate_spec_sha256(), 'b213905ad40cdcb9e759cc0d5e3231dfee78b2eda2c1406d2ceb419cc7e31179')
        # Re-pinned 2026-10-10 (D16 batch E post-install): the owner-approved release evidence-layer patch
        # (curd/curds, named cheeses, ilish/hilsa; BATCH_E/install/post_install_prep/release_evidence_layer_batch_e.patch)
        # moves lexicon_sha256() from a8d4258b6c34b4b3b2c2840661a349cfccba80447bd2a8fbf766e65c1075b313.
        self.assertEqual(audit_rules.lexicon_sha256(), '6d642766090d62c05678d5c2c2de2236727fe8a8c8b7afb2eb6b13a33c2385f6')

    def test_audit_carrier_exclusion_and_missing_text(self):
        self.assertIn('unspecified_oil', audit_rules.ambiguous_hits('peanut', ['2 tablespoons oil']))
        self.assertNotIn('unspecified_oil', audit_rules.ambiguous_hits('peanut', ['2 tablespoons olive oil']))
        result = audit_rules.instruction_status(audit_patterns, 'Example soup', ['water'], '')
        self.assertEqual(result['record_completeness'], 'MISSING')
        self.assertIsNone(result['end_state_stated'])

    def test_audit_aligned_fields_keep_language_guard_and_pan_indian_unassigned(self):
        row=self.row()
        row.update(RecipeName='Example soup',has_instructions=True,Cuisine='Indian')
        codes={'Goa':{'stratum':'primary_axis','level':'state'},
               'Pan-Indian':{'stratum':'unassigned','level':'unassigned'}}
        result=observe_audit_aligned(row,'Heat water and cook carrots. Serve the soup.',True,codes)
        self.assertEqual(result['audit_record_completeness'],'COMPLETE')
        self.assertEqual(result['end_state_stated'],'yes')
        self.assertEqual(result['region_stratum'],'primary_axis')
        row.update(Lang_base='hi',Region='Pan-Indian')
        result=observe_audit_aligned(row,'Heat water and cook carrots. Serve the soup.',True,codes)
        self.assertEqual(result['audit_record_completeness'],'COMPLETE')
        self.assertEqual(result['record_completeness'],'unknown')
        self.assertEqual(result['end_state_stated'],'unknown')
        self.assertEqual(result['region_stratum'],'unassigned')
        self.assertTrue(result['cuisine_generic_or_missing'])

    def test_missing_source_and_missing_source_text_are_distinct_in_audit(self):
        codes={'Goa':{'stratum':'primary_axis','level':'state'}}
        row=self.row()
        unavailable=observe_audit_aligned(row,None,False,codes)
        missing=observe_audit_aligned(row,'',True,codes)
        self.assertEqual(unavailable['audit_record_completeness'],'UNASSESSED')
        self.assertEqual(missing['audit_record_completeness'],'MISSING')
        self.assertFalse(unavailable['source_instruction_available'])
        self.assertTrue(missing['source_instruction_available'])


if __name__ == '__main__':
    unittest.main()
