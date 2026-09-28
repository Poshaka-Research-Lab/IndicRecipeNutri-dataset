import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from audit_quality_inputs import sha256
from item_card import attributes, VERSION
from quality_release_contract import validate_item_card, validate_release_quality_layers


class ReleaseContractTests(unittest.TestCase):
    def test_missing_additive_layers_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            errors = validate_release_quality_layers(Path(directory))
        self.assertEqual(len(errors), 5)
        self.assertTrue(all('cannot validate' in e or 'missing' in e for e in errors))

    def test_item_card_tampering_fails_even_with_updated_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for folder in ['data/corpus', 'data/quality', 'scripts']:
                (root / folder).mkdir(parents=True)
            source = root / 'data/corpus/recipes_structured.parquet'
            target = root / 'data/quality/item_attributes_v1.parquet'
            builder = root / 'scripts/item_card.py'
            builder.write_text('fixture')
            frame = pd.DataFrame({'recipe_id':[1], 'SpiceLevel':['mild'],
                'SpiceLevel_src':['source'], 'HealthGrade':['B'], 'RatingCount':[None],
                'RatingAverage':[None], 'Region':['Goa'], 'Cuisine':['Indian']})
            frame.to_parquet(source,index=False)
            out = attributes(frame)
            out.to_parquet(target,index=False)
            manifest = {'version':VERSION,'source_sha256':sha256(source),
                'builder_sha256':sha256(builder),'payload_sha256':sha256(target),'rows':1}
            receipt = root / 'data/quality/item_card_manifest.json'
            receipt.write_text(json.dumps(manifest))
            self.assertEqual(validate_item_card(root), [])
            out['rating_count_bin'] = 'zero'
            out.to_parquet(target,index=False)
            manifest['payload_sha256'] = sha256(target)
            receipt.write_text(json.dumps(manifest))
            self.assertIn('does not reproduce', validate_item_card(root)[0])

    def test_failure_in_one_layer_does_not_skip_other_layers(self):
        with patch('quality_release_contract.validate_quality', side_effect=ValueError('broken')), \
             patch('quality_release_contract.validate_item_card', return_value=['card defect']), \
             patch('quality_release_contract.validate_nutrition', return_value=[]), \
             patch('allergen_evidence_contract.validate', return_value={'errors':[]}), \
             patch('verify_interactions_v5.verify', return_value={'errors':['generator defect']}):
            errors = validate_release_quality_layers(Path('.'))
        self.assertEqual(len(errors), 3)
        self.assertIn('generator-v5: generator defect', errors)


if __name__ == '__main__':
    unittest.main()
