"""[derived: F007/F011/F018/F019/F027, archaeology0ef880e1f6ec9bc12b3f12c3aaecb4d747d9d5cb]
The managed country's 20 squad words and 80 reserve words; BA4E quick caller.
[designed: T45] Stable membership survives saves; views never regenerate records.
"""
import copy
from goal2.game import eligibility
from goal2.engine import confidence


def validate(state):
    """[designed: T45] Validate the sole manager's fixed 100-player universe."""
    if state.campaign is None:
        raise ValueError('pool requires a campaign')
    squad = state.managed_squad
    base = list(range((state.managed_country-1)*20+1, state.managed_country*20+1))
    reserves = state.campaign.reserve_ids
    if reserves is None:
        # [designed: compatibility] Old canonical saves predate exchanges. Infer
        # membership only; a noncanonical legacy roster cannot recover lost IDs.
        if squad != base:
            raise ValueError('legacy pool requires canonical squad membership')
        reserves = list(range(2561,2641))
    words = list(squad) + list(reserves)
    if (len(squad)!=20 or len(reserves)!=80 or any(type(w) is not int for w in words)
            or len(set(words))!=100 or set(words)!=set(base+list(range(2561,2641)))):
        raise ValueError('pool needs 20 squad and 80 distinct reserve identities')
    if any(len(state.players[w])!=20 or state.players[w][0]!=state.managed_country for w in words):
        raise ValueError('pool player belongs to another country')
    country_words=[int.from_bytes(state.countries[state.managed_country][i:i+2],'little') for i in range(0,40,2)]
    if country_words!=squad:
        raise ValueError('pool squad differs from country words')
    if (len(state.starting_eleven)!=11 or len(set(state.starting_eleven))!=11
            or not set(state.starting_eleven)<=set(squad)
            or (state.captain and state.captain not in state.starting_eleven)):
        raise ValueError('pool needs a valid eleven/captain')
    return list(reserves)


def window(state):
    """[assumed: Q008/#254] Only between supported friendlies, outside tours.

    [derived: 5A38] The country comparison uses the fixture's second country;
    [assumed] consecutive completed/pending cross-continent friendlies define
    the provisional tour. This is not a claim of original exchange-window fidelity.
    """
    if state.campaign is None:
        return {'allowed':False,'reason':'Campaign required'}
    c=state.campaign;next_fixture=c.next_fixture
    if next_fixture is None or next_fixture.kind!=1 or state.managed_country not in (next_fixture.side_a,next_fixture.side_b):
        return {'allowed':False,'reason':'Exchange requires a pending managed friendly'}
    def travelling(f):
        return (f.kind==1 and state.managed_country in (f.side_a,f.side_b)
                and state.countries[state.managed_country][44]!=state.countries[f.side_b][44])
    if c.completed_fixture_ids:
        previous=c.fixtures[len(c.completed_fixture_ids)-1]
        if travelling(previous) and travelling(next_fixture):
            return {'allowed':False,'reason':'Exchanges closed during provisional tour'}
    return {'allowed':True,'reason':'Between supported friendlies (provisional Q008 policy)'}


def view(state, goaldat, *, query='', position=None):
    """[derived: F011] Position+6 ordering; [designed] ID breaks equal keys.

    [designed] Search and position filter affect only reserve display. Position
    is the source numeric code; no invented fourteen-role naming is implied.
    """
    reserves=validate(state)
    if not isinstance(query,str) or (position is not None and (type(position) is not int or not 0<=position<14)):
        raise ValueError('invalid pool search or position')
    from goal2.game.state import _wrap_raw
    lines=_wrap_raw(state.vga,state.mem).ds_bytes(0xd4e,16)
    groups=('Goalkeeper','Defence','Midfield','Attack','Defence / midfield','Midfield / attack')
    def row(w):
        record=state.players[w]
        return {'id':w,'name':goaldat.player_names[w],'ability':record[4],
                'position':record[6],'position_group':groups[lines[record[6]]],'energy':record[14],'confidence':record[12],
                'availability':eligibility.info(record)}
    rows=[row(w) for w in sorted(reserves,key=lambda w:(state.players[w][6],w))]
    rows=[x for x in rows if query.casefold() in x['name'].casefold() and (position is None or x['position']==position)]
    return {'squad':[row(w) for w in sorted(state.managed_squad,key=lambda w:(state.players[w][6],w))], 'reserves':rows,'window':window(state)}


def exchange(state, outgoing, incoming):
    """[derived: F011/DEA6] Swap IDs; [designed] repair XI/captain atomically."""
    reserves=validate(state)
    if not window(state)['allowed']:
        raise ValueError(window(state)['reason'])
    if (type(outgoing) is not int or type(incoming) is not int
            or outgoing not in state.managed_squad or incoming not in reserves):
        raise ValueError('exchange needs one squad and one reserve ID')
    eligibility.require_available(state.players,[incoming])
    candidate=copy.copy(state);candidate.campaign=copy.copy(state.campaign)
    candidate.managed_squad=[incoming if w==outgoing else w for w in state.managed_squad]
    candidate.campaign.reserve_ids=[outgoing if w==incoming else w for w in reserves]
    candidate.starting_eleven=[incoming if w==outgoing else w for w in state.starting_eleven]
    candidate.captain=incoming if state.captain==outgoing else state.captain
    country=bytearray(state.countries[state.managed_country])
    country[:40]=b''.join(w.to_bytes(2,'little') for w in candidate.managed_squad)
    candidate.countries=list(state.countries);candidate.countries[state.managed_country]=bytes(country)
    validate(candidate)
    state.managed_squad=candidate.managed_squad;state.campaign=candidate.campaign
    state.countries=candidate.countries;state.starting_eleven=candidate.starting_eleven;state.captain=candidate.captain


def finish(qm,state):
    """[derived: BA4E] Reserve recovery flag0, rand4/rand4 C, then B27F.

    [designed] Called by the quick campaign tail before B7FA, never watched
    publication. Stored reserve-slot order controls the RNG assignment.
    """
    if getattr(qm,'_campaign_pool_complete',False):
        raise ValueError('pool effects already applied')
    reserves=validate(state)
    from goal2.game.campaign_energy import recover_player
    f=state.campaign.next_fixture
    if f is None or f.kind!=1:
        raise ValueError('pool effects require a pending friendly')
    kind_set=qm.state.ds_bytes(0x0f3e,32)
    gradual=bool(kind_set[f.kind//8] & (1<<(f.kind%8))) or state.countries[state.managed_country][44]!=state.countries[f.side_b][44]
    bases=tuple(qm.state.ds_bytes(0xe82,2));caps=tuple(qm.state.ds_bytes(0xe84,2))
    recovery_draws=0
    for word in reserves:
        before=qm.rng.draws
        record=bytearray(recover_player(qm._player(word),0,qm.rng,gradual=gradual,managed=True,caps=caps,redraw_bases=bases))
        recovery_draws+=qm.rng.draws-before
        first=qm.rng.rand(4);second=qm.rng.rand(4)
        record[12]=confidence.change(record[12],second-first)
        qm.playerrec[word]=bytearray(eligibility.after_fixture(record,f.kind))
    qm._campaign_pool_complete=True
    return {'fixture_id':f.fixture_id,'recovery_draws':recovery_draws,'confidence_draws':160}
