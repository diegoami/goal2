#!/usr/bin/env python3
"""[designed: T116] Same-input Qt/SDL throughput at an original speed selected only through original keys.

Run unchanged on the baseline and correction heads, with the same original state, drivers and frame count.
The output is metadata/timing only; no guest bytes are exported. Requires the desktop/watched dependencies.
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state',type=Path,default=ROOT/'.cache/e006-r0001-main.sav')
    p.add_argument('--frames',type=int,default=60)
    p.add_argument('--delay',type=int,choices=range(6),default=0)
    p.add_argument('--timeout',type=int,default=120)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    if not 1<=args.frames<=600 or not 1<=args.timeout<=600:p.error('frames and timeout must be 1..600')
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    from goal2.core import Core,views
    from goal2.core.driver import Driver,LEFT,RIGHT
    from goal2.desktop.core_model import CoreModel
    from goal2.desktop.core_window import CoreWindow
    from goal2.desktop.style import load_fonts
    app=QApplication.instance() or QApplication([]);load_fonts()
    data=args.state.read_bytes();d=Driver(Core.start(data).core)
    d.to_menu();d.round_start(watch=True);d.kick_off(watch=True)
    with tempfile.TemporaryDirectory(prefix='goal2-watch-benchmark-') as folder:
        model=CoreModel(d.core,None,Path(folder)/'unused.g2core')
        def speed():
            mem=views.Memory(model.state)
            return mem.byte(mem.far(views.GAME)+0x3F)
        for _ in range(5):
            if speed()==args.delay:break
            model.round_step('live_step',RIGHT if speed()>args.delay else LEFT)
        if speed()!=args.delay:raise RuntimeError('Original keys did not select the requested speed')
        out=dict(head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                 script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 state_sha256=hashlib.sha256(data).hexdigest(),initial_memory_sha256=model.memory_sha256(),
                 original_delay=args.delay,python=platform.python_version(),platform=platform.platform())
        w=CoreWindow(model);w.show();r=w.core_round;timing={}
        timer=QTimer();timer.setInterval(20)
        def check():
            viewer=r.viewer
            if viewer is None:return
            if viewer.frame_ack>=5 and not timing:timing.update(start=time.perf_counter(),first=viewer.frame_ack)
            if timing and viewer.frame_ack>=timing['first']+args.frames:
                elapsed=time.perf_counter()-timing['start'];frames=viewer.frame_ack-timing['first']
                out.update(frames=frames,seconds=elapsed,fps=frames/elapsed);app.quit()
        timer.timeout.connect(check);timer.start();QTimer.singleShot(args.timeout*1000,app.quit)
        app.exec();timer.stop();w.close()
        if 'fps' not in out:out['error']='Timed out before enough displayed acknowledgements'
        args.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
        return 0 if 'fps' in out else 1


if __name__=='__main__':raise SystemExit(main())
