import json,sys,tempfile
from pathlib import Path
root=Path.cwd();sys.path[:0]=[str(root),str(root/'tools/desktop-ui')]
from PySide6.QtWidgets import QApplication
from goal2.desktop.model import DesktopModel
from goal2.desktop.window import ManagementWindow
from match_handoff_scenario import quick_decisions
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=False);app=QApplication([]);r={'captures':[]}
with tempfile.TemporaryDirectory() as f:
 m=DesktopModel.open(root/'.cache/e010-r0008-halftime.sav',root/'.cache/GOAL.DAT',Path(f)/'owned.g2save',country=4);m.save(m.save_path);w=ManagementWindow(m);w.show();app.processEvents()
 try:quick_decisions(w,app,out,r);r['result']='PASS'
 finally:w.close();app.processEvents();(out/'report.json').write_text(json.dumps(r,indent=2)+'\n')
print('PASS actual quick halftime/Continue/two-window close')
