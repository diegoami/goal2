"""[designed: T170af/#822] Current native decoder data, never a career.

[confirmed: archaeology87d92501, F008/F010/F037, original42BC/157D/4B61]
Both sides' records and the raw context belong to the verified stopped image.
Identity overlays alone may come from the owner. Readability grants no input
permission; the original decision and backend still own legal actions.
"""
from copy import deepcopy
from dataclasses import dataclass,field

from goal2.engine.original_match.image import Image
from goal2.engine.original_match import screens as S
from goal2.game import engine_tables
from goal2.game.state import GameState
from goal2.game.stopped_snapshot import StoppedMatchSnapshot


@dataclass(frozen=True)
class StoppedMatchView:
    snapshot: StoppedMatchSnapshot
    players: tuple=field(repr=False)
    countries: tuple=field(repr=False)
    squad: tuple
    sides: tuple
    marks: tuple
    rng_words: tuple
    _memory: bytes=field(repr=False)

    @classmethod
    def from_packet(cls,packet,*,request,decision,managed_country,data):
        snapshot=StoppedMatchSnapshot.from_packet(packet,request=request,decision=decision,
            managed_country=managed_country,data=data)
        image=Image.from_state(snapshot.state,engine_tables.load())
        sides=(image.rd(0x9B34),image.rd(0x9B36));side=sides.index(managed_country)
        marks=tuple(image.rd(S.MARKING-2+40*side+2*slot) for slot in range(1,21))
        return cls(snapshot,tuple(image.players()),tuple(image.countries()),tuple(image.squad(managed_country)),
            sides,marks,(image.rd(0x7B62),image.rd(0x8336)),image.memory_component())

    @property
    def managed_country(self):return self.snapshot.managed_country

    @property
    def eleven(self):return self.squad[:11]

    @property
    def bench(self):return self.squad[11:]

    @property
    def opponents(self):
        raw=self.countries[self.sides[1-self.sides.index(self.managed_country)]]
        return tuple(int.from_bytes(raw[i:i+2],'little') for i in range(0,40,2))

    @property
    def team_context(self):return self.snapshot.data['team_context']

    def record(self,word):
        if type(word) is not int or not 0<=word<len(self.players):raise ValueError('invalid current player word')
        return self.players[word]

    def available(self,word):
        raw=self.record(word)
        return bool(word) and 0<raw[14]<128 and not raw[16]&0xA4

    def marking_word(self,word):
        self.record(word)
        if not word or word not in self.squad:raise ValueError('player has no current squad marking slot')
        return self.marks[self.squad.index(word)]

    def display_state(self,identities=None):
        """Detached full current records/memory; no old campaign/roster is copied."""
        state=GameState(list(self.players),list(self.countries),self.managed_country,list(self.squad),
            *self.rng_words,{},b'',self._memory,starting_eleven=list(self.eleven),
            country_tactics=self.countries[self.managed_country][0x2D])
        if identities is not None:
            state.player_renames=deepcopy(identities.player_renames);state.manager_name=identities.manager_name
        return state
