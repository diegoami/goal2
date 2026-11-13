"""T226: every taker decision the core recognises reaches the window's selector.

[confirmed: T225's package run 43443697191] A role-4 free-kick decision in a watched match raised KeyError: 4 in
`TakerPages.offer`, leaving the round page at set-piece-select. [confirmed: T120, T220] The catalogue recognises the
CC7B taker roles 2 (corner), 3 (penalty), 4 (free kick) and 5 (goal kick). The titles are [designed: T120, T226].
"""
import unittest


class Titles(unittest.TestCase):

    def test_each_recognised_taker_role_has_its_title(self):
        from goal2.desktop.core_takers import taker_title
        self.assertEqual({role: taker_title(role) for role in (2, 3, 4, 5)},
                         {2: 'CORNER TAKER', 3: 'PENALTY TAKER', 4: 'FREE KICK TAKER', 5: 'GOAL KICK TAKER'})

    def test_the_titles_cover_every_role_the_catalogue_recognises(self):
        from goal2.core import screens
        from goal2.desktop.core_takers import TAKER_TITLES
        # roles 3/4 are the ones T220 added with their origin frames; 2/5 are T120's
        self.assertTrue(set(screens.TAKER_ORIGINS) | {2, 5} <= set(TAKER_TITLES))

    def test_a_role_outside_them_is_refused_by_name(self):
        from goal2.desktop.core_takers import taker_title
        for role in (0, 1, 6):
            with self.assertRaisesRegex(ValueError, f'taker role {role}'):
                taker_title(role)


if __name__ == '__main__':
    unittest.main()
