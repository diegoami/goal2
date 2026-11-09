"""[designed: T186; T209] Run the real UI journey and inspect every view at three window sizes.

    QT_QPA_PLATFORM=offscreen python3 tools/ui_readability_screenshots.py DIR [--no-docs]

The original fixtures stay in ignored cache. Synthetic bulletin/help pages are explicitly labelled by goal2.ui's existing
screenshot journey. Does not touch an owner's career.

It writes, into DIR, the journey's pictures, a capture of every view at each size and `layout-report.json` (the full
`fixed_page.problems` text of every capture). Unless `--no-docs`, it also regenerates the design's receipt
`docs/design/ui-2026-11/t186-layout-receipt.json` (the text size, the sizes, and every screen whose `problems` are not empty)
and the ten screens' pictures it names under `docs/design/ui-2026-11/images/` and `images/t186-large/`: those are the
tool's output and are never edited by hand. [designed: T209] The sizes are the 4:3 page at its own size (1440x1080, the
pictures), the standard 1440x900 window (the page is 1200x900 in it) and a large 2110x1213 window.

Exit code 1 when any capture has a problem: a screen that does not fit its page at the one 32 px text is a finding to report,
never something to hide (docs/tasks/T209.md).
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
DESIGN=ROOT/'docs'/'design'/'ui-2026-11'
RECEIPT=DESIGN/'t186-layout-receipt.json'
DIMENSIONS=((1440,1080),(1440,900),(2110,1213))
# The journey's pictures the design shows (README section 2), by journey file name -> image name. The picture is the capture
# at the first size; the large one is its sibling at the last size.
SELECTED={'s06-desk.png':'s06-hub','s15-match-menu.png':'s15-match-menu','s19-bench.png':'s19-bench',
          's19-bench-refused.png':'s19-bench-refused','s17-pitch.png':'s17-pitch','s20-board-full.png':'s20-board',
          's11-fixtures.png':'s11-fixtures','s14-round.png':'s14-round',
          's04-country.png':'s04-country','s07-team-info.png':'s07-team-info'}   # [designed: T211b] S04 and S07 are embedded in the README

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('output',type=Path)
    parser.add_argument('--no-docs',action='store_true',help='do not regenerate the receipt and the design images')
    args=parser.parse_args()
    from PySide6.QtWidgets import QApplication
    from goal2.desktop import fixed_page
    from goal2.ui import theme
    from goal2.ui.window import Window
    from goal2.ui.__main__ import screenshots
    args.output.mkdir(parents=True,exist_ok=True)
    original=Window.grab
    records=[]
    def grab(window,*values):
        app=QApplication.instance()
        entry=dict(screen=type(window.current()).__name__,phase=getattr(window.current(),'phase',None),sizes=[])
        before=window.size()
        base=original(window,*values)
        for width,height in DIMENSIONS:
            window.resize(width,height)
            for _ in range(3):app.processEvents()
            problems=fixed_page.problems(window)
            name=f"{len(records):02}-{entry['screen']}-{width}x{height}.png"
            path=args.output/name
            assert original(window).save(str(path))
            entry['sizes'].append(dict(width=width,height=height,problems=problems,path=name,sha256=sha(path)))
        window.resize(before)
        for _ in range(3):app.processEvents()
        records.append(entry)
        return base
    Window.grab=grab
    written=[]
    try:
        written=screenshots(args.output/'journey')
    finally:
        Window.grab=original
        # The journey takes one picture (one `grab`) per name, in order: each capture says which picture it belongs to.
        if len(records)==len(written):
            for record,path in zip(records,written):record['journey']=path.name
        (args.output/'layout-report.json').write_text(json.dumps(records,indent=2)+'\n')
    bad=[(r['screen'],r['phase'],s['width'],s['height'],s['problems']) for r in records for s in r['sizes'] if s['problems']]
    if not args.no_docs:publish(args.output,records,[path.name for path in written],theme.TEXT)
    print(json.dumps(dict(captures=len(records)*len(DIMENSIONS),problems=bad),indent=2))
    return bool(bad)

def publish(output,records,journey_names,text):
    """Regenerate the design's receipt and its ten pictures from the capture just made. A picture taken twice under one
    name is the last one, which is the file the journey leaves."""
    picture,large=DIMENSIONS[0],DIMENSIONS[-1]
    if len(records)!=len(journey_names):
        raise SystemExit(f'{len(records)} captures for {len(journey_names)} journey pictures: they no longer pair up')
    entries=dict(zip(journey_names,records))
    selected=[]
    for journey,name in SELECTED.items():
        entry=entries.get(journey)
        if entry is None:
            raise SystemExit(f'the journey picture {journey} was not taken: its screen was not visited')
        for size,folder in ((picture,'images'),(large,'images/t186-large')):
            capture=next(s for s in entry['sizes'] if (s['width'],s['height'])==size)
            target=DESIGN/folder/f'{name}.png'
            shutil.copyfile(output/capture['path'],target)
            selected.append(dict(screen=entry['screen'],phase=entry['phase'],width=size[0],height=size[1],
                                 path=str(target.relative_to(ROOT)).replace('\\','/'),sha256=capture['sha256']))
    commit=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True).stdout.strip()
    report=output/'layout-report.json'
    problems=[dict(picture=r['journey'],screen=r['screen'],phase=r['phase'],width=s['width'],height=s['height'],
                   count=len(s['problems']),first=s['problems'][:3]) for r in records for s in r['sizes'] if s['problems']]
    receipt=dict(source_commit=commit,normal_text_px=text,
                 capture_environment='Qt offscreen on this computer; native Windows/package checks separate',
                 dimensions=[list(d) for d in DIMENSIONS],captures=len(records)*len(DIMENSIONS),
                 all_geometry_checks_passed=not problems,producer='tools/ui_readability_screenshots.py',
                 producer_sha256=sha(__file__),screens_with_problems=problems,selected=selected,report_sha256=sha(report))
    RECEIPT.write_text(json.dumps(receipt,indent=2)+'\n')

if __name__=='__main__':raise SystemExit(main())
