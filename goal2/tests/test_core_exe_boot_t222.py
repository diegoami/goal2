"""T222 (#705): the core booted from the player's own GOAL.EXE is the same game as one booted from the recorded state.

The recorded state is `e039-r0005-date-call.sav` (F033, E039-r0005): goal2-archaeology's E039 caught DOSBox-X at
load+2382:0074 (the CRT unit's tick wait), ran the rest under Unicorn to the date call 235C:0071 (derive.py) and wrote
it there. The GOAL.EXE boot (goal2/core/exeboot.py) runs the program from its MZ entry in a bare machine to the same
call. GOAL.EXE, GOAL.DAT and the recording are read from .cache/ (docs/artifacts.md) and the E039 records from the
goal2-archaeology checkout; a test skips, naming the file, when one is absent. Nothing of the original is in this file.

DIFFERENCES is the named table of item 2 (docs/core.md "Booting from GOAL.EXE"): every byte of the data segment and
of the live stack where the two date-call states differ, each entry checked by address against its cause, and the
test that replacing its bytes changes nothing to the first manager menu.
"""
import hashlib
import os
import struct
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from goal2.tests import requires
from goal2.tests.test_core_new_game_t106 import (DENMARK, E038_TIME, E039, GAME, SEED, SEED2, ENTER, archaeology,
                                                 game_word, observed, ranges, record)

EXE, DAT, DATE_CALL = "GOAL.EXE", "GOAL.DAT", "e039-r0005-date-call.sav"
NEEDS = {"modules": ("unicorn",), "files": (EXE, DAT, DATE_CALL)}
RECORDS = {**NEEDS, "archaeology": True}
# [confirmed: goal2-archaeology c9364f51, experiments/E039-start-year/out/derive-r0005.json: `state.bios_ticks`
# 655438 at the date call, `ticks_served` 3] The BIOS's count when E039's GOAL.EXE started: the boot models the same
# three ticks (exeboot.TICK) on its way to the date call. An input of the boot, like the date.
E039_TICKS = 655438 - 3
MODULE_BYTES = 92359             # [confirmed: GOAL.EXE's MZ header: 181 pages, 231 bytes in the last, 2 paragraphs]
STACK_TOP = 0x4000               # [derived: measured, exeboot.DateCall.stack_top] SP at the program's entry 0000:0000
# [confirmed: seg_23E4_01.asm 0035-004E, the vector list at 23E4:01DD] the 18 vectors the system unit saves at DS:ACC0
SAVED_VECTORS = (0x00, 0x02, 0x1B, 0x23, 0x24, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x3B, 0x3C, 0x3D, 0x3E,
                 0x3F, 0x75)
LZEXE_SS, LZEXE_SP = 0x2DE7, 0x0080   # [confirmed: GOAL.EXE's MZ header] the unpacker's stack

# The named table (task item 2, docs/core.md): (name, segment register, first offset, last offset, cause, why the game
# never reads it before writing it). Offsets are of DS or SS at the date call (DS 0823+2581, SS 3875: SS:0000 is
# DS:AD10, so the stack lies inside the data segment's 64 KiB).
DIFFERENCES = (
    ("LZEXE's stack", "DS", 0x86CC, 0x86DB,
     "the unpacker's stack (SS load+2DE7, SP 0080): GOAL.EXE's stub pushes its own return offset 002Bh at SS:007A; "
     "in the recording, an interrupt frame (IP FEAF, CS F000, FLAGS 7206h) and others that DOSBox-X's hardware "
     "interrupts pushed there while LZEXE ran; the boot models no hardware interrupt",
     "data the program has not yet written by the first manager menu; replaced, it changes nothing there "
     "(TheTableDoesNotMatter), nor in the first watched match (FirstWatchedMatch)"),
    ("saved vectors", "DS", 0xACC0, 0xAD07,
     "the 18 vectors 23E4:0035-004E saves (INT 21h AH=35h): F000:4n, the boot's stubs, against DOSBox-X's BIOS and "
     "DOS addresses in the recording; a value of the emulator's ROM layout, never produced here",
     "read only by the program's exit 23E4:0141, which restores them; the core stops before it (quitting stops at "
     "INT 10h AH=02h, docs/core.md Refusals)"),
    ("Intr's frames, below SS:SP", "SS", 0x3DC2, 0x3DD5,
     "Intr 235C:000B-0048 ran for INT 10h AH=02h (214B:0661) and left its pushes; E039's derivation served Intr at "
     "its entry and ran none of it",
     "below SS:SP: a push writes each word before a pop can read it"),
    ("GetDate's day", "SS", 0x3DF2, 0x3DF3,
     "214B:1C63's local [bp-4], which held Intr's record Flags (7202h, stored by 235C:0045/0066) in the boot and the "
     "request's word (296Eh) in the recording, where Intr's return path never ran",
     "GetDate stores the day there (235C:007E) right after the date call"),
    ("under the start-up's frames", "SS", 0x3FCD, 0x3FE1,
     "never written by the program before the date call (checked); in the recording, what DOSBox-X's own interrupt "
     "code left on the program's stack before E039's catch",
     "overwritten by the first manager menu; replaced, it changes nothing there (TheTableDoesNotMatter)"),
)
PERSISTING = ("LZEXE's stack", "saved vectors")     # entries still differing at the manager menu (never written)
# [derived: the date call's registers] Registers that differ at the date call, and why they do not matter.
REGISTER_DIFFERENCES = {
    "EAX": "AL: DOS answers the weekday in it (runner.date_registers); AH is the same 2Ah",
    "ECX": "DOS answers the year in CX",
    "EDX": "DOS answers the month and day in DX",
    "EBX": "the record's BX Intr loaded for INT 10h AH=02h (00AAh); E039's derivation never ran Intr's loads",
    "ES": "GetDate loads ES:DI at 235C:0075 before any use",
}


def cache(name):
    requires.require(**NEEDS)
    return (requires.CACHE / name).read_bytes()


def exe_call():
    from goal2.core import exeboot
    return exeboot.date_call(requires.CACHE / EXE, E039_TICKS)


def recorded():
    """(memory, regs, image) of the recording at the date call."""
    from goal2.core.runner import _image, cpu_state
    state = cache(DATE_CALL)
    image = _image(state)
    return bytes(image.memory[:0x110000]), cpu_state(state), image


def table_bytes(ds, ss):
    """{linear address: entry name} of DIFFERENCES."""
    out = {}
    for name, reg, first, last, _, _ in DIFFERENCES:
        base = ds if reg == "DS" else ss
        for off in range(first, last + 1):
            out[base * 16 + off] = name
    return out


def boot_exe(date, title_key="n", **kw):
    from goal2.core import Core
    return Core.boot_exe(requires.CACHE / EXE, date, dos_time=E038_TIME, goal_dat=requires.CACHE / DAT,
                         title_key=title_key, bios_ticks=E039_TICKS, **kw)


def boot_recorded(date, title_key="n"):
    from goal2.core import Core
    return Core.boot(cache(DATE_CALL), date, dos_time=E038_TIME, goal_dat=requires.CACHE / DAT, title_key=title_key)


def new_game(wait):
    """The driver's new game (Denmark, 'bob') with every wait on the way kept."""
    from goal2.core.driver import Driver
    driver = Driver(wait.core)
    driver.trail = [wait]
    driver.new_game(DENMARK, "bob")
    return driver


def waits(trail):
    return [(w.kind, w.site, w.screen, w.poll, w.polls, [(p.kind, p.polls, p.text, p.keys) for p in w.passed])
            for w in trail]


@requires.need(**NEEDS)
class AtTheDateCall(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.call = exe_call()
        cls.ref, cls.regs, cls.image = recorded()

    def test_the_load_module_and_the_build_guard(self):
        from goal2.core import exeboot
        from goal2.engine.original_match.image import Image
        call, ref = self.call, self.ref
        self.assertEqual(call.load, self.image.load)
        base = call.load * 16
        self.assertEqual(call.memory[base:base + MODULE_BYTES], ref[base:base + MODULE_BYTES])
        booted = Image.from_memory_component(call.header + call.memory)
        self.assertEqual((booted.load, booted.build_problems()), (call.load, []))
        self.assertEqual(call.stack_top, STACK_TOP)
        # DOS's block for the program: the recording's MCB and PSP top, by the header's rule (exeboot.block_paragraphs).
        size = exeboot.block_paragraphs(exeboot.header(cache(EXE)))
        psp = call.load - 0x10
        for mem in (ref, call.memory):
            self.assertEqual(struct.unpack_from("<BHH", mem, (psp - 1) * 16), (0x4D, psp, size))
            self.assertEqual(struct.unpack_from("<H", mem, psp * 16 + 2)[0], psp + size)
        # Only the requests the task lists, in the numbers the probe saw.
        counts = {}
        for number, ax in call.requests:
            key = (number, ax if (number, ax) == (0x10, 0x1130) else ax >> 8)
            counts[key] = counts.get(key, 0) + 1
        self.assertEqual(counts, {(0x21, 0x35): 18, (0x21, 0x25): 5, (0x21, 0x44): 1, (0x10, 0x0F): 2,
                                  (0x10, 0x1130): 1, (0x10, 0x08): 1, (0x10, 0x02): 2})
        self.assertEqual(call.header, exeboot.HEADER)

    def test_ds_and_the_live_stack_equal_the_recording_but_the_named_table(self):
        call, ref, regs = self.call, self.ref, self.regs
        ds, ss, sp = call.regs["DS"], call.regs["SS"], call.regs["ESP"] & 0xFFFF
        self.assertEqual((ds, ss, sp), (regs["DS"], regs["SS"], regs["ESP"] & 0xFFFF))
        named = table_bytes(ds, ss)
        windows = [(ds * 16, ds * 16 + 0x10000), (ss * 16 + sp, ss * 16 + STACK_TOP)]
        differing = {a for lo, hi in windows for a in range(lo, hi) if call.memory[a] != ref[a]}
        self.assertEqual(sorted(differing - set(named)), [], "a difference the table does not name")
        for name, *_ in DIFFERENCES:                      # every entry names a real difference
            self.assertTrue(any(named[a] == name for a in differing), name)
        mem = call.memory

        def word(seg, off, m=mem):
            return struct.unpack_from("<H", m, seg * 16 + off)[0]
        # LZEXE's stack: the stub's push of 002Bh at SS:007A, nothing else written; the recording's frame.
        lz = (call.load + LZEXE_SS) * 16
        self.assertEqual(lz - ds * 16 + LZEXE_SP - 6, 0x86DA)
        self.assertEqual(word(ds, 0x86DA), 0x002B)
        self.assertEqual(bytes(mem[ds * 16 + 0x86CC:ds * 16 + 0x86DA]), bytes(14))
        self.assertEqual([word(ds, o, ref) for o in (0x86CC, 0x86CE, 0x86D0)], [0xFEAF, 0xF000, 0x7206])
        # The saved vectors: the boot's stubs F000:4n, in the order 23E4:01DD lists them; the recording's are not.
        for i, n in enumerate(SAVED_VECTORS):
            self.assertEqual((word(ds, 0xACC0 + 4 * i), word(ds, 0xACC2 + 4 * i)), (4 * n, 0xF000), hex(n))
        self.assertTrue(all(word(ds, 0xACC2 + 4 * i, ref) != 0xF000 or word(ds, 0xACC0 + 4 * i, ref) != 4 * n
                            for i, n in enumerate(SAVED_VECTORS)))
        # Intr's frames lie below SS:SP.
        self.assertLess(0x3DD5, sp)
        # GetDate's day: GetDate's frame (BP = SP) holds the day's far pointer at [bp+0Ah], which is SS:3DF2.
        self.assertEqual((word(ss, sp + 0x0A), word(ss, sp + 0x0C)), (0x3DF2, ss))
        self.assertEqual((word(ss, 0x3DF2), word(ss, 0x3DF2, ref)), (0x7202, 0x296E))
        # Under the start-up's frames: zero in the boot (never written: WrittenInTheBoot).
        self.assertEqual(bytes(mem[ss * 16 + 0x3FCD:ss * 16 + 0x3FE2]), bytes(0x15))

    def test_the_registers_equal_the_recording_but_those_the_date_call_answers(self):
        regs, ours = self.regs, self.call.regs
        self.assertEqual(ours["EIP"] & 0xFFFF, 0x0071)
        differ = {k for k in regs if k in ours and k != "EIP" and regs[k] != ours[k]}
        self.assertEqual(differ, set(REGISTER_DIFFERENCES))
        self.assertEqual((regs["EAX"] >> 8, ours["EAX"] >> 8), (0x2A, 0x2A))
        self.assertEqual(ours["EFLAGS"], regs["EFLAGS"])

    def test_the_tick_gives_the_recordings_delay_counts(self):
        from goal2.core import exeboot
        ds = self.call.regs["DS"] * 16
        for off, n in ((0xAAB8, 2), (0xA9FF, 4), (0x7B4A, 2), (0x8336, 2)):
            self.assertEqual(self.call.memory[ds + off:ds + off + n], self.ref[ds + off:ds + off + n], hex(off))
        self.assertEqual(int.from_bytes(self.call.memory[ds + 0xA9FF:ds + 0xA9FF + 2], "little"), 4279)
        self.assertEqual(exeboot.TICK, 1647750)
        self.assertEqual(int.from_bytes(self.call.memory[0x46C:0x470], "little"), E039_TICKS + 3)


@requires.need(**RECORDS)
class Record(unittest.TestCase):
    def test_the_boot_count_is_e039s(self):
        import json
        d = json.loads(archaeology("experiments/E039-start-year/out/derive-r0005.json"))
        self.assertEqual(d["state"]["bios_ticks"] - d["ticks_served"], E039_TICKS)
        self.assertEqual(d["state"]["sha256"], hashlib.sha256(cache(DATE_CALL)).hexdigest())


@requires.need(**NEEDS)
class WrittenInTheBoot(unittest.TestCase):
    def test_the_start_up_frames_are_never_written_before_the_date_call(self):
        from unicorn import UC_HOOK_MEM_WRITE
        from goal2.core import exeboot
        exe, _ = exeboot.read_exe(requires.CACHE / EXE)
        boot = exeboot._Boot(exe, E039_TICKS)
        ss = 0x3875
        written = []
        boot.uc.hook_add(UC_HOOK_MEM_WRITE, lambda uc, acc, a, size, v, d: written.append(a),
                         begin=ss * 16 + 0x3FCD, end=ss * 16 + 0x3FE1)
        boot.run()
        self.assertEqual(boot.reg("ss"), ss)
        self.assertEqual(written, [])


@requires.need(**NEEDS)
class TheTableDoesNotMatter(unittest.TestCase):
    def test_the_named_bytes_change_nothing_to_the_manager_menu(self):
        """The table's bytes are an input that the game must not use: the same quick new game from the GOAL.EXE
        date call with every named byte as booted and with every one replaced by FFh reaches the same manager
        menu, memory equal but for the entries never written since (PERSISTING), which keep what each start had.
        [designed: T222] A perturbation, not a read hook: Unicorn 2.1.4 runs this program wrongly with a read
        hook over SS:3FCD-3FE1 (measured: both starts then stop at a stray INT 20h)."""
        from goal2.core import DEFAULT_BUDGET, Core, exeboot
        call = exe_call()
        named = table_bytes(call.regs["DS"], call.regs["SS"])
        poisoned = bytearray(call.memory)
        for a in named:
            poisoned[a] = 0xFF
        self.assertTrue(any(poisoned[a] != call.memory[a] for a in named))
        games = []
        for memory in (bytearray(call.memory), poisoned):
            wait = Core._boot_at_date_call(memory, call.load, call.regs, call.header, b"",
                                           exeboot.digest_id(cache(EXE)), E039["E039-r0001"][0],
                                           budget=DEFAULT_BUDGET, dos_time=E038_TIME,
                                           goal_dat=requires.CACHE / DAT, title_key="n")
            games.append(new_game(wait))
        clean, other = games
        self.assertEqual(waits(clean.trail), waits(other.trail))
        a, b = clean.core.memory(), other.core.memory()
        differing = {x for x in range(len(a)) if a[x] != b[x]}
        persisting = {x for x, name in named.items() if name in PERSISTING}
        self.assertEqual(sorted(f"{x:05X} ({named.get(x)})" for x in differing - persisting), [])
        for x in persisting:                                 # never written since the date call
            self.assertEqual((a[x], b[x]), (call.memory[x], 0xFF), f"{x:05X}")


@requires.need(**NEEDS)
class SameNewGame(unittest.TestCase):
    """Done-when 2 with N pressed in the title's tune (the desktop's boot): both E039 dates, both starts."""

    def test_both_starts_reach_the_same_manager_menu(self):
        for run, (date, start, stage) in E039.items():
            with self.subTest(run=run):
                theirs, ours = new_game(boot_recorded(date)), new_game(boot_exe(date))
                self.assert_same_game(theirs, ours)
                self.assertEqual((game_word(ours.core, 0x3A), game_word(ours.core, 0x3C, 1)), (start, stage))

    def assert_same_game(self, theirs, ours):
        a, b = theirs.core, ours.core
        self.assertEqual((a.wait.kind, b.wait.kind), ("manager-menu", "manager-menu"))
        self.assertEqual(waits(theirs.trail), waits(ours.trail))          # kinds, sites, screens, polls
        self.assertEqual(theirs.log, ours.log)
        self.assertEqual(a.date, b.date)
        ma, mb = a.memory(), b.memory()
        ds = a.m.DS * 16
        persisting = {ds + off for name, reg, first, last, _, _ in DIFFERENCES if name in PERSISTING
                      for off in range(first, last + 1)}
        differing = [x for x in range(ds, ds + 0x10000) if ma[x] != mb[x]]
        self.assertEqual([f"{x:05X}" for x in differing if x not in persisting], [])
        for off in (SEED, SEED2):
            self.assertEqual(a.m.rd(off), b.m.rd(off), hex(off))
        for ptr, size in ((0xA91B, 0x14 * 3061), (0xA917, 0xBF * 129)):
            self.assertEqual(a.m.far(ptr), b.m.far(ptr))
            self.assertEqual(ma[a.m.far(ptr):a.m.far(ptr) + size], mb[b.m.far(ptr):b.m.far(ptr) + size], hex(ptr))
        self.assertEqual(a.m.read(a.m.far(GAME), 0x40), b.m.read(b.m.far(GAME), 0x40))


@requires.need(**RECORDS, slow=True)
class StartYearFromExe(unittest.TestCase):
    """T106's E039 comparisons (StartYear) from the GOAL.EXE start: each date through the whole title tune."""

    @classmethod
    def setUpClass(cls):
        cls.title, cls.games, cls.recorded = {}, {}, {}
        for run, (date, _, _) in E039.items():
            wait = boot_exe(date, title_key=None)
            cls.title[run] = wait
            cls.games[run] = new_game(wait)
            cls.recorded[run] = new_game(boot_recorded(date, title_key=None))

    def test_the_title_read_holds_e039s_year_and_screen(self):
        for run, (date, _, _) in E039.items():
            rec, wait = record(run), self.title[run]
            self.assertEqual((wait.site, wait.kind), ("1771:085F", "title-load-prompt"), run)
            self.assertEqual([(p.kind, p.polls) for p in wait.passed], [("title-tune", 333)], run)
            self.assertEqual(hashlib.sha256(wait.screen).hexdigest(), observed(rec, "title-load-prompt", "sha256"), run)
            self.assertEqual(wait.text, observed(rec, "title-load-prompt", "CP437"), run)
            year = wait.core.m.rd(0xA9FD)
            self.assertEqual(year, date[0], run)
            self.assertEqual(f"{year:04x}", observed(rec, "title-load-prompt", "DS:A9FD"), run)
            self.assertEqual(wait.core.date, date)

    def test_a_new_game_has_ng9s_start_year_and_stage(self):
        for run, (_, start, stage) in E039.items():
            core, rec = self.games[run].core, record(run)
            self.assertEqual(self.games[run].wait.kind, "manager-menu", run)
            self.assertEqual((game_word(core, 0x3A), game_word(core, 0x3C, 1)), (start, stage), run)
            self.assertEqual(core.m.read(core.m.far(GAME) + 0x38, 10).hex(),
                             observed(rec, "manager-menu", "+0x38..+0x41"), run)
            SameNewGame.assert_same_game(self, self.recorded[run], self.games[run])
        from goal2.core import Core
        loaded = Core.load(self.games["E039-r0001"].core.save())
        self.assertEqual((loaded.date, loaded.dos_time), ((1990, 10, 4), E038_TIME))


@requires.need(**NEEDS, slow=True)
class FirstWatchedMatch(unittest.TestCase):
    """Done-when 3: the new game's first watched match, by the same keys from both starts, to full time."""

    def play(self, wait):
        from goal2.core import views
        driver = new_game(wait)
        got = {}
        finish = driver.finish

        def at_full_time():
            if "ds" not in got:
                core = driver.core
                got["ds"] = core.memory()[core.m.DS * 16:core.m.DS * 16 + 0x10000]
                got["board"] = views.board(driver.wait.state)
                got["keys"] = list(core.keys)
                got["screen"] = driver.wait.screen
            return finish()
        driver.finish = at_full_time
        for _ in range(10):
            if "ds" in got:
                break
            driver.play_round(watch=True, on_taker=lambda d, w: None, on_replay=lambda d, w: False)
        self.assertIn("ds", got, "no watched match in ten rounds")
        return got

    def test_the_same_result_and_ds_at_full_time(self):
        date = E039["E039-r0001"][0]
        theirs, ours = self.play(boot_recorded(date)), self.play(boot_exe(date))
        self.assertEqual(theirs["board"], ours["board"])
        self.assertEqual(theirs["keys"], ours["keys"])
        self.assertEqual(theirs["screen"], ours["screen"])
        persisting = sorted(off for name, reg, first, last, _, _ in DIFFERENCES if name in PERSISTING
                            for off in range(first, last + 1))
        differing = [off for off in range(0x10000) if theirs["ds"][off] != ours["ds"][off]]
        self.assertEqual([f"DS:{off:04X}" for off in differing if off not in persisting], [])


@requires.need(**NEEDS)
class Refused(unittest.TestCase):
    def test_another_goal_exe_is_refused_by_name_before_it_runs(self):
        from goal2.core import Core, CoreError, exeboot
        from goal2.desktop.core_model import CoreNewGame
        with tempfile.TemporaryDirectory() as folder:
            stand_in = Path(folder) / "GOAL.EXE"
            stand_in.write_bytes(b"MZ a stand-in, not the registered GOAL.EXE\n")
            flipped = Path(folder) / "OTHER.EXE"
            raw = bytearray(cache(EXE))
            raw[-1] ^= 0xFF
            flipped.write_bytes(bytes(raw))
            for path in (stand_in, flipped):
                with mock.patch.object(exeboot, "_Boot", side_effect=AssertionError("an instruction ran")), \
                        self.assertRaises(CoreError) as caught:
                    Core.boot_exe(path, (1990, 10, 4), goal_dat=requires.CACHE / DAT)
                self.assertIn(str(path), str(caught.exception))
                self.assertIn("not the registered GOAL.EXE", str(caught.exception))
                self.assertIn(hashlib.sha256(path.read_bytes()).hexdigest(), str(caught.exception))
            with self.assertRaises(ValueError) as caught:
                CoreNewGame(stand_in, requires.CACHE / DAT, Path(folder) / "x.g2core").browse(1990)
            self.assertIn(str(stand_in), str(caught.exception))

    def test_the_boot_refuses_a_request_it_does_not_serve(self):
        """The boot's answers are the task's list only: another request stops it (InterruptError), naming it."""
        from goal2.core import InterruptError, exeboot
        exe, _ = exeboot.read_exe(requires.CACHE / EXE)
        boot = exeboot._Boot(exe, E039_TICKS)
        boot._dos = lambda ax: boot._refuse(0x21, ax)        # as if INT 21h AH=35h were not served
        with self.assertRaises(InterruptError) as caught:
            boot.run()
        self.assertEqual((caught.exception.number, caught.exception.ah), (0x21, 0x35))


@requires.need(**NEEDS)
class Saved(unittest.TestCase):
    def test_a_saved_exe_boot_names_its_kind_and_loads(self):
        from goal2.core import Core, exeboot
        wait = boot_exe(E039["E039-r0001"][0])
        core = wait.core
        self.assertEqual(core.template_sha256, f"goal-exe:{exeboot.SHA256}")
        loaded = Core.load(core.save(), goal_dat=requires.CACHE / DAT)
        self.assertEqual((loaded.template_sha256, loaded.wait.kind, loaded.date), (core.template_sha256, wait.kind,
                                                                                    core.date))
        self.assertEqual(loaded.memory_sha256(), core.memory_sha256())
        self.assertEqual(loaded.press(ENTER).kind, core.press(ENTER).kind)
        self.assertEqual(loaded.memory_sha256(), core.memory_sha256())


@requires.need(**{**NEEDS, "modules": ("unicorn", "PySide6")})
class Desktop(unittest.TestCase):
    def test_the_desktop_with_no_arguments_boots_from_the_imported_goal_exe(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication
        from goal2.desktop import data_setup
        from goal2.desktop.__main__ import main
        from goal2.desktop.launch import LaunchWindow
        app = QApplication.instance() or QApplication([])
        out = {}
        with tempfile.TemporaryDirectory() as home, \
                mock.patch.dict(os.environ, {"HOME": home, "USERPROFILE": home,
                                             "LOCALAPPDATA": str(Path(home) / "AppData" / "Local")}):
            source = Path(home) / "offered"
            source.mkdir()
            for name in (EXE, DAT):
                (source / name).write_bytes(cache(name))
            target = data_setup.paths()
            data_setup.import_folder(source, target)
            self.assertEqual(sorted(p.name for p in target.data.iterdir()), [DAT, EXE])

            def drive():
                try:
                    launch = next(w for w in QApplication.topLevelWidgets() if isinstance(w, LaunchWindow))
                    out["boot"] = launch.core_new.boot_path
                    launch.show_page(1);app.processEvents()
                    out["countries"] = launch.country_list.count()
                    out["kind"] = launch.core_new.browse(1990).wait.kind
                except Exception as exc:                  # reported by the test, not lost in Qt
                    out["error"] = repr(exc)
                app.quit()
            QTimer.singleShot(0, drive)
            self.assertEqual(main([]), 0)
        self.assertNotIn("error", out)
        self.assertEqual(out["boot"], target.boot)
        self.assertEqual(out["boot"].name, EXE)
        self.assertEqual((out["countries"], out["kind"]), (128, "country-select"))


if __name__ == "__main__":
    unittest.main()
