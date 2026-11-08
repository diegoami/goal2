"""Rebuilt tactics view resumed from the private UI-created T191 audit save."""
from pathlib import Path
import sys,os,json,hashlib
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));os.chdir(ROOT)
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt
from goal2.desktop import data_setup
from goal2.ui.window import Window
from goal2.ui.s10_team_tactics import TeamTacticsScreen
app=QApplication([]);target=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
w=Window(data_setup.Paths(target/'data-root'));w.resize(1440,900);w.show();w.start();app.processEvents();QTest.keyClick(w,Qt.Key.Key_Return);app.processEvents();QTest.keyClick(w,Qt.Key.Key_T);app.processEvents();assert isinstance(w.current(),TeamTacticsScreen)
for width,height in ((1440,900),(1800,1125),(2110,1213)):
 w.resize(width,height);app.processEvents();QTest.qWait(50);assert w.grab().save(str(out/f'tactics-{width}x{height}.png'))
(out/'capture-scope.json').write_text(json.dumps({'scope':'Rebuilt UI resumed from the private fresh-management-audit named save, not a match/season claim','characteristic_text':w.current().characteristics.text(),'source_sha256':hashlib.sha256((ROOT/'goal2/ui/s10_team_tactics.py').read_bytes()).hexdigest()},indent=2)+'\n')
w.leave()
