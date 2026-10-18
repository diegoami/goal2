import json,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from goal2.desktop.model import DesktopModel
from goal2.desktop.window import ManagementWindow
app=QApplication([]);m=DesktopModel.open('.cache/e010-r0008-halftime.sav','.cache/GOAL.DAT','.cache/UNUSED-size-save',country=18);w=ManagementWindow(m);w.show();QTest.qWait(500)
r=[]
for i in range(10):
 w.showNormal();w.resize(900,640);QTest.qWait(250)
 props=subprocess.run(['xprop','-id',hex(int(w.winId())),'_NET_WM_STATE','WM_NORMAL_HINTS'],capture_output=True,text=True).stdout
 row={'attempt':i,'actual':[w.width(),w.height()],'min':[w.minimumSizeHint().width(),w.minimumSizeHint().height()],'maximized':w.isMaximized(),'window_state':w.windowState().value,'native_props':props};r.append(row)
 if row['actual']==[900,640]:break
print(json.dumps(r,indent=2));w.close();assert r[-1]['actual']==[900,640]
