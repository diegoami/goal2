import json,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from goal2.desktop.model import DesktopModel
from goal2.desktop.window import ManagementWindow
app=QApplication([]);m=DesktopModel.open('.cache/e010-r0008-halftime.sav','.cache/GOAL.DAT','.cache/UNUSED-size-save',country=18);w=ManagementWindow(m);w.show();QTest.qWait(150);w.showNormal();QTest.qWait(150);w.resize(900,640);QTest.qWait(150)
def size(s):return[s.width(),s.height()]
r={'ratio':w.devicePixelRatioF(),'actual':size(w.size()),'min':size(w.minimumSize()),'minimum_hint':size(w.minimumSizeHint()),'hint':size(w.sizeHint()),'available':size(w.screen().availableGeometry()),'central_min_hint':size(w.centralWidget().minimumSizeHint()),'pages':[]}
for p in w.pages:r['pages'].append({'object':p.objectName(),'min':size(p.minimumSize()),'minimum_hint':size(p.minimumSizeHint()),'hint':size(p.sizeHint()),'content_min_hint':size(p.widget().minimumSizeHint())})
print(json.dumps(r,indent=2));w.close()
