import json,sys,os
from pathlib import Path
root=Path(sys.argv[1]);sys.path.insert(0,str(root));os.environ['QT_SCALE_FACTOR']='2';os.environ['QT_QPA_PLATFORM']='windows'
from PySide6.QtWidgets import QApplication,QStyleOptionButton,QStyle
from PySide6.QtTest import QTest
from goal2.desktop.model import DesktopModel
from goal2.desktop.window import ManagementWindow
app=QApplication([]);model=DesktopModel.open(root/'.cache/e010-r0008-halftime.sav',root/'.cache/GOAL.DAT',Path(__file__).parent/'owned.g2save',country=13);w=ManagementWindow(model);w.resize(900,640);w.show();w.navigate(1);QTest.qWait(100)
if len(sys.argv)>2:
 w.setStyleSheet(w.styleSheet()+'QWidget#draftBar QPushButton {border:3px solid #5a7c6e;} QWidget#draftBar QPushButton:focus {border:3px solid #ffe799;}');app.processEvents();w.pages[1].place_footer();app.processEvents()
rows=[]
for b in (w.confirm,w.cancel):
 b.setFocus();app.processEvents();opt=QStyleOptionButton();b.initStyleOption(opt);rect=b.style().subElementRect(QStyle.SubElement.SE_PushButtonContents,opt,b);rows.append(dict(text=b.text(),widget=[b.width(),b.height()],contents=[rect.width(),rect.height()],font_advance=b.fontMetrics().horizontalAdvance(b.text()),font=b.font().toString(),ratio=w.devicePixelRatioF()))
print(json.dumps(rows));w.close();assert all(r['font_advance']<=r['contents'][0] for r in rows),'focused footer caption clipped'
