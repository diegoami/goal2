"""Synthetic wire control only; no original game or engine execution."""
import json,pathlib,sys,tempfile,threading,time
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path.cwd()))
from goal2.game.engine_process import EngineProcess
from goal2.game import engine_process
from goal2.engine.original_match import Fixture
WORKER=r'''
import os,pathlib,sys,time
from goal2.game.engine_server import read_packet,encode_packet
release=pathlib.Path(sys.argv[1]);mode=sys.argv[2];out=sys.stdout.buffer
def send(kind,value=None,payload=b''):
 out.write(encode_packet({'kind':kind,'value':value},payload));out.flush()
send('ready',{'implementation':'synthetic-wire-only','version':[0,0],'pid':os.getpid()})
while True:
 packet=read_packet(sys.stdin.buffer)
 if packet is None or packet[0]['op']=='quit':break
 if packet[0]['op']=='open':send('opened');continue
 if packet[0]['op']!='match':continue
 complete={'result':{},'events':[],'seeds':[1,2],'engine_year':1}
 send('complete',complete,b'synthetic-not-game-memory')
 while not release.exists():time.sleep(.001)
 if mode=='duplicate':send('complete',complete,b'synthetic-not-game-memory')
 send('settled')
'''
def probe(mode):
 replies=[];boundary=threading.Event();seen=False;original=engine_process.read_packet
 def read(*args,**kwargs):
  nonlocal seen
  if seen:boundary.set()  # prior packet has been handled before the reader asks for another
  packet=original(*args,**kwargs)
  if packet is not None and packet[0].get('kind')=='complete':seen=True
  return packet
 with tempfile.TemporaryDirectory(prefix='completion-boundary-') as folder:
  release=pathlib.Path(folder)/'release'
  client=EngineProcess(lambda k,v:replies.append((k,v)),command=[sys.executable,'-c',WORKER,str(release),mode])
  try:
   with patch.object(engine_process,'read_packet',read):
    client.open_encoded(b'synthetic-wire-game-placeholder')
    client.match('watched',Fixture(7,19,index=21,kind=1))
    assert boundary.wait(15),'first complete packet was not handled'
    early=any(k=='complete' for k,v in replies)
    assert not early,'completion became publishable before the transaction boundary'
    release.touch()
    deadline=time.monotonic()+15
    wanted='death' if mode=='duplicate' else 'complete'
    while not any(k==wanted for k,v in replies):
     assert time.monotonic()<deadline,mode
     time.sleep(.001)
    if mode=='duplicate':
     assert not any(k=='complete' for k,v in replies)
     assert any(k=='death' and 'no match running' in str(v.get('error')) for k,v in replies)
    else:assert sum(k=='complete' for k,v in replies)==1
    return {'mode':mode,'premature_publication':early,'public_completions':sum(k=='complete' for k,v in replies)}
  finally:
   release.touch(exist_ok=True);client.close()
if __name__=='__main__':print(json.dumps([probe(mode) for mode in ('good','duplicate')]))
