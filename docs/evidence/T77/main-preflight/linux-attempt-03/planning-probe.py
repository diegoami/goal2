"""[designed: T77] Planning runtime mock only; no product/source changes."""
import argparse,copy,hashlib,json,sys,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tools/desktop-ui'))
p=argparse.ArgumentParser();p.add_argument('--mode',choices=['baseline','mock','filter-mutates'],required=True);p.add_argument('--output',required=True);p.add_argument('--template',default=str(ROOT/'.cache/e010-r0008-halftime.sav'));p.add_argument('--data',default=str(ROOT/'.cache/GOAL.DAT'));a=p.parse_args()
out=Path(a.output);out.mkdir(parents=True,exist_ok=False)
from PySide6.QtCore import Qt,QCoreApplication,QEvent,qVersion
from PySide6.QtWidgets import QApplication,QLabel,QComboBox
from PySide6.QtTest import QTest
from goal2.desktop.model import DesktopModel
from goal2.desktop.window import ManagementWindow
from goal2.game import campaign_pool
from goal2.game.session_save import encode
from navigation import reveal
app=QApplication([]);w=None;errors=[];oldhook=sys.excepthook
sys.excepthook=lambda k,e,t:errors.append(''.join(traceback.format_exception(k,e,t)))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
sources={str(p.relative_to(ROOT)):digest(p) for p in sorted((ROOT/'goal2/desktop').glob('*.py'))}
r={'mode':a.mode,'planning_only':True,'limitations':['Runtime mock does not establish final product layout or Windows acceptance.','No real worker, preview, standalone, unavailable or closed-window refusal exercised.'],'sources_before':sources,'resources':{x:digest(Path(getattr(a,x))) for x in ('template','data')},'qt':qVersion(),'qpa':app.platformName(),'captures':[]}
try:
 m=DesktopModel.open(a.template,a.data,out/'owned.g2save',country=14);m.confirm(list(m.state.starting_eleven),261,m.state.country_tactics);m.save(m.save_path);saved=m.save_path.read_bytes()
 w=ManagementWindow(m);w.show();w.activateWindow();QTest.qWait(100)
 if a.mode!='baseline':
  layout=w.pool_panel.layout();w.pool_outgoing=QComboBox();w.pool_outgoing.setObjectName('poolOutgoing');w.pool_outgoing.setAccessibleName('Outgoing squad player')
  for word in m.state.managed_squad:w.pool_outgoing.addItem(f'{word} · {m.goaldat.player_names[word]}',word)
  layout.insertWidget(1,w.pool_outgoing)
  for name in ('poolDetail','exchangeSummary','poolPolicy'):
   label=QLabel();label.setObjectName(name);label.setWordWrap(True);label.setTextFormat(Qt.TextFormat.PlainText);label.setAccessibleName(name);setattr(w,name,label);layout.insertWidget(layout.count()-1,label)
  def update(*unused):
   index=w.reserves.currentRow();incoming=w.reserves.item(index,0).data(Qt.ItemDataRole.UserRole) if index>=0 and w.reserves.item(index,0) else None
   rows=m.pool_view()['reserves'] if m.state.campaign else [];row=next((x for x in rows if x['id']==incoming),None)
   text=(f"Incoming · {row['name']} · ID {incoming}\nPosition {row['position']} · {row['position_group']} · Ability {row['ability']} · Energy {row['energy']} · Confidence {row['confidence']}\nAvailability: "+(', '.join(row['availability']['reasons']) or 'Available')) if row else 'No incoming reserve selected'
   w.poolDetail.setText(text);word=w.pool_outgoing.currentData();w.exchangeSummary.setText(f'Outgoing · {word} · {m.goaldat.player_names[word]}\n'+(f'Incoming · {incoming} · {row["name"]}' if row else 'No incoming reserve selected'))
   w.poolPolicy.setText(m.pool_view()['window']['reason'] if m.state.campaign else 'Campaign required')
  def combo(index):
   word=w.pool_outgoing.itemData(index)
   for row in range(w.table.rowCount()):
    if w.table.item(row,0).data(Qt.ItemDataRole.UserRole)==word:w.table.setCurrentCell(row,1);break
   update()
  def table(row,*unused):
   if row>=0:
    word=w.table.item(row,0).data(Qt.ItemDataRole.UserRole);w.pool_outgoing.setCurrentIndex(w.pool_outgoing.findData(word))
  w.pool_outgoing.currentIndexChanged.connect(combo);w.table.currentCellChanged.connect(table);w.reserves.currentCellChanged.connect(update)
  def filtered(*unused):
   w.reserves.clearSelection();w.reserves.setCurrentCell(-1,-1)
   if a.mode=='filter-mutates' and w.search.text():m.state.rng_seed_7b62=(m.state.rng_seed_7b62+1)&65535
   update()
  w.search.textChanged.connect(filtered);w.position.currentIndexChanged.connect(filtered);combo(0);update()
 assert w.findChild(QLabel,'poolDetail') is not None and w.findChild(QLabel,'exchangeSummary') is not None,'focused incoming detail/exchange summary absent'
 def focus(widget):
  reveal(widget);widget.setFocus();app.processEvents();assert app.focusWidget() is widget,'keyboard focus missing'
 def search(text):
  focus(w.search);QTest.keyClick(w.search,Qt.Key.Key_A,Qt.KeyboardModifier.ControlModifier);QTest.keyClicks(w.search,text);app.processEvents()
 target=next(x for x in m.pool_view()['reserves'] if x['id']==2561);before=encode(m.state,m.template_bytes);before_state=copy.deepcopy(m.state);draft=copy.deepcopy(w.draft())
 search(target['name'].swapcase());focus(w.position);QTest.keyClick(w.position,Qt.Key.Key_Home)
 for _ in range(target['position']+1):QTest.keyClick(w.position,Qt.Key.Key_Down)
 assert m.state==before_state,'search/filter changed complete state or RNG'
 assert encode(m.state,m.template_bytes)==before,'search/filter changed encoded state or RNG'
 assert w.draft()==draft and m.save_path.read_bytes()==saved,'filter changed draft/save'
 assert w.reserves.currentRow()==-1 and 'No incoming' in w.poolDetail.text(),'hidden selection was not explicitly cleared'
 ids=[w.reserves.item(i,0).data(Qt.ItemDataRole.UserRole) for i in range(w.reserves.rowCount())];focus(w.reserves);w.reserves.setCurrentCell(ids.index(2561),1);app.processEvents()
 assert w.pool_outgoing.currentData()==261 and '2561' in w.exchangeSummary.text() and '261' in w.exchangeSummary.text(),'full identity summary wrong'
 assert all(str(target[k]) in w.poolDetail.text() for k in ('id','name','ability','energy','confidence','position_group')),'raw detail omitted values'
 # [designed] Dirty private tactics are discarded by the existing exchange refresh.
 w.tactics[0][1].toggle();assert w.draft()!=(m.state.starting_eleven,m.state.captain,m.state.country_tactics)
 expected=copy.deepcopy(m.state);campaign_pool.exchange(expected,261,2561);records=list(m.state.players);seeds=(m.state.rng_seed_7b62,m.state.rng_seed_8336)
 for width,height in ((1440,900),(1050,780),(900,700),(900,640)):
  w.resize(width,height);app.processEvents();focus(w.exchange)
  for widget in (w.poolDetail,w.exchangeSummary,w.poolPolicy,w.exchange):
   reveal(widget);app.processEvents();assert widget.width()>0 and widget.height()>0 and widget.isVisible(),'mock control invisible'
  focus(w.exchange);assert w.exchange.hasFocus(),'action focus lost';name=f'{width}x{height}.png';w.grab().save(str(out/name));r['captures'].append({'file':name,'size':[w.width(),w.height()],'ratio':w.devicePixelRatioF(),'detail_height':w.poolDetail.height(),'detail_width':w.poolDetail.width(),'detail_size_hint':[w.poolDetail.sizeHint().width(),w.poolDetail.sizeHint().height()],'font_height':w.poolDetail.fontMetrics().height(),'action_focus':w.exchange.hasFocus()})
 focus(w.exchange);QTest.keyClick(w.exchange,Qt.Key.Key_Space);app.processEvents();assert not errors,errors
 assert m.state==expected,'exchange differs from independent campaign_pool exchange';assert m.state.players==records and seeds==(m.state.rng_seed_7b62,m.state.rng_seed_8336),'records/RNG changed'
 assert m.state.captain==2561 and 2561 in m.state.starting_eleven and w.draft()==(m.state.starting_eleven,m.state.captain,m.state.country_tactics),'repair/draft discard failed'
 assert m.save_path.read_bytes()==saved,'exchange wrote save implicitly'
 m.save(m.save_path);m.resume(m.save_path);assert m.state==expected,'save/resume changed membership/state'
 r['passed']=True
except BaseException as exc:
 r['passed']=False;r['failure']=str(exc);r['traceback']=traceback.format_exc();raise
finally:
 if w is not None:w.close();w.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents()
 sys.excepthook=oldhook;r['callback_exceptions']=errors;r['sources_after']={x:digest(ROOT/x) for x in sources};r['sources_unchanged']=r['sources_before']==r['sources_after'];(out/'report.json').write_text(json.dumps(r,indent=2)+'\n');app.shutdown()
