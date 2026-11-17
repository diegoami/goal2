"""[designed: T213, #667] Capture the route's first round before and after a quick match, at the task's sizes.

Uses the private career inputs in .cache; writes rebuilt UI pictures and geometry receipts only.
The managed result is the quick route's, independently of the watched-match screenshot journey.
"""
import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    from PySide6.QtWidgets import QApplication
    from goal2.desktop import data_setup, fixed_page, worker
    from goal2.desktop.model import DesktopModel
    from goal2.ui import theme
    from goal2.ui.s14_round import RoundScreen
    from goal2.ui.window import Window
    app = QApplication.instance() or QApplication([])
    theme.install(app)
    args.output.mkdir(parents=True, exist_ok=True)
    records = []
    with tempfile.TemporaryDirectory(prefix='goal2-round-shots-') as folder:
        model = DesktopModel.open(ROOT/'.cache/e010-r0008-halftime.sav', ROOT/'.cache/GOAL.DAT', Path(folder)/'career',country=20)
        model.new_campaign(20,2028)
        fixture = model.state.campaign.next_fixture.fixture_id
        before = model.round_before()
        window = Window(data_setup.paths(Path(folder)/'data'))
        try:
            for phase in ('before','after'):
                if phase == 'after':
                    model.state = worker.play(model.state,model.template_bytes)
                model.mark_saved()
                window.open_career(model)
                screen = window.push(RoundScreen(window,before,lambda:None,
                                    after=model.round_after(fixture) if phase=='after' else None))
                screen.timer.stop()
                while screen.arriving:
                    screen.arrive()
                for width,height in ((1440,1080),(1440,900),(2110,1213),(1440,1061)):
                    window.resize(width,height)
                    window.show()
                    for _ in range(3):app.processEvents()
                    path=args.output/f's14-round-{phase}-{width}x{height}.png'
                    window.grab().save(str(path))
                    records.append(dict(phase=phase,requested=[width,height],actual=[window.width(),window.height()],
                                        path=path.name,problems=fixed_page.problems(window)))
        finally:
            window.leaving=True
            window.close()
            app.processEvents()
    (args.output/'layout-report.json').write_text(json.dumps(records,indent=2)+'\n')
    print(json.dumps(dict(captures=len(records),problems=[r for r in records if r['problems']])))
    return any(r['problems'] for r in records)


if __name__=='__main__':raise SystemExit(main())
