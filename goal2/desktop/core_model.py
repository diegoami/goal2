"""[designed: owner, 2026-10-22, #308, #321; T105] The desktop's model over the core: Qt-free.

The core route opens the original's own game (goal2/core, docs/core.md) and keeps it at the manager menu. Every
value the pages show comes from the original's memory through goal2/core/views.py; every move between the
original's screens is the original's own keys, pressed by the driver (goal2/core/driver.py). The model never writes
a byte into the core's memory and never reads the text page. It shares nothing with the Python route's
`DesktopModel` and its GameState (decision 7, docs/redesign-253/vision-reconciliation.md).

[designed] Routes the core cannot serve yet are named with the G task that brings them (#308's order after this
one, G11): `DISABLED`.

[designed: owner, 2026-10-22; T106, #308's G10] A new career on the core route is the original's own new game
(`CoreNewGame`): the core boots at the program's DOS date call answering the date that gives the chosen start year,
the browser's countries and card are read from its memory, and the driver plays the original's keys to the first
manager menu, through its bulletins.
"""
import os
from pathlib import Path

from goal2.core import views

# [designed: T105, #308] The routes of the manager menu and of goal2's pages the core cannot serve yet, and the G
# task that brings each, in #308's numbering: G10 the new game, G11 this task (menus, fixtures, tables, history),
# G12 squad, pool, select team and tactics, G13 bulletins, news and the year change, G14 the match flow.
# [T107, G12] Team and Pool are served now: the Team page is select squad and the team tactics, the Pool page the
# pool list of SELECT YOUR TEAM.
# [T108, G14a] Play next game is served now: the round by the original's keys, the own match as its quick result. The
# watched match is served by T109 (G14b), with one complete pose acknowledged before the next.
DISABLED = {}
DISABLED_TEXT = {}

# [designed: T107] The driver's team actions the pages may run (goal2/core/driver.py), each from the manager menu
# and back to it.
ACTIONS = ('swap', 'exchange', 'set_position', 'set_own_tactic', 'set_marking', 'rename', 'set_tactic')
# [designed: T108] The round's steps (goal2/core/driver.py): each stops where the original asks the manager.
ROUND_ACTIONS = ('round_start', 'kick_off', 'notice', 'substitute', 'play_on', 'prematch_swap', 'finish',
                 'live_step', 'summary_done', 'request_substitution', 'round_position', 'round_continue',
                 'shootout_start', 'shootout_pick', 'shootout_undo', 'taker_key', 'taker_highlight')
# the kinds a round waits at between its steps
ROUND_WAITS = ('match-menu', 'match-menu-halftime', 'substitution-notice', 'match-menu-fulltime',
               'match-live', 'match-summary-save-prompt', 'round-paused', 'shootout-announcement', 'shootout-order',
               'match-menu-extra-time', 'match-menu-extra-halftime', 'set-piece-select', 'set-piece-pitch',
               'bulletin-achievement')


class CoreModel:
    """The original's game at its manager menu. `open(savestate)` starts a core from a savestate (a new game's
    first screen is the team-info browser; Esc leaves it for the menu); `from_save(path)` resumes a core save."""
    core_route = True

    def __init__(self, core, data_path, save_path):
        from goal2.core.driver import Driver
        self.core = core
        self.driver = Driver(core)
        self.data_path = None if data_path is None else Path(data_path)
        self.save_path = Path(save_path)
        self.refused = None           # [T108] the original's last refusal of the eleven, while the round waits on it
        self.commentary_cursor = 0
        self.pitch_sequence = 0
        if core.wait.kind not in ROUND_WAITS + ('save-game-name-entry',):
            self.driver.to_menu()

    @classmethod
    def open(cls, savestate_path, data_path, save_path):
        from goal2.core import Core, CoreError
        try:
            raw = Path(savestate_path).read_bytes()
            return cls(Core.start(raw).core, data_path, save_path)
        except (OSError, ValueError, CoreError) as exc:
            raise ValueError(f'Cannot open the core: {exc}') from exc

    @classmethod
    def from_save(cls, path, data_path):
        from goal2.core import Core, CoreError
        try:
            return cls(Core.load(Path(path).read_bytes(), goal_dat=data_path), data_path, path)
        except (OSError, ValueError, KeyError, CoreError) as exc:
            raise ValueError(f'Cannot resume the core: {exc}') from exc

    # -- the views, read from memory at the manager menu -------------------------------------------------
    @property
    def state(self):
        return self.core.wait.state

    def desk(self):
        return views.desk(self.state)

    def fixture_list(self):
        return views.fixture_list(self.state)

    def tournament(self):
        return views.tournament(self.state)

    def history(self):
        return views.history(self.state)

    def memory_sha256(self):
        return self.core.memory_sha256()

    # -- the Team and Pool pages (T107) -------------------------------------------------------------------------
    def team(self):
        return views.team(self.state)

    def card(self, player):
        return views.player_card(self.state, player)

    def team_tactics(self):
        return views.team_tactics(self.state)

    def pool(self):
        return views.pool(self.state)

    def act(self, name, *args):
        """Run the driver's team action `name` (ACTIONS) with the original's own keys, from the manager menu and
        back. A refusal comes back as ValueError with the original's reason: the message box's text for a pool
        exchange the original refuses (0791:DBFA), the driver's statement for a screen that does not offer it."""
        from goal2.core import CoreError
        if self.in_save_name:
            raise ValueError('Resolve the original save decision before another action')
        if name in ROUND_ACTIONS:
            return self.round_step(name, *args)
        if name not in ACTIONS:
            raise ValueError(f'No team action {name!r}')
        if self.in_round:
            raise ValueError('The round is under way: its team changes are on the bench')
        try:
            result = getattr(self.driver, name)(*args)
        except CoreError as exc:
            if self.core.stopped is not None:
                raise
            self.driver.to_menu()
            raise ValueError(str(exc).split('\n')[0]) from exc
        if isinstance(result, dict) and result.get('refused'):
            raise ValueError(result['refused'])
        return result


    # -- the round (T108) -------------------------------------------------------------------------------------------
    @property
    def in_round(self):
        return self.core.wait.kind in ROUND_WAITS

    def round_step(self, name, *args):
        """[designed: T108] Run the round's step `name` (ROUND_ACTIONS) by the original's keys; returns round_state().
        A refusal of the eleven (EA09) comes back in the state's `refused`; a pair the original refuses in the
        substitution's `refused` (its own message). Nothing is decided here: the driver passes what it is given."""
        from goal2.core import CoreError
        if name == 'round_start':
            self.driver.pages = []
            self.commentary_cursor = 0
        if name == 'kick_off':
            self.commentary_cursor = 0       # the original clears its ring for this match
        try:
            # [designed: T116; confirmed: 0791:9571–9708] All original polls execute; only complete poses need
            # a kept snapshot/text page. Reads and manager decisions retain their immediate stops.
            with self.core.live_frames():
                watch = (args[1] if len(args)>1 and args[1] is not None else self.driver.watching)
                if name=='kick_off' and watch:
                    result = self.driver.kick_off(*args,speed=0)
                else:
                    result = getattr(self.driver, name)(*args)
        except CoreError as exc:
            if self.core.stopped is not None:
                raise
            raise ValueError(str(exc).split('\n')[0]) from exc
        position_refused = result['refused'] if isinstance(result, dict) and set(result)=={'refused'} else None
        if position_refused is not None:self.refused=position_refused
        elif name!='round_position':self.refused=None
        state = self.round_state()
        if name == 'substitute':
            state['substitution'] = result
        if name == 'round_position':
            state['position_player'] = args[0]
            state['position_refused'] = position_refused
        return state

    def round_state(self):
        """Where the round is, read from memory: `at` the wait's kind; at the match menu before the kick-off the
        captain prompt's list (`captain`) and the bench, at half time the board and the bench; `pages` the screens
        passed since the round began (the round's results, the boards, the table, the bulletins), as the driver read
        them; `refused` the original's message when it refused the eleven."""
        wait = self.core.wait
        out = {'at': wait.kind, 'stop': 'menu', 'pages': list(self.driver.pages), 'refused': self.refused,
               'captain': None, 'bench': None, 'board': None, 'notice': None}
        if wait.kind == 'shootout-announcement':
            out.update(stop='shootout-announcement',message=wait.view['message'],board=views.board(self.state))
        elif wait.kind == 'shootout-order':
            out.update(stop='shootout-order',order=views.shootout_order(self.state,wait.view))
        elif wait.kind in ('set-piece-select','set-piece-pitch'):
            preview = wait.kind == 'set-piece-pitch'
            out.update(stop='taker-pitch' if preview else 'taker', taker=views.taker_choice(self.state,wait.view))
            if preview:
                out.update(pitch=views.pitch(self.state,self.pitch_sequence,0),commentary=[],
                           speed=views.match_speed(self.state),identity=views.pitch_identity(self.state))
                self.pitch_sequence += 1
        elif wait.kind == 'round-paused':
            out.update(stop='round-paused', message=wait.view['message'],
                       results=views.round_results(self.state, wait.view['first'], wait.view['last']))
        elif wait.kind == 'bulletin-achievement':
            # [designed: #395] A current guest decision, preserved on partial save/resume.
            out.update(stop='bulletin-achievement', bulletin=views.achievement_bulletin(self.state))
        elif wait.kind == 'match-menu' and self.driver.stoppage():
            out.update(stop='pause' if wait.view.get('context') == 'pause' else 'stoppage',
                       board=views.board(self.state), bench=views.bench(self.state))
        elif wait.kind == 'match-menu':
            out.update(stop='captain', captain=views.captain_choice(self.state), bench=views.bench(self.state))
        elif wait.kind == 'match-menu-halftime':
            out.update(stop='half-time', board=views.board(self.state), bench=views.bench(self.state))
        elif wait.kind in ('match-menu-extra-time','match-menu-extra-halftime'):
            first = wait.kind == 'match-menu-extra-time'
            out.update(stop='extra-time-start' if first else 'extra-time-half',
                       interval_label='EXTRA TIME' if first else 'EXTRA-TIME HALF TIME',
                       board=views.board(self.state),bench=views.bench(self.state))
        elif wait.kind == 'substitution-notice':
            # the eleven's players whose status word is not the selected one's (1771:42BC: injured, sent off, ...)
            selected = views.Memory(self.state).code_str(0x1771, 0x42A6)
            players = [views.player_card(self.state, w) for w in views.match_sides(self.state)['eleven']]
            out.update(stop='notice', board=views.board(self.state), notice={
                'players': [{'player': c['player'], 'name': c['name'], 'readiness': c['readiness']}
                            for c in players if c['readiness'] != selected]})
        elif wait.kind == 'match-menu-fulltime':
            out.update(stop='full-time')
        elif wait.kind == 'match-live':
            self.commentary_cursor, lines = views.commentary(self.state, self.commentary_cursor)
            out.update(stop='live', pitch=views.pitch(self.state, self.pitch_sequence, 0), commentary=lines,
                       speed=views.match_speed(self.state),
                       identity=views.pitch_identity(self.state))
            self.pitch_sequence += 1
        elif wait.kind == 'match-summary-save-prompt':
            out.update(stop='summary-save', board=views.board(self.state))
        # [designed: owner#73, T122] Preserve raw original views; presentation names the declared deviation.
        if out['bench'] is not None:
            from goal2.core.patches import unlimited_friendly
            if unlimited_friendly(self.core):
                out['bench']['budget_label'] = 'Unlimited'
        if wait.kind in ROUND_WAITS and wait.kind != 'match-live' and self.driver.watching:
            self.commentary_cursor, out['commentary'] = views.commentary(self.state, self.commentary_cursor)
        return out

    # -- saving ----------------------------------------------------------------------------------------------
    @property
    def in_save_name(self):
        return self.core.wait.kind == 'save-game-name-entry'

    def begin_save_name(self):
        """[confirmed: T121 original F7 probe] Enter the original save decision only from management."""
        from goal2.core.screens import F7
        if self.in_round or self.in_save_name:
            raise ValueError('Finish the current decision before opening the original save prompt')
        self.driver.to_menu()
        self.driver.press(F7, expect=('save-game-name-entry',))

    def resolve_save_name(self, write, path=None):
        """[designed: T121, owner .g2core decision] Resolve the observed editor without a .GL writer.

        F7 cancels through the original Esc and saves the resulting live core. Terminal quit-save
        selects the one actual pre-F10 snapshot; it never rewinds or runs the quitting machine.
        """
        if not self.in_save_name:
            raise ValueError('The original is not asking for a saved-game name')
        if self.core.wait.view['quit']:
            if not write:
                return None
            if self.core.quit_origin is None:
                raise ValueError('This terminal save has no recorded playable origin')
            return self._write_save(self.core.quit_origin, path)
        self.driver.cancel_save_name()
        return self.save(path) if write else None

    def save(self, path=None):
        """[designed] The Save page (F7 in the original): the core save (docs/core.md, "Saving"), written whole to a
        temporary file and then moved over `path`."""
        if self.in_save_name:
            return self.resolve_save_name(True, path)
        return self._write_save(self.core.save(), path)

    def _write_save(self, data, path=None):
        target = Path(self.save_path if path is None else path)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(target.name + '.tmp')
            temporary.write_bytes(data)
            os.replace(temporary, target)
        except OSError as exc:
            raise ValueError(f'Cannot save the core: {exc}') from exc
        self.save_path = target
        return target

    def export_summary(self, path):
        """[designed: owner, 2026-10-23, T109] At the original's save-summary question, export a readable desktop
        summary. Answer its DOS question N afterwards; no original disk-writing routine or guest patch is used."""
        if self.core.wait.kind != 'match-summary-save-prompt':
            raise ValueError('The original is not asking to save a match summary')
        board = views.board(self.state)
        lines = [f"{board['names'][0]} {board['score'][0]} - {board['score'][1]} {board['names'][1]}", '']
        for side in (0, 1):
            lines.extend(f"{board['names'][side]}: {r['name']} {r['minute']}' {r['mark']}".rstrip()
                         for r in board['scorers'][side])
        if board.get('man_of_the_match'):
            lines.extend(['', f"Man of the match: {board['man_of_the_match']}"])
        Path(path).write_text('\n'.join(lines) + '\n', encoding='utf-8')
        return Path(path)



class CoreJobs:
    """[designed: T107, T65's pattern] One team action at a time, run off the window's thread: `start(name, *args)`
    hands it to a worker thread, `busy` holds while it runs, and `poll()` (the window's timer) returns None while it
    runs, then once ('done', result) or ('refused', message). The page reads the original's state only after poll
    says it ended, so it never shows a state the action is still changing."""

    def __init__(self, model):
        from concurrent.futures import ThreadPoolExecutor
        self.model = model
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='goal2-core')
        self.future = None
        self.name = None

    @property
    def busy(self):
        return self.future is not None

    def start(self, name, *args):
        if self.busy:
            raise ValueError('The original is busy with another action')
        self.name = name
        self.future = self.pool.submit(self.model.act, name, *args)

    def poll(self):
        if self.future is None or not self.future.done():
            return None
        future, self.future = self.future, None
        try:
            return ('done', future.result())
        except ValueError as exc:
            return ('refused', str(exc))

    def wait(self, timeout=60):
        """Block until the running action ends (tests and closing the window); poll() then collects it."""
        if self.future is not None:
            self.future.exception(timeout)


# [designed: T106] The DOS date's month and day the core answers (E039's, 10/04); the year is the start year - 1.
BOOT_MONTH_DAY = (10, 4)


def dos_year(start_year):
    """[confirmed: NG-9] A new game's start year is the DOS year + 1, rounded up to even: the DOS year that gives the
    even start year S is S - 1 (1990 -> 1989, 1992 -> 1991)."""
    if start_year % 2:
        raise ValueError(f"the original's start years are even, not {start_year}")
    return start_year - 1


class CoreNewGame:
    """[designed: T106] The original's new game for Launch's New career on the core route.

    `browse(start_year)` boots the core from the date-call state (e039-r0005-date-call.sav) with the DOS date of
    that start year, presses N while the title's tune plays (`Core.boot`'s title_key) and Enter on the player count
    (one manager), and keeps the core at the country browser, one per start year. `countries`, `card` and `campaign`
    read that core's memory (goal2/core/views.py). `start` plays the rest of the new game by the driver and returns
    the CoreModel at the first manager menu with the bulletins the original showed on the way."""

    def __init__(self, boot_path, data_path, save_path):
        self.boot_path, self.data_path, self.save_path = Path(boot_path), Path(data_path), Path(save_path)
        self._drivers = {}

    def browse(self, start_year):
        from goal2.core import Core, CoreError
        from goal2.core.driver import Driver
        from goal2.core.screens import RETURN
        if start_year not in self._drivers:
            try:
                state = self.boot_path.read_bytes()
                wait = Core.boot(state, (dos_year(start_year),) + BOOT_MONTH_DAY, goal_dat=self.data_path,
                                 title_key='n')
                driver = Driver(wait.core)
                if wait.kind == 'title-player-count':
                    driver.press(RETURN, expect=('country-select',))
                if driver.wait.kind != 'country-select':
                    raise CoreError(f'the new game shows {driver.wait.kind}, not the country browser')
            except (OSError, ValueError, CoreError) as exc:
                raise ValueError(f'Cannot start the original\'s new game: {exc}') from exc
            self._drivers[start_year] = driver
        return self._drivers[start_year]

    def countries(self, start_year):
        """The browser's countries in its order: number, name, world rank, continent name, rank within it."""
        return [(c['country'], c['name'], c['world_rank'], c['continent'], c['continent_rank'])
                for c in views.country_select(self.browse(start_year).wait.state)['countries']]

    def card(self, start_year, country):
        return views.country_card(self.browse(start_year).wait.state, country)

    def campaign(self, start_year):
        """The start year and stage the original set at the title's N (1771:9B85, NG-9), and the stage's words."""
        from goal2.desktop.model import STAGES
        view = views.country_select(self.browse(start_year).wait.state)
        return {'start_year': view['start_year'], 'stage': view['stage'], 'words': STAGES.get(view['stage'], '')}

    def start(self, start_year, country, manager_name):
        """Play the new game to the first manager menu; returns (CoreModel, [bulletin views])."""
        from goal2.core import CoreError
        driver = self.browse(start_year)
        bulletins = []
        try:
            driver.new_game(country, manager_name, on_bulletin=lambda wait: bulletins.append(views.bulletin(wait.state)))
            # [designed: owner#73, T122] New desktop careers explicitly opt in; imports/resumes never migrate.
            from goal2.core.patches import OWNER_SUBSTITUTIONS
            driver.core.apply_patch(OWNER_SUBSTITUTIONS)
        except (CoreError, ValueError) as exc:
            self._drivers.pop(start_year, None)
            raise ValueError(f'The new game stopped: {exc}') from exc
        self._drivers.pop(start_year, None)            # this core is the career now
        return CoreModel(driver.core, self.data_path, self.save_path), bulletins
