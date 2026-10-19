import os,sys,json
from pathlib import Path
os.environ["QT_QPA_PLATFORM"]="windows";os.environ["QT_SCALE_FACTOR"]="1";os.environ["PYTHONDONTWRITEBYTECODE"]="1"
sys.path[:0]=['C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\fix241-production-7560fbc336fa-1792394491870788399', 'C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\fix241-production-7560fbc336fa-1792394491870788399\\.cache\\python-libs-T78', 'C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\fix241-production-7560fbc336fa-1792394491870788399\\.cache\\python-libs-T79']
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtCore import QCoreApplication,QEvent
from goal2.desktop.model import DesktopModel
from goal2.desktop.window import ManagementWindow
app=QApplication([])
m=DesktopModel.open('C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\fix241-production-7560fbc336fa-1792394491870788399\\.cache\\e010-r0008-halftime.sav','C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\fix241-production-7560fbc336fa-1792394491870788399\\.cache\\GOAL.DAT','C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\fix241-geometry-diagnostic-1792394789152055881\\never-save.g2save',country=13)
w=ManagementWindow(m);w.show();w.activateWindow();QTest.qWait(150)
def record(label):
 s=w.screen();print(json.dumps({'label':label,'actual':[w.width(),w.height()],'minimum':[w.minimumWidth(),w.minimumHeight()],'hint':[w.minimumSizeHint().width(),w.minimumSizeHint().height()],'state':str(w.windowState()),'screen':[s.availableGeometry().width(),s.availableGeometry().height()]}),flush=True)
try:
 for country in (13,14):
  w.country.setCurrentIndex(w.country.findData(country));app.processEvents();record('country-'+str(country))
  for width,height in ((1440,900),(1050,780),(900,700)):
   w.resize(width,height);QTest.qWait(80);record(str(country)+'-resize-'+str((width,height))+'-80ms')
   QTest.qWait(400);record(str(country)+'-settled')
 w.showNormal();w.move(0,0);w.resize(1440,900);QTest.qWait(400);record('showNormal-move-resize')
finally:
 w.close();w.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents();assert not app.topLevelWidgets()
