"""[designed: T186] Run the real UI journey and inspect every view at two window sizes.
The original fixtures stay in ignored cache. Synthetic bulletin/help pages are explicitly
labelled by goal2.ui's existing screenshot journey. Does not touch an owner's career.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    from PySide6.QtWidgets import QApplication
    from goal2.desktop import fixed_page
    from goal2.ui.window import Window
    from goal2.ui.__main__ import screenshots
    args.output.mkdir(parents=True,exist_ok=True)
    original=Window.grab
    records=[]
    def grab(window,*values):
        app=QApplication.instance()
        entry=dict(screen=type(window.current()).__name__,phase=getattr(window.current(),'phase',None),sizes=[])
        base=original(window,*values)
        for width,height in ((1440,900),(2110,1213)):
            window.resize(width,height)
            for _ in range(3):app.processEvents()
            problems=fixed_page.problems(window)
            name=f"{len(records):02}-{entry['screen']}-{width}x{height}.png"
            path=args.output/name
            assert original(window).save(str(path))
            entry['sizes'].append(dict(width=width,height=height,problems=problems,path=name,
                                      sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        window.resize(1440,900)
        for _ in range(3):app.processEvents()
        records.append(entry)
        return base
    Window.grab=grab
    try:
        screenshots(args.output/'journey')
    finally:
        Window.grab=original
        (args.output/'layout-report.json').write_text(json.dumps(records,indent=2)+'\n')
    bad=[(r['screen'],s['width'],s['height'],s['problems']) for r in records for s in r['sizes'] if s['problems']]
    print(json.dumps(dict(captures=len(records)*2,problems=bad),indent=2))
    return bool(bad)

if __name__=='__main__':raise SystemExit(main())
