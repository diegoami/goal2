"""[designed: T170q/#742] Complete held-roster pairs, original order, actual pipe repair."""
import unittest
from goal2.tests import test_season_worker_t170o as wire


def roster_sequence(raw, case):
    import hashlib,json,sys
    from dataclasses import asdict
    from goal2.engine.original_match.image import Image
    from goal2.engine.original_match.match import PLAYER_POSITION
    from goal2.engine.original_match.machine import REGS,MEM_SIZE,Uc
    from goal2.game import engine_tables
    from goal2.game.season import SeasonSession
    from goal2.game.prematch_seam import PrematchSeam
    assert sys.implementation.name=='pypy' and sys.version_info[:2]==(3,11) and Uc is None
    state=Image.from_bytes(raw).state(engine_tables.load())
    def run(via_seam):
        session=SeasonSession(state);assert session.advance().status=='match'
        m=session.pending_match;seam=PrematchSeam(m)
        events=[]
        def decision():
            for ev in m.events():
                events.append(asdict(ev))
                if ev.kind=='decision':
                    assert ev.data['context']=='pre_match'
                    return ev.data
            raise AssertionError('missing pre-match decision')
        d=decision();pos=dict(d['positions'])
        if case=='same':
            pair=next([a,b] for i,a in enumerate(d['eleven']) for b in d['eleven'][i+1:] if pos[a]==pos[b])
        elif case=='different':
            pair=[d['eleven'][0],next(w for w in d['eleven'][1:] if pos[w]!=pos[d['eleven'][0]])]
        elif case=='reversed':
            pair=[d['bench'][0],next(w for w in d['eleven'] if pos[w]==pos[d['bench'][0]])]
        else:
            off=d['bench'][-1]
            pair=[off,next(w for w in d['pool'] if m._available(w) and m._player(w,PLAYER_POSITION)!=pos[off])]
        before={'eleven':d['eleven'],'bench':d['bench'],'pool':d['pool']}
        if via_seam:
            (seam.exchange if case=='pool' else seam.swap)(*pair)
        else:m.answer(edit_only=True,substitutions=[pair])
        d=decision();after={k:d[k] for k in before}
        if case in ('same','different','pool'):
            assert set(after['eleven'])==set(before['eleven'])
        if case=='pool':
            assert pair[1] in after['bench'] and pair[0] in after['pool']
            naive=list(before['bench']);naive[naive.index(pair[0])]=pair[1]
            assert after['bench']!=naive,'case must exercise original re-sort'
        captain=next(w for w in after['eleven'] if m._available(w))
        if via_seam:seam.play(captain=captain)
        else:m.answer(captain=captain)
        for ev in m.events():
            events.append(asdict(ev))
            if ev.kind=='minute':break
            assert ev.kind!='decision'
        assert ev.kind=='minute' and m.st['log']['substitutions']==[]
        return dict(pair=pair,before=before,after=after,events=events,captain=captain,
                    full_memory_sha256=hashlib.sha256(m.m.read(0,MEM_SIZE)).hexdigest(),
                    all16={r:m.m.reg(r) for r in REGS},
                    draws_sha256=hashlib.sha256(json.dumps(m.st['draws']).encode()).hexdigest())
    seam,direct=run(True),run(False)
    assert seam==direct
    return seam


class RosterSeam(unittest.TestCase):
    def test_supported_domains_and_native_order_equal_direct_answers(self):
        from pathlib import Path
        from goal2.engine.original_match.assets import REFERENCE,reference_image
        from goal2.tests import requires,pypy_engine
        requires.require(files=(REFERENCE['asset'],))
        raw=reference_image(Path(__file__).resolve().parents[2]/'.cache')
        for case in ('same','different','reversed','pool'):
            with self.subTest(case=case):
                result=pypy_engine.call(__name__+':roster_sequence',raw,case)
                self.assertEqual(len(result['all16']),16)
                print('T170Q_ROSTER '+__import__('json').dumps(dict(case=case,pair=result['pair'],
                      before=result['before'],after=result['after'],
                      full_memory_sha256=result['full_memory_sha256'],draws_sha256=result['draws_sha256']),
                      sort_keys=True),flush=True)


class RosterPipe(unittest.TestCase):
    make_engine=wire.Pipe.make_engine
    receive=wire.Pipe.receive
    actual_pipe=wire.Pipe.actual_pipe

    def test_starter_pair_and_pure_repair_cross_actual_pipe(self):
        self.actual_pipe(True,'starter')

    def test_bench_pool_native_order_and_repair_cross_actual_pipe(self):
        self.actual_pipe(True,'pool')


if __name__=='__main__':unittest.main()
