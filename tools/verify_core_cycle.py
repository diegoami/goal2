#!/usr/bin/env python3
"""[designed: T123] Verify the private four-year source/machine/input/replay receipts."""
import argparse
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from goal2.core.cycle_evidence import verify


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory',type=Path)
    p.add_argument('--data',type=Path,default=ROOT/'.cache/GOAL.DAT')
    p.add_argument('--archaeology',type=Path)
    a=p.parse_args(argv)
    try:
        report=verify(a.directory,data_path=a.data,archaeology=a.archaeology)
    except Exception as error:
        print('FAIL G16 verification:',error,file=sys.stderr)
        return 1
    print('PASS G16 verification:',report['steps'],'steps, four annual exact replays, source-bound final stage2/season2')
    return 0


if __name__=='__main__':sys.exit(main())
