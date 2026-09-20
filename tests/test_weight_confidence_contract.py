import sys
from pathlib import Path
import unittest
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from nutrition_contract import validate_weight_confidence_frames


class WeightConfidenceContractTests(unittest.TestCase):
    def frames(self):
        wide=pd.DataFrame({'recipe_id':[8,3,5],'ing_weight_confident_frac':[.5,0.,None]})
        weights=pd.DataFrame({'recipe_id':[8,3,8],'ing_index':[0,0,1],'confident':[True,False,False]})
        return wide,wide.iloc[::-1].copy(),weights

    def test_complete_id_join_and_undefined_denominator(self):
        self.assertEqual(validate_weight_confidence_frames(*self.frames()),[])

    def test_stale_fraction_or_missing_as_zero_is_detected(self):
        for index,value in [(0,1.),(2,0.)]:
            a,b,w=self.frames();a.loc[index,'ing_weight_confident_frac']=value
            self.assertTrue(validate_weight_confidence_frames(a,b,w))

    def test_duplicate_and_unknown_flags_refused(self):
        a,b,w=self.frames()
        self.assertTrue(validate_weight_confidence_frames(a,b,pd.concat([w,w.iloc[[0]]])))
        w['confident']=w.confident.astype(object);w.loc[0,'confident']=None
        self.assertTrue(validate_weight_confidence_frames(a,b,w))


if __name__=='__main__':unittest.main()
