"""Original pitch key dispatch with declared keyboard-ready input; no game routine replacement."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from goal2.engine.original_match.image import Image
from goal2.engine.original_match.machine import Machine

def probe(fixture):
    raw=fixture.read_bytes();image=Image.from_savestate(raw);rows=[]
    for flag in (0,1):
        for key in (0xB6,0xAF):
            m=Machine(image.memory,image.load);pointer=m.far(0xA923)
            m.write(pointer+0x41,bytes([flag]));m.write(pointer+0x3F,b'\x02')
            m.wr(0x79AE,1,1);m.wr(0xA976,key,1)
            def key_ready(replay):
                m.set_reg('ax',(m.reg('ax')&0xFF00)|1);m.return_from(True)
            m.at('214B:0723',key_ready)
            end=m.far_call('0791:9372',[],'0791:9544',ss=0x9000,sp=0x8000)
            assert not m._ports and len(m._handlers)==1
            assert m.run(end,timeout_s=2,fresh=True) is None
            after=m.read(pointer+0x41,1)[0];speed=m.read(pointer+0x3F,1)[0]
            assert after==flag
            assert speed==(1 if key==0xAF else 2)
            assert m.reg('sp')==0x8002
            assert m.rd(0x79AE,1)==0 and m.rd(0xA977,1)==key
            rows.append(dict(key=hex(key),replay_before=flag,replay_after=after,
                             speed_after=speed,stack_return='near ret +2',consumed=True))
    return dict(fixture_sha256=hashlib.sha256(raw).hexdigest(),
                scope='Actual original0791:9372, synthetic pushed-key fixture; only214B:0723 keyboard-ready returns true. Original game dispatch and pushed-key read run unchanged. Not a natural match.',rows=rows)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--fixture',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
    a=p.parse_args();a.out.write_text(json.dumps(probe(a.fixture),indent=2)+'\n');print('PASS four original pitch-key controls')
