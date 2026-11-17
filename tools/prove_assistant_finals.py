"""[designed: T183/#594, archaeology#725] Acquire the genuine finals refusal.

Load the retained, unmodified E031 G4B.GL in original DOSBox-X2024.03.01,
record ordinary keys and private savestates, then compare the PyPy assistant.
All original bytes and screen text belong in the owner's private output folder.
[confirmed: F031, original0791:DBFA/DC7E] A stage label alone is insufficient;
the real loaded manager's finals flag and actual refusal are both required.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SAVE_SHA256 = 'cfcea0ae6b01c2828e1c157ffd7036c2865dca301d9698586ea8015548e4f293'
FIXTURE_NAME = 'T183-finals-G4B-manager-v1.g2core'


def digest(value):
    return hashlib.sha256(value).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archaeology', required=True, type=Path)
    parser.add_argument('--save', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    args.archaeology = args.archaeology.resolve()
    args.save = args.save.resolve()
    out = args.out.resolve()
    assert digest(args.save.read_bytes()) == SAVE_SHA256, 'E031 G4B.GL differs'
    out.mkdir(parents=True, exist_ok=False)  # Prior acquisitions remain immutable.
    sys.path.insert(0, str(args.archaeology/'runtime/driver'))
    sys.path.insert(0, str(ROOT))
    import driver
    from goal2.core import Core
    from goal2.engine.original_match import Image
    from goal2.game import engine_tables
    from goal2.tests.pypy_engine import call
    from goal2.tests.test_best_twenty_t183a import records

    # Private Xvfb, never the owner's visible desktop or a dummy SDL display.
    os.environ.pop('SDL_VIDEODRIVER', None)

    class SavedDriver(driver.Driver):
        def _start_xvfb(self):
            shutil.copy2(args.save, self.game_dir/'G4B.GL')
            super()._start_xvfb()

    d = SavedDriver({'cycles': 'fixed 8000'}, workdir=out/'runtime',
                    game_dir=out/'game', mapper='nohost')
    rows, blobs = [], {}

    def observe(label, key=None):
        if key:
            d.keys(key)
            d.settle(rows[-1]['screen_sha256'], timeout=8, what=label)
        _, state, blob = d.read()
        screen = state.screen()
        (out/(label+'.sav')).write_bytes(blob)
        blobs[label] = blob
        rows.append(dict(label=label, key=key, sha256=digest(blob),
                         screen_sha256=screen.digest(), text=screen.text()))
        (out/'trace.json').write_text(json.dumps(rows, indent=2)+'\n')
        print(label, key, screen.digest(), flush=True)

    try:
        d.launch()
        observe('title')
        observe('load-list', 'y')
        observe('loaded', 'Return')
        # [confirmed: original manager menu, core.driver.MENU_TARGETS] Squad
        # is item5; the fresh loaded menu highlights item1 (team info).
        for number in range(4):
            observe(f'down-{number+1}', 'Down')
        observe('select-team', 'Return')
        observe('refusal', 'Insert')
        observe('acknowledged', 'Return')
        observe('manager-return', 'Escape')
    finally:
        d.terminate()
        (out/'driver-events.json').write_text(json.dumps(d.events, indent=2)+'\n')

    def core(label):
        return Core.start(blobs[label], goal_dat=ROOT/'.cache/GOAL.DAT').core

    before, selected, refusal, after, returned = [core(label) for label in
        ('loaded', 'select-team', 'refusal', 'acknowledged', 'manager-return')]
    assert before.wait.kind == returned.wait.kind == 'manager-menu'
    assert before.wait.view['item'] == 1
    assert selected.wait.kind == after.wait.kind == 'select-squad'
    assert refusal.wait.kind == 'squad-change-refused'
    assert refusal.wait.view == dict(message='cannot alter squad during finals', why='finals')
    tables = engine_tables.load()
    image = Image.from_memory_component(before.wait.state.memory_component())
    game = image.far(0xA923)
    manager = image.memory[game+1]
    assert manager == 1 and image.memory[game+0x13+manager] == 1
    value = image.state(tables)
    import copy
    unchanged = copy.deepcopy(value)
    answer = call('goal2.tests.test_best_twenty_t183a:native', value)
    assert value == unchanged
    assert answer['allowed'] is False and answer['refusal'] == 'finals'
    assert answer['recruited'] == []
    expected = records(Image.from_memory_component(after.wait.state.memory_component()))
    actual = records(Image.from_state(answer['state'], tables))
    assert actual == expected, 'Full original/native records/order/RNG differ'
    picked = records(Image.from_memory_component(selected.wait.state.memory_component()))
    assert expected == picked, 'Refusal/acknowledgement changed original records'
    assert len(set(answer['squad']+answer['pool'])) == 100
    assert answer['calls']['1771:52CC'] == answer['calls']['0791:DC7E'] == 1
    fixture = before.save()
    (out/FIXTURE_NAME).write_bytes(fixture)
    report = dict(
        schema='goal2/T183-finals-native/1', save_sha256=SAVE_SHA256,
        acquisition_source='E031 g1 G4B.GL: World Cup2030 wins over Chile and Zambia, before Germany',
        source_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=args.archaeology, text=True).strip(),
        driver_sha256=digest((args.archaeology/'runtime/driver/driver.py').read_bytes()),
        producer_sha256=digest(Path(__file__).read_bytes()),
        dosbox_version=driver.dosbox_version_of(driver.dosbox_x()),
        trace=[{k: v for k, v in row.items() if k != 'text'} for row in rows],
        fixture=dict(name=FIXTURE_NAME, sha256=digest(fixture), bytes=len(fixture)),
        manager=manager, finals=1, refusal=answer['refusal'], allowed=False, recruited=0,
        equality={key: digest(value if isinstance(value, bytes) else
                             json.dumps(value, separators=(',', ':')).encode())
                  for key, value in expected.items()},
        unchanged_after_select_team=True, unchanged_native_input=True,
        calls={key: answer['calls'][key] for key in ('1771:52CC', '0791:DC7E')},
        boundary='Native finals refusal evidence only; no current-UI projection or full T183/m3 completion.')
    (out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
