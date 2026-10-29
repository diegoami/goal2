"""T144: consume proposed F036/F037/F038 without changing original memory.

Typed expectations below come from the genuine E015-r0007 screens/receipts at
archaeology a42c2cbe. Authored host-image copies are boundary controls, never
guest campaigns or independent behavioural corroboration.
"""
import hashlib
from pathlib import Path
import unittest

from goal2.tests import requires

PINS = {
    'team_bars.py': '4631ccf2c135a151800d0cddd6a84819aaf7ef0ce7b1c646fc746a2bb94582cf',
    'team_skills.py': '1f530c1f7a9bad85af350343f222f8b702f508244ab7c7abd776da0dac858c6a',
    'team_performance.py': 'cd65009941455e7a0c1bd98a7d920ad3e57782f47e4940ccfe949c1a3e17200a',
    'team_characteristics.py': '29ce61b550537fa0e98c31144124b7e1cd07a1bd2767fc8ff3d9c5b1a465efe0',
}
FIXTURES = {
    'selection': ('T144-E015-snap-0003.sav', '4e5c2d51fcfb9140c37ef64046b2a1e62644d76b12242ef01321013a7a0dd55e'),
    'friendly': ('T144-E015-snap-0120.sav', 'e0050208da61a394d690791da72c1201c42214f6ce2f15abd8b194750b191e34'),
    'year_one': ('T144-E014-year-one.sav', '291d0eb3b0dcec348c0e166703f8033f795e2b4f1bc0dd4cd67f0888b8622b99'),
}


def image(name):
    from goal2.engine.original_match.image import Image
    path, digest = FIXTURES[name]
    raw = (requires.CACHE/path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise AssertionError('wrong genuine T144 fixture: '+path)
    return Image.from_savestate(raw)


class VendorContract(unittest.TestCase):
    def test_four_delivered_decoders_are_byte_identical_to_the_accepted_pin(self):
        from goal2.engine.team_card import team_bars, team_skills, team_performance, team_characteristics
        for module in (team_bars, team_skills, team_performance, team_characteristics):
            p = Path(module.__file__)
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), PINS[p.name])


@requires.need(modules=('unicorn',), files=tuple(v[0] for v in FIXTURES.values())+('e006-r0001-main.sav',))
class LiveProjection(unittest.TestCase):
    def test_genuine_selection_matches_the_recorded_denmark_screen(self):
        from goal2.core import views
        state = image('selection');before = state.memory_component()
        card = views.country_card(state, 7)
        self.assertEqual(card['team_skills']['line_sums'], [225, 1048, 1031, 395])
        self.assertEqual([b['cells'] for b in card['team_skills']['bars']], [21, 25, 25, 9])
        self.assertIsNone(card['performance'])
        chars = card['characteristics']
        self.assertEqual(chars['aggregates'], dict(morale=17, fitness=25, hardness=10, energy=25, age=29, caps=0))
        self.assertEqual([(d['field'], d['text'], d['cells']) for d in chars['descriptors']],
                         [('hardness', 'tough', 10), ('fitness', 'very fit', 12),
                          ('energy', 'energetic', 12), ('morale', 'not bad', 8)])
        self.assertEqual(set(card['not_decoded']), {'ranking top', 'strips'})
        self.assertEqual(state.memory_component(), before)

    def test_genuine_friendly_matches_the_recorded_italy_screen(self):
        from goal2.core import views
        state = image('friendly');before = state.memory_component()
        card = views.country_card(state, 16)
        self.assertEqual(card['team_skills']['line_sums'], [227, 805, 823, 318])
        self.assertEqual([b['cells'] for b in card['team_skills']['bars']], [22, 19, 20, 7])
        perf = card['performance']
        self.assertEqual((perf['side'], perf['team']), (1, 16))
        self.assertEqual(perf['role_sums'], [99, 497, 600, 204])
        self.assertEqual([b['cells'] for b in perf['bars']], [9, 12, 14, 4])
        self.assertEqual(card['characteristics']['aggregates'],
                         dict(morale=15, fitness=31, hardness=11, energy=27, age=29, caps=0))
        self.assertEqual([(d['text'], d['cells']) for d in card['characteristics']['descriptors']],
                         [('aggressive', 11), ('total', 15), ('full of life', 13), ('could be worse', 7)])
        # [derived: F037] A non-participant shows side0, rather than its own ratings.
        self.assertEqual(views.country_card(state, 7)['performance']['team'], 29)
        self.assertEqual(state.memory_component(), before)

    def test_year_one_nonzero_caps_and_all_country_reads_are_pure(self):
        from goal2.core import views
        state = image('year_one');before = state.memory_component();caps = []
        for country in range(1, 129):
            card = views.country_card(state, country)
            values = card['characteristics']['aggregates']
            caps.append(values['caps'])
            numbers = {n['field']: n for n in card['characteristics']['numbers']}
            self.assertEqual(numbers['caps']['text'], str(values['caps']))
            self.assertEqual(numbers['age']['text'], str(values['age']))
        # [derived: F038 original-r2, all128 genuine E014 year-one renders]
        self.assertEqual(max(caps), 12)
        self.assertEqual(state.memory_component(), before)

    def test_complete_live_core_save_is_unchanged_around_display_reads(self):
        from goal2.core import Core, views
        core = Core.start((requires.CACHE/'e006-r0001-main.sav').read_bytes()).core
        before = core.save()
        for country in (1, 7, 12, 16, 27, 128):
            card = views.country_card(core.wait.state, country)
            self.assertTrue({'team_skills', 'performance', 'characteristics'} <= card.keys())
        self.assertEqual(core.save(), before)

    def test_callbacks_have_exact_widths_and_support_zero_and_human_records(self):
        from goal2.core import views
        mem = views.Memory(image('selection'))
        for method, limit, width in ((mem.country_record, 128, 191),
                                     (mem.player_record, 3060, 20),
                                     (mem.manager_record, 134, 3)):
            self.assertEqual(len(method(0)), width)
            self.assertEqual(len(method(limit)), width)
            for bad in (-1, limit+1, True, '1'):
                with self.subTest(reader=method.__name__, bad=bad), self.assertRaises(ValueError):
                    method(bad)

    def test_authored_gate_inputs_do_not_turn_unavailable_into_zero_data(self):
        from goal2.core import views
        for set_up, menu_used in ((0, 0), (0, 1), (1, 0), (1, 1)):
            state = image('friendly');mem = views.Memory(state)
            mem.mem[mem.ds*16+0x0c1e] = set_up
            mem.mem[mem.ds*16+0x0c1f] = menu_used
            before = state.memory_component()
            card = views.country_card(state, 16)
            if set_up and menu_used:self.assertIsNotNone(card['performance'])
            else:self.assertIsNone(card['performance'])
            self.assertEqual(state.memory_component(), before)

    @requires.need(files=('e039-r0005-date-call.sav', 'GOAL.DAT'))
    def test_original_key_human_manager_and_tactic_changes_are_read_fresh(self):
        from goal2.core import Core, views
        from goal2.core.driver import Driver
        core = Core.boot((requires.CACHE/'e039-r0005-date-call.sav').read_bytes(),
                         (1991, 10, 4), goal_dat=requires.CACHE/'GOAL.DAT', title_key='n').core
        driver = Driver(core);driver.new_game(16, 'J Coach')
        mem = views.Memory(core.wait.state)
        self.assertEqual(mem.country(16, 0x2e), 129)
        driver.set_tactic(5, False)
        before_read = core.save();first = views.country_card(core.wait.state, 16)
        self.assertEqual(core.save(), before_read)
        driver.set_tactic(5, True)
        before_read = core.save();second = views.country_card(core.wait.state, 16)
        self.assertEqual(core.save(), before_read)
        # F036: ten outfielders each move M div8=2 from defence to attack.
        a, b = first['team_skills']['line_sums'], second['team_skills']['line_sums']
        self.assertEqual(b, [a[0], a[1]-20, a[2], a[3]+20])


@requires.need(modules=('unicorn',), files=(FIXTURES['selection'][0],))
class AuthoredBoundaries(unittest.TestCase):
    def setUp(self):
        from goal2.core import views
        self.views = views;self.state = image('selection');self.mem = views.Memory(self.state)

    def squad(self, words):
        start = self.mem.far(self.views.COUNTRIES)+191*7
        self.mem.mem[start:start+22] = b''.join(w.to_bytes(2, 'little') for w in words)

    def player(self, word, *, energy=20, morale=16, fitness=20, hardness=8, age=22, caps=11,
               position=0, performance=0x37, status=0):
        p = bytearray(20)
        p[0], p[1], p[4], p[5], p[6], p[7] = 7, age, 100, hardness, position, position
        p[8:10] = caps.to_bytes(2, 'little')
        p[12], p[13], p[14], p[16] = morale & 255, fitness & 255, energy & 255, status
        p[18:20] = performance.to_bytes(2, 'little')
        start = self.mem.far(self.views.PLAYERS)+20*word
        self.mem.mem[start:start+20] = p

    def put_ds(self, offset, raw):
        self.mem.mem[self.mem.ds*16+offset:self.mem.ds*16+offset+len(raw)] = raw

    def panels(self):
        before = self.state.memory_component();result = self.mem.country_panels(7)
        self.assertEqual(self.state.memory_component(), before)
        return result

    def open_performance(self):
        self.put_ds(0x0c1e, b'\x01\x01')
        self.put_ds(0x9b34, b'\x07\x00\x10\x00')

    def test_manager_zero_and_human_read_ability_not_confidence(self):
        base = self.mem.far(self.views.COUNTRIES)+191*7
        for ability in (0, 255):
            results = []
            for manager in (0, 129, 134):
                self.mem.mem[base+46] = manager
                at = self.mem.far(self.views.MANAGERS)+3*manager
                self.mem.mem[at:at+3] = bytes([7, ability, 255-ability])
                results.append(self.panels()['team_skills'])
                self.mem.mem[at+2] ^= 255
                self.assertEqual(results[-1], self.panels()['team_skills'])
            self.assertTrue(all(r == results[0] for r in results))

    def test_zero_words_are_skipped_only_by_skills_not_the_other_panels(self):
        self.squad([0]*11);self.player(0, energy=32);self.open_performance()
        result = self.panels()
        self.assertEqual(result['team_skills']['line_sums'], [0, 0, 0, 0])
        self.assertEqual(result['performance']['role_sums'], [1100, 0, 0, 0])
        self.assertEqual(result['characteristics']['aggregates'],
                         dict(morale=16, fitness=20, hardness=8, energy=32, age=22, caps=11))

    def test_unavailable_starters_keep_the_divisor_eleven(self):
        self.player(1);self.player(2, energy=0);self.squad([2]+[1]*10)
        self.assertEqual(self.panels()['characteristics']['aggregates'],
                         dict(morale=15, fitness=18, hardness=7, energy=18, age=20, caps=10))
        self.player(2, status=0x80)
        self.assertEqual(self.panels()['characteristics']['aggregates']['caps'], 10)

    def test_performance_signed_hybrid_half_and_rating_threshold(self):
        self.player(0, energy=0, performance=0xffd3);self.squad([1]+[0]*10);self.open_performance()
        self.player(1, position=3, performance=(-196) & 0xffff)
        self.put_ds(0x0d7c+3, b'\x04');self.put_ds(0x0d4e+3, b'\x05')
        self.assertEqual(self.panels()['performance']['role_sums'], [0, -75, -75, 0])
        for word, expected in ((5055, 5100), (5056, -4899), (10055, 100), (0x7fff, 22812)):
            self.player(1, performance=word)
            self.assertEqual(self.panels()['performance']['role_sums'], [expected, 0, 0, 0])

    def test_valid_off_table_descriptor_and_host_label_refusal_remain_distinct(self):
        self.player(1, hardness=17);self.squad([1]*11)
        d = self.panels()['characteristics']['descriptors'][0]
        self.assertEqual((d['text'], d['cells'], d['in_table']), ('injured', 17, False))
        index = self.mem.ds_byte(0x78c4+17)
        self.put_ds(0x6eb4+16*index, b'\x10')
        with self.assertRaisesRegex(ValueError, 'label exceeds'):
            self.panels()

    def test_wrapped_negative_fitness_preserves_full_bar_length(self):
        self.player(1, fitness=-128);self.squad([1]*11)
        self.put_ds(0x78d5+5830, b'\x00');self.put_ds(0x6eb4, b'\x04edge'+b'\x00'*11)
        result = self.panels()['characteristics']
        self.assertEqual(result['aggregates']['fitness'], 5830)
        d = next(d for d in result['descriptors'] if d['field'] == 'fitness')
        self.assertEqual((d['text'], d['cells'], d['in_table']), ('edge', 867, False))


@requires.need(modules=('unicorn', 'PySide6'), files=tuple(v[0] for v in FIXTURES.values()))
class PaintedPanels(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        from goal2.desktop.style import load_fonts
        cls.app = QApplication.instance() or QApplication([])
        load_fonts()

    def test_original_descriptor_highlight_wraps_without_clamping_its_extent(self):
        from goal2.desktop.country_card import characteristic_view
        rows = characteristic_view([dict(row=20, column=46, text='A', cells=81)])
        self.assertEqual(rows[0][0], ('A', True))
        self.assertTrue(all(filled for _, filled in rows[0]))
        self.assertEqual(rows[1][0], ('■', True))
        self.assertEqual(rows[1][1], ('■', False))
        huge = characteristic_view([dict(row=20, column=46, text='', cells=867)])
        self.assertTrue(all(filled for row in huge for _, filled in row))

    def test_genuine_card_paints_all_panels_in_wide_narrow_and_team_info_layouts(self):
        from goal2.core import views
        from goal2.desktop.country_card import CountryCardView
        for fixture, country, expected in (('selection', 7, [21, 25, 25, 9]+[None]*4),
                                            ('friendly', 16, [22, 19, 20, 7, 9, 12, 14, 4])):
            state = image(fixture);before = state.memory_component()
            card = views.country_card(state, country)
            for factor in (1, 2):
                for width, height, team_info in ((740, 640, False), (320, 1320, False), (740, 640, True)):
                    with self.subTest(fixture=fixture, factor=factor, width=width, team_info=team_info):
                        widget = CountryCardView(team_info=team_info);self.addCleanup(widget.close)
                        widget.setProperty('pageScale', factor);widget.resize(width*factor, height*factor)
                        widget.set_card(card);drawn = [];original = widget.text
                        def text(painter, x, y, value, *args, **kwargs):
                            drawn.append(str(value));return original(painter, x, y, value, *args, **kwargs)
                        widget.text = text;shot = widget.grab();self.app.processEvents()
                        for title in ('TEAM SKILLS', 'PERFORMANCE', 'CHARACTERISTICS'):
                            self.assertIn(title, drawn)
                        self.assertEqual([row[-1] for row in widget.painted_bars], expected)
                        # Actual pixels, rather than trusting the renderer's trace:
                        # original attribute0x70 has grey background, absent highlight black.
                        raster = shot.toImage();pixel_scale = factor*shot.devicePixelRatio()
                        for x, y, bar_width, count, filled in widget.painted_bars:
                            for cell in range(count):
                                at_x = round((x+(cell+0.5)*bar_width/count)*pixel_scale)
                                at_y = round((y-15)*pixel_scale)
                                color = '#aaaaaa' if filled is not None and cell < filled else '#000000'
                                self.assertEqual(raster.pixelColor(at_x, at_y).name(), color)
                        self.assertLessEqual(widget.bottom, height)
                        self.assertLessEqual(widget.right, width)
                        self.assertIn('Caps 0', ' '.join(drawn));self.assertIn('Age 29', ' '.join(drawn))
                        from goal2.desktop.core_roles import role_code
                        self.assertEqual(widget.card['eleven'], [role_code(p) for p in card['squad'][:11]])
                        if fixture == 'friendly':self.assertEqual(widget.card['eleven'][7:9], ['m', 'M'])
                        self.assertNotIn('TEAM BARS', drawn)
            self.assertEqual(state.memory_component(), before)

    def test_team_info_at_its_minimum_shrinks_every_panel_inside_its_bounds(self):
        """[designed: T144] The compact column's minimum is below its natural size (T107/T141
        reserve); there the whole column shrinks uniformly: every bar and title, nothing clipped."""
        from goal2.core import views
        from goal2.desktop.country_card import CountryCardView, TEAM_INFO_SHRINK
        state = image('friendly');card = views.country_card(state, 16)
        for factor in (1, 2):
            with self.subTest(factor=factor):
                widget = CountryCardView(team_info=True);self.addCleanup(widget.close)
                widget.setProperty('pageScale', factor)
                need = widget.minimumSizeHint();natural = widget.sizeHint()
                self.assertLess(need.width(), natural.width());self.assertLess(need.height(), natural.height())
                widget.resize(need);widget.set_card(card);drawn = [];original = widget.text
                def text(painter, x, y, value, *args, **kwargs):
                    drawn.append(str(value));return original(painter, x, y, value, *args, **kwargs)
                widget.text = text;shot = widget.grab();self.app.processEvents()
                for title in ('TEAM SKILLS', 'PERFORMANCE', 'CHARACTERISTICS'):
                    self.assertIn(title, drawn)
                self.assertAlmostEqual(widget.factor, TEAM_INFO_SHRINK, places=2)
                self.assertEqual([row[-1] for row in widget.painted_bars], [22, 19, 20, 7, 9, 12, 14, 4])
                raster = shot.toImage();pixel_scale = factor*shot.devicePixelRatio()
                for x, y, bar_width, count, filled in widget.painted_bars:
                    for cell in range(count):
                        at_x = round((x+(cell+0.5)*bar_width/count)*pixel_scale)
                        at_y = round((y-15*widget.factor)*pixel_scale)
                        color = '#aaaaaa' if cell < filled else '#000000'
                        self.assertEqual(raster.pixelColor(at_x, at_y).name(), color, (x, y, cell))
                self.assertLessEqual(widget.bottom, need.height()/factor)
                self.assertLessEqual(widget.right, need.width()/factor)

    def test_a_paint_reads_current_memory_again_without_set_card(self):
        from goal2.core import views
        from goal2.desktop.country_card import CountryCardView
        state = image('selection');mem = views.Memory(state);reads = []
        def read():
            reads.append(True);return views.country_card(state, 7)
        widget = CountryCardView();self.addCleanup(widget.close);widget.resize(740, 640)
        widget.set_card(read(), reader=read);widget.grab();self.app.processEvents()
        old = widget.card['team_skills']['line_sums'][0]
        # Authored host-image change only; no original guest or actual save is edited.
        keeper = mem.country(7, 0, 2)
        mem.mem[mem.far(views.PLAYERS)+20*keeper+0x0e] = 0
        after_edit = state.memory_component();widget.grab();self.app.processEvents()
        self.assertNotEqual(widget.card['team_skills']['line_sums'][0], old)
        self.assertGreaterEqual(len(reads), 3)
        self.assertEqual(state.memory_component(), after_edit)

    @requires.need(files=('e006-r0001-main.sav', 'GOAL.DAT'))
    def test_actual_team_info_has_current_panels_and_preserves_contextual_back(self):
        from unittest.mock import Mock
        from goal2.desktop.core_model import CoreModel
        from goal2.desktop.core_window import CoreWindow
        model = CoreModel.open(requires.CACHE/'e006-r0001-main.sav', requires.CACHE/'GOAL.DAT',
                               requires.CACHE/'T144-never-written.g2core')
        before = model.core.save()
        model.country_card = Mock(wraps=model.country_card)
        window = CoreWindow(model);self.addCleanup(window.close)
        window.resize(1440, 900);window.show();self.app.processEvents()
        self.assertEqual(model.country_card.call_count, 0, 'Hidden Team Info must not decode every refresh')
        window.core_routes['team info'].click();self.app.processEvents();window.grab()
        self.assertGreater(model.country_card.call_count, 0)
        self.assertTrue(window.core_team_panels.isVisible())
        self.assertEqual(window.core_team_panels.card['country'], model.team()['country'])
        self.assertEqual(len(window.core_team_panels.painted_bars), 8)
        pane = window.core_team_panels
        self.assertLessEqual(pane.bottom, pane.height()/pane.scale())
        self.assertLessEqual(pane.right, pane.width()/pane.scale())
        self.assertTrue(window.core_team_info_back.isVisible())
        self.assertTrue(window.tactics[0][1].isVisible())
        for _, row in window.tactics:
            self.assertGreaterEqual(row.width(), row.sizeHint().width())
        window.core_team_info_back.click();self.app.processEvents()
        self.assertEqual(window.page_stack.currentIndex(), 0)
        self.assertEqual(model.core.save(), before)


if __name__ == '__main__':
    unittest.main()
