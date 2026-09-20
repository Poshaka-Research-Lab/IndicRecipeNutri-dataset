"""Generated IFCT digest exceptions cannot hide other privacy matches."""
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import verify_release as verifier

TARGET='data/enrichment/ingredients_nutrition.parquet'
DIGEST='ifct_food::'+'a'*24+'4111111111111111'+'b'*24

class IFCTReviewPrivacyTests(unittest.TestCase):
    def scan(self,values,*,column='ifct_food_review_id',path=TARGET,patterns=None):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);target=root/path;target.parent.mkdir(parents=True)
            pd.DataFrame({column:values}).to_parquet(target,index=False)
            with patch.object(verifier,'failures',[]),patch.object(verifier,'notes',[]):
                if patterns is None:verifier.check_pii(root)
                else:
                    with patch.object(verifier,'PII_PATTERNS',patterns):verifier.check_pii(root)
                return verifier.failures.copy(),verifier.notes.copy()

    def test_valid_digest_only_two_exact_columns(self):
        self.assertRegex(DIGEST,re.compile(verifier.PII_PATTERNS['credit_card']))
        for column in ['match_review_id','ifct_food_review_id']:
            with self.subTest(column=column):
                failures,notes=self.scan([DIGEST,None],column=column)
                self.assertEqual(failures,[])
                self.assertTrue(any('validated IFCT context digest' in n for n in notes))

    def test_mixed_digest_and_card_text_still_flags_card(self):
        for column in ['match_review_id','ifct_food_review_id']:
            with self.subTest(column=column):
                failures,_=self.scan([DIGEST,'card 4111 1111 1111 1111'],column=column)
                self.assertEqual(len(failures),1)
                self.assertIn('matches credit_card in 1 row(s)',failures[0])

    def test_wrong_path_column_or_namespace_not_exempt(self):
        cases=[dict(path='data/corpus/ingredients_nutrition.parquet'),
               dict(path='data/enrichment/other.parquet'),
               dict(column='legacy_match_review_id'),dict(column='other_id')]
        for options in cases:
            with self.subTest(options=options):
                failures,_=self.scan([DIGEST],**options)
                self.assertTrue(any('matches credit_card' in f for f in failures))
        failures,_=self.scan([DIGEST.replace('ifct_food::','other_food::')])
        self.assertTrue(any('matches credit_card' in f for f in failures))

    def test_malformed_or_embedded_digest_not_exempt(self):
        for value in [DIGEST[:-1],DIGEST+'b',DIGEST.upper(),'prefix '+DIGEST,DIGEST+' suffix',DIGEST+'\n']:
            with self.subTest(value=value):
                failures,_=self.scan([value])
                self.assertTrue(any('matches credit_card' in f for f in failures))

    def test_other_patterns_still_scan_valid_digests(self):
        patterns={'credit_card':verifier.PII_PATTERNS['credit_card'],'email':r'ifct_food::'}
        failures,_=self.scan([DIGEST],patterns=patterns)
        self.assertEqual(len(failures),1)
        self.assertIn('matches email',failures[0])

    def test_actual_email_and_phone_text_still_flagged(self):
        failures,_=self.scan([DIGEST,'reviewer@example.org','contact +919876543210'])
        self.assertTrue(any('matches email' in f for f in failures))
        self.assertTrue(any('matches phone_intl' in f for f in failures))

if __name__=='__main__':unittest.main()
