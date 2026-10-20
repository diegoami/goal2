"""[designed: T86] `python3 -m goal2.scenario walkthrough [--redraw N]` prints the record as JSON."""
import argparse
import json
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description='goal2 fictional scenario lane (T86); never a career')
    parser.add_argument('command', choices=['walkthrough'])
    parser.add_argument('--redraw', type=int, default=0, help='repeat every read-only call N times per step')
    args = parser.parse_args(argv)
    from goal2.scenario.walkthrough import run
    json.dump(run(redraw=args.redraw), sys.stdout, sort_keys=True, indent=1)
    sys.stdout.write('\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
