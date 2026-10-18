"""[designed: T76] Main planning-only runtime mock; never implementation acceptance."""
from pathlib import Path
import argparse,copy,hashlib,json,os,platform,sys,tempfile
p=argparse.ArgumentParser();p.add_argument('--mode',choices=['baseline','mock','truncated-id','eager-publish'],required=True);p.add_argument('--output',required=True);a=p.parse_args()
ROOT=Path.cwd();sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tools/desktop-ui'))
from PySide6.QtCore import Qt,QCoreApplication,QEvent,qVersion,QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QLabel,QWidget,QHBoxLayout
from goal2.desktop.model import DesktopModel
from goal2.desktop.window import ManagementWindow,TACTICS
from goal2.game.session_save import encode
from navigation import reveal
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
out=Path(a.output);out.mkdir(parents=True,exist_ok=False)
sources={str(x.relative_to(ROOT)):sha(x) for x in sorted((ROOT/'goal2/desktop').glob('*.py'))}
report={'tag':'[designed: T76] planning-only mock','mode':a.mode,'platform':platform.platform(),'qt':qVersion(),'sources':sources,'probe_sha256':sha(__file__),'resources':{n:sha(ROOT/'.cache'/n)for n in ('e010-r0008-halftime.sav','GOAL.DAT')},'steps':[],'captures':[]}
app=QApplication([]);report['qpa']=app.platformName()
try:
 with tempfile.TemporaryDirectory(prefix='T76-main-mock-')as d:
  save=Path(d)/'owned.g2save';m=DesktopModel.open(ROOT/'.cache/e010-r0008-halftime.sav',ROOT/'.cache/GOAL.DAT',save,country=13)
  m.confirm(list(m.state.starting_eleven),m.state.starting_eleven[0],m.state.country_tactics);m.save(save);saved=save.read_bytes()
  w=ManagementWindow(m);w.show();w.activateWindow();QTest.qWait(100);report['ratio']=w.devicePixelRatioF()
  if a.mode!='baseline':
   for key,name in [('lineup','lineupBoard'),('bench','benchBoard'),('detail','playerDetail')]:
    label=QLabel();label.setObjectName(name);label.setWordWrap(True);setattr(w,'mock_'+key,label);w.pages[1].content.insertWidget(1,label)
   footer=QWidget(w.pages[1]);footer.setObjectName('draftBar');bar=QHBoxLayout(footer);w.mock_draft=QLabel('Draft');w.mock_draft.setObjectName('draftState');bar.addWidget(w.mock_draft,1);bar.addWidget(w.cancel);bar.addWidget(w.confirm)
   w.pages[1].setViewportMargins(0,0,0,72)
   def place():footer.setGeometry(0,w.pages[1].height()-72,w.pages[1].width(),72);footer.raise_()
   def update(*unused):
    v=w.display_model.view();selected=w.selected_ids();rows=v['players'];captain=w.captain.currentData()
    groups={}
    for row in rows:
     if row['id']in selected:groups.setdefault(row['position'],[]).append(row['name']+(' (Captain)'if row['id']==captain else''))
    w.mock_lineup.setText('Starting XI '+str(len(selected))+'\n'+'\n'.join(k+': '+', '.join(names)for k,names in groups.items()))
    w.mock_bench.setText('Bench '+str(20-len(selected))+'\n'+', '.join(row['name']for row in rows if row['id']not in selected))
    i=max(0,w.table.currentRow());row=rows[i];w.mock_detail.setText('Player detail: '+row['name']+' · '+row['position']+' · Ability '+str(row['ability'])+' · Energy '+str(row['energy'])+' · Confidence '+str(row['confidence'])+' · '+(', '.join(row['availability']['reasons'])or'Available'))
    state=w.display_model.state;dirty=w.draft()!=(state.starting_eleven,state.captain,state.country_tactics);w.mock_draft.setText('Unconfirmed draft'if dirty else'Confirmed management');place()
   old=w.refresh
   def refresh(*args,**kw):old(*args,**kw);update()
   w.refresh=refresh;w.table.itemChanged.connect(update);w.table.currentCellChanged.connect(update);w.captain.currentIndexChanged.connect(update)
   for _,box in w.tactics:box.toggled.connect(update)
   w.refresh();footer.show()
  assert w.findChild(QLabel,'lineupBoard')is not None,'grouped XI/bench and draft hierarchy absent on baseline'
  w.navigate(1);app.processEvents()
  def focus(widget):
   if not w.isActiveWindow():w.raise_();w.activateWindow()
   assert QTest.qWaitForWindowActive(w,2000),'owned window did not become active'
   widget.setFocus();app.processEvents();assert app.focusWidget()is widget,'native focus not acquired: '+widget.objectName()
  def toggle(i):
   reveal(w.table);w.table.setCurrentCell(i,0);w.table.scrollToItem(w.table.item(i,0));focus(w.table);QTest.keyClick(w.table,Qt.Key.Key_Space);app.processEvents()
  def click(widget):
   w.navigate(1);app.processEvents();place();focus(widget);QTest.keyClick(widget,Qt.Key.Key_Return);app.processEvents()
  if a.mode=='truncated-id':
   original=w.selected_ids;w.selected_ids=lambda:[x&255 for x in original()]
  if a.mode=='eager-publish':
   w.tactics[0][1].toggled.connect(lambda *_:m.confirm(w.selected_ids(),w.captain.currentData(),w.draft()[2]))
  before=encode(m.state,m.template_bytes)
  wanted=list(range(250,261))
  for i in range(20):
   if (w.table.item(i,0).checkState()==Qt.CheckState.Checked)!=(241+i in wanted):toggle(i)
   assert encode(m.state,m.template_bytes)==before,'XI checkbox prematurely published active state'
  assert w.selected_ids()==wanted,'full integer player IDs were truncated'
  reveal(w.captain);focus(w.captain);QTest.keyClick(w.captain,Qt.Key.Key_End);app.processEvents();assert w.captain.currentData()==260
  assert tuple(e for e,_ in w.tactics)==tuple(e for e,_ in TACTICS)
  for element,box in w.tactics:
   assert box.text()==dict(TACTICS)[element]
   reveal(box);focus(box);QTest.keyClick(box,Qt.Key.Key_Space);app.processEvents()
   assert encode(m.state,m.template_bytes)==before,'tactic checkbox prematurely published active state'
   if not box.isChecked():QTest.keyClick(box,Qt.Key.Key_Space);app.processEvents()
   assert encode(m.state,m.template_bytes)==before,'tactic checkbox prematurely published active state'
  assert w.draft()==(wanted,260,255) and 'Unconfirmed' in w.mock_draft.text()
  click(w.confirm);assert m.state.starting_eleven==wanted and m.state.captain==260 and m.state.country_tactics==255
  snapshot=encode(m.state,m.template_bytes);toggle(19);click(w.confirm);assert encode(m.state,m.template_bytes)==snapshot and 'eleven' in w.status.text()
  click(w.cancel);assert w.draft()==(wanted,260,255)
  try:m.confirm(wanted,241,255)
  except ValueError as e:assert 'Captain' in str(e)
  else:raise AssertionError('invalid captain accepted')
  assert encode(m.state,m.template_bytes)==snapshot
  for word in (260,241):
   rec=bytearray(m.state.players[word]);rec[14]=0;rec[16]=0x88;m.state.players[word]=bytes(rec)
  w.refresh();snapshot=encode(m.state,m.template_bytes);toggle(0);assert 241 not in w.selected_ids(),'unavailable reserve added to XI';assert encode(m.state,m.template_bytes)==snapshot
  toggle(19);toggle(1);assert len(w.selected_ids())==11 and 260 not in w.selected_ids() and 242 in w.selected_ids();click(w.confirm);assert 260 not in m.state.starting_eleven
  assert 'Injured' in w.table.item(19,6).text()and'Suspended'in w.table.item(19,6).text()
  report['steps'].append({'full_ids':wanted,'captain':260,'all8bits':255,'private_draft':True,'invalid_count_captain':True,'unavailable_starter_removed':True,'unavailable_reserve_refused':True})
  for size in ([(900,640)]if report['ratio']>1 else[(1440,900),(1050,780),(900,700)]):
   w.resize(*size);w.navigate(1);app.processEvents();place();w.pages[1].verticalScrollBar().setValue(w.pages[1].verticalScrollBar().maximum());app.processEvents()
   assert footer.isVisible()and w.confirm.isVisible()and w.cancel.isVisible();assert footer.geometry().bottom()<=w.pages[1].height()
   for action in (w.confirm,w.cancel):focus(action);assert action.accessibleName()
   name='squad-'+str(size[0])+'x'+str(size[1])+'.png';assert w.grab().save(str(out/name));report['captures'].append({'path':name,'sha256':sha(out/name)})
  snapshot=encode(m.state,m.template_bytes);draft=copy.deepcopy(w.draft());m.match_pending=True;w.set_busy(True);assert not w.confirm.isEnabled()and not w.table.isEnabled();w.confirm_draft();assert encode(m.state,m.template_bytes)==snapshot;m.match_pending=False;w.set_busy(False)
  assert save.read_bytes()==saved;report['steps'].append({'busy_refusal':True,'save_unchanged':True,'persistent_actions_reachable':True});report['result']='PASS'
  w.close();w.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents();app.shutdown()
except BaseException as e:report['failure']=str(e);report['exception']=type(e).__name__;raise
finally:
 assert sources=={name:sha(ROOT/name)for name in sources},'source changed during mock'
 report['source_unchanged']=True;(out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS T76 planning-only mock:',a.mode,'ratio',report['ratio'])
