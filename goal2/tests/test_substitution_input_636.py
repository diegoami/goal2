"""[designed: #636] Positive UI inputs respect original EA09/F029 played-role limits.
These controls select inputs only; original engine eligibility/refusal remains authoritative.
"""
import copy
import unittest
from collections import Counter

class Answer:
    context='substitution';takes_substitutions=True;left=5
    def __init__(self):
        self.eleven=list(range(1,12));self.bench=list(range(12,21));self.injured=set()
        roles=[0,1,2,2,2,3,3,3,5,5,5,2,1,6,6,7,7,8,9,0]
        self.positions=dict(zip(self.eleven+self.bench,roles))
    def position(self,word):return self.positions[word]

class LegalPositiveInputs(unittest.TestCase):
    def assert_valid(self,answer,pair):
        off,on=pair;counts=Counter(answer.position(w) for w in answer.eleven)
        counts[answer.position(off)]-=1;counts[answer.position(on)]+=1
        self.assertEqual(counts[0],1)
        self.assertTrue(all(counts[role]<=3 for role in range(1,14)),counts)

    def test_first_outfield_pair_does_not_create_a_fourth_played_c_role(self):
        from goal2.tests.substitution_selectors_636 import outfield_pair
        answer=Answer();before=copy.deepcopy(answer.__dict__)
        pair=outfield_pair(answer)
        self.assert_valid(answer,pair)
        self.assertEqual(pair,(2,13),'prefer a same-played-role incoming player before other legal roles')
        self.assertEqual(answer.__dict__,before)

    def test_incidental_injury_and_keeper_inputs_keep_original_role_counts(self):
        from goal2.tests.substitution_selectors_636 import compatible_pair
        for word in (1,2):
            answer=Answer();answer.injured={word}
            pair=compatible_pair(answer,injured_first=True)
            self.assertEqual(pair[0],word)
            self.assert_valid(answer,pair)

    def test_zero_budget_half_time_inputs_do_not_select_an_already_withdrawn_player(self):
        from goal2.tests.substitution_selectors_636 import compatible_pair
        answer=Answer();answer.context='half_time'
        pair=compatible_pair(answer,taken_off=(13,))
        self.assertNotIn(pair[1],(13,))
        self.assert_valid(answer,pair)
