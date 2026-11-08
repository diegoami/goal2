"""[designed: owner #636] Tactics cursor selection has no new game values to decode."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from PySide6.QtWidgets import QApplication
from goal2.ui.squad_card import Row


def screen_class():
    from goal2.ui.s10_team_tactics import TeamTacticsScreen
    return TeamTacticsScreen

class SelectionDoesNotDecode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def control(self, pending=False):
        rows = [Row(i, (100,100,0)) for i in range(8)]
        for row in rows: row.set(('synthetic line', 'clear', 'set'))
        rows[0].set_on(True)
        # A cursor move has no input changes to decode. Actual full-window controls
        # will additionally spy on model.view, BenchAnswer.card and role decoders.
        return SimpleNamespace(rows=rows, pending=pending, line=0,
            refresh=Mock(side_effect=AssertionError('cursor selection redecoded game/card data')),
            _refresh_hint=Mock())

    def test_selection_only_changes_highlight_and_hint(self):
        screen = self.control()
        before = [row.texts() for row in screen.rows]
        screen_class().choose(screen, 1)
        self.assertEqual(screen.line, 1)
        self.assertEqual([row.on for row in screen.rows], [False,True,False,False,False,False,False,False])
        self.assertEqual([row.texts() for row in screen.rows], before)
        screen.refresh.assert_not_called()
        screen._refresh_hint.assert_called_once_with()

    def test_pending_selection_keeps_all_rows_and_sends_no_change(self):
        screen = self.control(pending=True)
        screen_class().choose(screen, 1)
        self.assertEqual(screen.line, 0)
        self.assertEqual([row.on for row in screen.rows], [True,False,False,False,False,False,False,False])
        screen.refresh.assert_not_called();screen._refresh_hint.assert_not_called()


if __name__ == '__main__':unittest.main(verbosity=2)


from goal2.tests import requires
@requires.need(modules=('PySide6','pygame'), **requires.HALFTIME)
class FreshStoppedRoles(unittest.TestCase):
    def test_refresh_reads_new_snapshot_positions_and_flags_without_full_card_or_view_decoding(self):
        import copy
        from goal2.tests.test_live_team_tactics_610 import LiveTeamTactics
        from goal2.ui.s19_bench import BenchAnswer
        from goal2.ui.s10_team_tactics import LINES, words
        from goal2.game import roles
        from goal2.game.player_card import _wrap_raw
        from unittest.mock import patch
        LiveTeamTactics.setUp(self)
        LiveTeamTactics.prepare(self, 'half_time')
        screen=LiveTeamTactics.open_tactics(self)
        baseline=copy.deepcopy(self.model.state)
        original_words=screen.answer.words()
        slot=1;word=screen.answer.eleven[slot]
        table=roles.tables(self.model.state)
        for position in (12,5):
            data=copy.deepcopy(self.decision.data)
            data['tactics']=self.original_tactics ^ (16 if position==12 else 1)
            rows=[]
            for current in original_words:
                record=bytearray(self.model.state.players[current])
                if current==word:record[6]=position
                rows.append([current,record.hex()])
            data['player_records']=rows
            answer=BenchAnswer(self.model,SimpleNamespace(data=data,minute=45,score=[0,0]))
            screen.answer=answer
            with patch.object(answer,'card',side_effect=AssertionError('full card redecoded')),patch.object(
                    self.model,'view',side_effect=AssertionError('full career view redecoded')),patch(
                    'goal2.game.player_card._wrap_raw',wraps=_wrap_raw) as memory:
                screen.refresh()
            self.assertEqual(memory.call_count,1,'exactly one actual shared image read serves this live refresh')
            self.assertEqual(screen.strip.rows[slot].texts()[0],roles.role(self.model.state,position,cache=table)[0])
            lines=[roles.role(self.model.state,answer.position(w),cache=table)[1] for w in answer.eleven]
            formation='-'.join(str(lines.count(line)) for line in ('defence','midfield','attack'))
            self.assertIn(formation,screen.facts.text())
            for row,(_,element) in enumerate(LINES):
                clear,set_=words(self.model.state,element)
                now=bool(answer.team_tactics & (1<<(element-1)))
                self.assertEqual(screen.lines()[row][1:],(set_,clear) if now else (clear,set_))
            self.assertEqual(self.model.state,baseline)

    def key(self,value):
        from goal2.tests.test_live_team_tactics_610 import LiveTeamTactics
        LiveTeamTactics.key(self,value)
