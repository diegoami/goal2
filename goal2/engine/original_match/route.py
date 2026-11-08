"""The route harness (T119a, #427): one call of the original's route_fixture 000E:6CA7 on a kit Machine, every write
recorded, its managed match played by Match(tail=False).

    r = Route(image)                  # the default key policy, DEFAULT_KEYS
    record = r.call()                 # one call of 6CA7: it returns after a fixture with a managed side
    r.replay(r.origin) == r.m.read(0, MEM_SIZE)    # the record holds every write the call made

The call [derived: match.py ENTRY_SP/ENTRY_BP, E011-r0001; code/seg_000E_09.asm 6CA7-6CAA, 6F16-6F18 and
seg_000E_05 70B9-70D1]: Match calls 0791:F1F6 with SS = load + 0x3052, SP 0x3EC0 and BP 0x3EDE, route_fixture's BP
then. So the harness near-calls 6CA7 as play_round 000E:70B9 does at 70D1: SS = load + 0x3052, its return word
000E:70D4 at SP 0x3EE0 and BP 0x3EEA (70B9's own: `push bp; mov bp, sp; sub sp, 8` leaves SP = BP - 8 = 0x3EE2 at
the call). 6CA7's `push bp; mov bp, sp` makes BP 0x3EDE, `sub sp, 0x16` and the two pushes of the fixture's far
pointer at 6F16-6F17 leave SP 0x3EC4 at 000E:6F18, its `call far 0791:F1F6`.

At 6F18 the harness stops, snapshots the CPU and plays the match with Match(Image of this memory, the fixture at the
cursor, tail=False) on a machine of Match's own. Match's writes before play (the fixture, the managed side, the delay
calibration) must find their bytes there already (tail=False keeps the fixture's +1, a competitive fixture's round,
and +3 as route_fixture left them: T119c), and its far call's stack must be the one the `call far` would
push (its return address 000E:6F1D, then the fixture pointer already pushed): the harness compares the whole memory
and raises on any other byte. After the match the bytes it changed are written back (kit writes, in the record), the
CPU is the snapshot's at 000E:6F1D with SP + 4 (F1F6's `retf 4`; Match's machine must end there, with BP and SS
unchanged), and route_fixture runs on as guest code: B71C/B6CC, the news 4E0E, the update B7FA, the cursor and
1771:8757, to its return.

The record (Route.record), in order: every write on this machine (("w", pc, linear, size, value) for the guest's,
pc linear; ("k", why, linear, bytes) for the harness's own), every step of the RNG words DS:7B62 (F004) and DS:8336
(0791:94C9's, F006) as ("rng", word, old, new, pc, where) right after the write that makes it (where "route", or
"match" for Match's machine: the match's draws in order), every visit to a key site as ("key", site, kind, key,
source), the stop at 6F18 ("stop", regs), the match ("match", summary) and the resume ("resume", sp). The match's
own 70 million or so writes (one E006 friendly, measured) are on Match's machine; this machine gets their net
effect, the write-back, and the record holds it as ("k", "match", ...) runs.

Keys [designed: owner, 2026-11-03, goal2 4368fac and #509]: the harness answers each read (214B:08DD, at its entry)
and poll (214B:0723) from a key policy, by the call's return address, as Match does (match.py _on_readkey,
_on_keypressed); a site the policy does not name raises GuestError. The default is "a key at the first poll": a
poll of a wait finds a key, which stays waiting (every later poll finds it) until a read takes it; a read with no key
waiting takes the policy's key. So 04F5's tune makes no draw and 0572's crowd animation 045D runs once. A pushed-back
key (DS:79AE) is read by the guest itself, as in Match. No other hook: the machine has no foreign hook, and a
Prover can be installed on it (port/prove.py). A proof with ports runs only with Route(..., record_writes=False):
the write listener reads the pc at the ports' stack writes, which they make as 214B:0000 (port/runtime.py), and the
Prover refuses the first such push; without the listener the Prover compares every byte itself (T119c, #647).

T124t's managed eleven [designed: owner, 2026-11-04, goal2 #509]: Route uses RouteMatch (route_team.py), which
chooses a legal eleven before the match, pressing the original SELECT TEAM screen's keys. The original DEA6 swaps
and sorts the squad, and EA09 validates it. Choices keep the greatest number of existing starters, then take the
first squad-slot tuple; the record's ("team", {fixture, choices, keys}) entry preserves every choice and every
match key (site, byte, menu context). Normal Match callers retain their own team decisions. No status, energy,
position or squad word is assigned by this policy.

play_round (T124a, #427): Route(image, entry="play_round") calls play_round 000E:70B9 instead, as main_menu_loop
000E:7439 does at 77BF [confirmed: code/seg_000E_09.asm 77BF-77C2, 70B9-715D, seg_0000_01.asm 00C6; the BP chain of
the published E011-r0001 state (E011-r0001-halftime.sav): SS:3EDE = 3EEA (route_fixture's saved BP), SS:3EE0 = 70D4,
SS:3EEA = 3FF6 (7439's BP), SS:3EEC = 77C2]: its return word 77C2 at SP 0x3EEC and BP 0x3FF6, 7439's. 70B9's
`push bp; mov bp, sp; sub sp, 8` then makes BP 0x3EEA and SP 0x3EE2 at 70D1, so route_fixture runs in the frame the
route_fixture mode gives it, and the stop at 6F18 is the same. One call is one play_round: [A923]+1 := 1, one
route_fixture, and when the cursor +0x26 has reached the count +0x28 (70DE), the round's end: stage_end 1771:8208
(70E6), shareware_limit_reached 7072 (always 0 in this build, F025), run_stage 1771:76B1 (70F4), and, when the stage
byte +0x3C is in the set CS:7099 = {2, 3, 5, 7}, announce_stage_to_manager 000E:60CB for each manager whose +0x47 byte
is clear; it returns to 77C2 with SP 0x3EEE. The record gets ("round_end", {...}) at 70E6, the game record's cursor,
count, stage and rounds bytes there, and ("return", "000E:77C2"). Route.round() makes play_round calls until one
reaches the round's end (the last managed fixture of the stage's round, then the silent rest), so it stops there.
The stage pages' key reads and polls are answered by the same policy, at sites READS and POLLS name already:
60CB's page waits in the news pages' 05F6 (its call at 000E:6622), which polls at 0515 and 05EC and reads at 0624
[confirmed: code/seg_000E_08.asm 6622, seg_000E_01.asm 05F6-0624]; nothing under stage_end 1771:8208 (80DA's subtree
included) or run_stage 76B1 calls 214B:08DD or 0723 (the closure of calls.tsv's direct calls), and under 60CB only
05F6 does, so a round's end adds no site."""
from .image import Image, FIXTURES_PTR, FIXTURE_SIZE, GAME_PTR
from .route_team import RouteMatch
from .news import capture_news_page,news_pages as decode_news_pages
from .machine import Machine, GuestError, MEM_SIZE
from .match import (Match, Fixture, SS_PARAGRAPH, ENTRY_SP, ENTRY_BP, RUN_MATCH_RETURN, DELAY_COUNT,
                    DELAY_COUNT_VALUE, KEYPRESSED, READKEY, PUSHED_BACK, KEY, SEED, SCREEN_PTR, TABLE_READS, TABLE_KEY)

ROUTE_FIXTURE = "000E:6CA7"     # route_fixture (static/goal-exe/annotations/routines.tsv; F010, F030, F039)
CALLER, RETURN_TO = "000E:70D1", "000E:70D4"   # play_round 000E:70B9's call of 6CA7 and its return
CALL_SP = 0x3EE0                # the return word's slot: 70B9's SP at 70D1, its BP - 0xA (see the docstring)
CALLER_BP = 0x3EEA              # 70B9's BP: 6CA7 pushes it, and 6C21 and 6970 read their own frames, not it
MATCH_AT = "000E:6F18"          # route_fixture's `call far 0791:F1F6` (seg_000E_09.asm 6F18)
MATCH_SP = 0x3EC4               # SP at 6F18: BP 0x3EDE - 0x16 - 4
SPEAKER_SEED = 0x8336           # 0791:94C9's seed (F006; routines.tsv 0791:F3F2 sets it from the BIOS tick)
SEEDS = {"7B62": SEED, "8336": SPEAKER_SEED}
PLAY_ROUND = "000E:70B9"        # play_round (routines.tsv; F004)
ROUND_CALLER, ROUND_RETURN = "000E:77BF", "000E:77C2"   # main_menu_loop 7439's call of 70B9 and its return
ROUND_SP = 0x3EEC               # the return word's slot: 7439's SP at 77BF (BP 0x3FF6 - 0x108 - 2)
MENU_BP = 0x3FF6                # 7439's BP (the E011-r0001 state's SS:3EEA), which 70B9 pushes
ROUND_END = "000E:70E6"         # play_round's `call far 1771:8208`, reached when the cursor +0x26 is the count +0x28
ENTRIES = ("route_fixture", "play_round")
MENU_SITE = "214B:157C"         # 214B:1560 reads at 1578 (push cs; call 08DD): its caller names the screen
ENTER, KEY_N = 0x0D, 0x4E

# The key sites route_fixture's own code reaches (the return address of the call of 214B:08DD or 0723), from the
# listing [confirmed: code/seg_000E_01.asm 0510-0515, 05E7-05EC, 0624-0629; seg_000E_08.asm 6A84, 6B84-6B92,
# 6BF2-6BF7; seg_000E_09.asm 6C4A; seg_0791_23.asm E869 with seg_214B 1578; goal2 goal2/core/screens.py SITES].
READS = {
    "000E:0629": "000E:05F6, the news pages' key wait (its read at 0624)",
    "000E:6C4F": "000E:6C21, the gate: the round's results under DS:14A6 when a fixture was simulated before",
    "000E:6A89": "000E:6970 simulate_fixture: a declined fixture's result",
    "000E:6B92": "000E:6970 simulate_fixture: the key its poll at 6B84 found (0xAE, 0xAF the speed, space a pause)",
    MENU_SITE + "<0791:E86E": "0791:E80D ask_watch_match, through 214B:1560 (called at E869): Y, N, Esc or Enter",
    # 6970's score page for a fixture whose first byte is 0xFE calls show_updated_group_tables 0791:E929 (6A93),
    # whose table screen reads a key: Match's TABLE_READS and TABLE_KEY, where Match answers Enter [confirmed:
    # match.py TABLE_READS, TABLE_KEY; E040-r0009, T119b #646; T119c #647]
    **{MENU_SITE + "<" + s: f"0791:E929's table screen through 214B:1560 (called from {s}): one pass" for s in TABLE_READS},
    TABLE_KEY: "0791:E929's finals' table 1771:9509, 'hit any key' (its 214B:08DD at 9562)",
}
POLLS = {
    "000E:0515": "000E:04F5, the tune: a waiting key ends it before the next note",
    "000E:05EC": "000E:0572, the crowd animation 045D until a key",
    "000E:6B89": "000E:6970 simulate_fixture: a key while the round is shown (its read at 6B8D)",
    "000E:6BF7": "000E:6970 simulate_fixture: its delay loop (a waiting key skips the 50 ms waits)",
}
# [designed: owner, 2026-11-03] a key at the first poll, Enter; the watch prompt is declined (N: E80D marks the
# fixture 0xFE and it is simulated); the table screens are looked at once, Enter, as Match answers them (T119c).
DEFAULT_KEYS = {**{s: ENTER for s in READS}, **{s: ENTER for s in POLLS}, MENU_SITE + "<0791:E86E": KEY_N}


class Keys:
    """The key policy: {site: key, None (a poll: no key) or callable(route, site) -> either}, and the one key that
    waits (a poll found it, no read has taken it yet)."""

    def __init__(self, policy):
        self.policy = dict(policy)
        self.waiting = None

    def _answer(self, route, site):
        if site not in self.policy:
            raise GuestError(f"the key site {site} has no answer in the key policy"
                             + ("" if route is None else "\n" + route.screen_text()))
        ans = self.policy[site]
        return ans(route, site) if callable(ans) else ans

    def poll(self, site, route=None):
        """214B:0723 from `site`: (key waiting?, source)."""
        if self.waiting is not None:
            return True, "waiting"
        key = self._answer(route, site)
        if key is None:
            return False, "policy"
        self.waiting = key
        return True, "policy"

    def read(self, site, route=None):
        """214B:08DD from `site`: (key, source)."""
        if self.waiting is not None:
            key, self.waiting = self.waiting, None
            return key, "waiting"
        key = self._answer(route, site)
        if key is None:
            raise GuestError(f"the key read at {site}: the key policy gives no key")
        return key, "policy"


class Route:
    def __init__(self, image, keys=None, timeout_s=600, record_writes=True, entry="route_fixture", match_entry=False, capture_news=True):
        """match_entry: stop at the real F1F6 entry with its already-pushed far-call
        frame (T121); required when proving a translated route_fixture. Both the
        original and port then stop at that same site. The default keeps 6F18.
        entry: "route_fixture" (one call of 6CA7, as play_round's 70D1 makes it) or "play_round" (one call of 70B9,
        as main_menu_loop's 77BF makes it: the round's end included). record_writes: False drops only the all-memory
        write listener (the record's ("w", pc, ...) entries), so that a Prover can run on the machine: the listener
        reads the pc at stack writes, which ports make as 214B:0000 (port/runtime.py), and the Prover refuses that;
        it then checks every byte itself. The seed watches, the key sites and the 6F18 stop stay; replay() refuses
        such a run (T119c, #647)."""
        problems = image.build_problems()
        if problems:
            raise ValueError("the image does not hold the registered GOAL.EXE: " + "; ".join(problems))
        self.header, self.tail = image.header, bytes(image.memory[MEM_SIZE:])
        self.tables = getattr(image, "tables", None)
        self.origin = bytes(image.memory[:MEM_SIZE])
        self.m = Machine(image.memory, image.load)
        self.keys = Keys(DEFAULT_KEYS if keys is None else keys)
        if entry not in ENTRIES:
            raise ValueError(f"entry {entry!r}: one of {', '.join(ENTRIES)}")
        self.entry = entry
        self.match_entry = bool(match_entry)
        self.timeout_s = timeout_s
        self.record_writes = bool(record_writes)
        self.record = []
        self.capture_news = bool(capture_news)
        self.news_history = []
        self.inputs = []
        self.matches = []
        self._hooks()

    # -- the record ------------------------------------------------------------------------------------------
    def _write(self, why, linear, data):
        """The harness's own write: in the record, then made (Machine.write)."""
        data = bytes(data)
        self.record.append(("k", why, linear, data))
        self.m.write(linear, data)

    def _hooks(self):
        m, rec = self.m, self.record
        if self.record_writes:
            m.on_write(0, MEM_SIZE - 1, lambda a, size, value: rec.append(("w", m.pc(), a, size, value)))
        for name, off in SEEDS.items():
            self._watch_seed(m, name, off, "route")
        m.at(KEYPRESSED, self._on_poll)
        m.at(READKEY, self._on_read)
        if self.capture_news:
            m.at("000E:05F6", self._on_news_page)
        # [derived: T121] A translated 6CA7 calls F1F6 directly via guest.Call;
        # hook its entry in both proof runs so they visit the same real site.
        if self.match_entry:
            # The whole handoff is the answer of this real guest site. A Prover
            # can replay its writes/registers on the original's F1F6 visit.
            m.at("0791:F1F6", lambda replay: None if replay else self._match())
        else:
            m.at(MATCH_AT, lambda replay: replay or m.stop("match"))
        if self.entry == "play_round":
            m.at(ROUND_END, self._on_round_end)

    def _on_news_page(self, replay):
        """Actual05F6entry: back buffer is complete, front copy/celebration not begun.

        Prover muted replay validates these reads without re-running the handler;
        a resume at the same hook is not a second actual page. Identical content
        on two real entries remains two snapshots. No key-policy method is called.
        """
        m=self.m
        if not self.capture_news or replay or m.muted:
            return
        ret=m.stack_word(0)
        country=side=manager=None
        if ret==0x4F72:
            bp=m.reg("bp")
            country=m.frame_word(bp,8)
            side=m.read(m.reg("ss")*16+((bp-1)&0xFFFF),1)[0]
            manager=m.read(m.far(0xA917)+191*country+0x2E,1)[0]
        snapshot=capture_news_page(m,return_address=f"000E:{ret:04X}",country=country,side=side,manager=manager,
                                   flags_words=tuple(m.stack_word(2+2*i) for i in range(3)),
                                   waiting_key=self.keys.waiting,pushed_back=bool(m.rd(PUSHED_BACK,1)),key_code=m.rd(KEY,1),
                                   seed_words=tuple(m.rd(off,2) for off in SEEDS.values()))
        self.news_history.append(snapshot)

    @property
    def news_pages(self):
        """Ordered exact text pages from retained actual-entry snapshots."""
        return tuple(page for snapshot in self.news_history for page in decode_news_pages(snapshot))

    def _on_round_end(self, replay):
        """At 70E6: the round's end, the game record as stage_end finds it."""
        if replay:
            return
        m = self.m
        game = m.far(GAME_PTR)
        self.record.append(("round_end", {"cursor": m.word_at(game + 0x26), "count": m.word_at(game + 0x28),
                                          "stage": m.read(game + 0x3C, 1)[0], "rounds": m.read(game + 0x3D, 1)[0]}))

    def _watch_seed(self, m, name, off, where):
        def step(old, new):
            self.record.append(("rng", name, int.from_bytes(old, "little"), int.from_bytes(new, "little"), m.pc(),
                                where))
        m.watch(m.DS * 16 + off, 2, step)

    def _site(self):
        """The key site: the return address of the call of 214B:08DD or 0723, at its entry; for 214B:1560's read,
        with 1560's caller (its far return at [bp+2], BP still 1560's at 08DD's entry)."""
        m = self.m
        site = m.where(m.stack_word(2), m.stack_word(0))
        if site == MENU_SITE:
            bp = m.reg("bp")
            site += "<" + m.where(m.frame_word(bp, 4), m.frame_word(bp, 2))
        return site

    def _on_poll(self, replay):
        m = self.m
        site = self._site()
        has, source = self.keys.poll(site, self)
        self.record.append(("key", site, "poll", self.keys.waiting if has else None, source))
        m.set_reg("ax", (m.reg("ax") & 0xFF00) | int(has))    # 0723's AL (seg_214B_01.asm 0745-074E), retf
        m.return_from(True, 0)

    def _on_read(self, replay):
        m = self.m
        site = self._site()
        if m.rd(PUSHED_BACK, 1):        # 08E3: a pushed-back key is read by the guest without waiting
            self.record.append(("key", site, "read", m.rd(KEY, 1), "pushed-back"))
            return
        key, source = self.keys.read(site, self)
        self.record.append(("key", site, "read", key, source))
        self._write("08DD's key (0947 DS:A976, 097C DS:A977)", m.DS * 16 + KEY, bytes([key, key]))
        m.set_reg("ax", (m.reg("ax") & 0xFF00) | key)          # 0979: AL, then retf (0982)
        m.return_from(True, 0)

    def replay(self, memory):
        """The memory `memory` (the call's start, Route.origin) with every write of the record made on it, in order."""
        if not self.record_writes:
            raise ValueError("replay: this Route was made with record_writes=False, so its record holds no guest "
                             "writes")
        out = bytearray(memory)
        for e in self.record:
            if e[0] == "w":
                _, _, a, size, value = e
                out[a:a + size] = (value & ((1 << 8 * size) - 1)).to_bytes(size, "little")
            elif e[0] == "k":
                _, _, a, data = e
                out[a:a + len(data)] = data
        return bytes(out)

    def screen_text(self):
        m = self.m
        raw = m.read(m.far(SCREEN_PTR), 4000)
        return "\n".join(bytes(raw[r * 160:(r + 1) * 160:2]).decode("cp437", errors="replace").rstrip()
                         for r in range(25))

    # -- the call ----------------------------------------------------------------------------------------------
    def call(self):
        """One call of route_fixture: from the fixture at the cursor game +0x26, to its return after a fixture with
        a managed side (played, or prepared for kind 0) or at the end of the calendar; with entry="play_round", one
        call of play_round around it (the round's end included when the cursor reaches the count). Returns the
        record."""
        m = self.m
        delay = m.DS * 16 + DELAY_COUNT          # Match's own input, made first so that its write finds it there
        raw = DELAY_COUNT_VALUE.to_bytes(4, "little")
        if m.read(delay, 4) != raw:
            self.inputs.append({"what": "delay calibration dword DS:A9FF (as Match)", "linear": delay,
                                "old": m.read(delay, 4).hex(), "new": raw.hex()})
            self._write("delay calibration DS:A9FF (Match's input)", delay, raw)
        ss = m.seg(SS_PARAGRAPH)
        if self.entry == "play_round":
            target, caller, ret, sp, bp = PLAY_ROUND, ROUND_CALLER, ROUND_RETURN, ROUND_SP, MENU_BP
        else:
            target, caller, ret, sp, bp = ROUTE_FIXTURE, CALLER, RETURN_TO, CALL_SP, CALLER_BP
        name = self.entry
        rseg, roff = ret.split(":")
        self._write(f"the call of {target} at {caller}: its return word", ss * 16 + sp,
                    int(roff, 16).to_bytes(2, "little"))
        tseg, toff = target.split(":")
        for reg, value in (("ss", ss), ("sp", sp), ("bp", bp), ("ds", m.DS), ("es", m.DS),
                           ("cs", m.seg(int(tseg, 16))), ("eip", int(toff, 16))):
            m.set_reg(reg, value)
        end = m.lin(ret)
        if self.match_entry:
            # Unicorn's until address stops before hooks there. Let the prover
            # finish the outer 6CA7 call at its return hook before stopping.
            m.at(ret, lambda replay: m.stop("route-return"))
        fresh = True
        while True:
            stopped = m.run(end + int(self.match_entry), self.timeout_s, fresh=fresh)
            fresh = True
            if stopped is None or stopped == "route-return":
                break
            if stopped != "match":
                raise GuestError(f"{name} stopped: {stopped}")
            self._match()
        if m.reg("sp") != sp + 2:
            raise GuestError(f"{name} returned with SP {m.reg('sp'):04X}, not {sp + 2:04X}")
        self.record.append(("return", ret))
        return self.record

    def round(self, limit=64):
        """play_round calls until one reaches the round's end (70E6), at most `limit`; returns the record."""
        if self.entry != "play_round":
            raise ValueError('round(): a Route made with entry="play_round"')
        for _ in range(limit):
            before = sum(1 for e in self.record if e[0] == "round_end")
            self.call()
            if sum(1 for e in self.record if e[0] == "round_end") > before:
                return self.record
        raise GuestError(f"no round's end in {limit} calls of {PLAY_ROUND}")

    def _match(self):
        """At 6F18: the managed match, by Match(tail=False) on this memory, written back; then on at 6F1D."""
        m = self.m
        regs = {r: m.reg(r) for r in ("eax", "ebx", "ecx", "edx", "esi", "edi", "ebp", "esp", "eflags", "cs",
                                       "ds", "es", "ss", "fs", "gs")}
        self.record.append(("stop", "0791:F1F6" if self.match_entry else MATCH_AT, dict(regs)))
        ss, sp, bp = regs["ss"], regs["esp"] & 0xFFFF, regs["ebp"] & 0xFFFF
        expected_sp = MATCH_SP - 4 if self.match_entry else MATCH_SP
        after_sp = sp + (8 if self.match_entry else 4)
        if (ss, sp, bp) != (m.seg(SS_PARAGRAPH), expected_sp, ENTRY_BP):
            raise GuestError(f"at {MATCH_AT}: SS:SP {ss:04X}:{sp:04X} BP {bp:04X}, not Match's frame "
                             f"{m.seg(SS_PARAGRAPH):04X}:{expected_sp:04X} BP {ENTRY_BP:04X}")
        game = m.far(GAME_PTR)
        index = m.word_at(game + 0x26)
        fx = m.read(m.far(FIXTURES_PTR) + FIXTURE_SIZE * (index - 1), FIXTURE_SIZE)
        fixture = Fixture(first=int.from_bytes(fx[4:6], "little"), second=int.from_bytes(fx[6:8], "little"),
                          index=index, kind=fx[2])
        here = bytearray(m.read(0, MEM_SIZE))
        # what the `call far` at 6F18 pushes: its return address 000E:6F1D (offset, then segment) at SP - 4
        rseg, roff = RUN_MATCH_RETURN.split(":")
        push = ss * 16 + sp - 4
        if not self.match_entry:
            here[push:push + 4] = int(roff, 16).to_bytes(2, "little") + m.seg(int(rseg, 16)).to_bytes(2, "little")
        image = Image(self.header + bytes(m.read(0, MEM_SIZE)) + self.tail)
        image.tables = self.tables
        match = RouteMatch(image, fixture, tail=False)
        for name, off in SEEDS.items():
            self._watch_seed(match.m, name, off, "match")
        before = match.m.read(0, MEM_SIZE)
        if match.inputs or before != bytes(here):
            first = next((i for i in range(MEM_SIZE) if before[i] != here[i]), None)
            raise GuestError(f"Match's set-up wrote what route_fixture had not left there: inputs {match.inputs}"
                             + ("" if first is None else f", first other byte at linear 0x{first:05X}"))
        for _ in match.events():
            pass
        mm = match.m
        if (mm.pc(), mm.reg("sp"), mm.reg("bp"), mm.reg("ss"), mm.reg("ds")) != (
                mm.lin(RUN_MATCH_RETURN), after_sp & 0xFFFF, bp, ss, regs["ds"]):
            raise GuestError(f"Match did not end at {RUN_MATCH_RETURN} with F1F6's retf 4 "
                             f"(SP {after_sp:04X}, BP {bp:04X})")
        after = mm.read(0, MEM_SIZE)
        result = match.result()
        self.matches.append(match)
        self.record.append(("team", {"fixture": index, "choices": match.team_choices, "keys": match.team_keys}))
        self.record.append(("match", {"fixture": index, "first": fixture.first, "second": fixture.second,
                                      "kind": fixture.kind, "managed": result["managed"], "score": result["score"],
                                      "winner": result["winner"]}))
        now = m.read(0, MEM_SIZE)
        for a, b in _runs(now, after):
            self._write("match", a, after[a:b])
        for r, v in regs.items():
            m.set_reg(r, v)
        m.set_reg("cs", m.seg(int(rseg, 16)))
        m.set_reg("eip", int(roff, 16))
        m.set_reg("sp", after_sp & 0xFFFF)
        self.record.append(("resume", RUN_MATCH_RETURN, after_sp & 0xFFFF))


def _runs(a, b, chunk=256):
    """The [start, end) runs of bytes where a and b differ."""
    out, n, i = [], len(a), 0
    start = None
    while i < n:
        j = min(i + chunk, n)
        if start is None and a[i:j] == b[i:j]:
            i = j
            continue
        for k in range(i, j):
            if a[k] != b[k]:
                if start is None:
                    start = k
            elif start is not None:
                out.append((start, k))
                start = None
        i = j
    if start is not None:
        out.append((start, n))
    return out


# -- T123 sealed consumer ---------------------------------------------------
from dataclasses import dataclass
from copy import deepcopy


@dataclass(frozen=True)
class RoundStep:
    """One immutable observation of an in-process sealed round continuation."""
    status: str
    state: dict
    played_fixtures: tuple
    news_pages: tuple
    match: object = None
    continuation: object = None
    record: tuple = ()


def _deferred_image(image):
    data=image.memory;ds=image.DS*16
    def word(a):return int.from_bytes(data[a:a+2],'little')
    game=word(ds+GAME_PTR)+16*word(ds+GAME_PTR+2)
    return (word(game+0x26)==word(game+0x28) and data[game+0x3D]==1
            and data[game+0x3C] in (4,8))


class _RoundKeys:
    """Existing Route.Keys policy through the real menu ports' key API."""
    def __init__(self,round):self.round=round
    def keypressed(self,site):
        r=self.round;has,source=r.keys.poll(site,r)
        r.record.append(('key',site,'poll',r.keys.waiting if has else None,source))
        return has
    def key(self,site):
        r=self.round
        if site==MENU_SITE:site=r._site()
        key,source=r.keys.read(site,r)
        r.record.append(('key',site,'read',key,source))
        r._write("08DD's key (0947 DS:A976, 097C DS:A977)",r.m.DS*16+KEY,bytes([key,key]))
        r.m.set_reg('ax',(r.m.reg('ax')&0xFF00)|key)
        return key


class _RoundContinuation(Route):
    """Owns one plain dispatcher and its suspended ordinary Match, in process."""
    def __init__(self,image,keys):
        from .port.engine import PortMachine
        from . import port
        self.header=image.header;self.tail=bytes(image.memory[MEM_SIZE:]);self.tables=image.tables
        self.origin=bytes(image.memory[:MEM_SIZE]);self.m=PortMachine(image.memory,image.load)
        self.keys=keys if isinstance(keys,Keys) else Keys(DEFAULT_KEYS if keys is None else keys)
        self.record=[];self.inputs=[];self.matches=[];self.news_history=[]
        self.capture_news=True;self.record_writes=False;self.entry='play_round';self.match_entry=True;self.timeout_s=600
        self.pending=None;self.pending_context=None;self.completed=[];self.finished=False
        for name,off in SEEDS.items():self._watch_seed(self.m,name,off,'route')
        self.m.at('000E:05F6',self._on_news_page)
        self.m.at(ROUND_END,self._on_round_end)
        self.m.at('0791:F1F6',lambda replay:None if replay else self.m.stop('match'))
        self.m.at(READKEY,self._pushed_key)
        loaded=[]
        for reg,variant in port.load(['all']):
            real=port.Registry(reg.name,reg.doc)
            for entry in reg.entries.values():
                if entry.stub is None:real._add(entry)
            if real.entries:loaded.append((real,variant))
        self.ports=port.install(self.m,loaded,keys=_RoundKeys(self))
        self.m.watch(self.m.far(GAME_PTR)+0x26,2,self._fixture_completed)

    def _fixture_completed(self,old,new):
        previous=int.from_bytes(old,'little');current=int.from_bytes(new,'little')
        if current!=previous+1:return
        game=self.m.far(GAME_PTR)
        if not 1<=previous<self.m.word_at(game+0x28):return
        raw=self.m.read(self.m.far(FIXTURES_PTR)+8*(previous-1),8)
        item={'fixture':previous,'first':int.from_bytes(raw[4:6],'little'),
              'second':int.from_bytes(raw[6:8],'little'),'kind':raw[2],
              'score':tuple(raw[:2]),'winner_flag':raw[3]}
        self.completed.append(item)

    def _pushed_key(self,replay):
        if self.m.rd(PUSHED_BACK,1):
            self.record.append(('key',self._site(),'read',self.m.rd(KEY,1),'pushed-back'))

    def _image(self):
        image=Image.__new__(Image);image.header=self.header;image.memory=bytearray(self.m.read(0,MEM_SIZE)+self.tail)
        image.load=self.m.load;image.DS=self.m.DS;image.tables=self.tables
        return image

    def _step(self,status):
        return RoundStep(status,self._image().state(self.tables),tuple(deepcopy(self.completed)),
                         tuple(self.news_history),self.pending if status=='match' else None,
                         self if status=='match' else None,tuple(deepcopy(self.record)))

    def start(self):
        # Entry terminal guard was checked before constructing this controller.
        m=self.m;raw=DELAY_COUNT_VALUE.to_bytes(4,'little')
        if m.read(m.DS*16+DELAY_COUNT,4)!=raw:self._write('delay calibration DS:A9FF (Match input)',m.DS*16+DELAY_COUNT,raw)
        word=int(ROUND_RETURN.split(':')[1],16)
        self._write(f'the call of {PLAY_ROUND} at {ROUND_CALLER}: its return word',m.seg(SS_PARAGRAPH)*16+ROUND_SP,word.to_bytes(2,'little'))
        for name,value in [('ss',m.seg(SS_PARAGRAPH)),('sp',ROUND_SP),('bp',MENU_BP),('ds',m.DS),('es',m.DS),('cs',m.seg(0xE)),('eip',0x70B9)]:m.set_reg(name,value)
        return self.advance()

    def advance(self):
        from .machine import REGS
        m=self.m;stopped=m.run(m.lin(ROUND_RETURN),self.timeout_s,fresh=True)
        if stopped=='match':
            context={name:m.reg(name) for name in REGS}
            game=m.far(GAME_PTR);index=m.word_at(game+0x26);fx=m.read(m.far(FIXTURES_PTR)+8*(index-1),8)
            fixture=Fixture(first=int.from_bytes(fx[4:6],'little'),second=int.from_bytes(fx[6:8],'little'),index=index,kind=fx[2])
            self.pending=Match.from_route_entry(self._image(),fixture,context)
            self.pending_context=context
            for name,off in SEEDS.items():self._watch_seed(self.pending.m,name,off,'match')
            self.record.append(('stop','0791:F1F6',dict(context)))
            return self._step('match')
        if stopped is not None:raise GuestError('sealed round stopped unexpectedly: '+str(stopped))
        if m.reg('sp')!=ROUND_SP+2:raise GuestError('sealed play_round returned with wrong SP')
        self.finished=True;self.record.append(('return',ROUND_RETURN))
        return self._step('deferred-rollover' if _deferred_image(self._image()) else 'complete')

    def resume(self,match):
        # Every rejected request is checked BEFORE route-visible writes/counters.
        if self.finished or self.pending is None or match is not self.pending:
            raise ValueError('foreign or already consumed round match')
        if not match.over:raise ValueError('round match is incomplete')
        mm=match.m;context=self.pending_context;ss=context['SS']
        if (mm.pc(),mm.reg('sp'),mm.reg('bp'),mm.reg('ss'),mm.reg('ds'))!=(mm.lin(RUN_MATCH_RETURN),MATCH_SP+4,ENTRY_BP,ss,context['DS']):
            raise ValueError('completed route match has the wrong actual return frame')
        result=match.result();after=mm.read(0,MEM_SIZE);now=self.m.read(0,MEM_SIZE)
        self.pending=None;self.pending_context=None
        for start,end in _runs(now,after):self._write('match',start,after[start:end])
        # The caller resumes with the actual completed Match's whole CPU,
        # including scratch registers/flags, after validating its real frame.
        from .machine import REGS
        for name in REGS:self.m.set_reg(name,mm.reg(name))
        item={'fixture':match.opts['index'],'first':match.opts['first'],'second':match.opts['second'],
              'kind':match.opts['kind'],'managed':result['managed'],'score':deepcopy(result['score']),'winner':result['winner']}
        self.matches.append(match)
        self.record.append(('match',deepcopy(item)));self.record.append(('resume',RUN_MATCH_RETURN,MATCH_SP+4))
        return self.advance()


def play_round(state,tables,keys=None):
    """Start one sealed round; return its completed, managed, or deferred step.

    A supplied Keys object carries the caller's queue across round calls. A
    mapping follows Route's existing policy. Production chooses no legal eleven.
    """
    image=Image.from_state(state,tables)
    if _deferred_image(image):
        return RoundStep('deferred-rollover',deepcopy(state),(),())
    return _RoundContinuation(image,keys).start()


def resume_round(continuation,match):
    """Resume only the completed pending ordinary Match of this continuation."""
    if not isinstance(continuation,_RoundContinuation):raise ValueError('foreign round continuation')
    return continuation.resume(match)
