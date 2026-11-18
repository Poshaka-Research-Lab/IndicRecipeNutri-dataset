import sys
import unittest
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from cultural_labels_contract import COLUMNS,validate_frame,validate_release
class CulturalLabels(unittest.TestCase):
    def sample(self):
        return pd.DataFrame([[1,'proposed','pending','cultural_facets_v2_20261117',False,'["Goan"]']+['[]']*8],columns=COLUMNS)
    def test_valid(self): self.assertEqual(validate_frame(self.sample(),[1]),[])
    def test_private_columns_refused(self):
        data=self.sample(); data['quote']='private source'
        self.assertTrue(validate_frame(data,[1]))
    def test_unknown_or_duplicate_ids_refused(self):
        self.assertTrue(validate_frame(self.sample(),[2]))
        self.assertTrue(validate_frame(pd.concat([self.sample(),self.sample()]),[1]))
    def test_approval_or_malformed_labels_refused(self):
        data=self.sample(); data['review_status']='verified'; self.assertTrue(validate_frame(data,[1]))
        data=self.sample(); data['proposed_Cuisine_json']='not json'; self.assertTrue(validate_frame(data,[1]))
    def test_published_layer(self): self.assertEqual(validate_release(Path(__file__).resolve().parents[1]),[])
if __name__=='__main__': unittest.main()
