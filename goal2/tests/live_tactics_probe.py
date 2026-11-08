"""Read-only key/plan tracing of the natural injury-edit -> resume -> pause path."""
import copy
from collections import deque

def trace(state, fixture, engine):
    from goal2.tests.test_watched_adapter import direct_image
    from goal2.engine.original_match import Match
    from goal2.engine.original_match.match import SITE_MENU, SITE_SELECT
    m = Match(direct_image(state), fixture, managed=state.managed_country,
              captain=state.captain or None, record_draws=True, delay_byte=0,
              substitutions=255, engine=engine, ports=['all'] if engine=='port' else [], timeout_s=600)
    m.opts['ticks'] = True
    keys=deque(maxlen=80); real=m._key_for
    def plan():
        p=m._menu
        return None if p is None else dict(side=p.side,steps=list(p.steps),screen=p.in_screen,
            tactics=dict(p.tactics),edit=getattr(p,'edit_only',False),presses=p.presses)
    def read(site):
        before=plan();value=real(site)
        if site in (SITE_MENU,SITE_SELECT):
            keys.append(dict(site=site,key=value,context=m.st.get('menu_context'),before=before,after=plan(),
                editing_select=m.st.get('editing_select'),editing_menu=m.st.get('editing_menu'),
                readonly=m.m.rd(0xC20,1),match_menu=m.m.rd(0xC1F,1),countries=[m.m.rd(0x9B34),m.m.rd(0x9B36)]))
        return value
    m._key_for=read
    pause=False;injury=False;asked=None;decisions=[];tactics_events=[]
    for e in m.events():
        if e.kind=='tactics':tactics_events.append(copy.deepcopy(e.data))
        if e.kind=='tick' and e.minute>=5 and injury and not pause:
            pause=True;m.pause()
        if e.kind!='decision':continue
        d=e.data;decisions.append(copy.deepcopy(d))
        if d['context']=='substitution' and d['injured'] and not injury:
            off=d['injured'][0];pos=dict(d['positions'])
            on=next(w for w in d['bench'] if (pos[w]==0)==(pos[off]==0))
            injury=True;m.answer(substitutions=[(off,on)],edit_only=True)
        elif d['context']=='pause':
            if asked is None:
                asked=(d['tactics'] ^ 16)
                m.answer(tactics={5:bool(asked&16)},edit_only=True)
            else:
                return dict(engine=engine,applied=d['tactics']==asked,wanted=asked,got=d['tactics'],
                    readonly=m.m.rd(0xC20,1),side=m.side,managed=state.managed_country,
                    decisions=decisions,tactics_events=tactics_events,keys=list(keys))
        else:m.answer()
    return dict(engine=engine,error='did not reach post-injury pause',injury=injury,pause=pause,decisions=decisions,keys=list(keys))
