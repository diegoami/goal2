"""T224 (#454): tactics during a match, by the original's own route, under the core.

[confirmed: T224's probe of the original under the core, E006-r0001's round 1 watched (Denmark v Sweden): docs/core.md
"Tactics in a match (T224)"] In a match the original's match menu (0791:ED8A) offers the team tactics (its item 1/6,
1771:1981, editable for the managed side) before the kick-off, at a pause of live play (Enter, ED8A from 945B), at a
stoppage and at half time; its players (E949 -> E44F) offer a player's own tactics by T (1771:4B61), whose row 5,
the marking, is offered for an available outfield player of the eleven. Live play resumes after the menu's play at the
same minute and score; the tick loop 97D0 takes the change at its next iteration (DS:9B55).

Every check reads the original's memory (goal2/core/views.py) or its printed screen; the tests press only the
original's keys, through the driver, and write no byte. Nothing of the original is in this file: it reads .cache/ and
skips without.
"""
import unittest
from unittest.mock import patch

from goal2.tests import requires

NEEDS = dict(modules=('unicorn',), files=('e006-r0001-main.sav', 'GOAL.DAT'), archaeology=True)
REQUEST, SUBSTITUTIONS = 0x9B40, 0x9B3A      # DS:9B40 a substitution asked for; DS:9B3A + side the ones left
CHANGED = 0x9B55                             # set by 1981/4B61 in a match; 97D0 snapshots and clears it
_SAVES = {}


def _core(name):
    from goal2.core import Core
    return Core.load(_SAVES[name], goal_dat=requires.CACHE / 'GOAL.DAT')


def watched_live():
    """E006-r0001's round 1, watched, some poses into the first half (a live poll)."""
    from goal2.core import Core
    from goal2.core.driver import Driver
    if 'live' not in _SAVES:
        d = Driver(Core.start((requires.CACHE / 'e006-r0001-main.sav').read_bytes()).core)
        d.to_menu()
        d.round_start(watch=True)
        _SAVES['before'] = d.core.save()
        d.kick_off()
        with d.core.live_frames():
            for _ in range(120):
                d.live_step()
        assert d.wait.kind == 'match-live', d.wait.kind
        _SAVES['live'] = d.core.save()
    from goal2.core.driver import Driver
    return Driver(_core('live'))


def before_kick_off():
    from goal2.core.driver import Driver
    watched_live()
    return Driver(_core('before'))


def watched_half_time():
    """The same match watched on to its half-time menu (ED8A from 9AE3)."""
    from goal2.core.driver import Driver
    if 'half' not in _SAVES:
        d = watched_live()
        with d.core.live_frames():
            for _ in range(20000):
                if d.wait.kind != 'match-live':
                    break
                d.live_step()
        assert d.wait.kind == 'match-menu-halftime', d.wait.kind
        _SAVES['half'] = d.core.save()
    return Driver(_core('half'))


def clock(wait):
    """The minute DS:831F and the score DS:9B3C (views.pitch's event)."""
    from goal2.core import views
    mem = views.Memory(wait.state)
    return mem.ds_word(0x831F), (mem.ds_byte(0x9B3C), mem.ds_byte(0x9B3D))


def flags(wait):
    """The substitution request and the managed side's substitutions left: a tactics change touches neither."""
    from goal2.core import views
    mem = views.Memory(wait.state)
    side = views.match_sides(wait.state)['managed_side']
    return mem.ds_byte(REQUEST), mem.ds_byte(SUBSTITUTIONS + side), tuple(views.match_sides(wait.state)['eleven'])


def own(card, element):
    """1771:4B61's three states of row `element`: None the team's, False his own clear, True his own set."""
    r = card['own_tactics']
    return None if not r >> (element + 3) & 1 else bool(r >> (element - 1) & 1)


def outfield(wait, index=2):
    """A player of the managed eleven the original offers marking to: an outfield position (+6 >= 2)."""
    from goal2.core import views
    eleven = views.match_sides(wait.state)['eleven']
    return next(p for p in eleven[index:] if views.player_card(wait.state, p)['position'] >= 2)


def flat(text):
    return ' '.join(text.split())


class Oracle:
    """Each wait the route passed is the kind its printed text says (test_core_screens_t103's oracle)."""

    def assert_kinds(self, trail):
        from goal2.tests.test_core_screens_t103 import text_kind
        for wait in trail:
            if wait.kind in ('match-live',):
                continue
            self.assertEqual(text_kind(wait.text), wait.kind, wait.text)


@requires.need(**NEEDS)
class LivePlay(unittest.TestCase, Oracle):
    def test_own_tactic_from_live_play_resumes_at_the_same_minute_and_score(self):
        from goal2.core import views
        from goal2.core.screens import RETURN
        d = watched_live()
        player = outfield(d.wait)
        before, held = clock(d.wait), flags(d.wait)
        was = own(views.player_card(d.wait.state, player), 2)
        want = {None: False, False: True, True: None}[was]
        d.trail, start = [], len(d.log)
        card = d.match_own_tactic(player, 2, want)
        self.assertEqual(d.wait.kind, 'match-live')
        self.assertEqual(clock(d.wait), before)
        self.assertEqual(flags(d.wait), held)
        self.assertEqual(own(card, 2), want)
        # the player's record +0xF, which the manager menu's route (set_own_tactic) edits too
        self.assertEqual(own(views.player_card(d.wait.state, player), 2), want)
        keys = d.log[start:]
        self.assertEqual(keys[0], ('match-live', RETURN))
        self.assertIn(('substitution-request', ord('t')), keys)
        self.assertNotIn(('substitution-request', RETURN), keys)        # Enter there would request a substitution
        self.assertIn('match-own-tactics', [w.kind for w in d.trail])
        self.assert_kinds(d.trail)
        # the original shows it on its own tactics screen: pause, players, the player, T
        d.live_step(RETURN)
        d._menu_item('players')
        wait = d.press(RETURN, expect=('substitution-request',))
        for _ in range(20):
            if wait.view['player'] == player:
                break
            wait = d.press(0xB1, expect=('substitution-request',))
        wait = d.press('t', expect=('match-own-tactics',))
        name, word, mine = views.player_card(wait.state, player)['tactics'][1]
        self.assertEqual(mine, want is not None)
        self.assertIn(word + (' P' if mine else ''), flat(wait.text))

    def test_marking_from_live_play(self):
        from goal2.core import views
        d = watched_live()
        player = outfield(d.wait)
        before, held = clock(d.wait), flags(d.wait)
        card = d.match_marking(player, 0)                  # protect zone: status element 7 set, no opponent
        self.assertEqual(d.wait.kind, 'match-live')
        self.assertEqual((clock(d.wait), flags(d.wait)), (before, held))
        self.assertEqual(views.marking(d.wait.state, player), {'own': True, 'opponent': 0})
        self.assertEqual(card['mark'], 'Protect zone P')
        sides = views.match_sides(d.wait.state)
        rival = sides['teams'][1 - sides['managed_side']]
        opponent = views.Memory(d.wait.state).country(rival, 2 * 4, 2)        # the opposing squad's slot 5
        card = d.match_marking(player, opponent)
        self.assertEqual(views.marking(d.wait.state, player), {'own': True, 'opponent': opponent})
        self.assertEqual(card['mark'], views.Memory(d.wait.state).player_name(opponent) + ' P')
        self.assertEqual((clock(d.wait), flags(d.wait)), (before, held))
        card = d.match_marking(player, None)               # back to the team's marking
        self.assertFalse(views.marking(d.wait.state, player)['own'])
        self.assertEqual(d.wait.kind, 'match-live')

    def test_team_tactic_from_live_play_and_when_it_takes_effect(self):
        from goal2.core import views
        d = watched_live()
        before, held = clock(d.wait), flags(d.wait)
        byte = views.team_tactics(d.wait.state)['byte']
        view = d.match_tactic(6, not byte >> 5 & 1)
        self.assertEqual(view['byte'], byte ^ 0x20)                            # the country's +0x2D element 6
        self.assertEqual(views.team_tactics(d.wait.state)['byte'], byte ^ 0x20)
        self.assertEqual(d.wait.kind, 'match-live')
        self.assertEqual((clock(d.wait), flags(d.wait)), (before, held))
        self.assertEqual(views.Memory(d.wait.state).ds_byte(CHANGED), 1)
        # [confirmed: routines.tsv 0791:97D0] the tick loop's next iteration snapshots the state and clears 9B55
        for _ in range(400):
            if not views.Memory(d.wait.state).ds_byte(CHANGED):
                break
            d.live_step()
        self.assertEqual(views.Memory(d.wait.state).ds_byte(CHANGED), 0)
        self.assertEqual(views.team_tactics(d.wait.state)['byte'], byte ^ 0x20)

    def test_the_pause_menu_route_returns_to_the_pause(self):
        from goal2.core import views
        from goal2.core.screens import RETURN
        d = watched_live()
        d.live_step(RETURN)
        self.assertEqual(d.wait.view['context'], 'pause')
        player = outfield(d.wait)
        byte = views.team_tactics(d.wait.state)['byte']
        d.match_tactic(1, not byte & 1)
        self.assertEqual((d.wait.kind, d.wait.view['context']), ('match-menu', 'pause'))
        d.match_own_tactic(player, 1, True)
        self.assertEqual((d.wait.kind, d.wait.view['context']), ('match-menu', 'pause'))
        self.assertTrue(own(views.player_card(d.wait.state, player), 1))

    def test_the_original_offers_no_marking_to_its_goalkeeper(self):
        from goal2.core import views
        from goal2.core.driver import DriverError
        d = watched_live()
        before, held = clock(d.wait), flags(d.wait)
        keeper = views.match_sides(d.wait.state)['eleven'][0]
        with self.assertRaisesRegex(DriverError, '4 rows'):
            d.match_marking(keeper, 0)
        self.assertEqual(d.wait.kind, 'match-live')
        self.assertEqual((clock(d.wait), flags(d.wait)), (before, held))


@requires.need(**NEEDS)
class HalfTimeAndBeforeKickOff(unittest.TestCase, Oracle):
    def test_half_time_team_tactics_shown_by_the_original(self):
        from goal2.core import views
        from goal2.core.screens import ESCAPE, RETURN
        d = watched_half_time()
        held = flags(d.wait)
        byte = views.team_tactics(d.wait.state)['byte']
        view = d.match_tactic(7, not byte >> 6 & 1)
        self.assertEqual(view['byte'], byte ^ 0x40)
        self.assertEqual(d.wait.kind, 'match-menu-halftime')
        self.assertEqual(flags(d.wait), held)
        d._menu_item('team tactics')
        wait = d.press(RETURN, expect=('team-tactics',))
        row = next(r for r in views.team_tactics(wait.state)['rows'] if r['element'] == 7)
        self.assertIn(row['word'], flat(wait.text))
        d.press(ESCAPE, expect=('match-menu-halftime',))

    def test_half_time_own_tactic_and_marking_touch_no_substitution(self):
        from goal2.core import views
        d = watched_half_time()
        held = flags(d.wait)
        player = outfield(d.wait)
        d.trail = []
        card = d.match_own_tactic(player, 3, True)
        self.assertTrue(own(card, 3))
        self.assertEqual(d.wait.kind, 'match-menu-halftime')
        self.assertIn('squad-substitution-tactic', [w.kind for w in d.trail])
        self.assert_kinds(d.trail)
        d.match_marking(player, 0)
        self.assertEqual(views.marking(d.wait.state, player), {'own': True, 'opponent': 0})
        self.assertEqual(flags(d.wait), held)
        # the second half still kicks off from the same menu
        d.core.stop_at('match-live', 'substitution-notice', 'match-summary-save-prompt')
        self.assertEqual(d.play_on().kind, 'match-live')
        self.assertTrue(own(views.player_card(d.wait.state, player), 3))

    def test_before_the_kick_off(self):
        from goal2.core import views
        d = before_kick_off()
        self.assertEqual(d.wait.view['context'], 'before')
        player = outfield(d.wait)
        byte = views.team_tactics(d.wait.state)['byte']
        d.match_tactic(5, not byte >> 4 & 1)
        self.assertEqual(views.team_tactics(d.wait.state)['byte'], byte ^ 0x10)
        d.trail = []
        d.match_own_tactic(player, 4, False)
        self.assertIs(own(views.player_card(d.wait.state, player), 4), False)
        self.assertIn('own-tactics', [w.kind for w in d.trail])
        d.match_marking(player, 0)                          # 4B61 offers row 5 with the match set up
        self.assertTrue(views.marking(d.wait.state, player)['own'])
        self.assertEqual((d.wait.kind, d.wait.view['context']), ('match-menu', 'before'))
        self.assertEqual(d.kick_off().kind, 'match-live')

    @requires.need(files=('e010-r0001-halftime.sav',))
    def test_with_no_substitutions_left(self):
        from goal2.core import Core, views
        from goal2.core.driver import Driver
        from goal2.tests.test_core_round_t108 import same_line_pairs
        d = Driver(Core.start((requires.CACHE / 'e010-r0001-halftime.sav').read_bytes()).core)
        d.press(13, expect=('match-menu-halftime',))
        for pair in same_line_pairs(views.bench(d.wait.state), 5):
            self.assertTrue(d.substitute(*pair)['made'])
        player = outfield(d.wait)
        d.trail = []
        card = d.match_own_tactic(player, 1, True)
        self.assertTrue(own(card, 1))
        self.assertEqual(d.wait.kind, 'match-menu-halftime')
        self.assertIn('substitutions-used', [w.kind for w in d.trail])
        self.assertIn('match-own-tactics', [w.kind for w in d.trail])
        self.assert_kinds(d.trail)


@requires.need(modules=('unicorn', 'PySide6'), files=('e006-r0001-main.sav', 'GOAL.DAT'), archaeology=True)
class Window(unittest.TestCase):
    """Done-when 3: during live play and at half time the tactics controls are enabled and act; the rest are
    disabled with their reason shown."""

    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def window(self, name):
        import tempfile
        from pathlib import Path
        from goal2.desktop.core_model import CoreModel
        from goal2.desktop.core_window import CoreWindow
        (watched_live if name == 'live' else watched_half_time)()
        folder = tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        with patch.object(CoreWindow, 'resume_round'):     # no pitch window: the round's page is not under test
            w = CoreWindow(CoreModel(_core(name), requires.CACHE / 'GOAL.DAT', Path(folder.name) / 'g.g2core'))
        self.addCleanup(w.close)
        w.core_round.state = w.model.round_state()
        w.refresh_round_controls()
        return w

    def check_controls(self, w):
        tactics = [row for _, row in w.tactics] + w.own_tactics + [w.own_marking,
                                                                  w.core_team_buttons['teamTacticsRoute'],
                                                                  w.core_team_buttons['teamOwnRoute']]
        for widget in tactics:
            self.assertTrue(widget.isEnabled(), widget.objectName())
        rest = [w.core_team_buttons['reposition'], w.core_team_buttons['clubPosition'], w.rename, w.pool_move,
                w.pool_switch, w.core_routes['play next game']]
        for widget in rest:
            self.assertFalse(widget.isEnabled(), widget.objectName())
            self.assertTrue(widget.toolTip(), widget.objectName())
        self.assertIn('tactics', w.core_match_note.text())
        self.assertFalse(w.core_match_note.isHidden())

    def act(self, w, home):
        from goal2.core import views
        before = clock(w.model.core.wait)
        byte = w.model.team_tactics()['byte']
        row = dict(w.tactics)[5]
        row.click()
        self.assertEqual(w.finish_core()[0], 'done')
        self.assertEqual(w.model.team_tactics()['byte'], byte ^ 0x10)
        self.assertEqual(w.model.core.wait.kind, home)
        self.assertEqual(clock(w.model.core.wait), before)
        player = outfield(w.model.core.wait)
        w.team_roster.set_current([r[0] for r in w.team_roster.rows].index(player))
        was = own(w.model.card(player), 1)
        w.own_tactics[0].click()
        self.assertEqual(w.finish_core()[0], 'done')
        self.assertEqual(own(w.model.card(player), 1), {None: False, False: True, True: None}[was])
        self.assertEqual(w.model.core.wait.kind, home)
        w.own_marking.click()
        self.assertEqual(w.finish_core()[0], 'done')
        self.assertTrue(views.marking(w.model.state, player)['own'])
        self.assertEqual(clock(w.model.core.wait), before)
        self.check_controls(w)

    def test_live_play(self):
        w = self.window('live')
        self.check_controls(w)
        self.act(w, 'match-live')

    def test_half_time(self):
        w = self.window('half')
        self.check_controls(w)
        self.act(w, 'match-menu-halftime')


if __name__ == '__main__':
    unittest.main()
