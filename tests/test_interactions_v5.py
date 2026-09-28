from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from build_interactions_v5 import CONFIG, generate, groups_from_attributes, utility, draw_user


class GeneratorTests(unittest.TestCase):
    def items(self):
        return pd.DataFrame([{'recipe_id': i, 'Region': 'Goa' if i%2 else 'Kerala',
                              'SpiceLevel': 'hot' if i%3 else 'mild', 'HealthGrade': 'A',
                              'rating_count_bin': '1_9', 'hidden_rank': 900-i} for i in range(30)])

    def test_replay_no_pair_overlap_and_no_oracle_columns(self):
        cfg = dict(CONFIG, users=4)
        first, second = generate(self.items(), cfg), generate(self.items().iloc[::-1], cfg)
        for a,b in zip(first, second):
            pd.testing.assert_frame_equal(a,b)
        users, events, truth = first
        self.assertFalse(events.duplicated(['user_id','recipe_id']).any())
        self.assertEqual(events.groupby('split').size().to_dict(), {'test':16,'train':64})
        self.assertNotIn('utility',events)
        self.assertNotIn('conditional_choice_probability',events)
        self.assertTrue(truth.conditional_choice_probability.between(0,1).all())

    def test_hidden_columns_do_not_affect_generation(self):
        items = self.items()
        changed = items.copy()
        changed['hidden_rank'] = -1
        cfg = dict(CONFIG, users=2)
        for a,b in zip(generate(items,cfg),generate(changed,cfg)):
            pd.testing.assert_frame_equal(a,b)

    def test_group_sampler_matches_exact_item_softmax_probability(self):
        items=self.items()
        keys,members=groups_from_attributes(items)
        profile=dict(preferred_region='Goa',preferred_spice='hot',grade_direction=1,popularity_direction=1)
        cfg=dict(CONFIG,events_per_user=3,train_events=2)
        draws=draw_user(keys,members,profile,np.random.default_rng(4),cfg)
        remaining=set(items.recipe_id)
        group_of={int(r):g for g,rows in enumerate(members) for r in rows}
        for rid,step,split,score,prob in draws:
            scores=utility(keys,profile,cfg['train_weights' if split=='train' else 'test_weights'])
            mass=np.exp(scores-scores.max())
            expected=mass[group_of[rid]]/sum(mass[group_of[x]] for x in remaining)
            self.assertAlmostEqual(prob,expected,places=14)
            remaining.remove(rid)

    def test_invalid_count_rejected(self):
        with self.assertRaises(ValueError):
            generate(self.items(),dict(CONFIG,users=1,events_per_user=31))


if __name__ == '__main__':
    unittest.main()
