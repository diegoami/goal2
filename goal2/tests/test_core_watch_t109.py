"""[designed: T109] Watched play through the core, with no guest-memory writes by the tests."""
import unittest

from goal2.tests import requires

NEEDS = dict(modules=('unicorn',), files=('e006-r0001-main.sav', 'GOAL.DAT'))


def live():
    from goal2.core import Core
    from goal2.core.driver import Driver
    d = Driver(Core.start((requires.CACHE / 'e006-r0001-main.sav').read_bytes()).core)
    d.to_menu()
    d.round_start(watch=True)
    d.kick_off()
    return d


@requires.need(**NEEDS)
class Poll(unittest.TestCase):
    def test_one_poll_and_resume(self):
        from goal2.core import Core, views
        d = live()
        self.assertEqual(d.wait.kind, 'match-live')
        self.assertTrue(d.wait.poll)
        first = views.pitch(d.wait.state, 0, 0)
        self.assertEqual(len(first['players']), 22)
        saved = d.core.save()
        d.live_step()
        self.assertEqual(d.wait.kind, 'match-live')
        self.assertEqual(d.wait.view['slot'], 2)
        other = Core.load(saved)
        other.advance()
        self.assertEqual(other.memory_sha256(), d.core.memory_sha256())
        self.assertEqual(other.keys, d.core.keys)


if __name__ == '__main__':
    unittest.main()
