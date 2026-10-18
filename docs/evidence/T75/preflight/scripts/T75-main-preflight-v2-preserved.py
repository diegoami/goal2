"""Planning-only runtime composition; never T75 implementation acceptance."""
import argparse,copy,hashlib,json,os,platform,sys,tempfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path.cwd();sys.path.insert(0,str(ROOT))
from PySide6.QtCore import Qt,QByteArray,qVersion
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QLabel,QPushButton
from PySide6.QtSvgWidgets import QSvgWidget
from goal2.desktop.model import DesktopModel
from goal2.desktop.window import ManagementWindow
from goal2.game.session_save import encode

p=argparse.ArgumentParser();p.add_argument('--mode',choices=['baseline','mock','wrong-display'],required=True);p.add_argument('--output',required=True);a=p.parse_args()
out=ROOT/a.output;out.mkdir(parents=True,exist_ok=False)
source_names=['goal2/desktop/window.py','goal2/desktop/pages.py','goal2/desktop/overview_page.py','goal2/desktop/model.py']
digest=lambda b:hashlib.sha256(b).hexdigest()
sources={n:digest((ROOT/n).read_bytes())for n in source_names}
r={'kind':'planning-only runtime mock, not T75 acceptance','probe_sha256':digest(Path(__file__).read_bytes()),'resources':{n:digest((ROOT/'.cache'/n).read_bytes())for n in ('e010-r0008-halftime.sav','GOAL.DAT')},'mode':a.mode,'platform':platform.platform(),'qt':qVersion(),'qpa':os.environ.get('QT_QPA_PLATFORM'),'requested_scale':os.environ.get('QT_SCALE_FACTOR'),'sources':sources,'steps':[]}
app=QApplication([])
binding=patch.object(ManagementWindow,'display_model',property(lambda self:self.model)) if a.mode=='wrong-display' else None
if binding:binding.start()
try:
 with tempfile.TemporaryDirectory(prefix='goal2-t75-main-')as folder:
  save=Path(folder)/'owned.g2save';m=DesktopModel.open(ROOT/'.cache/e010-r0008-halftime.sav',ROOT/'.cache/GOAL.DAT',save,country=4)
  if a.mode!='baseline':
   # Existing pure Quick function prepares an owned real completed-result input.
   from goal2.desktop.worker import play
   m.confirm(list(m.state.starting_eleven),m.state.starting_eleven[0],m.state.country_tactics)
   m.state=play(m.state,m.template_bytes)
   assert m.state.last_match is not None
  m.save(save);saved=save.read_bytes();encoded=encode(m.state,m.template_bytes)
  w=ManagementWindow(m);w.show();w.raise_();w.activateWindow();QTest.qWait(150)
  r['ratio']=w.devicePixelRatioF();w.resize(900,640 if r['ratio']>1 else 700);app.processEvents();r['initial_viewport']=[w.width(),w.height()];r['available']=[w.screen().availableGeometry().width(),w.screen().availableGeometry().height()]
  def active(target=None):
   if not w.isActiveWindow():w.raise_();w.activateWindow()
   assert QTest.qWaitForWindowActive(w,2000)
   if target is not None:target.setFocus();app.processEvents();QTest.qWait(150);assert app.focusWidget()is target
  def click(button,page=0):
   w.navigate(page);w.pages[page].ensureWidgetVisible(button);app.processEvents();active(button)
   QTest.mouseClick(button,Qt.MouseButton.LeftButton);app.processEvents()
  if a.mode=='baseline':
   assert hasattr(w,'overview_country_identity'),'country identity and overview hierarchy are absent'
  else:
   # Runtime-only mock, reusing the accepted model, widget owners and callbacks.
   w.overview_country_identity=QLabel();w.overview_country_identity.setWordWrap(True)
   w.overview_fixture=QLabel();w.overview_fixture.setWordWrap(True)
   w.overview_result=QLabel();w.overview_result.setWordWrap(True)
   w.overview_return=QPushButton('Return to active game')
   w.overview_return.clicked.connect(lambda:w.country.setCurrentIndex(w.country.findData(m.state.managed_country)))
   shirt=QSvgWidget();shirt.setFixedSize(80,88)
   shirt.load(QByteArray(b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 88"><path d="M24 8L8 20L16 36L24 32V80H56V32L64 36L72 20L56 8L48 16H32Z" fill="#bbcfc5" stroke="#081c18" stroke-width="2"/><path d="M25 38H55V44H25Z" fill="#f5f2e8"/><path d="M25 44H55V50H25Z" fill="#777777"/><path d="M25 50H55V56H25Z" fill="#333333"/></svg>'))
   for widget in (w.overview_country_identity,shirt,w.overview_fixture,w.overview_result,w.overview_return):w.pages[0].content.insertWidget(w.pages[0].content.count()-1,widget)
   original_refresh=w.refresh
   def refresh(*args,**kwargs):
    original_refresh(*args,**kwargs);display=w.display_model;v=display.view()
    w.overview_country_identity.setText(v['country_name']+' · neutral identity fallback')
    w.overview_fixture.setText(v['fixture']or'Standalone friendly / no supported fixture')
    w.overview_result.setText(display.result_text());w.overview_return.setEnabled(w.preview is not None)
   w.refresh=refresh;w.refresh()
   def select(number):
    active(w.country);QTest.keyClick(w.country,Qt.Key.Key_Down,Qt.KeyboardModifier.AltModifier,80);app.processEvents();QTest.qWait(100)
    view=w.country.view();assert view.isVisible(),'country popup did not open'
    QTest.keyClick(view,Qt.Key.Key_Home)
    for _ in range(number-1):QTest.keyClick(view,Qt.Key.Key_Down)
    assert view.currentIndex().row()==number-1,'popup request row differs from requested country'
    QTest.keyClick(view,Qt.Key.Key_Return);app.processEvents();QTest.qWait(60)
    assert not view.isVisible()and w.country.currentData()==number,'native country browse selected wrong country'
   # Deliberately invalid private draft; keep it across country previews.
   w.navigate(1);row=next(i for i in range(20)if w.table.item(i,0).checkState()==Qt.CheckState.Checked)
   w.table.setCurrentCell(row,0);w.pages[1].ensureWidgetVisible(w.table);app.processEvents();active(w.table)
   QTest.keyClick(w.table,Qt.Key.Key_Space);app.processEvents();dirty=copy.deepcopy(w.draft());assert len(dirty[0])==10,'invalid draft not established'
   longest=max(range(1,129),key=lambda n:len(m.goaldat.country_names[n]));countries=list(dict.fromkeys([5,13,longest]))
   for number in countries:
    select(number);expected=DesktopModel.open(ROOT/'.cache/e010-r0008-halftime.sav',ROOT/'.cache/GOAL.DAT',save,country=number);v=expected.view()
    assert w.overview_country_identity.text()==v['country_name']+' · neutral identity fallback','overview identity bound to active country instead of preview'
    assert w.title.text()==v['country_name']
    assert [w.table.item(i,1).text()for i in range(20)]==[x['name']for x in v['players']],'preview roster differs from independent model'
    assert w.overview_fixture.text()==(v['fixture']or'Standalone friendly / no supported fixture')
    assert w.overview_result.text()==expected.result_text()
    pool=expected.pool_view()['reserves'];assert [w.reserves.item(i,1).text()for i in range(80)]==[x['name']for x in pool]
    assert encode(m.state,m.template_bytes)==encoded and save.read_bytes()==saved
    assert w.active_draft==dirty,'country browse lost invalid active draft'
    w.navigate(0);app.processEvents()
    size=(900,640)if w.devicePixelRatioF()>1 else(900,700);w.resize(*size);app.processEvents()
    assert w.grab().save(str(out/('preview-'+str(number)+'.png')))
    r['steps'].append({'country':number,'name':v['country_name'],'all20_names':True,'pool80':True,'fixture_result':'independent model match','active_and_save_unchanged':True})
   click(w.overview_return);assert w.preview is None and w.draft()==dirty,'return did not recover invalid active draft'
   assert w.overview_result.text()==m.result_text()and encode(m.state,m.template_bytes)==encoded and save.read_bytes()==saved
   # Explicit replacement actions and Resume use the existing guarded callbacks.
   select(13);click(w.new);assert m.state.managed_country==13 and w.preview is None
   assert w.overview_country_identity.text().startswith(m.view()['country_name'])and w.overview_result.text()==m.result_text()
   select(5);click(w.friendly);assert m.state.managed_country==5 and m.state.campaign is None and w.preview is None
   select(13);click(w.resume,4)
   assert m.state.managed_country==4 and w.preview is None and encode(m.state,m.template_bytes)==encoded and save.read_bytes()==saved
   assert w.overview_country_identity.text().startswith(m.view()['country_name'])and w.overview_result.text()==m.result_text()
   r['result']='PASS';r['invalid_draft_return']=True;r['explicit_campaign_friendly_resume']=True;r['completed_result_restored']=True
  w.close();app.processEvents()
except BaseException as exc:
 r['failure']=str(exc);r['exception']=type(exc).__name__;raise
finally:
 if binding:binding.stop()
 assert sources=={n:digest((ROOT/n).read_bytes())for n in source_names},'product source changed during planning'
 r['source_unchanged']=True;(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
print('PASS planning mock: independent preview identity/20players/80pool/fixture/result; invalid-draft Return; explicit activation/Resume; state/save/source preserved; actual ratio',r['ratio'])
