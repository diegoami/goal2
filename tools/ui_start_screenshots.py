"""[designed: T214, #667] Capture real imports, named saves and start choices at the task sizes, in private temporary data."""
import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def main():
    parser=argparse.ArgumentParser(description=__doc__.splitlines()[0]);parser.add_argument('output',type=Path);args=parser.parse_args()
    from PySide6.QtWidgets import QApplication
    from goal2.desktop import data_setup,fixed_page
    from goal2.desktop.model import DesktopModel
    from goal2.ui import saves,theme
    from goal2.ui.s01_import import ImportScreen
    from goal2.ui.s02_start import StartScreen
    from goal2.ui.s03_new_game import NewGameScreen
    from goal2.ui.s04_country import PlayersScreen
    from goal2.ui.s06_desk import ReimportScreen
    from goal2.ui.friendly import FriendlyScreen
    from goal2.ui.window import Window
    app=QApplication.instance() or QApplication([]);theme.install(app);args.output.mkdir(parents=True,exist_ok=True);records=[]
    with tempfile.TemporaryDirectory(prefix='goal2-start-shots-') as tmp:
        target=data_setup.paths(Path(tmp)/'goal2');window=Window(target)
        def shot(name):
            for width,height in ((1440,1080),(1440,900),(2110,1213),(1440,1061)):
                window.resize(width,height);window.show()
                for _ in range(3):app.processEvents()
                folder=args.output/f'{width}x{height}';folder.mkdir(exist_ok=True)
                window.grab().save(str(folder/name))
                records.append(dict(screen=type(window.current()).__name__,picture=name,requested=[width,height],actual=[window.width(),window.height()],problems=fixed_page.problems(window)))
        try:
            screen=window.push(ImportScreen(window,target,choose=lambda:None));shot('s01-import-first.png')
            missing=Path(tmp)/'empty';missing.mkdir();screen.offer(missing);shot('s01-import.png')
            screen.offer(ROOT/'.cache');shot('s02-start-empty.png')
            screen=window.push(NewGameScreen(window));shot('s03-new-game.png');screen.choose(6);shot('s03-managers-later.png');window.pop()
            model=DesktopModel.open(target.data/data_setup.TEMPLATE_NAME,target.goal_dat,Path(tmp)/'career',country=20)
            model.new_campaign(20,2028)
            for i in range(6):saves.write(model,target.saves,f'{i} Road to the championship')
            window.replace_home(StartScreen(window));shot('s02-start.png')
            bad=target.saves/'broken.g2game';bad.write_bytes(b'not a zip')
            start=window.current();start.read();start.cursor_row=next(i for i,e in enumerate(start.entries) if e.path==bad);start.press_y();shot('s02-start-failed.png');start.press_n()
            friendly=window.push(FriendlyScreen(window));friendly.choose();shot('s02-friendly.png');window.pop()
            window.push(PlayersScreen(window,model,'Holland'));shot('s04-players.png');window.pop()
            window.open_career(model);window.push(ReimportScreen(window,target,choose=lambda:None));shot('s01-reimport.png')
        finally:window.leaving=True;window.close();app.processEvents()
    (args.output/'layout-report.json').write_text(json.dumps(records,indent=2)+'\n')
    bad=[r for r in records if r['problems']];print(json.dumps(dict(captures=len(records),problems=bad),indent=2));return bool(bad)
if __name__=='__main__':raise SystemExit(main())
