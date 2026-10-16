"""[designed: T70] Qt-free, explicit-data quick-match process entry.
[derived: T41/T42/T43/T44/T45] Existing friendly runner owns condition changes.
"""
import copy
import sys
from goal2.engine.savestate import Savestate
from goal2.game.state import to_savestate
from goal2.game.quick_match import run_full_match
from goal2.game.session_save import load, save


def play(state, template):
    """[designed] Compute a complete candidate without touching the caller."""
    candidate=copy.deepcopy(state)
    adapted=Savestate(to_savestate(candidate,original=template))
    result=run_full_match(adapted,candidate,retain_state=True)
    if not isinstance(candidate.last_match,dict):
        raise ValueError('Friendly runner did not retain its result')
    candidate.last_match['managed_side']=result['managed_side']
    candidate.last_match['match_count']=candidate.match_count
    if candidate.campaign is not None:
        campaign=candidate.campaign;fixture=campaign.next_fixture
        campaign.complete_fixture(fixture.fixture_id)
        campaign.results.append({'fixture_id':fixture.fixture_id,'teams':list(result['teams']),'score':list(result['score'])})
        pending=campaign.next_fixture
        if pending is not None and pending.stage!=campaign.stage and pending.kind==1:
            campaign.advance_calendar()
    return candidate


def main(argv=None):
    source,target=sys.argv[1:] if argv is None else argv
    state,template=load(source)
    save(target,play(state,template),template)

if __name__=='__main__':main()
