"""[designed: owner #435/T135] Read-only recruitment proposals from the original assistant.

[confirmed: T107 INSERT/F031, original-key T123 policy] The assistant selects on a copied Core.
Pairing outgoing/incoming players for comparison is this UI's policy, not an original AI claim.
"""
import hashlib


def state_key(core):
    return hashlib.sha256(core.save()).hexdigest()


def propose(core,data_path,cancel=None):
    from goal2.core import Core,CoreError,views
    from goal2.core.driver import Driver
    from goal2.core.screens import INSERT,RETURN
    if core.wait.kind!='manager-menu':
        raise ValueError('Return to the country desk before asking the assistant')
    before=core.save()
    result=dict(input_sha256=hashlib.sha256(before).hexdigest(),assistant_sha256=None,
                selected=[],proposals=[],rejected=[],refusal=None,cancelled=False)
    def cancelled():
        if cancel is not None and cancel.is_set():
            result['cancelled']=True
            return True
        return False
    try:
        if cancelled():return result
        clone=Core.load(before,goal_dat=data_path)
        initial=views.team(clone.wait.state)['squad']
        pool={p['player'] for p in views.pool(clone.wait.state)['rows']}
        d=Driver(clone);d.goto('select-squad')
        if cancelled():return result
        wait=d.press(INSERT,expect=('select-squad','squad-change-refused'))
        if wait.kind=='squad-change-refused':
            result['refusal']=wait.view['message'];d.press(RETURN,expect=('select-squad',))
        if cancelled():return result
        d.to_menu()
        after=views.team(clone.wait.state)['squad']
        result['assistant_sha256']=state_key(clone)
        result['selected']=[p['player'] for p in after]
        if result['refusal']:return result
        old={p['player'] for p in initial};new=set(result['selected'])
        if len(old)!=20 or len(new)!=20:
            raise ValueError('The assistant did not return twenty distinct players')
        outgoing=[p for p in initial if p['player'] not in new]
        incoming=[p for p in after if p['player'] not in old]
        if len(outgoing)!=len(incoming) or any(p['player'] not in pool for p in incoming):
            raise ValueError('The assistant selected a player outside this pool')
        for player in incoming:
            if cancelled():result['proposals']=[];return result
            match=next((p for p in outgoing if p['position']==player['position']),None)
            pairing='same position'
            if match is None:
                match=next((p for p in outgoing if p['line']==player['line']),None)
                pairing='same line'
            if match is None:match=outgoing[0];pairing='squad place'
            outgoing.remove(match)
            card=views.player_card(clone.wait.state,player['player'])
            proposal=dict(outgoing=match['player'],incoming=player['player'],pairing=pairing,
                          suggested_position=player['position'],suggested_code=player['code'],
                          suggested_role=card['position_name'])
            # Each proposal is independently legal as the next action, not an assumed batch transfer.
            trial=Driver(Core.load(before,goal_dat=data_path))
            verdict=trial.exchange(match['player'],player['player'])
            if verdict['refused']:
                result['rejected'].append(dict(outgoing=match['player'],incoming=player['player'],
                                               reason=verdict['refused']))
            else:
                proposal['validation_sha256']=state_key(trial.core)
                result['proposals'].append(proposal)
        if cancelled():result['proposals']=[]
        return result
    except CoreError as exc:
        raise ValueError(f'The assistant could not complete its selection: {exc}') from exc
    finally:
        if core.save()!=before:
            raise ValueError('The career changed while the assistant was working; ask again')
