"""[derived: F023 §8, archaeology 3656a2d26e0f57a410d648edeaa6cd9eb7d1f607]
Played stage-kind fixtures, 2/1/0 points and the original in-place exchange sort.
No random draws, ID tiebreak or calendar advancement belong in table reads.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class TableFixture:
    """[designed: T49] Explicit source-order fixture identity and endpoints."""
    fixture_id: str
    kind: int
    side_a: int
    side_b: int


@dataclass(frozen=True)
class TableRow:
    """[designed] Immutable display row; country identity survives every slot exchange."""
    country: int
    won: int
    drawn: int
    lost: int
    goals_for: int
    goals_against: int
    points: int
    rank: int
    advances: bool

    @property
    def played(self):return self.won+self.drawn+self.lost

    @property
    def goal_difference(self):return self.goals_for-self.goals_against


def _integer(v,low,high):return type(v) is int and low<=v<=high


def group_table(slots, fixtures, results, *, stage, places):
    """[derived: F023 §8] Rebuild counters and repeat sorting in source fixture order.

    Results may arrive in any container order; their fixture IDs select the
    source chronology. The exchange sort is intentionally not a stable sort:
    indirect swaps may reverse equal teams. Later all-equal comparisons retain
    that current order. Goals and points are original byte counters.
    [designed] Completed-ledger membership marks completion; scores retain the
    world ledger's full 0..255 range, independently of original raw FE/FF marks.
    places identifies provisional progressing positions, not a clinch.
    """
    if (len(slots)!=4 or any(not _integer(c,1,128) for c in slots) or len(set(slots))!=4
            or type(stage) is not int or stage not in (2,3,5,7) or not _integer(places,0,4)):
        raise ValueError('four distinct countries, a group stage and 0..4 places are required')
    fixtures=tuple(fixtures);known={}
    for f in fixtures:
        if (not isinstance(f,TableFixture) or not isinstance(f.fixture_id,str) or not f.fixture_id
                or f.fixture_id in known or not _integer(f.kind,1,255)
                or not _integer(f.side_a,1,128) or not _integer(f.side_b,1,128) or f.side_a==f.side_b):
            raise ValueError('invalid or duplicate source fixture')
        known[f.fixture_id]=f
    completed={}
    for r in results:
        if not isinstance(r,dict) or not isinstance(r.get('fixture_id'),str):
            raise ValueError('invalid completed fixture')
        fid=r['fixture_id'];f=known.get(fid)
        if f is None or fid in completed:
            raise ValueError('unknown or replayed fixture result')
        if (not isinstance(r.get('teams'),(tuple,list)) or list(r['teams'])!=[f.side_a,f.side_b]
                or any(type(c) is not int for c in r['teams']) or not isinstance(r.get('score'),(tuple,list))
                or len(r['score'])!=2 or any(not _integer(g,0,255) for g in r['score'])):
            raise ValueError('result endpoints or played scores differ from the fixture')
        completed[fid]=tuple(r['score'])
    stats={c:dict(won=0,drawn=0,lost=0,goals_for=0,goals_against=0,points=0) for c in slots}
    order=list(slots);counts={c:0 for c in slots}
    for f in fixtures:
        if f.kind!=stage:continue
        members=(f.side_a in stats,f.side_b in stats)
        if members==(False,False):continue
        if members!=(True,True):raise ValueError('stage fixture crosses the supplied group')
        for c in (f.side_a,f.side_b):
            counts[c]+=1
            if counts[c]>12:raise ValueError('group fixture window exceeds the original last twelve entries')
        if f.fixture_id not in completed:continue
        a,b=completed[f.fixture_id]
        for c,gf,ga in ((f.side_a,a,b),(f.side_b,b,a)):
            s=stats[c]
            s['goals_for']=(s['goals_for']+gf)&255
            s['goals_against']=(s['goals_against']+ga)&255
            field='won' if gf>ga else 'drawn' if gf==ga else 'lost'
            s[field]+=1
            s['points']=(s['points']+(2 if gf>ga else 1 if gf==ga else 0))&255
        def key(c):
            s=stats[c]
            return s['points'],s['goals_for']-s['goals_against'],s['goals_for']
        # [confirmed: F023 8476..85F1] Compare all later slots; only strictly better keys swap.
        for i in range(3):
            for j in range(i+1,4):
                if key(order[j])>key(order[i]):order[i],order[j]=order[j],order[i]
    return tuple(TableRow(c,**stats[c],rank=i+1,advances=i<places) for i,c in enumerate(order))


def opening_groups(campaign, template):
    """[derived: T41a/F023 §3] Recover all 32 original draw groups from saved ordered pairs.

    [designed] Complete opening stage-2/5 schedules only; None for a legacy or
    later-stage session without those source rows. No draw is repeated and no RNG is used.
    Returns (continent, group, slots) in source continent/group order.
    """
    from goal2.game.campaign_schedule import _read_tables
    c=campaign
    if c is None or c.world is None or c.cycle!=1 or c.stage not in (2,5):return None
    # [confirmed: F023 §3] Source order is round, continent, group; one group fixture each round.
    _,schedule,_,_,_=_read_tables(template)
    rounds={r:[] for r in range(1,13)}
    for f in c.world.fixtures:
        if f.kind==c.stage:
            if f.round_number not in rounds:raise ValueError('invalid opening group round')
            rounds[f.round_number].append(f)
    if any(len(rows)!=32 for rows in rounds.values()):
        raise ValueError('complete opening group schedule is required')
    groups=[]
    for index in range(32):
        continent,group=index//8+1,index%8+1
        slots=[None]*4
        for round_number,rows in rounds.items():
            f=rows[index];a,b=schedule[(continent+group,round_number)]
            for slot,country in ((a,f.side_a),(b,f.side_b)):
                if slots[slot-1] not in (None,country):raise ValueError('saved source group slots are inconsistent')
                slots[slot-1]=country
        if any(not _integer(n,1,128) for n in slots) or len(set(slots))!=4:
            raise ValueError('invalid recovered source group')
        groups.append((continent,group,tuple(slots)))
    if len({country for _,_,slots in groups for country in slots})!=128:
        raise ValueError('saved opening groups do not cover all 128 countries once')
    return tuple(groups)


def opening_group(state, template):
    """[derived: T41a/F023 §3] The managed country's recovered opening group. [designed] None
    without a complete opening schedule."""
    c=state.campaign
    groups=opening_groups(c,template)
    if groups is None:return None
    for continent,group,slots in groups:
        if state.managed_country in slots:
            # [confirmed: F023 §§4,7] Europe gets two WC places, America one;
            # Africa/Asia group winners enter playoffs. Continental groups supply one winner.
            places=2 if c.stage==5 and continent==1 else 1
            return {'continent':continent,'group':group,'slots':slots,'places':places,
                    'playoff':c.stage==5 and continent in (3,4)}
    raise ValueError('managed country is absent from the saved opening groups')
