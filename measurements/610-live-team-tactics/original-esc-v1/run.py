"""Real original ESC at the root menu, not a guessed UI-policy assertion."""
import sys,json
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,'/home/diego/projects/m3-trackb/goal2')
from goal2.engine.original_match import Match,Fixture,Image,screens as S
raw=Path('/home/diego/projects/m3-trackb/goal2/.cache/e0afff6751747233-e006-1000-r0001.sav').read_bytes()
rows=[]
for target in ('pause','half_time'):
 m=Match(Image.from_savestate(raw),Fixture(7,19,index=21),managed=7,seed=0x1234,delay_byte=0,ports=[])
 m.opts['ticks']=True;requested=False;sent=False;before=None;info={}
 old=S.MenuPlan.menu_key
 def key(plan,item):
  global sent,before,info
  if m.st.get('menu_context')==target and plan.steps==['play']:
   sent=True;before=m.st['ticks'];info=dict(context=target,original_menu_used=m.m.rd(0xC1F,1),key=27,highlight=item)
   return plan.act(S.ESC)
  return old(plan,item)
 with patch.object(S.MenuPlan,'menu_key',key):
  for event in m.events():
   if event.kind=='tick' and sent:
    assert m.st['ticks']>before
    rows.append(dict(info,resumed=True,ticks_before=before,ticks_after=m.st['ticks']));break
   if target=='pause' and event.kind=='minute' and event.minute>=2 and not requested:
    requested=True;m.pause()
   if event.kind=='decision':m.answer()
  else:raise AssertionError('original Esc did not resume')
assert len(rows)==2 and all(r['original_menu_used']==1 for r in rows)
p=Path('/home/diego/projects/goal2-keep/m3-trackb-2026-11-05/original-menu-esc-v1.json')
with p.open('x') as f:json.dump(rows,f,indent=2);f.write('\n')
print(json.dumps(rows))
