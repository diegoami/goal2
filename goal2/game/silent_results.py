"""[derived: F024 §4, archaeology0ef880e1f6ec9bc12b3f12c3aaecb4d747d9d5cb]
One B19D count batch, not a full quick match. [designed: T48] CPU setup is
T46 top-ability/stored tactics with zero unknown host bonus; no CPU tail updates.
"""
from goal2.engine.quick_engine import QuickMatch,LCG
from goal2.engine.savestate import Savestate
from goal2.game.computer import prepare
from goal2.game.state import to_savestate


class SilentResolver:
    """[designed] Replaceable adapter; engine primitives remain vendored."""
    def __init__(self,state,template):
        self.state=state
        self.qm=QuickMatch(Savestate(to_savestate(state,original=template)))
        self.qm.flag80fc=0

    def __call__(self,fixture,seed):
        qm=self.qm;qm.teams[:]=[fixture.side_a,fixture.side_b];qm.rng=LCG(seed)
        for country in qm.teams:
            prepared=prepare(self.state,country)
            qm.countries[country]={'squad':list(prepared['squad']),'tactics':prepared['tactics'],'managed':country}
        score=qm.roll_quick_goals(12)
        decider=fixture.kind==4 or 8<=fixture.kind<=203
        if decider and score[0]==score[1]:
            extra=qm.roll_quick_goals(4);score=[a+b for a,b in zip(score,extra)]
        winner=2 if score[0]==score[1] else int(score[1]>score[0])
        if decider and winner==2:winner=int(qm.rng.rand(2)==1)
        return {'score':list(score),'winner':winner,'seed_after':qm.rng.seed,'draws':qm.rng.draws}
