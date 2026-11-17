"""[designed: T170x/#768] Detached current data for the pre-match window.

[confirmed: T170s/T170w, archaeology87d92501] Preview state/2, rather than the
route boundary, owns current records and native marking words. This is a view,
not a career, native bootstrap, publication or backend mutation interface.
"""
from copy import deepcopy
from dataclasses import dataclass, field
from zlib import error as ZlibError

from goal2.engine.original_match.image import Image
from goal2.engine.original_match import screens as S
from goal2.game import engine_tables
from goal2.game.season import canonical_hash
from goal2.game.state import GameState


def _words(value, size=None, *, zero=False):
    if not isinstance(value, list) or (size is not None and len(value)!=size):
        raise ValueError('invalid pre-match word list')
    if any(type(w) is not int or not (0 if zero else 1)<=w<3061 for w in value):
        raise ValueError('invalid pre-match player word')
    nonzero=[w for w in value if w]
    if len(set(nonzero))!=len(nonzero):
        raise ValueError('duplicate pre-match player word')
    return tuple(value)


@dataclass(frozen=True)
class PrematchView:
    decision: int
    state_hash: str
    managed_country: int
    squad: tuple
    pool: tuple
    sides: tuple
    players: tuple = field(repr=False)
    countries: tuple = field(repr=False)
    marks: tuple
    setup: int
    in_match_menu: int
    rng_words: tuple
    _memory: bytes = field(repr=False)

    @classmethod
    def from_preview(cls, packet, data, *, decision, managed_country):
        """Verify one worker preview against its pending decision; retain no aliases."""
        if type(decision) is not int or decision<1 or type(managed_country) is not int or not 1<=managed_country<129:
            raise ValueError('invalid pre-match decision/country')
        if not isinstance(packet,dict) or packet.get('action')!='preview' or not isinstance(data,dict) or data.get('context')!='pre_match':
            raise ValueError('a current pre-match preview is required')
        meta=packet.get('preview')
        if (not isinstance(meta,dict) or set(meta)!={'schema','decision','state_hash'}
                or meta['schema']!='goal2/prematch-preview/1' or type(meta['decision']) is not int
                or meta['decision']!=decision):
            raise ValueError('pre-match preview decision mismatch')
        native=packet.get('state')
        if not isinstance(native,dict) or meta['state_hash']!=canonical_hash(native):
            raise ValueError('pre-match preview hash mismatch')
        try:
            image=Image.from_state(deepcopy(native),engine_tables.load())
            players=tuple(image.players());countries=tuple(image.countries())
        except (KeyError,TypeError,IndexError,ValueError,ZlibError) as exc:
            raise ValueError('invalid native pre-match state') from exc
        if any(len(p)!=20 for p in players) or any(len(c)!=191 for c in countries):
            raise ValueError('invalid pre-match record spans')
        squad=_words(data.get('eleven'),11,zero=True)+_words(data.get('bench'),9,zero=True)
        if len({w for w in squad if w})!=sum(bool(w) for w in squad):
            raise ValueError('duplicate squad membership')
        pool=_words(data.get('pool'),80,zero=True)
        if (set(pool)-{0})&(set(squad)-{0}) or tuple(image.squad(managed_country))!=squad:
            raise ValueError('pre-match roster mismatch')
        # [confirmed: F011, Match._pool at87d92501] Read the current manager's
        # made list, not the legacy career's assumed canonical reserve IDs.
        manager_at=image.far(0xA923)+1
        if not 0<=manager_at<len(image.memory):raise ValueError('invalid manager span')
        manager=image.memory[manager_at]
        base=image.rd(0x6D18+2*manager)
        at=image.far(0xA927)+2*base
        if not 0<=at<=len(image.memory)-160:raise ValueError('invalid pool span')
        native_pool=tuple(int.from_bytes(image.memory[i:i+2],'little') for i in range(at,at+160,2))
        if pool!=native_pool:raise ValueError('pre-match pool mismatch')
        sides=(image.rd(0x9B34),image.rd(0x9B36))
        if sides[0]==sides[1] or any(not 1<=c<129 for c in sides) or managed_country not in sides:
            raise ValueError('invalid pre-match sides')
        other=sides[1-sides.index(managed_country)]
        _words(image.squad(other),20,zero=True)
        context={'match_set_up':image.rd(0xC1E,1),'in_match_menu_used':image.rd(0xC1F,1),'sides':list(sides)}
        declared=data.get('team_context')
        if (not isinstance(declared,dict) or set(declared)!=set(context)
                or any(type(declared[k]) is not int for k in ('match_set_up','in_match_menu_used'))
                or not isinstance(declared['sides'],list) or any(type(c) is not int for c in declared['sides'])
                or declared!=context or type(data.get('tactics')) is not int
                or data['tactics']!=countries[managed_country][0x2D]):
            raise ValueError('pre-match context/tactics mismatch')
        expected=[[w,players[w].hex()] for w in squad if w]
        records,positions=data.get('player_records'),data.get('positions')
        if (not isinstance(records,list) or not isinstance(positions,list)
                or any(not isinstance(r,list) or len(r)!=2 or type(r[0]) is not int or type(r[1]) is not str for r in records)
                or any(not isinstance(r,list) or len(r)!=2 or any(type(v) is not int for v in r) for r in positions)
                or records!=expected or positions!=[[w,players[w][6]] for w in squad if w]):
            raise ValueError('pre-match current records mismatch')
        side=sides.index(managed_country)
        marks=tuple(image.rd(S.MARKING-2+40*side+2*slot) for slot in range(1,21))
        return cls(decision,meta['state_hash'],managed_country,squad,pool,sides,players,countries,
                   marks,context['match_set_up'],context['in_match_menu_used'],
                   (image.rd(0x7B62),image.rd(0x8336)),image.memory_component())

    @property
    def eleven(self):return self.squad[:11]

    @property
    def bench(self):return self.squad[11:]

    @property
    def opponents(self):
        country=self.sides[1-self.sides.index(self.managed_country)]
        raw=self.countries[country]
        return tuple(int.from_bytes(raw[i:i+2],'little') for i in range(0,40,2))

    @property
    def team_context(self):
        return {'match_set_up':self.setup,'in_match_menu_used':self.in_match_menu,'sides':list(self.sides)}

    def record(self,word):
        if type(word) is not int or not 0<=word<len(self.players):
            raise ValueError('invalid player word')
        return self.players[word]

    def available(self,word):
        raw=self.record(word)
        return bool(word) and 0<raw[14]<128 and not raw[16]&0xA4

    @property
    def captain_choices(self):return tuple(w for w in self.eleven if self.available(w))

    @property
    def marking_targets(self):return tuple(w for w in self.opponents[1:11] if self.available(w))

    def can_mark(self,word,*,pane='squad'):
        """[confirmed: original4B61] Setup + squad pane + available position>=2."""
        if pane not in ('squad','pool'):raise ValueError('invalid pre-match pane')
        self.record(word)
        return bool(self.setup and pane=='squad' and word in self.squad
                    and self.record(word)[6]>=2 and self.available(word))

    def marking_word(self,word):
        self.record(word)
        if word not in self.squad or not word:raise ValueError('player has no squad marking slot')
        return self.marks[self.squad.index(word)]

    def marking_goal(self,word):
        target=self.marking_word(word)
        return target if self.record(word)[16]&64 else None

    def own_override(self,word,element):
        if type(element) is not int or not 1<=element<=4:raise ValueError('own element must be1..4')
        raw=self.record(word)[15]
        return bool(raw&(1<<(element-1))) if raw&(1<<(element+3)) else None

    def own_value(self,word,element):
        value=self.own_override(word,element)
        country=self.record(word)[0]
        if not 0<=country<len(self.countries):raise ValueError('invalid player country')
        return bool(self.countries[country][0x2D]&(1<<(element-1))) if value is None else value

    def display_state(self,identities=None):
        """Fresh decoder-only state. No campaign/calendar or publication is fabricated."""
        view=GameState(list(self.players),list(self.countries),self.managed_country,list(self.squad),
                       *self.rng_words,{},b'',self._memory,starting_eleven=list(self.eleven),
                       country_tactics=self.countries[self.managed_country][0x2D])
        if identities is not None:
            view.player_renames=deepcopy(identities.player_renames)
            view.manager_name=identities.manager_name
        return view
