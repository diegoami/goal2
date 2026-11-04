"""[designed: owner, T181 #575] Goal2's recorded goals and boards, beside the career saves.

A goal holds only samples already painted by S17. The rolling window is 600 samples: ten seconds at the normal
60 samples/s, covering the recent attack while keeping memory independent of match length [designed: T181].
Records are UTF-8 JSON, versioned and written atomically. No original goal or summary file is opened.
"""
from __future__ import annotations

from collections import deque
import copy
import json
import os
from pathlib import Path
import tempfile

from goal2.ui.saves import NAME_MAX, SaveError, clean_name, file_stem

WINDOW_FRAMES = 600
FORMAT = 'goal2-recording'
SUFFIXES = {'goal': '.g2goal', 'summary': '.g2summary'}
MAX_BYTES = 4 * 1024 * 1024   # [designed: T181] bounded even when a damaged record is selected


class RecordError(ValueError):
    """A recording could not be saved or opened; the player stays on the current screen."""


class GoalWindow:
    def __init__(self):
        self.rows = deque(maxlen=WINDOW_FRAMES)

    def painted(self, frame):
        if frame is not None and (not self.rows or frame['sequence'] > self.rows[-1]['sequence']):
            self.rows.append(copy.deepcopy(frame))

    def samples(self):
        return copy.deepcopy(list(self.rows))

    def clear(self):
        self.rows.clear()


class Playback:
    """[designed: T181] Advance once each selected sample was painted; repainting never touches the live bridge."""
    def __init__(self, frames):
        self.frames = copy.deepcopy(frames)
        self.index = -1
        self.frame = None
        self.drawn = -1
        self.next_frame = 0
        self.finished = not self.frames

    def painted(self, sequence):
        if self.frame is not None and sequence == self.frame['sequence']:
            self.drawn = self.index

    def advance(self, now, rate):
        if self.finished or self.drawn < self.index or now < self.next_frame:
            return False
        if self.index + 1 == len(self.frames):
            self.finished = True
            return False
        self.index += 1
        self.frame = self.frames[self.index]
        self.next_frame = now + 1 / rate
        return True


def _validate(value):
    if (not isinstance(value, dict) or value.get('format') != FORMAT or type(value.get('version')) is not int
            or value['version'] != 1 or value.get('kind') not in SUFFIXES or not isinstance(value.get('data'), dict)):
        raise RecordError('This is not a goal2 recording.')
    try:
        if clean_name(value['name']) != value['name']:
            raise ValueError('invalid name')
        data = value['data']
        if (not isinstance(data['countries'], list) or len(data['countries']) != 2
                or any(not isinstance(n, str) or len(n) > 100 for n in data['countries'])
                or not isinstance(data['kind'], str) or len(data['kind']) > 100):
            raise ValueError('invalid countries or match kind')
        kits = data['kits']
        if any(not isinstance(kits[k], list) or len(kits[k]) != 2
               or any(type(n) is not int or not 0 <= n <= 15 for n in kits[k]) for k in ('shirt', 'keeper')):
            raise ValueError('invalid kits')
        roles = data.get('roles', {})
        if (not isinstance(roles, dict) or len(roles) > 64
                or any(not isinstance(k, str) or not k.isascii() or not k.isdigit() or not 1 <= int(k) <= 3060
                       or not isinstance(v, str) or len(v) != 1 for k, v in roles.items())
                or data.get('managed') not in (None, 0, 1)
                or type(data.get('marks', 0)) is not int or not 0 <= data.get('marks', 0) < 5):
            raise ValueError('invalid role display')
        menu = data.get('menu', {})
        if (not isinstance(menu, dict) or set(menu) - {'0', '1'}
                or any(not isinstance(side, (list, tuple)) or len(side) != 2 or not isinstance(side[0], str)
                       or not isinstance(side[1], (list, tuple)) or len(side[1]) > 11
                       or any(not isinstance(row, (list, tuple)) or len(row) != 2
                              or any(not isinstance(cell, str) for cell in row) for row in side[1])
                       for side in menu.values())):
            raise ValueError('invalid saved lineup')
        if value['kind'] == 'goal':
            from goal2.game.watched_pitch import validate
            rows = data['frames']
            if not isinstance(rows, list) or not 1 <= len(rows) <= WINDOW_FRAMES:
                raise ValueError('invalid sample count')
            previous, watermark = rows[0]['sequence'] - 1, 0
            for row in rows:
                validate(row, previous + 1, watermark)
                previous, watermark = row['sequence'], row['watermark']
            if (not isinstance(data['scorer'], str) or len(data['scorer']) > 100
                    or type(data['minute']) is not int or not 0 <= data['minute'] <= 65535
                    or not isinstance(data['score'], list) or len(data['score']) != 2
                    or any(type(n) is not int or not 0 <= n <= 65535 for n in data['score'])):
                raise ValueError('invalid goal detail')
        else:
            board = data['board']
            if (not isinstance(board, dict) or set(board) != {'score', 'half_time', 'scorers', 'counters', 'bars',
                                                           'man_of_the_match', 'quick', 'scorer_names', 'motm_name'}):
                raise ValueError('invalid board')
            from goal2.ui.s20_board import COUNTERS
            def pair(row):
                return (isinstance(row, (list, tuple)) and len(row) == 2
                        and all(type(n) is int and 0 <= n <= 65535 for n in row))
            if (not pair(board['score']) or (board['half_time'] is not None and not pair(board['half_time']))
                    or not isinstance(board['scorers'], list) or len(board['scorers']) != 2
                    or any(not isinstance(side, list) or any(not pair(row) for row in side)
                           for side in board['scorers'])
                    or not isinstance(board['scorer_names'], list) or len(board['scorer_names']) != 2
                    or not isinstance(board['counters'], dict) or set(board['counters']) != {k for k, _ in COUNTERS}
                    or any(row is not None and not pair(row) for row in board['counters'].values())
                    or any(not isinstance(names, list) or len(names) != len(scorers)
                           for names, scorers in zip(board['scorer_names'], board['scorers']))
                    or any(not isinstance(n, str) or len(n) > 100 for names in board['scorer_names'] for n in names)
                    or not isinstance(board['motm_name'], str) or len(board['motm_name']) > 100
                    or type(board['quick']) is not bool
                    or (board['bars'] is not None and (not isinstance(board['bars'], list) or len(board['bars']) != 2
                                                       or any(not pair(row) for row in board['bars'])))):
                raise ValueError('invalid board detail')
    except (ValueError, TypeError, KeyError, IndexError, SaveError) as exc:
        raise RecordError('The recording is damaged or incomplete.') from exc
    return value


def read(path):
    path = Path(path)
    try:
        if path.suffix not in SUFFIXES.values() or path.stat().st_size > MAX_BYTES:
            raise RecordError('This is not a supported goal2 recording.')
        value = _validate(json.loads(path.read_text(encoding='utf-8')))
        if path.suffix != SUFFIXES[value['kind']]:
            raise RecordError('The recording has the wrong file type.')
        return value
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        if isinstance(exc, RecordError):
            raise
        raise RecordError('The recording could not be opened.') from exc


def entries(folder, kind):
    rows = []
    for path in Path(folder).glob('*' + SUFFIXES[kind]):
        try:
            record = read(path)
        except RecordError:
            continue
        rows.append({'name': record['name'], 'path': path})
    return sorted(rows, key=lambda row: (row['name'].casefold(), row['path'].name))


def path_for(folder, kind, name):
    try:
        name = clean_name(name)
    except SaveError as exc:
        raise RecordError(str(exc)) from exc
    folder = Path(folder)
    for entry in entries(folder, kind):
        if entry['name'] == name:
            return entry['path']
    stem = file_stem(name)
    for n in range(1, 1000):
        path = folder / (stem + ('' if n == 1 else f'-{n}') + SUFFIXES[kind])
        if not path.exists():
            return path
    raise RecordError('Too many recordings have similar names.')


def write(folder, kind, name, data):
    try:
        name = clean_name(name)
        value = _validate({'format': FORMAT, 'version': 1, 'kind': kind, 'name': name, 'data': copy.deepcopy(data)})
        raw = json.dumps(value, ensure_ascii=True, allow_nan=False).encode('utf-8')
        if len(raw) > MAX_BYTES:
            raise RecordError('This recording is too large.')
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        path = path_for(folder, kind, name)
        handle, temporary = tempfile.mkstemp(prefix='.recording-', suffix='.part', dir=folder)
        try:
            with os.fdopen(handle, 'wb') as stream:
                stream.write(raw)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return path
    except (OSError, ValueError, TypeError) as exc:
        if isinstance(exc, RecordError):
            raise
        raise RecordError(f'The recording was not saved: {exc}') from exc


def goal_data(pitch, event):
    """[designed: T181] Freeze the goal as shown; its names and kits survive a different career being loaded."""
    from goal2.ui.squad_card import full_name
    return {'frames': pitch.controller.goal_window.samples(), 'countries': list(pitch.controller.display.countries),
            'score': list(event['score']), 'minute': event['minute'], 'scorer': full_name(pitch.model, event['data']['player']),
            'kits': {'shirt': list(pitch.kits.shirt), 'keeper': list(pitch.kits.keeper)},
            'kind': pitch.controller.display.kind.upper(),
            'menu': copy.deepcopy(getattr(pitch.day, 'recorded_menu', {})),
            'roles': {str(k): v for k, v in pitch.controller.display.roles.items()},
            'managed': pitch.controller.display.managed, 'marks': pitch.pitch.marks}


def summary_data(screen):
    from goal2.ui.squad_card import full_name
    data = copy.deepcopy(screen.data)
    data['scorer_names'] = [[full_name(screen.model, word) for word, minute in side] for side in data['scorers']]
    data['motm_name'] = full_name(screen.model, data['man_of_the_match']) if data['man_of_the_match'] else ''
    return {'countries': list(screen.countries), 'kind': screen.kind,
            'kits': {'shirt': list(screen.kits.shirt), 'keeper': list(screen.kits.keeper)}, 'board': data}


# The screens use S21's existing name box, so typing, replacement and cancellation behave like a career save.
def name_recording(window, under, kind, data, done):
    from goal2.ui.s21_save import SaveScreen
    from goal2.ui.screen import set_para

    class RecordingNameScreen(SaveScreen):
        box_title = 'save goal' if kind == 'goal' else 'save match summary'

        def __init__(self):
            super().__init__(window, under, None, done=done, cancelled=done)
            self.record_kind = kind
            self.head.setText(self.box_title.capitalize())
            self.note.setText('Give this recording a name. Enter saves it; Esc returns without saving.')
            self._mode()

        def _mode(self):
            super()._mode()
            if self.replacing is None:
                set_para(self.text, 'Please enter the name of the goal.' if kind == 'goal'
                         else 'Please enter the name of the match summary.')
            else:
                set_para(self.text, f'A recording named “{self.name}” is there already. Replace it? (Y/N)')

        def save(self):
            try:
                path = path_for(window.target.root / 'recordings', kind, self.name)
                if path.exists():
                    self.replacing = path
                    self._mode()
                    return None
                return self.write()
            except RecordError as exc:
                self.say(str(exc))

        def write(self):
            try:
                path = write(window.target.root / 'recordings', kind, self.name, data)
            except RecordError as exc:
                self.replacing = None
                self._mode()
                self.say(str(exc))
                return None
            window.pop()
            done()
            return path

    return window.push(RecordingNameScreen())


def open_list(window, model, kind):
    """[designed: T181; confirmed: T156-R1 245–256] F3/F4: a bounded list by stored name, Enter opens, Esc back."""
    from PySide6.QtCore import Qt
    from goal2.ui.screen import Screen, label, para, set_para
    from goal2.ui.squad_card import box

    class RecordingsScreen(Screen):
        title = 'saved goals' if kind == 'goal' else 'saved match summaries'

        def __init__(self):
            super().__init__(window)
            self.entries = entries(window.target.root / 'recordings', kind)
            self.position = 0
            self.top = 0
            frame, column = box(self.title)
            self.rows = []
            # [designed: T181] Eight rows keep the list within the fixed page; arrows scroll longer collections.
            for index in range(8):
                row = self.add_option('', lambda i=index: self.open_row(i), enter='Open')
                column.addWidget(row)
                self.rows.append(row)
            self.body_layout.addWidget(frame)
            self.note = para('', 'sub')
            self.body_layout.addWidget(self.note)
            self.body_layout.addStretch(1)
            self.bindings = [b for b in self.bindings if b.keys not in ((Qt.Key.Key_Up,), (Qt.Key.Key_Down,))]
            self.bind((Qt.Key.Key_Up,), '', lambda: self.move(-1), shown=False)
            self.bind((Qt.Key.Key_Down,), '', lambda: self.move(1), shown=False)
            self.bind((), 'choose recording', None, captions=('↑', '↓'))
            self._show()

        def _show(self):
            if self.position < self.top:
                self.top = self.position
            elif self.position >= self.top + len(self.rows):
                self.top = self.position - len(self.rows) + 1
            for i, row in enumerate(self.rows):
                index = self.top + i
                row.setVisible(index < len(self.entries))
                if index < len(self.entries):
                    row.text_label.setText(self.entries[index]['name'])
            self.highlight(self.position - self.top if self.entries else -1)
            set_para(self.note, f'{self.position + 1} of {len(self.entries)} · Enter opens; Esc returns.'
                     if self.entries else 'No saved goals.' if kind == 'goal' else 'No saved match summaries.')

        def move(self, step):
            if self.entries:
                self.position = (self.position + step) % len(self.entries)
                self._show()

        def open_row(self, index):
            if self.top + index >= len(self.entries):
                return None
            self.position = self.top + index
            return self.open()

        def open(self):
            if not self.entries:
                return None
            try:
                record = read(self.entries[self.position]['path'])
                return open_record(window, model, record)
            except RecordError as exc:
                set_para(self.note, str(exc))

    return window.push(RecordingsScreen())


def open_record(window, model, record):
    data = record['data']
    if record['kind'] == 'goal':
        from goal2.ui.s15_match_menu import SavedGoalMenu
        return window.push(SavedGoalMenu(window, model, record))
    from goal2.ui.kits import Kits
    from goal2.ui.s20_board import BoardScreen
    kits = Kits(tuple(data['kits']['shirt']), tuple(data['kits']['keeper']))
    return window.push(BoardScreen(window, model, data['countries'], data['kind'], 'full', data['board'],
                                  lambda note: window.pop(), kits))


def play_saved(window, model, record):
    """[designed: T181] Reuse S17's painting and playback without starting or acknowledging an engine."""
    from goal2.desktop.match_view import Display, PLAYBACK_RATE
    from goal2.ui.kits import Kits
    from goal2.ui.s17_pitch import PitchScreen

    class SavedController:
        def __init__(self):
            data = record['data']
            self.display = Display('saved-goal')
            self.display.countries = list(data['countries'])
            self.display.managed = data.get('managed')
            self.display.roles = {int(k): v for k, v in data.get('roles', {}).items()}
            self.display.kind = data['kind']
            self.display.pitch_rate = PLAYBACK_RATE
            self.display.frame = copy.deepcopy(data['frames'][-1])
            self.kits = Kits(tuple(data['kits']['shirt']), tuple(data['kits']['keeper']))
            self.quick = False
            self.finished = False
            self.error = self.outcome = self.goal = None
            self.note = f"{data['scorer']} · {data['minute']}′"

        def shown(self):
            return []

        def frame_or_event(self):
            return self.display.frame['minute'], self.display.frame['score']

        def step_speed(self, step):
            self.display.step_rate(step)

        def painted(self, sequence):
            pass

        def cancel(self):
            self.finished = True

    class SavedPitchScreen(PitchScreen):
        escape_text = 'match menu'

        def __init__(self):
            super().__init__(window, model, SavedController())
            self.set_enter('Match menu', self.escape)
            self.pitch.marks = record['data'].get('marks', self.pitch.marks)
            self.start_replay(record['data']['frames'], self.completed)
            self.set_enter('Match menu', self.escape)

        def tick(self):
            if self.replay is not None:
                self.replay_tick(__import__('time').monotonic())

        def completed(self):
            self.timer.stop()
            self._result_text('REPLAY')

        def handle_key(self, key):
            from PySide6.QtCore import Qt
            if key in (Qt.Key.Key_Escape, Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.escape()
                return True
            return super().handle_key(key)

        def request_bench(self):
            self.escape()

        def quick_result(self):
            pass

        def escape(self):
            self.timer.stop()
            window.pop()

    return window.push(SavedPitchScreen())
