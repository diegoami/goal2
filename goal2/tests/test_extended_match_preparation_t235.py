"""T235: private current-pool projection, never Match or worker activation."""
import copy
import unittest
from unittest.mock import patch

from goal2.engine.original_match import Image, Fixture
from goal2.game import campaign_pool
from goal2.game.watched_match import prepare_watched
from goal2.tests import requires
from goal2.tests.test_assistant_pipe_t183c import model


def prepare(*args, **kwargs):
    from goal2.game.extended_match import prepare_extended_watched
    return prepare_extended_watched(*args, **kwargs)


@requires.need(**requires.HALFTIME)
class Preparation(unittest.TestCase):
    def setUp(self):
        self.model = model()
        f = self.model.state.campaign.next_fixture
        self.fixture = Fixture(f.side_a, f.side_b, index=int(f.fixture_id.split(':')[1]), kind=f.kind)

    def projected(self):
        return prepare(self.model.state, self.model.template_bytes, self.fixture)

    def pool(self, image):
        at = image.far(0xA927) + 2*image.rd(0x6D1A)
        return [int.from_bytes(image.memory[at+2*i:at+2*i+2], 'little') for i in range(80)]

    def selected(self, capacity, count):
        m = self.model; m.resize_squad(capacity)
        words = campaign_pool.validate(m.state)[:count]
        for i, w in enumerate(words):
            rec = bytearray(m.state.players[w]); rec[14] = 100; rec[16] &= ~0xA4
            m.state.players[w] = bytes(rec); m.fill_extra(i, w)
        return words

    def test_default_twenty_is_exact_existing_preparation(self):
        before = copy.deepcopy(self.model.state)
        expected = prepare_watched(before, self.model.template_bytes, self.fixture)
        got, extras = self.projected()
        self.assertEqual(extras, ())
        self.assertEqual(got.memory_component(), expected.memory_component())
        self.assertEqual(self.model.state, before)

    def test_empty_partial_full_capacity_returns_exact_current_native_lists(self):
        for capacity, count in ((22,0),(22,1),(22,2),(24,0),(24,1),(24,3),(24,4)):
            with self.subTest(capacity=capacity, count=count):
                self.model = model(); words = self.selected(capacity, count)
                before = copy.deepcopy(self.model.state); got, extras = self.projected()
                self.assertEqual(extras, tuple(words))
                self.assertEqual(self.pool(got), campaign_pool.validate(before))
                expected = before.starting_eleven + [w for w in before.managed_squad if w not in before.starting_eleven]
                self.assertEqual(got.squad(before.managed_country), expected)
                self.assertEqual(got.players(), before.players)
                self.assertEqual(self.model.state, before)

    def test_actual_selected_promotion_and_outside_recruitment_use_current_pool(self):
        words = self.selected(24,2); m = self.model
        m.swap(m.state.starting_eleven[2], words[0])
        incoming = next(w for w in campaign_pool.validate(m.state) if w not in m.state.extra_squad)
        rec = bytearray(m.state.players[incoming]); rec[14] = 100; rec[16] &= ~0xA4
        m.state.players[incoming] = bytes(rec)
        m.exchange(words[1], incoming)
        before = copy.deepcopy(m.state); got, extras = self.projected()
        self.assertNotEqual(self.pool(Image(before.mem)), campaign_pool.validate(before))
        self.assertEqual(self.pool(got), campaign_pool.validate(before))
        self.assertEqual(extras, tuple(w for w in before.extra_squad if w is not None))
        self.assertIn(words[0], got.squad(before.managed_country)[:11])
        self.assertEqual(m.state, before)

    def test_independent_byte_mask_preserves_finals_calendar_records_and_rng(self):
        self.selected(24,2); s = self.model.state; image = Image(s.mem)
        game = image.far(0xA923); managers = image.far(0xA91F)
        image.memory[game+1] = 2
        image.memory[game+0x14:game+0x1A] = bytes((1,2,3,4,5,6))
        image.memory[game+0x48] = 3
        image.memory[image.DS*16+0xC1E:image.DS*16+0xC20] = bytes((1,2))
        image.memory[managers+129*3] = 19; s.mem = image.memory_component()
        s.campaign.reserve_ids.reverse()
        baseline = prepare_watched(s, self.model.template_bytes, self.fixture)
        before = copy.deepcopy(s); got, _ = self.projected()
        at = baseline.far(0xA927)+2*baseline.rd(0x6D1A)
        allowed = set(range(at,at+160)) | {game+1,managers+129*3}
        changed = {i for i,(a,b) in enumerate(zip(baseline.memory,got.memory)) if a!=b}
        self.assertTrue(changed); self.assertLessEqual(changed, allowed)
        self.assertEqual(got.memory[game+0x14:game+0x1A], bytes((1,2,3,4,5,6)))
        self.assertEqual(got.memory[game+0x48], 3)
        self.assertEqual(got.rd_far(0xA923,1,1), 1)
        self.assertEqual(got.memory[managers+129*3], s.managed_country)
        self.assertEqual(got.build_problems(), [])
        self.assertEqual(s, before)

    def test_malformed_selection_and_multiple_managers_refuse_purely(self):
        self.selected(22,1); original = copy.deepcopy(self.model.state)
        cases = []
        for capacity,slots in ((True,[]),(23,[None]*3),(22,[1,1]),(22,[3061,None]),(22,[1,None]),(22,[True,None]),(22,[None])):
            s=copy.deepcopy(original); s.squad_capacity=capacity; s.extra_squad=slots; cases.append(s)
        s=copy.deepcopy(original); row=bytearray(s.countries[5]);row[0x2E]=130;s.countries[5]=bytes(row);cases.append(s)
        for s in cases:
            before=copy.deepcopy(s)
            with self.assertRaises(ValueError):prepare(s,self.model.template_bytes,self.fixture)
            self.assertEqual(s,before)

    def test_zero_wrapped_overlapping_and_outside_allocations_refuse_without_backend(self):
        self.selected(24,1); original=copy.deepcopy(self.model.state)
        variants=[(0xA927,0,0),(0xA91F,0,0),(0xA923,0,0),
                  (0xA927,0xFFF0,0x1000),(0xA91F,0xFFF0,0x1000),
                  (0xA927,0xFFF0,0xFFFF),(0xA91F,0xFFF0,0xFFFF),
                  (0xA923,0xFFF0,0xFFFF)]
        for ptr,offset,segment in variants:
            s=copy.deepcopy(original);image=Image(s.mem);at=image.DS*16+ptr
            image.memory[at:at+4]=offset.to_bytes(2,'little')+segment.to_bytes(2,'little');s.mem=image.memory_component()
            before=copy.deepcopy(s)
            with self.subTest(ptr=ptr,offset=offset,segment=segment), self.assertRaises(ValueError):
                prepare(s,self.model.template_bytes,self.fixture)
            self.assertEqual(s,before)
        s=copy.deepcopy(original);image=Image(s.mem);at=image.DS*16+0xA927
        image.memory[at:at+4]=image.memory[image.DS*16+0xA917:image.DS*16+0xA91B];s.mem=image.memory_component()
        with self.assertRaises(ValueError):prepare(s,self.model.template_bytes,self.fixture)
        s=copy.deepcopy(original);image=Image(s.mem);at=image.DS*16+0x6D1A
        image.memory[at:at+2]=bytes(2);s.mem=image.memory_component()
        with self.assertRaises(ValueError):prepare(s,self.model.template_bytes,self.fixture)
        with patch('goal2.game.watched_match.Match',side_effect=AssertionError('no engine')), \
             patch('goal2.game.best_twenty_state.prepare',side_effect=AssertionError('no assistant projection')):
            self.projected()


if __name__ == '__main__': unittest.main()
