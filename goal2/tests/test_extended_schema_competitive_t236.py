"""T236: actual competitive full24 validation; no fixture/option patch after entry."""
import copy
import unittest

from goal2.game import campaign_pool, extended_squad
from goal2.game.extended_match import prepare_extended_watched
from goal2.game.watched_match import sealed
from goal2.tests import pypy_engine, requires


def actual_competitive(state,raw,fixture):
    from goal2.engine.original_match import Match, screens as S
    from goal2.game.extended_schema import ExtendedSelection
    state=extended_squad.resized(state,24);pool=campaign_pool.validate(state);pairs=[]
    def available(w):
        r=state.players[w]
        return 0<r[14]<128 and not r[16]&0xA4
    for off in reversed(state.starting_eleven):
        if len(pairs)==4:break
        if state.players[off][6]==0 or not available(off):continue
        on=next((w for w in pool if available(w) and state.players[w][6]==state.players[off][6]
                 and w not in [p[1] for p in pairs]),None)
        if on is not None:pairs.append((off,on))
    assert len(pairs)==4;state.extra_squad=[p[1] for p in pairs]
    prepared,extras=prepare_extended_watched(state,raw,fixture,competitive=True);image=sealed(prepared)
    selection=ExtendedSelection.from_prepared(state,fixture,image)
    match=Match(image,fixture,managed=state.managed_country,captain=state.captain or None,
                engine='port',live_players=True,substitutions=5,extra_players=list(extras))
    stream=iter(match.events())
    for event in stream:
        if event.kind=='decision':
            if event.data['context']=='half_time':break
            match.answer(quick=True)
    else:raise AssertionError('missing original competitive halftime')
    waiting=copy.deepcopy(event.data);pairs.sort(key=lambda p:waiting['eleven'].index(p[0]))
    match.answer(substitutions=pairs,quick=True)
    for event in stream:
        if event.kind=='decision':match.answer(quick=True)
    result=match.result();ours=[r for r in result['substitutions'] if r['team']==match.side]
    assert [(r['off'],r['on']) for r in ours]==pairs
    assert match.m.rd(S.SUBS_LEFT+match.side,1)==1
    assert len(result['players'])==44
    assert all(on in match._squad(state.managed_country)[:11] for off,on in pairs)
    return selection,waiting,result


class CompetitiveProfile(unittest.TestCase):
    def test_actual_competitive_full24_keeps_exact_native_budget_and_resolution(self):
        from goal2.game.extended_schema import validate_extended_result,validate_extended_decision
        from goal2.tests.test_campaign_competitive_publication import campaign
        # Existing accepted T51 source fixture/input contract, declared before Match exists.
        state,raw,fixture=campaign(index=42,kind=2)
        selection,waiting,result=pypy_engine.call(__name__+':actual_competitive',state,raw,fixture)
        before=copy.deepcopy(result);view=validate_extended_decision(waiting,selection)
        checked=validate_extended_result(result,selection,competitive=True)
        self.assertEqual((len(view.bench),view.substitutions_left),(13,5))
        self.assertEqual((len(checked.national),len(checked.consequence_words)),(24,44))
        self.assertEqual(result['substitution_budget'],[5,5]);self.assertEqual(result,before)
        self.assertRaises(ValueError,validate_extended_result,result,selection)
        for budget in ([255,255],[True,5],[5,False]):
            bad=copy.deepcopy(result);bad['substitution_budget']=budget
            self.assertRaises(ValueError,validate_extended_result,bad,selection,competitive=True)


if __name__=='__main__':unittest.main()
