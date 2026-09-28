from pathlib import Path
import sys
import unittest
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_nutrition_evidence import summarize


class NutritionEvidenceTests(unittest.TestCase):
    def frames(self):
        corpus=pd.DataFrame({'recipe_id':[1,2],'ing_weight_confident_frac':[0.5,float('nan')],
                             'per100g_confident':[True,False]})
        weights=pd.DataFrame({'recipe_id':[1,1],'ing_index':[0,1],'tier':['A','E'],'grams':[100.,20.]})
        nutrition=pd.DataFrame({'recipe_id':[1,1],'ing_index':[0,1],'grams':[100.,20.],'Nut_Calories':[100.,None]})
        return corpus,weights,nutrition

    def test_missing_not_zero_and_partial_energy_disclosed(self):
        out=summarize(*self.frames())
        self.assertTrue(pd.isna(out.loc[1,'count_confident_fraction']))
        self.assertEqual(out.loc[1,'ingredient_line_count'],0)
        self.assertEqual(out.loc[0,'partial_ab_energy_fraction'],1.0)
        self.assertEqual(out.loc[0,'energy_available_line_count'],1)
        self.assertFalse(out.loc[0,'estimator_high_confidence_rule'])

    def test_gram_drift_and_duplicate_occurrences_rejected(self):
        c,w,n=self.frames()
        n.loc[0,'grams']=101
        with self.assertRaisesRegex(ValueError,'grams differ'): summarize(c,w,n)
        c,w,n=self.frames()
        with self.assertRaisesRegex(ValueError,'occurrence keys'): summarize(c,pd.concat([w,w]),n)

    def test_untiered_missing_grams_are_explicitly_unassessed(self):
        c,w,n=self.frames()
        w.loc[1,['tier','grams']]=[None,float('nan')]
        n.loc[1,'grams']=float('nan')
        out=summarize(c,w,n)
        self.assertEqual(out.loc[0,'unassessed_weight_line_count'],1)
        w.loc[1,'grams']=20
        n.loc[1,'grams']=20
        with self.assertRaisesRegex(ValueError,'Untiered'): summarize(c,w,n)


if __name__=='__main__': unittest.main()
