"""[designed: T70] Qt-free, explicit-data quick-match process entry.
[derived: T41/T42/T43/T44/T45] Existing friendly runner owns condition changes.
"""
import copy
import fcntl  # T98 Done-when 2: a deliberate POSIX-only fault; reverted next commit
import sys
from goal2.engine.savestate import Savestate
from goal2.game.state import to_savestate
from goal2.game.quick_match import run_full_match,begin_full_match
from goal2.game.session_save import load, save
from goal2.game.campaign_rounds import prepare as prepare_round,complete as complete_round


def play(state, template):
    """[designed] Compute a complete candidate without touching the caller."""
    candidate=prepare_round(state,template)
    adapted=Savestate(to_savestate(candidate,original=template))
    result=run_full_match(adapted,candidate,retain_state=True)
    return complete(candidate,result,template=template)


def complete(candidate,result,*,template=None):
    """[designed: T48] Shared atomic full-time and world-turn publication."""
    return complete_round(candidate,result,template=template)


def write_json(path,data):
    """[designed: T47] Atomic explicit-data IPC, never Python object loading."""
    import json
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(data));temporary.replace(path)


def main(argv=None):
    from pathlib import Path
    import json,time
    args=sys.argv[1:] if argv is None else argv
    source,target=args[:2];state,template=load(source)
    if len(args)==2:
        candidate=play(state,template)
    elif args[2:] == ['--halftime']:
        # [designed: T47] load() created this private child-owned state from IPC.
        candidate=prepare_round(state,template)
        match=begin_full_match(Savestate(to_savestate(candidate,original=template)),candidate)
        directory=Path(target).parent
        write_json(directory/'halftime.json',match.preview())
        command=directory/'continue.json'
        while not command.exists():time.sleep(.02)
        changes=json.loads(command.read_text())
        if (not isinstance(changes,list) or any(not isinstance(p,list) or len(p)!=2 for p in changes)):
            raise ValueError('Invalid halftime substitutions')
        for outgoing,incoming in changes:match.substitute(outgoing,incoming)
        candidate=complete(candidate,match.finish(retain_state=True),template=template)
    else:raise ValueError('Invalid friendly worker mode')
    save(target,candidate,template)

if __name__=='__main__':main()
