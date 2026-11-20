"""[designed: T170ab/#808] Existing native screens with sampling opted in."""
import queue
import unittest
from unittest.mock import patch

from goal2.tests import requires
requires.require(modules=('PySide6',))


@requires.need(files=('GOAL.DAT',))
class Window(unittest.TestCase):
    def test_actual_existing_owner_screens_and_first_pitch_share_the_same_lease(self):
        from goal2.tests.test_native_season_window_t170aa import Screens
        from goal2.game.native_season import NativeSeasonOwner
        from goal2.tests.test_season_pitch_t170ab import policy
        Screens.setUpClass();case=Screens('test_actual_owner_enters_widgets_edits_current_xi_and_transfers_captain_once')
        self.addCleanup(case.doCleanups)
        with patch('goal2.tests.test_native_season_window_t170aa.NativeSeasonOwner',
                   side_effect=lambda owner,state:NativeSeasonOwner(owner,state,frames=True)):
            case.setUp()
        case.test_actual_owner_enters_widgets_edits_current_xi_and_transfers_captain_once()
        connection,_=case.handoffs[0];p=connection.packet
        while not p['frames']:
            if p['decision'] is not None:
                connection.send('answer',decision=p['decision'],answer=policy(p['events'][-1]['data']))
                kind,value=connection.replies.get(timeout=120)
                self.assertEqual((kind,value['action']),('season','answer'))
            connection.send('next',count=1)
            kind,p=connection.replies.get(timeout=120);self.assertEqual(kind,'season')
        self.assertEqual(p['frames'][0]['sequence'],0)
        self.assertEqual(len(p['frames'][0]['players']),22)
        self.assertEqual(case.native.pid,case.pid);self.assertIs(case.native.shared.match,case.native)
        self.assertEqual(case.owner.state,case.before)
