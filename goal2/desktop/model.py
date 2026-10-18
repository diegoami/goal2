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


class DesktopModel:
    """[designed: T69] Own one active game; publish validated candidates only."""
    def __init__(self,goaldat,template_bytes,save_path):
        self.goaldat=goaldat;self.template_bytes=template_bytes
        self.save_path=Path(save_path);self.state=None

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

    def new_campaign(self,country):
        """[designed] Explicit new-game action, never a selector/redraw callback."""
        if type(country) is not int or not 1<=country<=128:
            raise ValueError('Country must be an integer from1 to128')
        candidate,_=start_opening_campaign(self.goaldat,self.template_bytes,managed_country=country,
                                         start_year=1990,seed_7b62=4660,seed_8336=33590)
        self.view(candidate)
        self.state=candidate

    def new_friendly(self,country):
        """[designed: T70] Explicit fresh standalone mode, no campaign ledger."""
        self.new_campaign(country)
        self.state.campaign=None

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
        for word in state.managed_squad:
            record=state.players[word]
            if len(record)!=20:
                raise ValueError('Invalid player record')
            rows.append({'id':word,'name':self.goaldat.player_names[word],
                         'position':groups[lines[record[6]]],'ability':record[4],'energy':record[14],
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

    def save(self,path):
        """[designed] Reuse the atomic explicit-data save writer."""
        if getattr(self,'match_pending',False):
            raise ValueError('Saving during a match is unavailable; cancel or finish first')
        try:
            save_state(Path(path),self.state,self.template_bytes)
        except (OSError,ValueError) as exc:
            raise ValueError(f'Cannot save game: {exc}') from exc
        self.save_path=Path(path)

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
        self.state=candidate;self.template_bytes=raw;self.save_path=Path(path)
