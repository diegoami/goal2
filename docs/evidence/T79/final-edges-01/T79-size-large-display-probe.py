import json,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from goal2.desktop.model import DesktopModel
from goal2.desktop.window import ManagementWindow
app=QApplication([]);m=DesktopModel.open('.cache/e010-r0008-halftime.sav','.cache/GOAL.DAT','.cache/UNUSED-size-save',country=18);w=ManagementWindow(m);w.show();assert QTest.qWaitForWindowExposed(w,2000);QTest.qWait(150)
def take():return {'actual':[w.width(),w.height()],'minimum':[w.minimumSizeHint().width(),w.minimumSizeHint().height()],'maximized':w.isMaximized(),'window_state':w.windowState().value,'available':[w.screen().availableGeometry().width(),w.screen().availableGeometry().height()],'ratio':w.devicePixelRatioF()}
w.resize(900,640);QTest.qWait(150);before=take();w.showNormal();QTest.qWait(150);w.resize(900,640);QTest.qWait(150);after=take();print(json.dumps({'before_normal':before,'after_normal':after},indent=2));assert after['actual']==[900,640];w.close()
