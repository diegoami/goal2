"""[designed: T170z/#776] Existing screens over an explicitly owned held session.

The caller owns bootstrap, the exclusive process lease, reply queue and disposal.
This adapter owns presentation only; no legacy Match construction/publication.
"""
from __future__ import annotations
import queue

from PySide6.QtCore import QObject,QTimer

from goal2.ui.match_day import MatchDay,asks_watch


class HeldModel:
    held_prematch=True

    def __init__(self,flow,owner):
        self.flow,self.owner=flow,owner
        self._last=flow.controller.view

    @property
    def snapshot(self):
        if self.flow.controller.view is not None:self._last=self.flow.controller.view
        return self._last

    @property
    def state(self):return self.snapshot.display_state(self.owner.state)

    @property
    def goaldat(self):return self.owner.goaldat

    @property
    def held_block_reason(self):
        c=self.flow.controller
        return '' if c.status=='ready' else ('Applying changes. Please wait.' if c.pending else c.message or 'This held session is not ready.')

    @property
    def team_tactics(self):return self.snapshot.countries[self.snapshot.managed_country][0x2D]

    @property
    def team_context(self):return self.snapshot.team_context

    @property
    def live_records(self):return {w:self.snapshot.record(w) for w in self.snapshot.squad if w}

    @property
    def injured(self):return {w for w in self.snapshot.squad if w and self.snapshot.record(w)[14]==0}

    @property
    def eleven(self):return self.snapshot.eleven

    def words(self):return list(self.snapshot.squad)

    def position(self,w):return self.snapshot.record(w)[6]

    def can_mark(self,w):return self.snapshot.can_mark(w)

    def view(self):
        from goal2.game import roles
        state=self.state;table=roles.tables(state)
        return {'country_name':self.goaldat.country_names[state.managed_country],
                'players':[dict(id=w,role=roles.role(state,self.position(w),cache=table)[0],
                                line=roles.role(state,self.position(w),cache=table)[1]) for w in self.words()]}

    def pool_view(self,*,query='',position=None):
        from goal2.game import roles
        from goal2.game.campaign_pool import fold
        state=self.state;table=roles.tables(state);rows=[]
        for w in self.snapshot.pool:
            if not w:continue
            raw=self.snapshot.record(w);name=self.goaldat.player_names[w]
            if fold(query) not in fold(name) or (position is not None and raw[6]!=position):continue
            role,line=roles.role(state,raw[6],cache=table)
            rows.append(dict(id=w,name=name,position=raw[6],role=role,line=line))
        return {'reserves':rows}  # no guessed legacy pool permission

    def card(self,w):
        from goal2.game.player_card import card
        value=card(self.state,w,self.goaldat)
        if w in self.snapshot.squad and self.snapshot.record(w)[6]>=2:
            target=self.snapshot.marking_word(w)
            if self.snapshot.record(w)[16]&64 and target:
                from goal2.ui.squad_card import full_name
                value['mark']=full_name(self,target)+' P'
        return value

    def mark_text(self,w):return self.card(w)['mark']

    def _ready(self):
        if self.held_block_reason:raise ValueError(self.held_block_reason)

    def swap(self,a,b):self._ready();self.flow.controller.swap(a,b)

    def exchange(self,a,b):self._ready();self.flow.controller.exchange(a,b)

    def set_position(self,w,step):
        self._ready();self.flow.controller.set_position(w,(self.position(w)+step)%14)

    def club_position(self,w):self._ready();self.flow.controller.club_position(w)

    def own_tactic(self,w,element):
        self._ready();current=self.snapshot.own_override(w,element)
        following=False if current is None else True if current is False else None
        self.flow.controller.set_own_tactic(w,element,following)

    def step_mark(self,w):
        self._ready();options=(None,0,*self.snapshot.marking_targets)
        current=self.snapshot.marking_goal(w)
        following=options[(options.index(current)+1)%len(options)] if current in options else None
        self.flow.controller.set_marking(w,following)

    def rename_player(self,w,text):return self.owner.rename_player(w,text)

    def assistant_jobs(self):
        raise ValueError('Ask the assistant before starting this round. Held-match assistant support is pending.')

    def continent(self,country=None):return self.snapshot.countries[country or self.snapshot.managed_country][0x2C]

    @staticmethod
    def home(fixture):
        from goal2.desktop.model import DesktopModel
        return DesktopModel.home(fixture)

    def prematch_kits(self,fixture):
        from goal2.engine.original_match.image import Image
        from goal2.ui.kits import compute
        image=Image.from_memory_component(self.state.mem)
        return compute(lambda off:image.rd(off,1),fixture.side_a,fixture.side_b)


class HeldPrematchFlow(QObject):
    """Bind an already-configured owner session; explicit callbacks keep its lease."""
    asks_watch=staticmethod(asks_watch)
    _settings_path=MatchDay._settings_path
    _settings=MatchDay._settings
    set_replay_auto=MatchDay.set_replay_auto

    def __init__(self,window,owner,controller,fixture,replies,*,on_handoff,on_close,on_tournament,on_stats,watch=None):
        super().__init__(window)
        if controller.status!='ready' or controller.view is None:raise ValueError('held pre-match view is not ready')
        if (fixture.side_a,fixture.side_b)!=controller.view.sides:raise ValueError('fixture does not match held sides')
        if owner.state.managed_country!=controller.managed_country:raise ValueError('career belongs to another country')
        if not all(callable(x) for x in (on_handoff,on_close,on_tournament,on_stats)):
            raise ValueError('explicit native session-owner callbacks are required')
        self.window,self.owner,self.controller,self.fixture,self.replies=window,owner,controller,fixture,replies
        self.model=HeldModel(self,owner);self.bench=None;self.watch=watch
        self.on_handoff,self.on_close,self.on_tournament,self.on_stats=on_handoff,on_close,on_tournament,on_stats
        self.replay_auto=self._settings().get('automatic_action_replay',False)
        self.closed=False;self.handed_off=False;self._tactics=None
        self.timer=QTimer(self);self.timer.setInterval(20);self.timer.timeout.connect(self.poll)
        window.destroyed.connect(self.close)

    @property
    def kind_name(self):
        from goal2.desktop.model import kind_word
        return kind_word(self.fixture.kind,self.fixture.stage)

    def open(self):
        from goal2.ui.s15_match_menu import MenuScreen
        screen=MenuScreen(self.window,self,'before');screen._held_hash=self.model.snapshot.state_hash
        self.timer.start();return self.window.push(screen)

    def refresh_menu(self,menu):
        if self.closed or self.window.current() is not menu:return
        if getattr(menu,'_held_hash',None)==self.model.snapshot.state_hash:return
        from goal2.ui.s15_match_menu import MenuScreen
        fresh=MenuScreen(self.window,self,'before');fresh._held_hash=self.model.snapshot.state_hash
        fresh.restore_navigation(menu)
        # Replace the current frame without invoking an intermediate screen's
        # shown callback (which could reopen a different route).
        self.window.stack.pop();self.window.page.removeWidget(menu);menu.deleteLater()
        self.window.push(fresh)

    def play(self,menu):
        if self.model.held_block_reason:return menu.say(self.model.held_block_reason)
        from goal2.ui.s16_choose import ChooseScreen
        from goal2.ui.s17_pitch import suggested_captain
        view=self.model.snapshot;current=suggested_captain(self.model.state)
        if current not in view.captain_choices:current=next(iter(view.captain_choices),view.eleven[0])
        names=self.model.goaldat.country_names
        return self.window.push(ChooseScreen(self.window,self.model,'captain',view.eleven,current,self.kick_off,
            available=view.captain_choices,computer=None,match=f'{names[self.fixture.side_a]} v {names[self.fixture.side_b]}'))

    def kick_off(self,captain):self.controller.play(captain=captain)

    def apply_tactic(self,screen,element,value):
        self._tactics=screen
        try:self.controller.set_team_tactic(element,value)
        except ValueError as exc:
            screen.pending=False;screen.message=str(exc);screen.refresh();self._tactics=None

    def open_team_tactics(self):
        from goal2.ui.s10_team_tactics import TeamTacticsScreen
        return self.window.push(TeamTacticsScreen(self.window,self.model,answer=self.model,apply=self.apply_tactic))

    def open_tournament(self):return self.on_tournament(self)

    def show_stats(self,menu):return self.on_stats(self,menu)

    def poll(self):
        if self.closed or self.handed_off:return
        from goal2.ui.s08_squad import SquadScreen
        from goal2.ui.s09_player_tactics import PlayerTacticsScreen
        screen=self.window.current();old=self.controller.view;status=self.controller.status
        # Help may cover the editor while the reply arrives. Preserve the
        # editor's word, rather than an index in the old native sort order.
        selected={s:s.current() for s in self.window.stack if isinstance(s,SquadScreen)}
        while True:
            try:kind,value=self.replies.get_nowait()
            except queue.Empty:break
            self.controller.receive(kind,value)
        c=self.controller
        if c.status=='handoff':
            self.handed_off=True;self.timer.stop()
            self.on_handoff(self,c.handoff,{'watch':self.watch,'replay_auto':self.replay_auto})
            return
        changed=c.view is not old or c.status!=status
        if not changed:return
        if c.status=='ready' and self._tactics is not None:
            target,self._tactics=self._tactics,None
            target.applied(self.model,{})
            if c.message:target.message=c.message;target.refresh()
        elif c.status=='lost' and self._tactics is not None:
            target,self._tactics=self._tactics,None
            target.pending=False;target.message=c.message;target.refresh()
        from goal2.ui.s16_choose import ChooseScreen
        if c.status=='ready' and isinstance(screen,ChooseScreen) and screen.done:
            self.window.pop();screen=self.window.current()
        for editor,word in selected.items():
            rows=editor.rows()
            if word is not None:
                found=next((i for i,r in enumerate(rows) if r['id']==word),None)
                if found is not None:editor.cursor[editor.side]=found
            if editor.picked:
                pane,w=editor.picked
                if w not in [r['id'] for r in editor.rows(pane)]:editor.picked=None
            editor.message=c.message or self.model.held_block_reason
            editor.refresh()
        for editor in self.window.stack:
            if isinstance(editor,PlayerTacticsScreen):
                editor.refresh()
                if c.message:editor.explain.setText(c.message)
        if isinstance(screen,(SquadScreen,PlayerTacticsScreen)):return
        if hasattr(screen,'refresh'):
            screen.refresh()
            if c.message and hasattr(screen,'explain'):screen.explain.setText(c.message)
        elif hasattr(screen,'phase'):
            self.refresh_menu(screen)
            self.window.current().say(c.message or self.model.held_block_reason)
        elif isinstance(screen,ChooseScreen) and c.status=='lost':
            screen.wait_for('The held session disconnected.',c.message)

    def close(self,*_):
        if self.closed:return
        self.closed=True;self.timer.stop();self.controller.detach()
        if not self.handed_off:self.on_close(self)
