"""[designed: T69] Qt-free desktop controller over game/state/save interfaces.
[derived: T40/T41/T43/T44] Existing campaign generation, confidence and eligibility.
No HTTP session or widget imports belong here.
"""
import copy
import zipfile
import zlib
import struct
from pathlib import Path
from goal2.data.goaldat import load as load_goaldat
from goal2.game.campaign_schedule import start_opening_campaign
from goal2.game.campaign_confidence import team_morale
from goal2.game import eligibility
from goal2.game.session_save import load as load_save, save as save_state
from goal2.game.state import from_savestate, to_savestate
from goal2.engine.savestate import Savestate


# [designed: owner, 2026-10-20, T50] New campaign offers both source start calendars:
# [confirmed: F025 §2 P8] 1990 opens at stage 5 (World Cup qualifying), 1992 at stage 2
# (continental qualifying). 1990 stays the default.
START_YEARS=((1990,'1990 (World Cup first)'),(1992,'1992 (Continental first)'))

# [confirmed: F023 §§2-7 at goal2-archaeology 3656a2d26e0f57a410d648edeaa6cd9eb7d1f607] The
# competition each calendar stage plays; [designed: T86] the wording.
STAGES={2:'Continental qualifying',3:'Continental finals groups',4:'Continental semi-finals and final',
        5:'World Cup qualifying',6:'World Cup play-offs',7:'World Cup finals groups',8:'World Cup knockout'}
# [confirmed: F023 §§4,7] Continent numbers 1..4 are Europe, America, Africa and Asia.
CONTINENTS={1:'Europe',2:'America',3:'Africa',4:'Asia'}
# [designed: T86] Until #265 delivers manager names, the one manager is shown by number.
MANAGER='Manager 1 (naming arrives later, #265)'


def campaign_year(campaign):
    """[derived: F025 §2 displayed year = base + 2 * word; docs/watched-kit-acceptance.md] The
    source year of the campaign's current stage."""
    word=2*(campaign.cycle-1)+int(campaign.stage>=5)-int(campaign.start_year%4==2)
    return campaign.start_year+2*word


class DesktopModel:
    """[designed: T69] Own one active game; publish validated candidates only."""
    def __init__(self,goaldat,template_bytes,save_path):
        self.state=None;self.goaldat=goaldat;self.template_bytes=template_bytes
        self.save_path=Path(save_path);self.state=None
        # [designed: T87] The state last created, resumed or saved; later confirmed changes are unsaved.
        self.saved=None

    @classmethod
    def open(cls,template_path,data_path,save_path,*,country=1):
        try:
            raw=Path(template_path).read_bytes()
            from_savestate(raw)
            model=cls(load_goaldat(Path(data_path).read_bytes()),raw,save_path)
            model.new_campaign(country)
            return model
        except (OSError,ValueError,IndexError,KeyError,zipfile.BadZipFile,zlib.error,struct.error) as exc:
            raise ValueError(f'Cannot open game: {exc}') from exc

    @classmethod
    def from_save(cls,path,data_path):
        try:
            model=cls(load_goaldat(Path(data_path).read_bytes()),b'',path)
            model.resume(path)
            return model
        except (OSError,ValueError,IndexError,KeyError,zipfile.BadZipFile,zlib.error,struct.error) as exc:
            raise ValueError(f'Cannot resume game: {exc}') from exc

    def new_campaign(self,country,start_year=1990):
        """[designed] Explicit new-game action, never a selector/redraw callback."""
        if type(country) is not int or not 1<=country<=128:
            raise ValueError('Country must be an integer from1 to128')
        # [confirmed: NG-9, docs/assumptions.md; designed: T163, #537] Every start year the calendar takes
        # (campaign.opening_calendar: an even year), as the original's new game sets it from the clock; the
        # old window still offers START_YEARS only.
        from goal2.game.campaign import CampaignError,opening_calendar
        try:opening_calendar(start_year)
        except CampaignError as exc:raise ValueError(f'Start year {start_year!r} cannot open a campaign: {exc}') from exc
        candidate,_=start_opening_campaign(self._goaldat,self.template_bytes,managed_country=country,
                                         start_year=start_year,seed_7b62=4660,seed_8336=33590)
        # [designed: T92] A new game keeps the manager (the same person); renamed players do not carry.
        if self.state is not None:candidate.manager_name=self.state.manager_name
        self.view(candidate)
        self.state=candidate;self.mark_saved()

    # [designed: T92] Every view reads names through the game: GOAL.DAT's names with this
    # session's renames applied (goal2.game.identities), never a copy that can go stale.
    @property
    def goaldat(self):
        from goal2.game.identities import named
        if self.state is None:return self._goaldat
        # [designed: T93] The managed country's localized pool, then the renames.
        key=(id(self._goaldat),self.state.managed_country,tuple(sorted(self.state.player_renames.items())))
        if getattr(self,'_named',(None,))[0]!=key:self._named=(key,named(self._goaldat,self.state))
        return self._named[1]

    @goaldat.setter
    def goaldat(self,value):
        self._goaldat=value;self._named=(None,)

    @property
    def manager(self):
        """[designed: T92] The manager's name, or the numbered default until one is given."""
        return self.state.manager_name if self.state is not None and self.state.manager_name else MANAGER

    def rename_player(self,word,text):
        """[designed: T92] Rename a squad or pool player of the active game; returns the name."""
        from goal2.game import identities
        candidate=copy.deepcopy(self.state)
        name=identities.rename_player(candidate,identities.base(self._goaldat,candidate),word,text)
        self.state=candidate
        return name

    def rename_manager(self,text):
        from goal2.game import identities
        candidate=copy.deepcopy(self.state)
        name=identities.rename_manager(candidate,text)
        self.state=candidate
        return name

    def mark_saved(self):
        self.saved=copy.deepcopy(self.state)

    @property
    def unsaved(self):
        """[designed: T87] Confirmed changes since the last create, resume or save."""
        return self.state!=self.saved

    def new_friendly(self,country):
        """[designed: T70] Explicit fresh standalone mode, no campaign ledger."""
        self.new_campaign(country)
        self.state.campaign=None;self.mark_saved()

    def pool_view(self,*,query='',position=None):
        """[derived: T45; designed: T71] Display-only source pool view."""
        from goal2.game import campaign_pool
        if self.state.campaign is None:return None
        return campaign_pool.view(self.state,self.goaldat,query=query,position=position)

    def exchange(self,outgoing,incoming):
        """[derived: T45; designed: T71] Validate copied candidate before publication."""
        from goal2.game import campaign_pool
        candidate=copy.deepcopy(self.state)
        campaign_pool.exchange(candidate,outgoing,incoming)
        self.view(candidate)
        campaign_pool.view(candidate,self.goaldat)
        self.state=candidate

    # -- Player and team edits of the squad screens (T165). Each validates a copied candidate before publication.
    # [confirmed: goal2-archaeology F029 at b519d999673c9458211279fd4da8a8325b9f56fe, "The C key of the select-squad
    # screen": 0791:E44F's R and C call 1771:4952; C sets the position +6 to the club position +7, R cycles +6.]
    # [confirmed: goal2-archaeology docs/tasks/T74.md at b519d999, from E033's notes: R steps +6 by one, wrapping
    # 0..13 (1771:4925).]
    # [designed: owner, #423] Shift+R steps back by one. [designed: T165] 4952's marking refresh and the in-match
    # flag DS:9B55 need a match set up; this route has none between matches, so only +6 changes.
    def _managed_words(self,state):
        words=list(state.managed_squad)
        if state.campaign is not None:
            from goal2.game import campaign_pool
            words+=campaign_pool.validate(state)
        return words

    def _edit_player(self,word,change):
        state=self.state
        if type(word) is not int or word not in self._managed_words(state):
            raise ValueError('Choose a player of this squad or its pool')
        record=bytearray(state.players[word])
        if len(record)!=20 or not 0<=record[6]<14 or not 0<=record[7]<14:
            raise ValueError('Invalid player record')
        change(record)
        candidate=copy.copy(state);candidate.players=list(state.players);candidate.players[word]=bytes(record)
        self.view(candidate)
        self.state=candidate
        return candidate.players[word]

    def set_position(self,word,step=1):
        """R (step 1) or Shift+R (step -1): the player's position +6 one step on, wrapping 0..13."""
        if step not in (1,-1):raise ValueError('A position step is 1 or -1')
        return self._edit_player(word,lambda r:r.__setitem__(6,(r[6]+step)%14))

    def club_position(self,word):
        """C: the player's position +6 becomes his club position +7."""
        return self._edit_player(word,lambda r:r.__setitem__(6,r[7]))

    def own_tactic(self,word,element):
        """[confirmed: F010 at b519d999, `1771:4B61`] Enter on own-tactics row `element` 1..4 cycles +0xF: no own
        setting -> his own with element clear (sets element+4, clears element) -> his own with element set -> no own
        setting (clears element+4 and copies the team's element into +0xF). Element k is bit k-1 (F027)."""
        if element not in (1,2,3,4):raise ValueError('An own tactic is element 1..4')
        team=self.state.country_tactics
        def cycle(r):
            own,value,bit=1<<(element+3),1<<(element-1),r[15]
            if not bit&own:bit=(bit|own)&~value
            elif not bit&value:bit|=value
            else:bit=(bit&~own&~value)|(team&value)
            r[15]=bit&255
        return self._edit_player(word,cycle)

    def set_team_tactic(self,element):
        """[confirmed: F010 at b519d999] The team tactics screen 1771:1981 toggles element `element` 1..8 of the
        country's tactics +0x2D (214B:0CF4 XORs bit element-1); the managed country's live byte is
        state.country_tactics, as `confirm` sets it."""
        if element not in range(1,9):raise ValueError('A team tactic is element 1..8')
        candidate=copy.copy(self.state);candidate.country_tactics=self.state.country_tactics^(1<<(element-1))
        self.view(candidate)
        self.state=candidate
        return candidate.country_tactics

    def result_text(self,state=None):
        """[designed: T70] Name retained quick results, never watched events."""
        state=self.state if state is None else state
        match=state.last_match
        if match is None:return 'No match played'
        if not isinstance(match,dict):raise ValueError('Invalid saved match result')
        teams=match.get('teams');score=match.get('score');goals=match.get('goals')
        if (not isinstance(teams,(list,tuple)) or len(teams)!=2
                or any(type(t) is not int or not 1<=t<=128 for t in teams) or teams[0]==teams[1]
                or not isinstance(score,(list,tuple)) or len(score)!=2
                or any(type(n) is not int or n<0 for n in score) or not isinstance(goals,list)):
            raise ValueError('Invalid saved match result')
        for goal in goals:
            if (not isinstance(goal,dict) or type(goal.get('team')) is not int or goal['team'] not in (0,1)
                    or type(goal.get('minute')) is not int or goal['minute']<0
                    or type(goal.get('player')) is not int or not 1<=goal['player']<len(self.goaldat.player_names)):
                raise ValueError('Invalid saved match goal')
        text=f"{self.goaldat.country_names[teams[0]]} {score[0]} — {score[1]} {self.goaldat.country_names[teams[1]]}"
        goals=[f"{g['minute']}′ {self.goaldat.player_names[g['player']]} ({self.goaldat.country_names[teams[g['team']]]})" for g in match['goals']]
        lines=[text,'\n'.join(goals) if goals else 'No goals']
        # [designed: T51] Render validated competitive stages without counting kicks as goals.
        from goal2.game.watched_schema import watched,COMPETITIVE_SCHEMA,validate_result,resolution
        if watched(match) and match.get('schema')==COMPETITIVE_SCHEMA:
            original=match.get('original');validate_result(original,competitive=True)
            stages=resolution(original)
            for key,label in (('regulation','Regulation'),('extra_time','Extra time'),('penalties','Penalties')):
                score=stages[key]
                if score is not None:lines.append(f'{label}: {score[0]} — {score[1]}')
            winner=stages['winner']
            lines.append('Draw' if winner==2 else f'Winner: {self.goaldat.country_names[teams[winner]]}')
        return '\n'.join(lines)

    def view(self,state=None):
        """[derived: F002/F007; designed] Resolve original names and live fields."""
        state=self.state if state is None else state
        if not 1<=state.managed_country<=128 or len(state.managed_squad)!=20:
            raise ValueError('Invalid managed country or squad')
        # [derived: 1771:0D3D; QuickMatch.POS_LINE] Runtime position-to-line mapping.
        from goal2.game.state import _wrap_raw
        lines=_wrap_raw(state.vga,state.mem).ds_bytes(0xd4e,16)
        groups=('Goalkeeper','Defence','Midfield','Attack','Defence / midfield','Midfield / attack')
        rows=[]
        # [designed: owner, 2026-10-21; #283/#286] One-letter role codes; no overall ability, ever.
        from goal2.game import roles
        table=roles.tables(state);names=roles.names(state)
        for word in state.managed_squad:
            record=state.players[word]
            if len(record)!=20:
                raise ValueError('Invalid player record')
            code,line=roles.role(state,record[6],cache=table)
            rows.append({'id':word,'name':self.goaldat.player_names[word],'role':code,'line':line,
                         'club_role':roles.role(state,record[7],cache=table)[0],
                         'position_name':names[record[6]] if record[6]<14 else 'unknown position',
                         'position':groups[lines[record[6]]],'energy':record[14],
                         'confidence':record[12],'availability':eligibility.info(record)})
        self.result_text(state)  # [designed: T70] Validate renderable results before publication.
        fixture=state.campaign.next_fixture if state.campaign else None
        # [derived: T51; designed: T80] Capability names use the adapter's supported kinds.
        from goal2.engine.original_match.match import KINDS
        competitive=fixture is not None and fixture.kind!=1 and fixture.kind in KINDS
        label='Friendly' if fixture is not None and fixture.kind==1 else ('Original competitive' if competitive else 'Unsupported fixture')
        if fixture is None or fixture.kind==1:
            play_label='Play quick friendly'
        elif competitive:
            play_label='Play original competitive'
        else:
            play_label='Play unavailable'
        return {'countries':[(n,self.goaldat.country_names[n]) for n in range(1,129)],
                'country':state.managed_country,'country_name':self.goaldat.country_names[state.managed_country],
                'players':rows,'morale':team_morale(state.players,state.starting_eleven),
                'play_label':play_label,
                'fixture':None if fixture is None else f'{self.goaldat.country_names[fixture.side_a]} — {self.goaldat.country_names[fixture.side_b]} ({label})'}

    def competition_table(self):
        """[designed: T49; derived: F023] Pure named view of the managed opening group."""
        from dataclasses import asdict
        from goal2.game.standings import TableFixture,group_table,opening_group
        group=opening_group(self.state,self.template_bytes)
        if group is None:return None
        campaign=self.state.campaign;world=campaign.world
        fixtures=tuple(TableFixture(f.fixture_id,f.kind,f.side_a,f.side_b) for f in world.fixtures)
        table=group_table(group['slots'],fixtures,world.results,stage=campaign.stage,places=group['places'])
        rows=[dict(asdict(r),name=self.goaldat.country_names[r.country],played=r.played,
                   goal_difference=r.goal_difference) for r in table]
        return dict(group,stage=campaign.stage,rows=rows)

    def fixture_label(self,fixture):
        """[designed: T86] Opponent and competition of a scheduled fixture, without claiming a home side."""
        state=self.state;names=self.goaldat.country_names
        opponent=fixture.side_b if fixture.side_a==state.managed_country else fixture.side_a
        kind='Friendly' if fixture.kind==1 else 'Qualifier' if fixture.kind in (2,5) else STAGES.get(fixture.stage,'Competitive')
        return f'{names[opponent]} / {kind}'

    def summary(self):
        """[designed: T86] What the Launch window shows of a validated career."""
        state=self.state;names=self.goaldat.country_names;campaign=state.campaign
        rows={'country':names[state.managed_country],'manager':self.manager}
        if campaign is None:
            rows.update(campaign='Standalone friendly',next='Quick friendly',then='—',checkpoint='Between friendlies')
        else:
            completed=set(campaign.completed_fixture_ids)
            pending=[f for f in campaign.fixtures if f.fixture_id not in completed]
            rows['campaign']=f'{campaign_year(campaign)} {STAGES[campaign.stage]}'
            rows['next']=self.fixture_label(pending[0]) if pending else 'Stage complete'
            rows['then']=self.fixture_label(pending[1]) if len(pending)>1 else '—'
            rows['checkpoint']=('Before '+names[pending[0].side_b if pending[0].side_a==state.managed_country else pending[0].side_a]
                                if pending else 'After the last fixture of the stage')
        captain=names_of(self,[state.captain])[0] if state.captain else 'chosen by the original at kickoff'
        rows['team']=f'Confirmed / {len(state.managed_squad)} players / captain {captain}'
        return rows

    def countries(self):
        """[confirmed: F007] Every country with its world rank, continent and rank within it."""
        from goal2.game.new_game import country_rank
        return [(n,self.goaldat.country_names[n],*country_rank(self.goaldat,n)) for n in range(1,129)]

    def qualifying(self):
        """[derived: F023 §4; designed: T50] Named stage-2 outcome, or None outside stage 2."""
        from goal2.game import continental_qualifying
        state=self.state
        result=continental_qualifying.outcome(state.campaign,self.template_bytes,state.managed_country)
        if result is None:return None
        names=self.goaldat.country_names;own=result['managed']
        status={'in progress':f"In progress: {own['rank']}. in group {own['group']}; only the group winner qualifies",
                'qualified':f"Qualified for the continental finals as winner of group {own['group']}",
                'eliminated':f"Eliminated: finished {own['rank']}. in group {own['group']}"}[own['status']]
        qualifiers=None if result['qualifiers'] is None else {
            continent:[names[c] for c in winners] for continent,winners in result['qualifiers'].items()}
        return dict(result['managed'],complete=result['complete'],text=status,qualifiers=qualifiers)

    def confirm(self,eleven,captain,tactics):
        """[designed: T69; derived: T36/T44] Validate before changing live state."""
        if (not isinstance(eleven,list) or len(eleven)!=11 or any(type(w) is not int for w in eleven)
                or len(set(eleven))!=11 or not set(eleven)<=set(self.state.managed_squad)):
            raise ValueError('Choose eleven distinct players from this squad')
        if type(captain) is not int or captain not in eleven:
            raise ValueError('Captain must be in the starting eleven')
        if type(tactics) is not int or not 0<=tactics<=255:
            raise ValueError('Tactics must be an eight-bit integer')
        eligibility.require_available(self.state.players,eleven)
        candidate=copy.copy(self.state)
        candidate.starting_eleven=list(eleven);candidate.captain=captain;candidate.country_tactics=tactics
        self.view(candidate)
        self.state=candidate

    def swap(self,first,second):
        """S08's Enter, Enter on two players of the twenty: they change places in the line-up. [confirmed:
        docs/original-game/images/m244-squad.png, T156-R1 steps 14–29: the twenty's order is the line-up, the eleven
        above the bench, and *move player* exchanges two of them] A starter and a bench player swap in and out, the
        incoming player taking the starter's place in the eleven; two starters exchange their places in it.
        [designed: T164, #555] The eleven is published as `confirm` publishes it (a copied candidate, validated by
        `view`, then made live), with the captain and the tactics kept; a captain who leaves the eleven is replaced
        by the incoming player, as a substituted captain is (T47). Unlike `confirm` it does not refuse an
        unavailable eleven: one swap at a time must be able to repair an eleven with two injured starters, and
        kickoff still refuses an unavailable eleven (eligibility.validate_teams) [designed: T44, "retain human
        repair"]. Two bench players keep the squad's order: this route holds the bench as the squad's order and no
        bench order of its own, so they are refused with that reason. Returns the new eleven."""
        state=self.state;squad=list(state.managed_squad);eleven=list(state.starting_eleven)
        if (type(first) is not int or type(second) is not int or first==second
                or first not in squad or second not in squad):
            raise ValueError('Choose two different players of this squad')
        if len(eleven)!=11 or len(set(eleven))!=11 or not set(eleven)<=set(squad):
            raise ValueError('Invalid starting eleven')
        if first not in eleven and second not in eleven:
            raise ValueError('Two bench players keep the squad\'s order on this route')
        captain=state.captain
        if first in eleven and second in eleven:
            i,j=eleven.index(first),eleven.index(second)
            eleven[i],eleven[j]=second,first
        else:
            out,incoming=(first,second) if first in eleven else (second,first)
            eleven[eleven.index(out)]=incoming
            if captain==out:captain=incoming
        candidate=copy.copy(state)
        candidate.starting_eleven=eleven;candidate.captain=captain
        self.view(candidate)
        self.state=candidate
        return list(eleven)

    def save(self,path):
        """[designed] Reuse the atomic explicit-data save writer."""
        if getattr(self,'match_pending',False):
            raise ValueError('Saving during a match is unavailable; cancel or finish first')
        try:
            save_state(Path(path),self.state,self.template_bytes)
        except (OSError,ValueError) as exc:
            raise ValueError(f'Cannot save game: {exc}') from exc
        self.save_path=Path(path);self.mark_saved()

    def resume(self,path):
        """[designed] Validate the complete saved continuation before publishing."""
        try:
            candidate,raw=load_save(Path(path))
            from_savestate(raw)
            continuation=to_savestate(candidate,original=raw)
            from_savestate(continuation);Savestate(continuation)
            self.view(candidate)
        except (OSError,ValueError,IndexError,KeyError,zipfile.BadZipFile,zlib.error,struct.error) as exc:
            raise ValueError(f'Cannot resume game: {exc}') from exc
        self.state=candidate;self.template_bytes=raw;self.save_path=Path(path);self.mark_saved()


def names_of(model,words):
    """[designed] Player names by player word."""
    return [model.goaldat.player_names[w] for w in words]
