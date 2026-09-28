import unittest
import test_ifct_review_privacy as privacy_fixtures


class QualityDigestPrivacyTests(unittest.TestCase):
    scan = privacy_fixtures.IFCTReviewPrivacyTests.scan

    def test_only_exact_quality_digest_is_exempt(self):
        digest = 'q1_' + 'a'*24 + '4111111111111111' + 'b'*24
        paths = ['data/quality/recipe_quality_v1.parquet',
                 'data/quality/duplicate_crosswalk_v1.parquet']
        for path in paths:
            failures, _ = self.scan([digest], path=path, column='dup_cluster_id')
            self.assertEqual(failures, [])
            for invalid in [digest[:-1], digest+'b', 'prefix '+digest,
                            digest+'\n', 'card 4111 1111 1111 1111']:
                failures, _ = self.scan([invalid], path=path, column='dup_cluster_id')
                self.assertTrue(any('matches credit_card' in f for f in failures))
        failures, _ = self.scan([digest], path='data/quality/other.parquet', column='dup_cluster_id')
        self.assertTrue(any('matches credit_card' in f for f in failures))

    def test_other_pii_remains_detectable(self):
        failures, _ = self.scan(['reviewer@example.org','contact +919876543210'],
            path='data/quality/recipe_quality_v1.parquet', column='dup_cluster_id')
        self.assertTrue(any('matches email' in f for f in failures))
        self.assertTrue(any('matches phone_intl' in f for f in failures))


if __name__ == '__main__':
    unittest.main()
