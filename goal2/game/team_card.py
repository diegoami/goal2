"""[derived: F034–F038; T197] Accepted TEAM decoders over current GameState records.

Only immutable reads are supplied. The managed squad/tactics overlay is the same
current data the career UI edits; original tables and manager records remain in
its imported memory. Match performance retains the original two visibility gates.
"""
from goal2.game.player_card import _Memory


class TeamMemory(_Memory):
    def __init__(self,state):
        super().__init__(state)
        self.state=state

    @staticmethod
    def _range(index,limit,name):
        if type(index) is not int or not 0<=index<=limit:
            raise ValueError(f'{name} must be 0..{limit}')

    def read_ds(self,offset,size):
        if (type(offset) is not int or type(size) is not int or size<1
                or offset<0 or offset+size>65536):
            raise ValueError('display read is outside the data segment')
        return self.raw.ds_bytes(offset,size)

    def read_code(self,segment,offset,size):
        from goal2.engine.original_match.build import CODE_SIZE
        if (type(segment) is not int or not 0<=segment<=65535
                or type(offset) is not int or type(size) is not int or size<1
                or offset<0 or offset+size>65536 or segment*16+offset+size>CODE_SIZE):
            raise ValueError('display read is outside the code image')
        return self.raw.memory(self.raw._prog.load*16+segment*16+offset,size)

    def country_record(self,index):
        self._range(index,128,'country')
        record=bytes(self.state.countries[index])
        if len(record)!=191:raise ValueError('country record must be 191 bytes')
        if index==self.state.managed_country:
            words=self.state.managed_squad
            if len(words)!=20:raise ValueError('managed squad must contain twenty player words')
            for word in words:self._range(word,3060,'player')
            tactics=self.state.country_tactics
            self._range(tactics,255,'tactics')
            record=bytearray(record)
            record[:40]=b''.join(word.to_bytes(2,'little') for word in words)
            record[0x2D]=tactics
            record=bytes(record)
        return record

    def player_record(self,index):
        self._range(index,3060,'player')
        record=bytes(self.state.players[index])
        if len(record)!=20:raise ValueError('player record must be 20 bytes')
        return record

    def manager_record(self,index):
        self._range(index,134,'manager')
        pointer=self.read_ds(0xA91F,4)
        address=int.from_bytes(pointer[:2],'little')+16*int.from_bytes(pointer[2:],'little')
        return self.raw.memory(address+3*index,3)

    def panels(self,country):
        from goal2.engine.team_card.country import team_labels
        from goal2.engine.team_card.team_skills import team_skills
        from goal2.engine.team_card.team_performance import team_performance
        from goal2.engine.team_card.team_characteristics import team_characteristics
        self._range(country,128,'country')
        if country==0:raise ValueError('country must be 1..128')
        record=self.country_record(country);manager=record[0x2E]
        labels=team_labels(record,self.manager_record(manager) if manager else None,self.read_ds,self.read_code)
        sides=tuple(int.from_bytes(self.read_ds(off,2),'little') for off in (0x9B34,0x9B36))
        return {key:labels[key] for key in ('status','skill')} | {
            'team_skills':team_skills(record,self.player_record,self.country_record,self.manager_record,self.read_ds,self.read_code),
            'performance':team_performance(country,self.read_ds(0xC1E,1)[0],self.read_ds(0xC1F,1)[0],sides,
                                           self.country_record,self.player_record,self.read_ds),
            'characteristics':team_characteristics(record,self.player_record,self.read_ds),
        }
