"""Planning feasibility only. Runtime --mock is never production acceptance."""
import argparse,json,sys,tempfile,os,hashlib,traceback,platform
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--template',required=True);p.add_argument('--data',required=True);p.add_argument('--mock',action='store_true');p.add_argument('--output',required=True);p.add_argument('--size',default='1050x780');p.add_argument('--control',choices=['wrong-rate','ignore-selection','missing-entry']);a=p.parse_args()
root=Path.cwd();sys.path.insert(0,str(root))
from PySide6.QtCore import Qt,QCoreApplication,QEvent,qVersion,QRect
from PySide6.QtWidgets import QApplication,QPushButton,QComboBox,QLabel,QStyle,QStyleOptionButton,QStyleOptionComboBox
from PySide6.QtTest import QTest
from goal2.desktop.model import DesktopModel
from goal2.desktop.window import ManagementWindow
from goal2.game.session_save import encode
callbacks=[]
def callback_error(kind,value,tb):
 callbacks.append(''.join(traceback.format_exception(kind,value,tb)));traceback.print_exception(kind,value,tb)
sys.excepthook=callback_error
app=QApplication([])
with tempfile.TemporaryDirectory(prefix='T85-planning-') as folder:
 m=DesktopModel.open(a.template,a.data,Path(folder)/'probe.g2save',country=4);m.save(m.save_path)
 w=ManagementWindow(m);calls=[]
 if a.mock:
  entry=QPushButton('Play a match');entry.setObjectName('playMatchEntry');w.pages[0].content.insertWidget(1,entry);entry.clicked.connect(lambda:w.navigate(3))
  rate=QComboBox();rate.setObjectName('watchPlaybackRate');rate.setAccessibleName('Watch playback speed')
  for label,value in [('Slow · 15 samples/s',15),('Normal · 60 samples/s',60),('Fast · 120 samples/s',120)]:rate.addItem(label,value)
  rate.setCurrentIndex(1);w.pages[3].content.insertWidget(1,rate)
  for page,name,text in [(0,'playEntryGuidance','Quick simulates a result. Watch shows the original friendly on the animated pitch. Confirm team edits before watching.'),(3,'watchPlaybackGuidance','Watch speed: Slow / Normal / Fast. Match results stay unchanged.')]:
   label=QLabel(text);label.setObjectName(name);label.setWordWrap(True);w.pages[page].content.insertWidget(2,label)
  w.watch.clicked.disconnect();w.watch.clicked.connect(lambda:calls.append(60 if a.control=='wrong-rate' else rate.currentData()))
  if a.control=='ignore-selection':rate.currentIndexChanged.connect(lambda:rate.setCurrentIndex(1))
  if a.control=='missing-entry':entry=None
 else:
  entry=w.findChild(QPushButton,'playMatchEntry');rate=w.findChild(QComboBox,'watchPlaybackRate')
  # Observe the actual product callback argument without starting an engine.
  w.watched.start=lambda **kw:calls.append(kw.get('playback_rate',60))
 before=encode(m.state,m.template_bytes);saved=m.save_path.read_bytes()
 out=Path(a.output);out.mkdir(parents=True,exist_ok=False);observations=[]
 def observe(widget,page,name):
  w.pages[page].ensureWidgetVisible(widget);app.processEvents();QTest.qWait(30)
  assert widget.visibleRegion().contains(widget.rect()),name+' clipped by parent/viewport'
  if isinstance(widget,QComboBox):
   option=QStyleOptionComboBox();widget.initStyleOption(option);bounds=widget.style().subControlRect(QStyle.ComplexControl.CC_ComboBox,option,QStyle.SubControl.SC_ComboBoxEditField,widget);text=widget.currentText()
  elif isinstance(widget,QPushButton):
   option=QStyleOptionButton();widget.initStyleOption(option);bounds=widget.style().subElementRect(QStyle.SubElement.SE_PushButtonContents,option,widget);text=widget.text()
  else:bounds=widget.contentsRect();text=widget.text()
  font=widget.fontMetrics();need=font.boundingRect(QRect(0,0,bounds.width(),5000),Qt.TextFlag.TextWordWrap,text) if isinstance(widget,QLabel) else QRect(0,0,font.horizontalAdvance(text),font.height())
  assert need.width()<=bounds.width() and need.height()<=bounds.height(),name+' text clipped'
  image=out/(name+'.png');assert w.grab().save(str(image));observations.append({'object':name,'text':text,'content':list(bounds.getRect()),'text_bounds':list(need.getRect()),'widget':list(widget.rect().getRect()),'visible':True,'font':widget.font().toString(),'capture':image.name,'sha256':hashlib.sha256(image.read_bytes()).hexdigest()})
 try:
  width,height=map(int,a.size.split('x'));w.resize(width,height);w.show();w.activateWindow();QTest.qWait(150)
  assert entry is not None,'primary Play a match entry absent'
  assert rate is not None,'Watch playback selector absent'
  assert QTest.qWaitForWindowActive(w,2000),'owned window did not activate'
  w.pages[0].ensureWidgetVisible(entry);entry.setFocus();app.processEvents();assert entry.hasFocus(),'entry focus absent';QTest.keyClick(entry,Qt.Key.Key_Space);app.processEvents()
  assert w.page_stack.currentIndex()==3,'entry input did not reach match route'
  assert not calls,'entry launched a match'
  w.navigate(0);observe(entry,0,'playMatchEntry');observe(w.findChild(QLabel,'playEntryGuidance'),0,'playEntryGuidance');w.navigate(3)
  observe(rate,3,'watchPlaybackRate');observe(w.findChild(QLabel,'watchPlaybackGuidance'),3,'watchPlaybackGuidance')
  assert [rate.itemData(i) for i in range(rate.count())]==[15,60,120] and rate.currentData()==60,'speed choices/default incorrect'
  w.pages[3].ensureWidgetVisible(rate);rate.setFocus();app.processEvents();assert rate.hasFocus(),'speed focus absent';QTest.keyClick(rate,Qt.Key.Key_Home);app.processEvents();assert rate.currentData()==15,'chosen Slow rate was ignored'
  QTest.mouseClick(w.navigation[0],Qt.MouseButton.LeftButton);QTest.mouseClick(entry,Qt.MouseButton.LeftButton);app.processEvents()
  assert rate.currentData()==15,'choice lost across navigation'
  w.refresh();assert rate.currentData()==15,'choice lost across redraw'
  # Production guard intentionally remains authoritative. Prepare fixture/confirm with real input in final scenario.
  if a.mock:w.watch.setEnabled(True)
  w.pages[3].ensureWidgetVisible(w.watch);QTest.mouseClick(w.watch,Qt.MouseButton.LeftButton);app.processEvents()
  assert calls==[15],f'wrong playback rate binding: {calls}'
  assert [w.width(),w.height()]==[width,height],'requested logical geometry not realized'
  assert not callbacks,callbacks
  assert before==encode(m.state,m.template_bytes) and saved==m.save_path.read_bytes(),'presentation changed saved state'
  assert w.grab().save(str(out/'planning.png'))
  (out/'planning.json').write_text(json.dumps({'planning_only':True,'observations':observations,'platform':platform.platform(),'python':sys.version,'available':list(app.primaryScreen().availableGeometry().getRect()),'runtime_mock':a.mock,'qpa':app.platformName(),'ratio':w.devicePixelRatioF(),'rate_calls':calls,'geometry':[w.width(),w.height()],'requested_scale':os.environ.get('QT_SCALE_FACTOR','1'),'qt':qVersion(),'callbacks':callbacks,'sources':{str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted((root/'goal2/desktop').glob('*.py'))},'production_acceptance':False},indent=2))
  print('PASS planning feasibility; NOT production acceptance')
 finally:
  w.close();w.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents();assert not app.topLevelWidgets();assert not callbacks,callbacks
