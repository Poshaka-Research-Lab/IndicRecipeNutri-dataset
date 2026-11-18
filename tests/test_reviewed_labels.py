import sys,unittest,tempfile
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from reviewed_labels_contract import BUNDLE,DECL,SCOPE,validate_frame
import verify_release as verifier
class ReviewedLabelsTests(unittest.TestCase):
    def declaration(self):
        return pd.DataFrame([[1,'cuisine','Tamil','Tamil','Cuisine','a'*64,'accept','Dataset owner','owner_approved_rule_assisted_review','b'*64,BUNDLE,'example.org',False]],columns=DECL)
    def test_private_evidence_rejected(self):
        f=self.declaration();f['evidence_quote']='private';self.assertTrue(validate_frame(f,[1]))
    def test_digest_and_approval_tamper(self):
        f=self.declaration();self.assertEqual(validate_frame(f,[1]),[])
        for col,value in [('result_hash','bad'),('approval_bundle_sha256','c'*64),('review_decision','abstain')]:
            g=f.copy();g[col]=value;self.assertTrue(validate_frame(g,[1]))
    def test_ambiguous_scope_not_excluded(self):
        f=pd.DataFrame([[1,'["International"]',None,'owner_approved_assistant_review',False,BUNDLE]],columns=SCOPE)
        self.assertEqual(validate_frame(f,[1],True),[])
        f['reviewed_legacy_scope_candidate']='non-indian';self.assertTrue(validate_frame(f,[1],True))
    def test_unknown_and_duplicate(self):
        f=self.declaration();self.assertTrue(validate_frame(f,[]));self.assertTrue(validate_frame(pd.concat([f,f]),[1]))
    def test_hash_privacy_exception_is_narrow(self):
        digest='a'*20+'4111111111111111'+'b'*28
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path=root/'data/labels/cuisine_declarations_v1.parquet';path.parent.mkdir(parents=True)
            for col,value,expected in [('result_hash',digest,False),('other',digest,True),('result_hash','card 4111 1111 1111 1111',True),('result_hash','someone@example.org',True)]:
                pd.DataFrame({col:[value]}).to_parquet(path,index=False)
                errors,_=verifier._pii_file(str(root),str(path))
                self.assertEqual(bool(errors),expected)
