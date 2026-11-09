"""[confirmed: upstream T131, goal2-archaeology 7fbfd2e9, #707; goal2 #695, T220] The penalty (role 3) and free-kick
(role 4) taker screens of the Core, from the kept original-key inputs.

T131's description is docs/requests/400-roles34.md and its manifest notes/400-roles34/delivery.json in goal2-archaeology.
Three cases, each of five kept Core states (`Core.save()`, magic G2C1; the private owner Drive folder
`goal2-archaeology/400-roles34-20261109/`, pulled into .cache/ by hand: they are no GOAL2 asset of this repository's):
0 the wait before the decision; 1 the decision pending at the poll 0791:CC54; 2 Space, the board, the blocking read
0791:CF3A; 3 Return, back at the same selector; 4 Return again, the pick accepted and the match resumed at 0791:93C2.
Each name carries the first 16 hex digits of the file's SHA-256, and the full digest is checked here.

Role 3 Denmark (country 7, side 1) v England, round 7 minute 33; role 4 England (9, side 0) v Portugal, round 3
minute 71; role 4 Albania (1, side 1) v Cyprus, round 3 minute 58. **Albania's case is the weakest**: T131's verifier
compares an unchanged Core's own stop with the decision for role 3 and for England's role 4, but not for Albania's,
whose unchanged Core stops earlier at a role 3 of its own (minute 13), so its input comes from T131's label-adapted run
alone. Role 3 was kept at side 1 only; its side 0 (round 10 minute 78, search-r1 step 21) is a recorded observation of the
role and side bytes, with no kept state.

What is tested, as roles 2 and 5 are in test_core_takers_t120.py: each kept decision is recognised with its role, side,
country, highlight and stored pick as the checkpoint records them; the keys the original takes continue it (Space the
board, Return the same selector, Return the pick), to the very machine each later checkpoint kept; and the catalogue
does not guess: the entry asks for the caller 6D4E's frame T131 read (6EEF with [10, 3, side] for the penalty, 6F92
with [11, 4, side] for the free kick), and answers nothing for a role 3 or 4 without it.
"""
import hashlib
import unittest

from goal2.tests import requires

SELECT, PITCH, LIVE, NOTICE = "set-piece-select", "set-piece-pitch", "match-live", "substitution-notice"
SPACE, RETURN = 32, 13

# (case, role, side, country, highlight and pick, minute, 6D4E's return, its first byte argument)
CASES = {
    "role3": dict(role=3, side=1, country=7, slot=11, pick=131, minute=33, origin=0x6EEF, first=10),
    "england": dict(role=4, side=0, country=9, slot=3, pick=163, minute=71, origin=0x6F92, first=11),
    "albania": dict(role=4, side=1, country=1, slot=10, pick=10, minute=58, origin=0x6F92, first=11),
}
# step: (file, SHA-256, site, kind). Steps 1-3 sit in the CC7B selector or its board read, 0 and 4 in the match.
FILES = {
    "role3": (
        ("t131-a9fe9ceb05994265-role3-preceding-wait.g2core",
         "a9fe9ceb05994265428ee410b15abba7d1c9aa814f5a296516bfb703f5ca7304", "0791:93C2", LIVE),
        ("t131-964d78d67e8cd83c-role3-decision-before-space.g2core",
         "964d78d67e8cd83c4248106d304d2dfd09f411f6b3f50782412d983b617780de", "0791:CC54", SELECT),
        ("t131-a09516fe0d0d4ca4-role3-space-pitch-read.g2core",
         "a09516fe0d0d4ca4fcf2b828f371580a75bf7981898b442d684e4add9134d634", "0791:CF3A", PITCH),
        ("t131-407b6a751d22a72b-role3-return-back-at-selector.g2core",
         "407b6a751d22a72b38d25bc412b35c85e1cf9650b26509d737577c822922a74b", "0791:CC54", SELECT),
        ("t131-238785d42fd20539-role3-return-accept.g2core",
         "238785d42fd205392c35ad68cf58dee6a99f8aa3a08ee8bb410c9abf0c2488ed", "0791:93C2", LIVE)),
    "england": (
        ("t131-6557737543da7701-role4-england-preceding-wait.g2core",
         "6557737543da7701aa6b7377340a44f0e60de2594c25d3843c2e5e837510a60e", "0791:93C2", LIVE),
        ("t131-dc1f31f1af0b355c-role4-england-decision-before-space.g2core",
         "dc1f31f1af0b355cb9d9c3a4514b4755fccb1bd9359fbe5914fd897d49478bc4", "0791:CC54", SELECT),
        ("t131-4a956146b9eac9dd-role4-england-space-pitch-read.g2core",
         "4a956146b9eac9dd6774fb249eee49da3eca13f36c5f9accd74205d34bc58982", "0791:CF3A", PITCH),
        ("t131-1e3ecd1594e728b1-role4-england-return-back-at-selector.g2core",
         "1e3ecd1594e728b1115db70c41fbfa3c9e20a5625081a1cb362287ef29a1b97b", "0791:CC54", SELECT),
        ("t131-2a70cbc70a9767c4-role4-england-return-accept.g2core",
         "2a70cbc70a9767c4da5f32c08948967c04ab73e26d90ee693b4554a9f8ecf1b5", "0791:93C2", LIVE)),
    "albania": (
        ("t131-4c28a1087379994d-role4-albania-preceding-wait.g2core",
         "4c28a1087379994d04a5630cea948966a388f07ff6c51d4a77fc45cd9190bc16", "0791:CC54", NOTICE),
        ("t131-b2221e9c681dec5a-role4-albania-decision-before-space.g2core",
         "b2221e9c681dec5a4aa257f795922ecafc7df7e105cde6c7599b0de6ed60d439", "0791:CC54", SELECT),
        ("t131-8e0fd565b24f9925-role4-albania-space-pitch-read.g2core",
         "8e0fd565b24f992554ab7a3478087303c2837f37c71a828d938518dc506c9bd6", "0791:CF3A", PITCH),
        ("t131-4b08af6a0b187a42-role4-albania-return-back-at-selector.g2core",
         "4b08af6a0b187a422e3f6361a13809b26495c0607379088e8b9f88c9fcc599c3", "0791:CC54", SELECT),
        ("t131-4a78a12771878a30-role4-albania-return-accept.g2core",
         "4a78a12771878a3022f324e12a347c20c8d692f4236be9b425746f173ad28055", "0791:93C2", LIVE)),
}
NEEDS = dict(modules=("unicorn",), files=("GOAL.DAT",) + tuple(s[0] for steps in FILES.values() for s in steps))


def raw(case, step):
    name, sha = FILES[case][step][:2]
    data = (requires.CACHE / name).read_bytes()
    assert hashlib.sha256(data).hexdigest() == sha, name
    return data


def driver(case, step):
    """The kept Core of one checkpoint, loaded with the catalogue as it stands; a Driver over it (its `wait` the state)."""
    from goal2.core import Core
    from goal2.core.driver import Driver
    core = Core.load(raw(case, step), goal_dat=requires.CACHE / "GOAL.DAT")
    return Driver(core)


def expected_view(case):
    c = CASES[case]
    return dict(role=c["role"], side=c["side"], country=c["country"], slot=c["slot"], stored=c["pick"])


@requires.need(**NEEDS)
class Recognised(unittest.TestCase):
    """Done when 1: a role-3 prompt, and the role-4 prompts, are recognised and read as the checkpoints record them."""

    def test_each_decision_is_the_selector_with_the_role_side_highlight_and_pick_the_checkpoint_records(self):
        from goal2.core import views
        for case in CASES:
            for step in (1, 3):
                with self.subTest(case=case, step=step):
                    d = driver(case, step)
                    self.assertEqual((d.wait.kind, d.wait.site, bool(d.wait.poll)), (SELECT, "0791:CC54", True))
                    self.assertEqual(d.wait.view, expected_view(case))
                    choice = views.taker_choice(d.wait.state, d.wait.view)
                    self.assertEqual(len(choice["players"]), 11)
                    self.assertEqual(choice["selected_player"], CASES[case]["pick"])   # the highlight is the pick
                    self.assertEqual(choice["name"], {7: "Denmark", 9: "England", 1: "Albania"}[CASES[case]["country"]])
                    self.assertEqual(d.core.m.rd(0x9976 + 2 * CASES[case]["role"] + 10 * CASES[case]["side"]),
                                     CASES[case]["pick"])

    def test_the_board_read_is_the_taker_pitch_screen_with_the_same_view(self):
        for case in CASES:
            with self.subTest(case=case):
                d = driver(case, 2)
                self.assertEqual((d.wait.kind, d.wait.site, bool(d.wait.poll)), (PITCH, "0791:CF3A", False))
                self.assertEqual(d.wait.view, expected_view(case))

    def test_the_checkpoints_around_a_decision_keep_the_screens_they_had(self):
        """Steps 0 and 4 are the match (or Albania's substitution notice), no taker: the entry names no taker there."""
        for case in CASES:
            for step in (0, 4):
                with self.subTest(case=case, step=step):
                    d = driver(case, step)
                    self.assertEqual((d.wait.kind, d.wait.site), (FILES[case][step][3], FILES[case][step][2]))

    def test_the_kept_keys_grow_by_the_space_and_the_two_returns(self):
        for case in CASES:
            with self.subTest(case=case):
                base = len(driver(case, 1).core.keys)
                self.assertEqual([len(driver(case, s).core.keys) for s in (1, 2, 3, 4)],
                                 [base, base + 1, base + 2, base + 3])


@requires.need(**NEEDS)
class Answered(unittest.TestCase):
    """Done when 1: answering the decision continues the original, to the machines the later checkpoints kept."""

    def test_space_return_return_reach_each_later_checkpoint_byte_for_byte(self):
        for case in CASES:
            with self.subTest(case=case):
                d = driver(case, 1)
                for key, step in ((SPACE, 2), (RETURN, 3), (RETURN, 4)):
                    d.taker_key(key)
                    kept = driver(case, step)
                    self.assertEqual((d.wait.kind, d.wait.site), (FILES[case][step][3], FILES[case][step][2]))
                    self.assertEqual(d.core.keys, kept.core.keys)
                    self.assertEqual(d.core.memory_sha256(), kept.core.memory_sha256())
                self.assertEqual(d.core.m.rd(0x9976 + 2 * CASES[case]["role"] + 10 * CASES[case]["side"]),
                                 CASES[case]["pick"])

    def test_a_moved_highlight_is_accepted_into_the_stored_pick_and_nothing_else_changes(self):
        from goal2.core import views
        from goal2.core.screens import DOWN
        for case in CASES:
            with self.subTest(case=case):
                d = driver(case, 1)
                c = CASES[case]
                captain = d.core.m.rd(0x9978 + 10 * c["side"])
                other = d.core.m.rd(0x9976 + 2 * (7 - c["role"]) + 10 * c["side"])    # the other of roles 3/4's pair
                d.taker_key(DOWN if c["slot"] < 11 else 0xAC)                         # Down, or Up from the last slot
                chosen = views.taker_choice(d.wait.state, d.wait.view)["selected_player"]
                self.assertNotEqual(chosen, c["pick"])
                d.taker_key(RETURN)
                self.assertEqual(d.wait.kind, LIVE)
                self.assertEqual(d.core.m.rd(0x9976 + 2 * c["role"] + 10 * c["side"]), chosen)
                self.assertEqual(d.core.m.rd(0x9978 + 10 * c["side"]), captain)
                self.assertEqual(d.core.m.rd(0x9976 + 2 * (7 - c["role"]) + 10 * c["side"]), other)

    def test_the_remaining_original_timeout_keeps_the_pick(self):
        for case in CASES:
            with self.subTest(case=case):
                d = driver(case, 1)
                d.taker_key(None)
                self.assertEqual(d.wait.kind, LIVE)
                self.assertEqual(d.core.m.rd(0x9976 + 2 * CASES[case]["role"] + 10 * CASES[case]["side"]),
                                 CASES[case]["pick"])

    def test_a_scripted_round_needs_an_explicit_answer_for_a_penalty_too(self):
        from unittest.mock import patch
        from goal2.core.driver import DriverError
        d = driver("role3", 1)
        with patch.object(d, "round_start", return_value=d.wait), patch.object(d, "kick_off", return_value=d.wait):
            with self.assertRaisesRegex(DriverError, "on_taker"):
                d.play_round()
        self.assertEqual(d.wait.kind, SELECT)


def stack(role, side, origin, args, near=0x6D74, slot=5):
    """A synthetic stack with CC7B's frame (its role and side byte arguments, its highlight [bp-5], its near caller) and
    its caller 6D4E's frame (its return and three byte arguments), for the pure entry. [designed] Corruption controls of
    the catalogue's checks; none is an original input (the kept states above are)."""
    import goal2.core.screens as screens
    mem = bytearray(0x200)
    ss, bp, parent = 0x10, 0x80, 0xC0

    def put(at, value, size=2):
        mem[ss * 16 + at:ss * 16 + at + size] = value.to_bytes(size, "little")
    put(bp, parent)                         # CC7B's saved BP: 6D4E's frame
    put(bp + 2, near)                       # CC7B returns near to 6D74
    put(bp + 4, role | 0x5A00)              # the byte arguments have scratch high bytes (T88)
    put(bp + 6, side | 0x3C00)
    put(bp - 5, slot)
    put(parent + 2, origin)
    for i, value in enumerate(args):
        put(parent + 4 + 2 * i, value | 0x7700)
    frame = screens.Frame(lambda a, n: bytes(mem[a:a + n]), 0, 0, ss, bp)
    return screens, frame, bp


class NeverGuessed(unittest.TestCase):
    """The catalogue's rule (screens.py: it never guesses): roles 3 and 4 are answered only with the caller 6D4E's frame
    T131 read; anything else, or a role no input supplied, gives None and the runner stops."""

    def test_the_two_origins_the_checkpoints_show_are_recognised_at_either_side(self):
        for role, origin, first in ((3, 0x6EEF, 10), (4, 0x6F92, 11)):
            for side in (0, 1):
                screens, f, bp = stack(role, side, origin, (first, role, side))
                self.assertEqual(screens._taker(f, bp), screens.TAKER_SELECT, (role, side))

    def test_a_role_3_or_4_without_its_own_origin_frame_is_not_recognised(self):
        for role, origin, first in ((3, 0x6EEF, 10), (4, 0x6F92, 11)):
            for what, kw in (("the other restart's return", dict(origin=0x6F92 if role == 3 else 0x6EEF)),
                             ("no known return", dict(origin=0x6D74)),
                             ("the other restart's first argument", dict(args=(21 - first, role, 1))),
                             ("another role in the argument", dict(args=(first, 7 - role, 1))),
                             ("another side in the argument", dict(args=(first, role, 0))),
                             ("a far caller of CC7B", dict(near=0x1234)),
                             ("a highlight outside the eleven", dict(slot=12)),
                             ("no highlight", dict(slot=0))):
                with self.subTest(role=role, what=what):
                    params = dict(origin=origin, args=(first, role, 1))
                    params.update(kw)
                    screens, f, bp = stack(role, 1, **params)
                    self.assertIsNone(screens._taker(f, bp))

    def test_roles_without_an_input_stay_unrecognised_with_the_origin_of_a_known_one(self):
        for role in (0, 1, 6, 7):
            for origin, first in ((0x6EEF, 10), (0x6F92, 11)):
                screens, f, bp = stack(role, 1, origin, (first, role, 1))
                self.assertIsNone(screens._taker(f, bp), (role, origin))

    def test_roles_2_and_5_keep_the_entry_they_had_without_asking_for_an_origin(self):
        for role in (2, 5):
            screens, f, bp = stack(role, 0, 0x0001, (0, 0, 0))
            self.assertEqual(screens._taker(f, bp), screens.TAKER_SELECT, role)

    def test_the_catalogue_no_longer_says_these_roles_are_unobserved(self):
        import inspect
        from goal2.core import screens
        text = inspect.getsource(screens)
        self.assertNotIn("roles3/4 still have no entry", text)
        self.assertNotIn("roles3/4 remain explicitly unobserved", text)


if __name__ == "__main__":
    unittest.main()
