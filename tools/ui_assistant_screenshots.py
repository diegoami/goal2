"""[designed: T183c] Capture explicit assistant states from private current-career input.

Busy and unavailable are labelled UI controls. Completed/no-improvement images
come from actual PyPy requests; no original-game pixels are copied.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
SIZES=((1440,1080),(1440,900),(2110,1213))


def main():
    p=argparse.ArgumentParser(description=__doc__.splitlines()[0]);p.add_argument('output',type=Path)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
    from goal2.desktop import data_setup,fixed_page
    from goal2.desktop.model import DesktopModel
    from goal2.ui import theme
    from goal2.ui.window import Window
    from goal2.ui.s08_squad import open_squad
    from goal2.game import best_twenty_jobs
    spec=importlib.util.spec_from_file_location('density',ROOT/'docs/design/ui-2026-11/check_density.py')
    density=importlib.util.module_from_spec(spec);spec.loader.exec_module(density)
    app=QApplication.instance() or QApplication([]);theme.install(app)
    records=[]
    def wait(predicate):
        end=time.monotonic()+30
        while time.monotonic()<end:
            app.processEvents()
            if predicate():return
            QTest.qWait(10)
        raise RuntimeError('assistant capture did not complete')
    for width,height in SIZES:
        with tempfile.TemporaryDirectory() as tmp:
            model=DesktopModel.open(ROOT/'.cache/e010-r0008-halftime.sav',ROOT/'.cache/GOAL.DAT',Path(tmp)/'career.g2save',country=4)
            w=Window(data_setup.paths(Path(tmp)/'data'));w.resize(width,height);w.open_career(model);w.show()
            s=open_squad(w,model)
            folder=args.output/f'{width}x{height}';folder.mkdir(exist_ok=True)
            def shot(name,context):
                for _ in range(4):app.processEvents()
                path=folder/(name+'.png');assert w.grab().save(str(path))
                means=density.measure(path);minimum=min(min(row) for row in means)
                records.append({'picture':str(path.relative_to(args.output)),'context':context,
                    'requested':[width,height],'actual':[w.width(),w.height()],
                    'problems':fixed_page.problems(w),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                    'density_floor':density.DEFAULT_FLOOR,'minimum':minimum,'density_passed':minimum>=density.DEFAULT_FLOOR})
            try:
                shot('idle','No assistant request on screen entry')
                entered,release=threading.Event(),threading.Event();real=best_twenty_jobs.prepare
                def held(value):
                    entered.set()
                    if not release.wait(10):raise RuntimeError('busy capture control not released')
                    return real(value)
                with patch.object(best_twenty_jobs,'prepare',held):
                    try:
                        s.assistant();wait(entered.is_set)
                        shot('busy','Controlled held preparation; real explicit request, no publication')
                    finally:release.set()
                    wait(lambda:s._assistant_token is None)
                assert 'Recruited' in s.note.text(),s.note.text()
                shot('complete','Actual PyPy result atomically published')
                pid=model.assistant_jobs().shared.engine.pid
                s.assistant();wait(lambda:s._assistant_token is None)
                assert 'No stronger players' in s.note.text(),s.note.text()
                assert model.assistant_jobs().shared.engine.pid==pid
                shot('no-improvement','Actual repeated request on the same engine, no new recruits')
                model.state=copy.deepcopy(model.state);model.state.campaign.world=None
                s.assistant();wait(lambda:s._assistant_token is None)
                assert 'not available' in s.note.text(),s.note.text()
                shot('unavailable','Authored missing-current-calendar control, not an original refusal case')
            finally:
                w.leaving=True;w.close();app.processEvents()
    (args.output/'layout-report.json').write_text(json.dumps(records,indent=2)+'\n')
    bad=[r for r in records if r['problems'] or not r['density_passed']]
    print(json.dumps({'captures':len(records),'problems':bad},indent=2))
    return bool(bad)


if __name__=='__main__':raise SystemExit(main())
