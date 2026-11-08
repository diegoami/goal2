"""Same verified PyPy/engine server; observe menu reads without changing keys or state."""
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from goal2.engine.original_match.match import Match,SITE_MENU,SITE_SELECT
real=Match._key_for
path=Path(os.environ['GOAL2_TACTICS_TRACE'])
def describe(m):
 p=m._menu
 return None if p is None else dict(side=p.side,steps=list(p.steps),screen=p.in_screen,tactics=dict(p.tactics),edit=getattr(p,'edit_only',False),presses=p.presses)
def read(m,site):
 before=describe(m);key=real(m,site)
 if m.st.get('menu_context')=='pause' and site in (SITE_MENU,SITE_SELECT):
  row=dict(site=site,key=key,minute=m.st['minute'],before=before,after=describe(m),side=m.side,managed=m.opts['managed'],
   readonly=m.m.rd(0xC20,1),menu=m.m.rd(0xC1F,1),countries=[m.m.rd(0x9B34),m.m.rd(0x9B36)],
   actual_tactics=m._tactics(),editing_select=m.st.get('editing_select'),editing_menu=m.st.get('editing_menu'))
  with path.open('a') as f:f.write(json.dumps(row)+'\n')
 return key
Match._key_for=read
from goal2.game import engine_server
raise SystemExit(engine_server.main())
