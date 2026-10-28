"""[designed: T137] Consume proposed F034/F035 without changing the original machine.

Genuine E006 and an original-key new career exercise the current records. Explicit
host Image copies exercise malformed records and synthetic boundary contexts;
they are never run as guest campaigns or called behavioral corroboration.
"""
import hashlib
from pathlib import Path
import unittest

from goal2.tests import requires

NEEDS = dict(modules=('unicorn',), files=('e006-r0001-main.sav',
             'e039-r0005-date-call.sav', 'GOAL.DAT'))
EXPECTED = {12: ('Germany', 'giant', 'eclectic'), 1: ('Albania', 'poor', 'very bad'),
            27: ('Sweden', 'major', 'exceptional'), 128: ('Yemen AR', 'very small', 'negligible')}
PINS = {'manager.py': '1d4340eb8ab57c65c7d4186390842d769eaaf954ed7f205ca9ad83a3f1bba5bf',
        'country.py': 'd2ab97927ecd7ae269f9351f7244dde9eee56af41ffa774a34f520428c4c7b3a'}


def genuine():
    from goal2.core import Core
    return Core.start((requires.CACHE/'e006-r0001-main.sav').read_bytes()).core


def host_copy(core):
    from goal2.core.views import Memory
    from goal2.engine.original_match.image import Image
    return Memory(Image(core.wait.state._image.memory_component()))


class PureContract(unittest.TestCase):
    def test_vendored_modules_are_the_exact_registered_sources(self):
        from goal2.engine.team_card import manager, country
        for module in (manager, country):
            path = Path(module.__file__)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), PINS[path.name])

    def test_manager_declared_cells_glyphs_width_and_malformed_records(self):
        from goal2.engine.team_card.manager import manager_text, manager_payload
        def record(payload):
            return bytes([len(payload)])+payload+b'!'*(12-len(payload))
        self.assertEqual(manager_text(ord('B'), record(b'Vogts\0')), 'B Vogts ')
        self.assertEqual(manager_text(1, record(b'A\0B\x7f\x82')), '☺ A B⌂é')
        self.assertEqual(manager_text(0, record(b' X ')), '   X ')
        self.assertEqual(manager_payload(255, record(b'123456789012')), b'\xff 123456789012')
        for initial, raw in ((True, record(b'A')), (-1, record(b'A')),
                             (256, record(b'A')), (65, b'\x01A'), (65, b'\x0d'+b'A'*12)):
            with self.subTest(initial=initial, raw=raw), self.assertRaises(ValueError):
                manager_text(initial, raw)


@requires.need(**NEEDS)
class CurrentMemory(unittest.TestCase):
    def setUp(self):
        self.core = genuine()
        self.before = self.core.save()
        self.image = self.core.wait.state._image
        self.image_before = self.image.memory_component()

    def tearDown(self):
        self.assertEqual(self.core.save(), self.before)
        self.assertEqual(self.image.memory_component(), self.image_before)

    def test_germany_name_projects_the_declared_nul_as_a_blank(self):
        from goal2.core.views import Memory
        mem = Memory(self.core.wait.state)
        self.assertEqual(mem.manager_name(12), 'B Vogts ')
        # The generic Pascal reader keeps its existing contract.
        from goal2.core.views import MANAGER_NAMES
        self.assertEqual(mem.pstr(mem.far(MANAGER_NAMES)+13*12), 'Vogts\0')

    def test_independent_country_labels_and_remaining_placeholders(self):
        from goal2.core import views
        for c, (name, status, skill) in EXPECTED.items():
            with self.subTest(country=c):
                card = views.country_card(self.core.wait.state, c)
                self.assertEqual((card['name'], card['status'], card['skill']), (name, status, skill))
                self.assertEqual(set(card['not_decoded']),
                                 {'ranking top', 'strips'})  # T144 consumes the delivered three panels.

    def test_original_key_new_career_uses_its_current_human_manager(self):
        from goal2.core import Core, views
        from goal2.core.driver import Driver
        core = Core.boot((requires.CACHE/'e039-r0005-date-call.sav').read_bytes(),
                         (1991, 10, 4), goal_dat=requires.CACHE/'GOAL.DAT', title_key='n').core
        Driver(core).new_game(12, 'J Coach')
        before = core.save()
        mem = views.Memory(core.wait.state)
        self.assertEqual(mem.country(12, 0x2e), 129)
        card = views.country_card(core.wait.state, 12)
        self.assertEqual((card['status'], card['skill']), ('giant', 'unknown'))
        self.assertEqual(card['skill'], views.desk(core.wait.state)['rating'])
        self.assertEqual(core.save(), before)

    def test_host_contexts_use_selected_manager_ability_not_confidence(self):
        from goal2.core import views
        for m in (0, 129, 130, 131, 132, 133, 134):
            for ability in (0, 1, 8, 9, 128, 129, 248, 249, 255):
                with self.subTest(manager=m, ability=ability):
                    mem = host_copy(self.core)
                    mem.mem[mem.far(views.COUNTRIES)+191*12+46] = m
                    base = mem.far(views.MANAGERS)+3*m
                    mem.mem[base:base+3] = bytes([12, ability, 255-ability])
                    expected = (None if not m else 'unknown' if not ability else
                                mem.pstr(mem.ds*16+0x6eb4+16*mem.ds_byte(0x7894+(ability-1)//8)))
                    labels = mem.country_labels(12)
                    self.assertEqual(labels, {'status': 'giant', 'skill': expected})
                    card = views.country_card(mem.image, 12)
                    self.assertEqual((card['status'], card['skill']), ('giant', expected))

    def test_all_label_band_endpoints_use_bounded_current_tables(self):
        from goal2.engine.team_card.country import country_status, manager_skill
        from goal2.core import views
        mem = views.Memory(self.core.wait.state)
        for ability in range(1, 256):
            expected = mem.pstr(mem.ds*16+0x6eb4+16*mem.ds_byte(0x7894+(ability-1)//8))
            self.assertEqual(manager_skill(134, ability, mem.read_ds, mem.read_code), expected)
        ranks = {}
        for c in range(1, 5):
            for r in range(1, 33):
                for w in range(1, 129):
                    ranks.setdefault(((5-c)*(33-r)+129-w)//2, (c, r, w))
        self.assertEqual(set(ranks), set(range(1, 129)))
        for rating in range(1, 129):
            expected = mem.pstr(mem.ds*16+0x6eb4+16*mem.ds_byte(0x7884+(rating-1)//8))
            self.assertEqual(country_status(*ranks[rating], mem.read_ds), expected)

    def test_malformed_records_and_out_of_bounds_callbacks_are_host_errors(self):
        from goal2.core import views
        mem = host_copy(self.core)
        for m in (-1, 135, True):
            with self.subTest(manager=m), self.assertRaises(ValueError):
                mem.manager_name(m)
        for c in (0, 129, True):
            with self.subTest(country=c), self.assertRaises(ValueError):
                mem.country_labels(c)
        for args in ((-1, 1), (65535, 2), (0, 0), (True, 1)):
            with self.subTest(ds=args), self.assertRaises(ValueError):mem.read_ds(*args)
        for args in ((0xffff, 0, 8), (0x1771, 65535, 2), (0, -1, 1), (0, 0, 0)):
            with self.subTest(code=args), self.assertRaises(ValueError):mem.read_code(*args)
        for args in ((-1, 1), (len(mem.mem), 1), (0, 65537), (True, 1)):
            with self.subTest(memory=args), self.assertRaises(ValueError):mem.read_bytes(*args)
        a = mem.far(views.MANAGER_NAMES)+13*12
        mem.mem[a] = 13
        with self.assertRaises(ValueError):mem.manager_name(12)
        a = mem.far(views.COUNTRIES)+191*12
        mem.mem[a+46] = 135
        with self.assertRaises(ValueError):mem.country_labels(12)
        mem.mem[a+46] = 12;mem.mem[a+44] = 0
        with self.assertRaises(ValueError):mem.country_labels(12)


@requires.need(**{**NEEDS, 'modules': ('unicorn', 'PySide6')})
class NativeCard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_card_paints_labels_blank_skill_and_legacy_fallback_with_roles(self):
        from goal2.core import views
        from goal2.desktop.country_card import CountryCardView
        from goal2.game.country_card import NOT_DECODED
        from goal2.desktop.core_roles import role_code
        core = genuine();before = core.save()
        for country in EXPECTED:
            card = views.country_card(core.wait.state, country)
            for width, height in ((820, 640), (320, 1320)):
                widget = CountryCardView();self.addCleanup(widget.close)
                widget.resize(round(width*widget.scale()), round(height*widget.scale()))
                widget.set_card(card)
                drawn = []
                widget.text = lambda p, x, y, value, *a, **kw: drawn.append(str(value))
                widget.grab();self.app.processEvents()
                self.assertIn(card['status'], drawn);self.assertIn(card['skill'], drawn)
                self.assertIn(NOT_DECODED, drawn)
                self.assertEqual(widget.card['eleven'], [role_code(p) for p in card['squad'][:11]])
                self.assertIn(card['status'], widget.accessibleName())
                widget.set_card({**card, 'skill': None});drawn.clear()
                widget.grab();self.app.processEvents()
                self.assertNotIn('None', drawn);self.assertIn('', drawn)
                legacy = {k: v for k, v in card.items() if k not in ('status', 'skill')}
                widget.set_card(legacy);drawn.clear();widget.grab();self.app.processEvents()
                self.assertGreaterEqual(drawn.count(NOT_DECODED), 2)
        self.assertEqual(core.save(), before)

    def test_real_painted_country_cards_retain_the_supported_bounds(self):
        from goal2.core import views
        from goal2.desktop.country_card import CountryCardView
        core = genuine();before = core.save()
        for country in EXPECTED:
            for width, height in ((820, 640), (320, 1320)):
                widget = CountryCardView();self.addCleanup(widget.close)
                widget.resize(round(width*widget.scale()), round(height*widget.scale()))
                widget.set_card(views.country_card(core.wait.state, country))
                widget.grab();self.app.processEvents()
                self.assertGreater(widget.bottom, 0)
                self.assertLessEqual(widget.bottom, height, (country, width, height, widget.bottom))
        self.assertEqual(core.save(), before)


if __name__ == '__main__':
    unittest.main()
