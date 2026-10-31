"""The original's watched match, played interactively on goal2's own state (issue 250).

    m = Match(image, Fixture(first=7, second=19), managed=7)
    for ev in m.events():                       # the original runs; events come as they happen
        show(ev)
        if ev.kind == "decision":               # the original stops and asks the manager
            m.answer(substitutions=[(off, on)], tactics={4: True})
    result = m.result()

By default the match is the original's code (0791:F1F6 run_match, then route_fixture's 0791:B7FA update_fixture_player_state)
under Unicorn. Explicit engine="port" runs the registered Python translations on plain memory instead. The kit
answers the original's key reads at its decision points, with the keys a manager would press (screens.py).
Every constant cites the listing or a finding."""
import hashlib
import json
import zlib
from dataclasses import dataclass, field, asdict

from .image import (Image, COUNTRIES_PTR, COUNTRY_SIZE, PLAYERS_PTR, PLAYER_SIZE, N_PLAYERS, N_COUNTRIES,
                    MANAGERS_PTR, FIXTURES_PTR, FIXTURE_SIZE, GAME_PTR, TACTICS, MANAGER, names_and_templates)
from .machine import Machine, GuestError, MEM_SIZE
from . import screens as S

VERSION = "4"                  # 4: live Python port frames are reconstructed by deterministic replay on load
LOADS = ("2", "3", VERSION)

# -- the calls (route_fixture's own, static/goal-exe/code/seg_000E_09.asm:308 and :396) -------------------------
RUN_MATCH, RUN_MATCH_RETURN = "0791:F1F6", "000E:6F1D"
PLAYER_UPDATE, PLAYER_UPDATE_RETURN = "0791:B7FA", "000E:6FFD"
SS_PARAGRAPH = 0x3052          # SS = load + 0x3052 (E011-r0001 and E006: SS 0x3875 at load 0x823, CPU component)
ENTRY_SP = 0x3EC0              # SP at F1F6's entry in E011-r0001 (its BP chain; E033 notes section 1)
ENTRY_BP = 0x3EDE              # route_fixture's BP then
DELAY_COUNT, DELAY_COUNT_VALUE = 0xA9FF, 20   # the delay calibration dword (F006; E032: passes only, >= 10)
# -- the keyboard (214B) and the read sites (the return address of each call of 214B:08DD) ------------------------
KEYPRESSED, READKEY = "214B:0723", "214B:08DD"
PUSHED_BACK, KEY = 0x79AE, 0xA976            # 08DD: 08E3 tests the pushed-back flag; 0947/097C store the key
SITE_BOARD = "0791:041A"       # 0791:0106 the match board (0415)
SITE_POLL = "0791:93D3"        # 0791:9372 the in-play key poll (93CE)
SITE_NOTICE = "0791:8050"      # 0791:7FCF the substitution notice (804B)
SITE_PROMPT = "0791:CEED"      # 0791:CC7B the captain and taker prompt (CEE8)
SITE_SELECT = "0791:E61F"      # 0791:E44F SELECT TEAM (E61A)
SITE_MENU = "214B:157C"        # 214B:1560's read; its caller says which menu:
MENU_TEAM, MENU_TACTICS = "0791:EE9F", "1771:1A24"     # ED8A (EE9A), 1771:1981 (1A1F)
MENU_OWN = "1771:4C0A"         # 1771:4B61 a player's own tactics (4C05); 1560's [bp+6] is its row count, 5 with
OWN_TACTICS, PLAYER_STATUS = 0x0F, 0x10   # the man-marking row; player +0xF own tactic set, +0x10 status (F010)
SITE_MESSAGE = "214B:098A"     # 214B:0983, the message routines' read (04F8, 1765)
MESSAGE_IF = "214B:1765"       # message_if_flag(text far pointer at [SP+4], flag at [SP+8]): shows text when flag
PLAYER_POSITION, PLAYER_ENERGY = 0x06, 0x0E   # player record: position code (0 the keeper), energy (0 injured; F018)
KP_POLL, KP_WAIT, KP_PROMPT, KP_NOTICE = "0791:93C2", "0791:CC54", "0791:CEDE", "0791:8047"
WAIT_FROM = {0xCED9: "prompt", 0x8042: "notice"}   # 0791:CC2E's callers: CC7B (CED6), 7FCF (803F)
TEAM_MENU = "0791:ED8A"
MENU_CONTEXT = {"0791:F20A": "pre_match", "0791:F331": "post_match", "0791:9AE3": "half_time",
                "0791:8103": "substitution", "0791:945B": "pause", "0791:9B42": "extra_time",
                "0791:9B70": "extra_time"}     # ED8A's callers: F207, F32E, 9A32 (9AE0), 8062 (8100), 9372, 9B0C, 9B5B
DECIDED_AT_MENU = ("half_time", "pause", "extra_time")
NOTICE, PROMPT, WAIT = "0791:7FCF", "0791:CC7B", "0791:CC2E"
TICK, MATCH_PLAYED = "0791:970C", "0791:F2E3"       # the clock (E011 notes 4); F1F6 after play_match
PLAY_MATCH = "0791:F098"       # play_match, called by F1F6 at F2E0 after the set-up and the team screen
WAIT_FAMILY = ("000E:05F6", "000E:0572", "000E:04F5", "000E:045D")   # menu code only (E010; watched.py)
BOOKING, SEND_OFF, INJURE = "0791:798D", "0791:7B77", "0791:7D56"   # F027, F020
# -- match state (DS offsets) ------------------------------------------------------------------------------------
SEED = 0x7B62                  # the main RNG word (F004)
MINUTE, SUBTICK = 0x831F, 0x831D
SCORE = 0x9B3C                 # the two score bytes (team 0, team 1)
STATS = 0x7B7E                 # bytes + 10*team, in this order (0791:0106 rows; 7D56 adds injuries at + 9)
STAT_NAMES = ("corners", "free_kicks", "penalties", "shots", "on_target", "saves", "fouls", "bookings",
              "red_cards", "injuries")
# The event stamps: each of these is recorded at the original's own write of the byte (Machine.watch), in write
# order: bookings +7, red cards +8, injuries +9 of STATS + 10t (798D at 7A01, 7B77 at 7B6D, 7D56 at 7DD9); the
# score bytes (a watched goal 685C, its cancellation 68B3, the quick engine B261/D77B); the commentary ring's
# counter DS:80EE (1D4A); the minute DS:831F (the clock 970C at 9762); substitutions left DS:9B38 + t (C5DC).
# What a write of the score bytes means, by the instruction that makes it (static/goal-exe/code/seg_0791_11.asm,
# _18.asm, _21.asm, _02.asm; named/seg_0791_11.c quick_match_engine):
GOAL_WRITE, CANCEL_WRITE = "0791:685C", "0791:68B3"   # the watched goal (inc) and its take-back (dec, DS:830E set)
QUICK_CLEAR, QUICK_COMMIT = "0791:D77B", "0791:DA58"  # quick_match_engine D733 saves the committed score word in
# [bp-2] (D75C) and clears DS:9B3C (D77B); roll_quick_goals (B19D, inc at B261) rolls trial counts into it and D8A5
# subtracts the saved ones: scratch, no goal; it commits at most one goal per call (record_goal 6443, [bp-2] + 1)
# and writes [bp-2] back at DA58: the committed goals are DA58's word minus the word D77B cleared.
QUICK_SCRATCH = ("0791:B261", "0791:D8A5")
REPLAY_RESTORE = "0791:0F11"   # action_replay 0C65 restores a snapshot's score (not reached by the kit's runs)
# The only instructions whose writes make the other events, in play (E033 writer probe, PR 251 round 2: 5 matches,
# watched, quick, cards, injury, substitutions): u214b_wrap_add_in_range 214B:1C86 (add at 1CBC, wrap at 1CF8)
# called by write_commentary_line 0791:1D4A; 798D, 7B77, 7D56 (above); the clock 9762; C5DC at C7DC.
WRITERS = {"line": ("214B:1CBC", "214B:1CF8"), "booking": ("0791:7A01",), "sending_off": ("0791:7B6D",),
           "injury": ("0791:7DD9",), "minute": ("0791:9762",), "substitution": ("0791:C7DC",)}
CARD_EVENTS = (("booking", "bookings"), ("sending_off", "sendings_off"), ("injury", "injuries"))
BARS = (0x80F2, 0x80F6)        # the board's two bar rows (0106: f_0791_006C rows 0x13, 0x14)
SCORERS, SCORERS_SIDE = 0x7BD1, 0x21          # 0106: 0x7BD1 + 0x21*team + 3*k (word player, byte minute)
MOTM = 0x7C3A                  # F014
GOAL_COUNTS = 0x80F0           # record_goal 6443 adds 1 to DS:80F0 + side (up to 11): the original's own goal count
RING, RING_REC, RING_SIZE, RING_NEWEST = 0x7C38, 6, 200, 0x80EE   # commentary.py; 1D4A
SCREEN_PTR = 0xA96A            # the text page's far pointer (214B:0755)
PITCH, PITCH_SIZE = 0x80E8, 0x16   # pitch record of slot s (1..22) at DS:80E8 + 0x16 s: +0 x, +1 y, +0xD the
BALL = 0x82F6                      # player word, +0x12 the state; the ball at DS:82F6: +0 x, +1 y (F013;
TEAM_KEYS = ("first", "second")    # static/goal-exe/annotations/fields.tsv, `likely`)


# -- the fixture's kind byte +2 (F023 section 9): the kinds the stage builders write; 1 is a friendly
KINDS = (1, 2, 3, 5, 6, 7, 8, 101, 102, 103, 200, 201, 202, 203)
DECIDERS = frozenset([4] + list(range(8, 204)))   # DS:693A, the set A405 tests into DS:7C36: extra time and shoot-out
# -- extra time and the shoot-out (issue 252): play_match F098 (named seg_0791_12.c) runs, for a decider level after
# 90 minutes, 9B0C (extra time's first half) and 9B5B (its second), then, still level, penalty_shootout A10A
# (static/goal-exe/code/seg_0791_16.asm; named seg_0791_08.c):
EXTRA_TIME_CLOCK = "0791:9B15"  # 9B0C sets the clock for extra time: minute DS:831F := 0x59 (89); 970C counts on
SHOOTOUT = "0791:A10A"          # penalty_shootout's entry
KICK, KICK_RETURN = "0791:A006", "0791:A1EF"   # play_shootout_kick(A10A's BP), called at A1EC
ORDER_READ = "0791:9D67"        # pick_shootout_takers_managed 9B93: its 214B:1560 read (9D62); 9B93's frame:
ORDER_HIGHLIGHT_BP, ORDER_NEEDED_BP = -6, -4   # local_8 the highlighted squad slot 1..11, local_6 the picks needed
# A10A's frame (its BP is the argument of 9B93, 9ED3 and A006): the side to kick [bp-0x1F], the next taker's index
# of side t [bp-0x1E+t], the takers of side t a Pascal string of pitch slots at [bp-0x1A+12t] (9B93 fills its
# length byte; 9ED3 entries 1..11).
SO_SIDE, SO_INDEX, SO_TAKERS = -0x1F, -0x1E, -0x1A
TABLE_READS = ("1771:9022", "1771:91BE")   # after a non-friendly, run_match's E929 calls 1771:958D(.., 0): one pass of
#                                            the competition's table screen, 8E9A (read at 901D) or 9028 (91B9)
TABLE_KEY = "1771:9567"         # ... or the finals' table 9509, 'hit any key' (its 214B:08DD at 9562)
CONFIDENCE, STATUS = 0x0C, 0x10  # player +0xC confidence (F020), +0x10 status: element k is bit k-1 (F027 section 2)
SUSPENDED, SENT_OFF, CARRIED_BOOKING, SUBSTITUTED_OFF = 0x80, 0x20, 0x08, 0x04


class MatchError(RuntimeError):
    """The original refused a decision or a state goal2 asked for (the message says which)."""


@dataclass(frozen=True)
class Fixture:
    first: int                 # team 0: fixture +4 (DS:9B34)
    second: int                # team 1: fixture +6 (DS:9B36), the host of a friendly (0791:A6E4)
    index: int = None          # the calendar number the set-up seeds from (0791:2648); None: [A923]+0x26
    kind: int = 1              # fixture +2 (F023 section 9): 1 a friendly; KINDS the ones the builders write


@dataclass
class Event:
    kind: str
    minute: int
    score: tuple
    data: dict = field(default_factory=dict)

    def __str__(self):
        extra = " ".join(f"{k}={v}" for k, v in self.data.items() if k not in ("players", "eleven", "bench", "positions"))
        return f"[{self.minute:3d}' {self.score[0]}-{self.score[1]}] {self.kind} {extra}"


class _PortKeys:
    """The kit's key logic for a port's key reads (port/mem.py read_key, keypressed): what the hooks at 214B:08DD and
    0723 answer from the same site, with 08DD's own writes (seg_214B_02.asm): the pushed-back flag cleared (08EA),
    the key DS:A976 (0947) and the last key DS:A977 (097C)."""

    def __init__(self, match):
        self.match = match

    def _unprovable(self, site):
        """Under a proof (port/prove.py) the original's key read is the kit's site, replayed from the port's run; a
        port that answers its key read itself leaves nothing to replay: refused, never proved blind."""
        prover = getattr(self.match, "prover", None)
        if prover is not None and prover.in_port_run():
            from .port import PortError
            raise PortError(f"a proved port answers a key read itself at {site}: such a port cannot be proved yet")

    def keypressed(self, site):
        self._unprovable(site)
        return self.match._key_waiting(site)

    def key(self, site):
        self._unprovable(site)
        k = self.match
        m, mem = k.m, k.ports.mem
        cached = getattr(k, "_ported_key", None)
        if site == SITE_BOARD and cached is None:
            k._on_board()
        if m.rd(PUSHED_BACK, 1):
            mem.wds8(PUSHED_BACK, 0, "214B:08EA")
            key = m.rd(KEY, 1)
        else:
            if cached is not None:
                if cached[0] != site:
                    raise MatchError(f"cached menu key for {cached[0]}, read at {site}")
                key = cached[1]
                del k._ported_key
            else:
                key = k._key_for(site)
            if key is None:
                return None             # stopped for a decision: mem.read_key refuses it (PortError)
            mem.wds8(KEY, key, "214B:0947")
        mem.wds8(KEY + 1, key, "214B:097C")
        return key


def fresh_state(players_before):
    """The kit's state of a match before run_match starts (Match.__init__; E034 builds one at a shoot-out's
    start from a recorded state the same way)."""
    return {"phase": "run_match", "fresh": True, "over": False, "full_time": False, "minute": 0,
            "score": [0, 0], "squads": None, "scorers": [[], []],
            "candidates": {}, "menu_context": None, "notice": None, "answer": None, "waiting": None,
            "poll_keys": [], "prompt": None, "pending_subs": [], "recording": False,
            "decisions": [], "draws": [], "commentary": [], "half_time_score": None, "board": None,
            "ticks": 0, "kickoff_seed": None, "live": False, "pending": [],
            "log": {"goals": [], "goals_disallowed": [], "bookings": [], "sendings_off": [], "injuries": [],
                    "substitutions": []},
            "stage": "match", "score_90": None, "score_120": None, "kick": None, "kicks": [], "order": None,
            "players_before": players_before}


class Match:
    def __init__(self, image, fixture, *, managed=None, captain=None, seed=None, players=None, countries=None,
                 substitutions=None, ticks=False, record_draws=False, delay_byte=None, timeout_s=60, ports=None,
                 prove=None, set_piece=False, engine="original"):
        """image: an Image of the original (goal2's savestate bytes through Image.from_savestate, e.g. of
        to_savestate(state, template); or GameState.mem through Image.from_memory_component). On the fixture
        tried, the match depended on the image only through its two teams' records (E033 notes, section 2).
        players, countries: goal2's records to write first (lists of 3061 byte
        strings of 0x14 and 129 of 0xBF), else the image's are used. managed: the country goal2 manages (default:
        the image's human country); the other must be the computer's. captain: a player word of the managed
        eleven (default: the original's pick, its best leader). seed: written to the main RNG word at the captain
        prompt, after the set-up's own reseed (default: none, the original's). ticks: also yield one `tick` event
        per tick. record_draws: keep every main-RNG write from the captain prompt to the full-time board (the
        engine check). delay_byte: the speed byte [A923]+0x3F at the captain prompt (the engine check).
        timeout_s: the most one stretch between two events may take (normally well under a second).
        substitutions: the substitution budget, one number for both sides or (team 0, team 1), 0..255, written over
        the set-up's (A4A1: 5 a side for a friendly, kind 1, and 2 for every other kind; F027 section 4) when
        play_match starts; None keeps the original's. The original counts it down (C5DC) and stops both the
        manager (E544 'no more substitutes') and the computer's rule (8062) at 0; a player taken off cannot come
        back (element 3, 1771:3216), so 9 or more is no limit for a bench of 9.
        ports: the port mode (port/, README "Ports"): port modules ('pilot', 'pilot.coin-swapped' for a variant,
        'all') whose Python routines run in place of the original's; None or empty: the original's code only.
        prove: the proof mode (port/prove.py, T59): None, or N, every call of a ported routine from the main RNG's
        N-th draw on (0: from the start; N > 0 needs record_draws) is run side by side with the original's, and the
        first difference raises ProofError; `prover.summary()` counts the proved calls. A proved match cannot be
        saved."""
        if engine not in ("original", "port"):
            raise ValueError("engine: original or port")
        if engine == "port" and prove is not None:
            raise ValueError("engine=port cannot run an inline original proof; compare backends externally")
        self.engine = engine
        if fixture.kind not in KINDS:
            raise ValueError(f"fixture kind {fixture.kind} is none of the kinds the original's builders write {KINDS}")
        if fixture.first == fixture.second:
            raise ValueError("the fixture needs two distinct countries")
        for c in (fixture.first, fixture.second):
            if not 1 <= c <= 128:
                raise ValueError(f"country {c} is not 1..128")
        problems = image.build_problems()
        if problems:
            raise ValueError("the image does not hold the GOAL.EXE this kit was made on (the registered version, set "
                             "goal2-a949da2f); it differs in: " + "; ".join(problems))
        self.timeout_s = timeout_s
        if engine == "port":
            from .port.engine import PortMachine
            self.m = PortMachine(image.memory, image.load)
            ports = ["all"] + list(ports or ())
        else:
            self.m = Machine(image.memory, image.load)
        self.image_header = image.header
        self.image_tail = bytes(image.memory[MEM_SIZE:])    # guest memory above 1 MiB + HMA: the match never
        self.image_sha256 = image.sha256()                  # touches it; kept for memory_component()
        self.tables = getattr(image, "tables", None)        # GOAL.EXE's tables when the image is goal2's state (T80)
        self.inputs = []
        self._write_state(players, countries)
        if managed is None:
            human = [c for c in (fixture.first, fixture.second) if self._manager_byte(c) > 0x80]
            if len(human) != 1:
                raise ValueError("name the managed country: the image's human country is not in this fixture")
            managed = human[0]
        if isinstance(managed, bool) or not isinstance(managed, int) or not 1 <= managed <= 128:
            raise ValueError("the managed country must be 1..128")
        self._make_managed(managed, fixture)
        index = fixture.index if fixture.index is not None else self.m.rd_far(GAME_PTR, 0x26)
        if substitutions is not None:
            budget = [substitutions] * 2 if isinstance(substitutions, int) else list(substitutions)
            if len(budget) != 2 or any(not isinstance(b, int) or not 0 <= b <= 255 for b in budget):
                raise ValueError("substitutions: a budget 0..255, or (team 0's, team 1's)")
            substitutions = budget
        self.opts = {"first": fixture.first, "second": fixture.second, "index": index, "managed": managed,
                     "captain": captain, "seed": seed, "ticks": ticks, "record_draws": record_draws,
                     "delay_byte": delay_byte, "kind": fixture.kind, "substitutions": substitutions}
        if engine == "port":self.opts["engine"] = "port"
        if not isinstance(set_piece, bool):
            raise ValueError("set_piece: a boolean opt-in")
        if set_piece:
            self.opts["set_piece"] = True
        self.side = (0 if managed == fixture.first else 1) if managed in (fixture.first, fixture.second) else None
        if captain is not None and (self.side is None or captain not in self._squad(managed)[:11]):
            raise ValueError(f"captain {captain} is not in the managed eleven")
        self._write_fixture(index, fixture)
        self._declare("delay calibration dword DS:A9FF", self.m.DS * 16 + DELAY_COUNT,
                      DELAY_COUNT_VALUE.to_bytes(4, "little"))
        self.st = fresh_state(self._players_now([fixture.first, fixture.second]))
        self._queue = []
        self._menu = None
        self._result = None
        self._names = None
        self._hooks()
        self._install_ports(ports)
        self._install_proof(prove)
        self._call(RUN_MATCH, RUN_MATCH_RETURN)

    def _install_proof(self, prove):
        """The proof mode (T59, port/prove.py): the ports' calls from the draw `prove` on, side by side."""
        self.prover = None
        if prove is None:
            return
        if not self.ports:
            raise ValueError("prove: a proof needs ports")
        if isinstance(prove, bool) or not isinstance(prove, int) or prove < 0:
            raise ValueError("prove: the draw from which calls are proved, 0 or more")
        if prove and not self.opts["record_draws"]:
            raise ValueError("prove: from a draw > 0 needs record_draws")
        from .port.prove import Prover
        self.prover = Prover(self.m, self.ports, armed=lambda: len(self.st["draws"]) >= prove,
                             where=lambda: f"minute {self.m.rd(MINUTE)}, after draw {len(self.st['draws'])}")

    def port_frames(self):
        """The port frames waiting on a call of the original's code now, outermost first (port/guest.py): a
        decision reached inside such a call is answered with them live."""
        return [f.describe() for f in self.m.frames]

    def _install_ports(self, specs):
        """The port mode (T58): ports run in place of their routines, after the kit's hooks (port/__init__.py)."""
        self.ports = None
        if specs:
            from . import port
            self.ports = port.install(self.m, specs, keys=_PortKeys(self))
            self.opts["ports"] = self.ports.names
            self.ports.calls.update(self.st.get("port_calls") or {})   # a loaded match goes on counting
            self.st["port_calls"] = self.ports.calls

    # -- inputs ------------------------------------------------------------------------------------------
    def _declare(self, what, linear, raw):
        raw = bytes(raw)
        old = self.m.read(linear, len(raw))
        if old != raw:
            self.m.write(linear, raw)
            self.inputs.append({"what": what, "linear": linear, "old": old.hex(), "new": raw.hex()})

    def _write_state(self, players, countries):
        if players is not None:
            if len(players) != N_PLAYERS or any(len(p) != PLAYER_SIZE for p in players):
                raise ValueError(f"players: {N_PLAYERS} records of {PLAYER_SIZE} bytes")
            self._declare("goal2's player records [DS:A91B]", self.m.far(PLAYERS_PTR), b"".join(players))
        if countries is not None:
            if len(countries) != N_COUNTRIES or any(len(c) != COUNTRY_SIZE for c in countries):
                raise ValueError(f"countries: {N_COUNTRIES} records of {COUNTRY_SIZE} bytes")
            self._declare("goal2's country records [DS:A917]", self.m.far(COUNTRIES_PTR), b"".join(countries))

    def _country(self, c):
        return self.m.far(COUNTRIES_PTR) + COUNTRY_SIZE * c

    def _manager_byte(self, c):
        return self.m.read(self._country(c) + MANAGER, 1)[0]

    def _squad(self, c):
        raw = self.m.read(self._country(c), 40)
        return [int.from_bytes(raw[2 * i:2 * i + 2], "little") for i in range(20)]

    def _tactics(self):
        return self.m.read(self._country(self.opts["managed"]) + TACTICS, 1)[0]

    def _player(self, player, field):
        return self.m.read(self.m.far(PLAYERS_PTR) + PLAYER_SIZE * player + field, 1)[0]

    def _players_now(self, countries):
        """{player word: [team, confidence +0xC, energy +0xE, status +0x10]} for the squads of the two countries."""
        out = {}
        for team, c in enumerate(countries):
            for w in self._squad(c):
                if w:
                    out[str(w)] = [team, self._player(w, CONFIDENCE), self._player(w, PLAYER_ENERGY),
                                   self._player(w, STATUS)]
        return out

    def _make_managed(self, managed, fixture):
        """Make `managed` manager 1's country as the original's records hold one (+0x2E = 0x81, and the manager
        array's byte at +3*0x81), releasing manager 1's former country as 000E:01FA does (+0x2E := its number)."""
        other = fixture.second if managed == fixture.first else fixture.first
        mgr = self.m.far(MANAGERS_PTR) + 3 * 0x81
        old = self.m.read(mgr, 1)[0]
        if old != managed:
            if 1 <= old <= 128 and self._manager_byte(old) == 0x81:
                self._declare(f"release country {old} from manager 1 (+0x2E := {old}, as 000E:01FA)",
                              self._country(old) + MANAGER, [old])
            self._declare(f"manager 1's country := {managed}", mgr, [managed])
        self._declare(f"country {managed} managed by manager 1 (+0x2E := 0x81)", self._country(managed) + MANAGER, [0x81])
        for other in (fixture.first, fixture.second):
            if other != managed and self._manager_byte(other) > 0x80:
                raise ValueError(f"country {other} is another human manager's: two managed sides are not supported")

    def _write_fixture(self, index, fixture):
        count = self.m.rd_far(GAME_PTR, 0x28)
        if not 1 <= index <= count:
            raise ValueError(f"fixture index {index} outside the calendar 1..{count}")
        rec = bytes([0xFE, 0, fixture.kind, 0]) + fixture.first.to_bytes(2, "little") + fixture.second.to_bytes(2, "little")
        base = self.m.far(FIXTURES_PTR) + FIXTURE_SIZE * (index - 1)
        self._declare(f"fixture {index} := {fixture.first} v {fixture.second}, kind {fixture.kind}", base, rec)
        self._declare("fixture index [A923]+0x26 (route_fixture's; the set-up seeds from it, 0791:2648)",
                      self.m.far(GAME_PTR) + 0x26, index.to_bytes(2, "little"))
        self.fixture_ptr = (self.m.rd(FIXTURES_PTR + 2), self.m.rd(FIXTURES_PTR) + FIXTURE_SIZE * (index - 1))

    def _call(self, target, return_to):
        seg, off = self.fixture_ptr
        self.m.set_reg("bp", ENTRY_BP)
        self.end_lin = self.m.far_call(target, [seg, off], return_to, self.m.seg(SS_PARAGRAPH), ENTRY_SP)
        self.st["fresh"] = True

    # -- the public interface ------------------------------------------------------------------------------
    @property
    def over(self):
        return self.st["over"]

    @property
    def score(self):
        return tuple(self.st["score"])

    @property
    def minute(self):
        return self.st["minute"]

    @property
    def waiting(self):
        """The decision the original waits on (its event data), or None."""
        return self.st["waiting"]

    def events(self):
        """The match's events as they happen. A `decision` event means the original stopped and asks the
        manager: call answer() before taking the next event (taking it without an answer plays on)."""
        self._replay_start()
        while True:
            if self._queue:
                ev = self._queue.pop(0)
                if ev.kind == "decision":
                    self.st["waiting"] = dict(ev.data)
                self._replay_events = getattr(self, "_replay_events", 0) + 1
                yield ev
                continue
            if self.st["over"]:
                return
            if self.st["waiting"] is not None:
                self.answer()
            self._advance()

    def answer(self, substitutions=(), tactics=None, positions=None, marking=None, own_tactics=None, quick=False,
               speed=None, shootout_order=None, taker=None):
        """goal2's answer to the waiting decision; nothing given plays on.
        substitutions: (off, on) player words of the managed squad, made now at half time and at a substitution
          notice; at a pause the original only takes the request and offers it at the next stoppage (a
          `substitution` decision whose default answer is what was asked for).
        tactics: {element 1..8: bool} or the whole byte (bit e-1 = element e; F026; element 8 is man-to-man
          marking for the team).
        positions: {player: position code 0..13} (the formation: F028), made on SELECT TEAM by the original's R key.
        marking: {player: opponent player word, or 0 for none} (his man-marking, 1771:49B8).
        own_tactics: {player: {element 1..4: True, False or None for the team's}} (his own setting, 1771:4B61).
        quick: the rest as a quick result (the original's R key in play). speed: the original's speed byte 0..5
          (presentation only: it never changes the match, E033 notes).
        shootout_order: at the `shootout_order` decision only (and nothing else there): player words of the
          decision's `available` list, distinct, the first takers in order; the rest follow by the original's
          Enter (the highlighted player, from the top of the eleven)."""
        if self.st["waiting"] is None:
            raise MatchError("no decision is waiting")
        if self.st["waiting"]["context"] == "set_piece":
            if substitutions or tactics or positions or marking or own_tactics or quick or speed is not None or shootout_order is not None:
                raise ValueError("the set-piece prompt takes taker only")
            if taker is not None and (isinstance(taker, bool) or not isinstance(taker, int) or taker not in self.st["waiting"]["available"]):
                raise ValueError("taker: an available player of the managed eleven")
            self._replay_action("answer", {"taker": taker})
            self.st["answer"] = {"taker": taker}
            self.st["decisions"].append({"context": "set_piece", "minute": self.st["minute"], "answer": {"taker": taker}})
            self.st["waiting"] = None
            return
        if taker is not None:
            raise ValueError("taker answers the set-piece prompt only")
        if self.st["waiting"]["context"] == "shootout_order":
            if substitutions or tactics or positions or marking or own_tactics or quick or speed is not None:
                raise ValueError("the shoot-out order takes shootout_order only")
            order = [int(w) for w in (shootout_order or [])]
            avail = self.st["waiting"]["available"]
            if len(set(order)) != len(order) or any(w not in avail for w in order):
                raise ValueError(f"shootout_order: distinct players of the available eleven {avail}")
            self._replay_action("answer", {"shootout_order": order})
            self.st["answer"] = {"shootout_order": order}
            self.st["decisions"].append({"context": "shootout_order", "minute": self.st["minute"],
                                         "answer": {"shootout_order": order}})
            self.st["waiting"] = None
            return
        if shootout_order is not None:
            raise ValueError("shootout_order answers the shoot-out order only")
        if isinstance(tactics, int):
            tactics = {e: bool(tactics >> (e - 1) & 1) for e in range(1, 9)}
        tactics = {int(e): bool(v) for e, v in (tactics or {}).items()}
        if any(not 1 <= e <= 8 for e in tactics):
            raise ValueError("tactic elements are 1..8")
        if speed is not None and not 0 <= speed <= 5:
            raise ValueError("speed is 0..5")
        squad = self._squad(self.opts["managed"])
        subs = [[int(a), int(b)] for a, b in substitutions]
        for off, on in subs:
            if off not in squad[:11] or on not in squad[11:]:
                raise ValueError(f"substitution ({off}, {on}): the first must be in the eleven, the second on the bench")
        positions = {int(p): int(c) for p, c in (positions or {}).items()}
        if any(p not in squad or not 0 <= c <= 13 for p, c in positions.items()):
            raise ValueError("positions: {player of the managed squad: position code 0..13}")
        other = self._squad(self.opts[TEAM_KEYS[1 - self.side]])
        marking = {int(p): int(o) for p, o in (marking or {}).items()}
        if any(p not in squad[:11] or (o and o not in other[:11]) for p, o in marking.items()):
            raise ValueError("marking: {player of the managed eleven: an opponent of their eleven, or 0}")
        own = {int(p): {int(e): (None if v is None else bool(v)) for e, v in d.items()} for p, d in (own_tactics or {}).items()}
        if any(p not in squad or any(not 1 <= e <= 4 for e in d) for p, d in own.items()):
            raise ValueError("own_tactics: {player of the managed squad: {element 1..4: True, False or None}}")
        self._replay_action("answer", {"substitutions": subs, "tactics": tactics, "positions": positions,
                                      "marking": marking, "own_tactics": own, "quick": bool(quick), "speed": speed})
        self.st["answer"] = {"substitutions": subs, "tactics": tactics, "positions": positions, "marking": marking,
                             "own": own, "quick": bool(quick), "speed": speed}
        self.st["decisions"].append({"context": self.st["waiting"]["context"], "minute": self.st["minute"],
                                     "answer": {"substitutions": subs, "tactics": sorted(tactics.items()),
                                                "positions": sorted(positions.items()), "marking": sorted(marking.items()),
                                                "own_tactics": sorted((p, sorted(d.items())) for p, d in own.items()),
                                                "quick": bool(quick), "speed": speed}})
        self.st["waiting"] = None

    def _new_plan(self, answer):
        return S.MenuPlan(self.side, tactics=answer.get("tactics"), subs=answer.get("substitutions"),
                          positions=answer.get("positions"), marking=answer.get("marking"), own=answer.get("own"))

    def pause(self):
        """Ask the original for the team menu at its next key poll (as a manager pressing Enter in play): a
        `decision` event with context `pause` follows."""
        if self.side is None:
            raise MatchError("neither side is managed: there is no team menu to pause")
        if self.st["waiting"] is not None:
            raise MatchError("a decision is waiting: answer it")
        if self.st["over"] or self.st["full_time"]:
            raise MatchError("the match is over")
        if self.st.get("stage") == "shootout":
            raise MatchError("the kit takes no pause in the shoot-out (what the original's team menu does mid-kick is not checked)")
        self._replay_action("pause", {})
        if S.ENTER not in self.st["poll_keys"]:        # asked already: one menu
            self.st["poll_keys"].append(S.ENTER)

    def result(self):
        if not self.st["over"]:
            raise MatchError("the match is not over")
        return self._result

    def pitch(self):
        """Where everyone is now, as the original keeps it: the 22 pitch records (slot, team, player word, x, y,
        state) and the ball (x, y). Coordinates are the original's own; their meaning on the pitch is `likely`
        (F013). Read between events, for an animation; reading never changes the match."""
        m = self.m
        first = set(self._squad(self.opts["first"]))
        players = []
        for s in range(1, 23):
            r = m.read(m.DS * 16 + PITCH + PITCH_SIZE * s, PITCH_SIZE)
            w = int.from_bytes(r[0xD:0xF], "little")
            players.append({"slot": s, "team": 0 if w in first else 1, "player": w,
                            "x": r[0], "y": r[1] - 256 if r[1] > 127 else r[1], "state": r[0x12]})
        b = m.read(m.DS * 16 + BALL, 2)
        return {"ball": [b[0], b[1] - 256 if b[1] > 127 else b[1]], "players": players}

    def memory_component(self):
        """The guest memory now, as a DOSBox-X Memory component of the image's own size (goal2's GameState.mem
        form): the image's component with its first 1 MiB + HMA replaced by the machine's."""
        return self.image_header + self.m.read(0, MEM_SIZE) + self.image_tail

    def image(self):
        return Image(self.memory_component())

    def records_after(self, tables=None):
        """goal2's state now (T80, image.state_of): after the match and its post-match update, the same form the
        sealed engine takes (Image.from_state), so the next match starts from it. `tables`: GOAL.EXE's tables
        (port.tables.load), by default those the match was built from."""
        from types import SimpleNamespace
        from .image import state_of
        tables = tables or getattr(self, "tables", None)
        if tables is None:
            raise MatchError("records_after needs GOAL.EXE's tables (port.tables.load): this match was not built "
                             "from them")
        now = SimpleNamespace(header=self.image_header, memory=self.m.read(0, MEM_SIZE) + self.image_tail,
                              load=self.m.load)
        return state_of(now, tables)

    # -- running -----------------------------------------------------------------------------------------
    def _advance(self):
        fresh, self.st["fresh"] = self.st["fresh"], False
        stopped = self.m.run(self.end_lin, self.timeout_s, fresh=fresh)
        # Every stop is outside the original's screens: a decision stops at a menu's first read or at the notice,
        # before any plan; a tick and the end of a call come after the menus closed. A plan left here is done, so
        # nothing of a screen survives into the state between events (save() relies on it).
        self._menu = None
        if stopped is not None:
            return
        self._flush()
        if self.st["phase"] == "run_match":
            seg, off = self.fixture_ptr
            self.st["fixture_after"] = list(self.m.read(seg * 16 + off, FIXTURE_SIZE))
            self.st["phase"] = "player_update"
            self._call(PLAYER_UPDATE, PLAYER_UPDATE_RETURN)
        else:
            self.st["phase"] = "done"
            self._finish()

    # -- the hooks -----------------------------------------------------------------------------------------
    def _hooks(self):
        m = self.m
        m.at(KEYPRESSED, self._on_keypressed)
        m.at(READKEY, self._on_readkey)
        m.at(TEAM_MENU, self._on_team_menu)
        m.at(NOTICE, self._on_notice)
        m.at(PROMPT, self._on_prompt)
        m.at(WAIT, self._on_wait)
        m.at("0791:D010", self._on_taker_accepted)
        m.at(TICK, self._on_tick)
        m.at(PLAY_MATCH, self._on_play)
        m.at(MATCH_PLAYED, self._on_played)
        m.at(MESSAGE_IF, self._on_message)
        m.at(SHOOTOUT, self._on_shootout)
        m.at(KICK, self._on_kick)
        m.at(KICK_RETURN, self._on_kicked)
        for name in WAIT_FAMILY:
            m.at(name, lambda replay, name=name: self._fail(f"the 000E wait {name} was reached: it is menu code"))
        for name, kind in ((BOOKING, "booking"), (SEND_OFF, "sending_off"), (INJURE, "injury")):
            m.at(name, lambda replay, kind=kind: replay or self._candidate(kind))
        ds = m.DS * 16
        m.watch(ds + RING_NEWEST, 2, self._on_line)
        m.watch(ds + SCORE, 2, self._on_score)
        m.watch(ds + STATS + 7, 3, lambda old, new: self._on_cards(0, old, new))
        m.watch(ds + STATS + 17, 3, lambda old, new: self._on_cards(1, old, new))
        m.watch(ds + MINUTE, 2, self._on_minute)
        m.watch(ds + S.SUBS_LEFT, 2, self._on_subs_left)
        if self.opts["record_draws"]:
            lin = m.DS * 16 + SEED

            def seed_write(address, size, value):     # a guest write or a port's (Machine.on_write)
                if not self.st["recording"]:
                    return
                old = m.word_at(lin)
                raw = bytearray(old.to_bytes(2, "little"))
                for i in range(size):
                    if 0 <= address + i - lin < 2:
                        raw[address + i - lin] = (value >> (8 * i)) & 0xFF
                self.st["draws"].append([m.rd(MINUTE), m.rd(SUBTICK), old, int.from_bytes(raw, "little")])
            m.on_write(lin, lin + 1, seed_write)

    def _fail(self, message):
        raise GuestError(message + "\n" + self.screen_text())

    def _on_message(self, replay):
        """214B:1765: the original shows a message (a refusal: 'X has too many goalkeepers', a substitution it
        will not make); its text is kept for the refusal the kit reports."""
        m = self.m
        if replay or not m.stack_word(8) & 0xFF:
            return
        a = m.stack_word(6) * 16 + m.stack_word(4)
        n = m.read(a, 1)[0]
        text = " ".join(m.read(a + 1, n).decode("cp437", errors="replace").split())
        self.st["message"] = text
        if self._menu is not None:
            self._menu.last_message = text

    def _menus_ported(self):
        return self.ports is not None and any(n.split(".")[0] == "menus" for n in self.ports.names)

    def _on_keypressed(self, replay):
        if self._menus_ported():
            return                      # the port implements the same key service
        m = self.m
        has = self._key_waiting(m.where(m.stack_word(2), m.stack_word(0)))
        m.set_reg("ax", (m.reg("ax") & 0xFF00) | (1 if has else 0))
        m.return_from(True, 0)

    def _key_waiting(self, site):
        """214B:0723 called from `site`: whether the kit has a key for the original there."""
        m = self.m
        if site == KP_POLL:
            has = bool(self.st["poll_keys"])
        elif site == KP_WAIT:          # inside 0791:CC2E (near-called within 0791): its caller says whose wait
            has = self._prompt_key(WAIT_FROM.get(m.frame_word(m.reg("bp"), 2))) is not None
        elif site == KP_PROMPT:
            has = self._prompt_key("prompt") is not None
        elif site == KP_NOTICE:
            has = self._prompt_key("notice") is not None
        else:
            has = False                # replays, save-goal and summary questions, walk-offs: no key (No)
        return has

    def _prompt_key(self, kind):
        p = self.st["prompt"]
        return p["key"] if p is not None and kind is not None and p["kind"] == kind else None

    def _on_readkey(self, replay):
        m = self.m
        site = m.where(m.stack_word(2), m.stack_word(0))
        if site == SITE_BOARD:
            self._on_board()           # the board is drawn: its event, whether a key is waiting or not
        if m.rd(PUSHED_BACK, 1):
            return                     # a pushed-back key: the guest reads it without waiting (after a shoot-out
        key = self._key_for(site)      # 9B93's last Down, 9E5B, passes the full-time board)
        if key is None:
            return                     # stopped for a decision
        if self._menus_ported():
            self._ported_key = (site, key)  # decision preflight precedes the Python port
            return
        m.wr(KEY, key | (key << 8))    # DS:A976 the key, DS:A977 the last key
        m.return_from(True, 0)

    def _on_board(self):
        st = self.st
        self._flush()
        if st["full_time"] and st["board"] is None:
            st["board"] = self._board()
            st["recording"] = False
            self._emit("full_time", **st["board"])
        elif not st["full_time"] and st["half_time_score"] is None:
            st["half_time_score"] = list(st["score"])
            self._emit("half_time")

    def _key_for(self, site):
        m, st = self.m, self.st
        if site == SITE_BOARD:
            return S.ENTER
        if site == SITE_POLL:
            if not st["poll_keys"]:
                self._fail("a key read at the poll with no key queued")
            return st["poll_keys"].pop(0)
        if site == SITE_PROMPT:
            return self._captain_key()
        if site == SITE_NOTICE:
            st["prompt"] = None
            return S.ENTER
        if site == SITE_MESSAGE:
            return S.ENTER
        if site == TABLE_KEY and st["full_time"]:
            return S.ENTER
        if site == SITE_SELECT and self._menu is not None:
            return self._menu.select_key({
                "cursor": m.rd(S.SELECT_CURSOR), "squad": self._squad(self.opts["managed"]),
                "allowed": m.rd(S.SUBS_ALLOWED, 1), "request": m.rd(S.SUBS_REQUEST, 1),
                "subs_left": m.rd(S.SUBS_LEFT + self.side, 1), "position": lambda p: self._player(p, PLAYER_POSITION)})
        if site == SITE_MENU:
            bp = m.reg("bp")                                  # 214B:1560's frame (its far return above it)
            caller = m.where(m.frame_word(bp, 4), m.frame_word(bp, 2))
            if caller == MENU_TEAM:
                return self._team_menu_key(m.frame_word(m.frame_word(bp, 0), S.MENU_ITEM_BP))
            if caller == MENU_TACTICS and self._menu is not None:
                table = list(m.read(m.DS * 16 + S.TACTICS_ELEMENT_OF_ROW, 9))
                return self._menu.tactics_key(m.rd(S.TACTICS_ROW), table, self._tactics())
            if caller == ORDER_READ:
                return self._order_key(m.frame_word(bp, 0))
            if caller in TABLE_READS and st["full_time"]:
                return S.ENTER                                # the competition's table, looked at: one pass
            if caller == MENU_OWN and self._menu is not None:
                player = self._menu.jobs[self._menu.job][1]
                slot = self._squad(self.opts["managed"]).index(player) + 1
                marking = m.rd(S.MARKING - 2 + 0x28 * self.side + 2 * slot)
                return self._menu.own_key(m.rd(S.OWN_ROW), self._player(player, OWN_TACTICS), marking,
                                          self._tactics(), m.frame_word(bp, 6) & 0xFF == 5)
            self._fail(f"an undeclared menu read (214B:1560 called from {caller})")
        self._fail(f"an undeclared key read at {site}")

    # -- the team menu and the decisions ------------------------------------------------------------------
    def _on_team_menu(self, replay):
        if replay:
            return
        ret = self.m.where(self.m.reg("cs"), self.m.stack_word(0))
        self.st["menu_context"] = MENU_CONTEXT.get(ret, "other:" + ret)
        self.st["menu_half"] = 2 if ret == "0791:9B70" else 1      # extra time's second half: 9B5B's menu
        self._menu = None

    def _team_menu_key(self, item):
        st = self.st
        plan = self._menu
        if plan is not None and plan.steps == ["play"] and plan.in_screen is None and plan.menu_reads_after_play:
            # "play" was pressed and the menu is read again: 0791:EA09 refused the eleven (its message is kept)
            refusal = st.get("message") or "the original refused the managed eleven"
            if st["menu_context"] not in DECIDED_AT_MENU + ("substitution",):
                raise MatchError(f"the original refuses goal2's eleven: {refusal}")
            st["refused"], st["message"], self._menu = refusal, None, None
            plan = None
        if plan is None:
            context = st["menu_context"]
            if self.side is None:
                # run_match still visits its menu for two computer sides. Keep
                # its sorting/validation and choose play, with no human answer.
                self._menu = S.MenuPlan(1)
            elif context in DECIDED_AT_MENU or (context == "substitution" and st.get("refused")):
                if st["answer"] is None:
                    self._decide(context, substitutions_now=bool(self.m.rd(S.SUBS_ALLOWED, 1)),
                                 refused=st.get("refused"))
                    return None
                answer, st["answer"], st["refused"] = st["answer"], None, None
                self._extras(answer)
                if not self.m.rd(S.SUBS_ALLOWED, 1) and answer["substitutions"]:
                    st["pending_subs"] = answer["substitutions"]    # the original makes them at the next stoppage
                self._menu = self._new_plan(answer)
            elif context == "substitution":
                answer, st["notice"] = st["notice"] or {}, None
                self._menu = self._new_plan(answer)
            else:                                            # before and after the match: play
                self._menu = S.MenuPlan(self.side)
            plan = self._menu
        key = plan.menu_key(item)
        if plan.steps[0] == "play" and key == S.ENTER and not getattr(plan, "closed", False):
            plan.closed = True
            self._close_plan(plan)
        return key

    def _extras(self, answer):
        """The answer's in-play keys, pressed at the next polls: the speed (9372: Right lowers the delay byte,
        Left raises it, one step a key) and R (the quick result, 0791:92FC)."""
        if answer.get("speed") is not None:
            now = self.m.rd_far(GAME_PTR, 0x3F, 1)
            key = S.RIGHT if answer["speed"] < now else S.LEFT
            self.st["poll_keys"].extend([key] * abs(now - answer["speed"]))
        if answer.get("quick"):
            self.st["poll_keys"].append(S.KEY_R)

    def _close_plan(self, plan):
        self._flush()                  # the substitutions this visit made come first, in the order they were made
        made = {(job[1], job[2]) for job in plan.done if job[0] == "sub"}
        self.st["pending_subs"] = [s for s in self.st["pending_subs"] if tuple(s) not in made]
        for job, why in plan.refused:
            self._emit("refused", job=job[0], player=job[1], target=job[2] if job[0] != "own" else job[3], reason=why)
        if plan.tactics:
            byte = self._tactics()
            missed = [e for e, v in plan.tactics.items() if bool(byte >> (e - 1) & 1) != v]
            self._emit("tactics", byte=byte, **({"not_set": missed} if missed else {}))
        name, _ = self._text()
        for job in plan.done:
            if job[0] == "position":
                self._emit("position", player=job[1], name=name(job[1]), position=job[2])
            elif job[0] == "own":
                slot = self._squad(self.opts["managed"]).index(job[1]) + 1
                mark = self.m.rd(S.MARKING - 2 + 0x28 * self.side + 2 * slot)
                self._emit("player_tactics", player=job[1], name=name(job[1]), own_set=self._player(job[1], OWN_TACTICS),
                           marking=mark, marking_name=name(mark))
        if plan.requested:
            self._emit("substitution_requested", pending=[list(s) for s in self.st["pending_subs"]])

    def _on_notice(self, replay):
        """0791:7FCF timed_notice(side, keeper unavailable): the original offers the managed side a substitution
        at a stoppage (0791:8062: after an injury, or a substitution asked for at a pause)."""
        st = self.st
        if st["answer"] is None and st["notice"] is None:
            self._decide("substitution", keeper_unavailable=bool(self.m.stack_word(2) & 0xFF),
                         requested=[list(s) for s in st["pending_subs"]], substitutions_now=True)
            return
        if st["answer"] is not None:
            answer, st["answer"] = st["answer"], None
            changes = [answer.get(k) for k in ("substitutions", "tactics", "positions", "marking", "own")]
            if not any(changes) and st["pending_subs"]:
                answer["substitutions"] = [list(s) for s in st["pending_subs"]]   # default: what was asked for
            self._extras(answer)
            st["notice"] = answer
            if answer["substitutions"] or any(changes):
                st["prompt"] = {"kind": "notice", "key": S.ENTER}

    def _decide(self, context, **data):
        self._flush()
        squad = self._squad(self.opts["managed"])
        injured = [i["player"] for i in self.st["log"]["injuries"] if i["team"] == self.side and i["player"] in squad[:11]]
        base = self.m.far(PLAYERS_PTR)
        positions = [[w, self.m.read(base + PLAYER_SIZE * w + PLAYER_POSITION, 1)[0]] for w in squad if w]
        data.update(context=context, eleven=squad[:11], bench=squad[11:], injured=injured, positions=positions,
                    substitutions_left=self.m.rd(S.SUBS_LEFT + self.side, 1), tactics=self._tactics())
        if context == "extra_time":
            data["half"] = self.st.get("menu_half", 1)    # before extra time's first half (1) or its second (2)
        self._emit("decision", **data)
        self.m.stop("decision")

    # -- the captain prompt -------------------------------------------------------------------------------
    def _on_prompt(self, replay):
        """0791:CC7B(role, side), role the last pushed: 1 the captain, 2-5 the set-piece takers (F030); the
        takers' prompts get no key and keep their pick after 1000 polls, as with a manager who does nothing."""
        if replay:
            return
        role, side = self.m.stack_word(2) & 0xFF, self.m.stack_word(4) & 0xFF
        if role == 1 and side == self.side:
            self.st["prompt"] = {"kind": "prompt", "key": S.ENTER, "role": 1, "waited": False}
        elif self.opts.get("set_piece") and side == self.side and role in (2, 3, 4, 5):
            self.st["prompt"] = {"kind": "prompt", "key": None, "role": role, "waited": False}

    def _on_wait(self, replay):
        """0791:CC2E, the prompts' wait: at the captain prompt's (where E011's watchstart was taken) the optional
        seed and speed byte are written and the draw record starts."""
        p = self.st["prompt"]
        if p is not None and p.get("role") in (2, 3, 4, 5) and not p["waited"] and self.m.stack_word(0) == 0xCED9:
            if self.st["answer"] is None:
                bp = self.m.reg("bp")
                squad = self._squad(self.opts["managed"])[:11]
                self._decide("set_piece", role=p["role"], current=self.m.frame_word(bp, -7),
                             available=[w for w in squad if w and self._available(w)])
                return
            answer, self.st["answer"] = self.st["answer"], None
            p.update(waited=True, target=answer["taker"], key=S.ENTER if answer["taker"] is not None else None)
            return
        if replay or p is None or p.get("role") != 1 or p["waited"] or self.m.stack_word(0) != 0xCED9:
            return
        p["waited"] = True
        if self.opts["seed"] is not None:
            self._declare("main seed DS:7B62 at the captain prompt", self.m.DS * 16 + SEED,
                          int(self.opts["seed"]).to_bytes(2, "little"))
        if self.opts["delay_byte"] is not None:
            self._declare("delay byte [A923]+0x3F at the captain prompt", self.m.far(GAME_PTR) + 0x3F,
                          [self.opts["delay_byte"]])
        self.st["kickoff_seed"] = self.m.rd(SEED)
        self.st["recording"] = True

    def _captain_key(self):
        p = self.st["prompt"]
        if p is None:
            self._fail("a key read at the captain prompt the kit did not ask for")
        want = self.opts["captain"] if p.get("role") == 1 else p.get("target")
        if want is not None:
            slot = self._squad(self.opts["managed"]).index(want) + 1
            here = self.m.frame_word(self.m.reg("bp"), S.PROMPT_SLOT_BP)
            if here != slot:
                p["moves"] = p.get("moves", 0) + 1
                if p["moves"] > S.MAX_MOVES:
                    raise S.ScreenError(f"the captain prompt's highlight does not reach slot {slot} (it reads {here})")
                return S.step_toward(here, slot)
        if p.get("role") == 1:
            self.st["prompt"] = None
        return S.ENTER

    def _on_taker_accepted(self, replay):
        """D010 follows the original's D00D load of its accepted result into AX."""
        p = self.st["prompt"]
        if not replay and p is not None and p.get("role") in (2, 3, 4, 5):
            self._flush()
            self._emit("set_piece", role=p["role"], player=self.m.reg("ax"), team=self.side)
            self.st["prompt"] = None

    # -- events --------------------------------------------------------------------------------------------
    def _emit(self, kind, minute=None, score=None, **data):
        """Queue an event stamped with the minute and score of the original's write it reports (the flush passes
        them), or with the guest's minute and score now (a decision, a board, a screen's outcome)."""
        if minute is None:
            minute, s0, s1 = self._stamp()
            score = [s0, s1]
        self.st["minute"], self.st["score"] = minute, list(score)
        self._queue.append(Event(kind, minute, tuple(score), data))

    def _candidate(self, kind):
        pitch = self.m.stack_word(6) * 16 + self.m.stack_word(4)      # the pitch record (far pointer argument)
        self.st["candidates"].setdefault(kind, []).append(self.m.word_at(pitch + 0xD))

    def _on_tick(self, replay):
        if replay:
            return
        self.st["ticks"] += 1
        self.st["notice"] = None       # a notice's menu comes in the same stoppage (0791:8062), never a tick later
        self._menu = None
        self._flush()
        if self.opts["ticks"]:
            self._emit("tick", subtick=self.m.rd(SUBTICK))
        if self._queue:
            self.m.stop("events")

    def _on_play(self, replay):
        """0791:F098 play_match: the set-up (A4A1) has reset the score, the statistics, the clock and the
        substitutions left; from here their writes are the match's events."""
        if not replay:
            self.st["live"] = True
            if self.side is None:
                # No human captain prompt exists. Start the optional inputs and
                # draw transcript at play_match entry, after the original setup.
                if self.opts["seed"] is not None:
                    self._declare("main seed DS:7B62 at computer fixture kickoff",
                                  self.m.DS * 16 + SEED, int(self.opts["seed"]).to_bytes(2, "little"))
                if self.opts["delay_byte"] is not None:
                    self._declare("delay byte [A923]+0x3F at computer fixture kickoff",
                                  self.m.far(GAME_PTR) + 0x3F, [self.opts["delay_byte"]])
                self.st["kickoff_seed"] = self.m.rd(SEED)
                self.st["recording"] = True
            if self.opts.get("substitutions") is not None:
                self._declare("substitution budget DS:9B3A (team 0, team 1) after the set-up's (A605)",
                              self.m.DS * 16 + S.SUBS_LEFT, self.opts["substitutions"])
            self.st["budget"] = list(self.m.read(self.m.DS * 16 + S.SUBS_LEFT, 2))

    def _on_played(self, replay):
        if not replay:
            self.st["full_time"] = True
            self.st["live"] = False

    def _text(self):
        if self._names is None:
            self._names = names_and_templates(self.m.read, self.m.DS, self.m.far)
        return self._names

    # -- the original's writes, each recorded when it happens (the event's stamp) ------------------------------
    def _stamp(self):
        """The guest's minute and score now: [minute, score team 0, score team 1]. Inside the quick engine (from its
        clear at D77B to its commit at DA58) DS:9B3C holds trial counts: the score is the committed one it saved."""
        m = self.m
        quick = self.st.get("quick")
        if quick is not None:
            return [m.rd(MINUTE)] + list(quick)
        return [m.rd(MINUTE), m.rd(SCORE, 1), m.rd(SCORE + 1, 1)]

    def _on_line(self, old, new):
        """1D4A increments the ring counter DS:80EE (1..200) for each line it writes (A4A1 writes 0)."""
        n = int.from_bytes(new, "little")
        if n and n != int.from_bytes(old, "little"):
            self._declared("the commentary ring counter DS:80EE", WRITERS["line"])
            self.st["pending"].append(["line"] + self._stamp() + [n])

    def _declared(self, what, writers):
        """A write that makes an event must come from the instruction the kit read it from (WRITERS)."""
        pc = self.m.pc()
        if pc not in [self.m.lin(a) for a in writers]:
            self._fail(f"a write of {what} at {pc:05X}, not from {', '.join(writers)}: the kit does not declare it")

    def _on_score(self, old, new):
        """A write of the score bytes, read by the instruction that makes it (QUICK_CLEAR above): the watched goal
        685C (+1: a goal) and its take-back 68B3 (-1 in the same action, DS:830E set, no record_goal: a goal
        disallowed, queued here at its own write, after what the original wrote in between; the goal it takes back
        stays where it was written, marked so it takes no scorer row and leaves the result's goals); the quick
        engine's clear D77B (the committed score saved), its trial counts B261/D8A5 (nothing) and its commit DA58
        (each byte above the saved one: a goal). Any other write in play stops the kit (GuestError): it does not
        guess what a write it has not read means."""
        st, m = self.st, self.m
        if not st["live"]:
            return
        pc, minute = m.pc(), m.rd(MINUTE)
        if pc == m.lin(QUICK_CLEAR):
            if st.get("quick") is not None:
                self._fail("the quick engine cleared the score twice without its commit (0791:D77B, DA58)")
            st["quick"] = [old[0], old[1]]
            return
        if st.get("quick") is not None:
            if pc in [m.lin(a) for a in QUICK_SCRATCH]:
                return
            if pc != m.lin(QUICK_COMMIT):
                self._fail(f"a score write at {pc:05X} inside the quick engine, not one of its own")
            saved, st["quick"] = st["quick"], None
            for t in (0, 1):
                if new[t] < saved[t]:
                    self._fail(f"the quick engine's commit lowered team {t}'s score ({saved} to {list(new)})")
                for _ in range(new[t] - saved[t]):
                    st["pending"].append(["goal", minute, new[0], new[1], t, False])
            return
        for t in (0, 1):
            d = (new[t] - old[t]) & 0xFF
            if not d:
                continue
            if st.get("stage") == "shootout":
                kick = st["kick"]
                if d != 1 or pc != m.lin(GOAL_WRITE) or kick is None or kick["team"] != t or kick["scored"]:
                    self._fail(f"a score write at {pc:05X} in the shoot-out ({list(old)} to {list(new)}) that is not "
                               "the kicking side's one goal (0791:685C): the kit does not declare it")
                kick["scored"] = True
                st["pending"].append(["kick", minute, new[0], new[1], t])
            elif d == 1 and pc == m.lin(GOAL_WRITE):
                st["pending"].append(["goal", minute, new[0], new[1], t, False])
            elif d == 0xFF and pc == m.lin(CANCEL_WRITE):
                taken = [p for p in st["pending"] if p[0] == "goal" and p[4] == t and not p[5]]
                if not taken:
                    self._fail(f"the original took back a goal of team {t} the kit did not see written (0791:68B3)")
                taken[-1][5] = True
                st["pending"].append(["goal_disallowed", minute, new[0], new[1], t])
            else:
                self._fail(f"a score write at {pc:05X} in play ({list(old)} to {list(new)}) the kit does not declare"
                           + (" (the action replay's restore, 0791:0F11)" if pc == m.lin(REPLAY_RESTORE) else ""))

    def _on_cards(self, team, old, new):
        """Bookings, red cards and injuries of `team`: STATS + 10 team + 7, 8, 9 (798D 7A01, 7B77 7B6D, 7D56 7DD9);
        the player is the one the routine was called for (its entry, the latest call)."""
        if not self.st["live"]:
            return
        for k, (kind, _) in enumerate(CARD_EVENTS):
            if new[k] != old[k]:
                self._declared(f"team {team}'s {kind} count", WRITERS[kind])
            for _ in range(max(0, new[k] - old[k])):
                cands = self.st["candidates"].get(kind) or [0]
                self.st["pending"].append([kind] + self._stamp() + [team, cands[-1]])

    def _on_minute(self, old, new):
        """The clock 970C writes the minute DS:831F (9762 `inc`); A4A1 resets it before play_match."""
        if self.st["live"] and new != old:
            if self.m.pc() == self.m.lin(EXTRA_TIME_CLOCK):     # 9B0C: extra time begins; the clock is set back
                self.st["pending"].append(["extra_time", int.from_bytes(new, "little")] + self._stamp()[1:])
                return
            self._declared("the minute DS:831F", WRITERS["minute"])
            self.st["pending"].append(["minute", int.from_bytes(new, "little")] + self._stamp()[1:])

    def _on_subs_left(self, old, new):
        """C5DC counts a substitution down (DS:9B3A + t, at C7DC), for both teams' substitutions."""
        if not self.st["live"]:
            return
        for t in (0, 1):
            if new[t] != old[t]:
                self._declared(f"team {t}'s substitutions left", WRITERS["substitution"])
            if new[t] < old[t]:
                self.st["pending"].append(["substitution"] + self._stamp() + [t])

    def _flush(self):
        """Turn the original's writes recorded since the last flush into events, in the order it made them, each
        stamped with the minute and score of its write; the details come from the records the writes completed
        (the commentary line, the scorer row, the squad words)."""
        m, st = self.m, self.st
        if st["squads"] is None:      # the first flush comes after the set-up 0791:A4A1 (ring, scorers cleared)
            st["squads"] = [self._squad(c) for c in (self.opts["first"], self.opts["second"])]
        name, templates = self._text()
        rows, swaps = [], []
        for team in (0, 1):
            seen = []
            for k in range(1, 12):
                a = m.DS * 16 + SCORERS + SCORERS_SIDE * team + 3 * k
                w = m.word_at(a)
                if w:
                    seen.append([w, m.read(a + 2, 1)[0]])
            rows.append(seen[len(st["scorers"][team]):])
            st["scorers"][team] = seen
            now = self._squad(self.opts[TEAM_KEYS[team]])
            before = st["squads"][team]
            swaps.append(list(zip([w for w in before[:11] if w not in now[:11]],
                                  [w for w in now[:11] if w not in before[:11]])))
            st["squads"][team] = now
        pending, st["pending"] = st["pending"], []
        for item in pending:
            kind, minute, score = item[0], item[1], [item[2], item[3]]
            if kind == "line":
                r = m.read(m.DS * 16 + RING + RING_REC * item[4], RING_REC)
                p1, p2 = int.from_bytes(r[1:3], "little"), int.from_bytes(r[3:5], "little")
                t = templates[r[0]] if r[0] < len(templates) else f"<template {r[0]}>"
                text = " ".join(t.replace("\x01", f" {name(p1)} ").replace("\x02", f" {name(p2)} ").split())
                st["commentary"].append({"minute": minute, "template": r[0], "players": [p1, p2], "team": r[5],
                                         "text": text})
                self._emit("commentary", minute, score, text=text, template=r[0], team=r[5], players=[p1, p2])
            elif kind == "minute":
                self._emit("minute", minute, score)
            elif kind == "extra_time":
                st["stage"], st["score_90"] = "extra_time", list(score)
                self._emit("extra_time", minute, score)
            elif kind == "kick":
                self._emit_kick(minute, score)
            elif kind in ("goal", "goal_disallowed"):
                team = item[4]
                scored = kind == "goal" and not item[5]      # a goal taken back has no record_goal row
                w, mb = rows[team].pop(0) if scored and rows[team] else (0, None)
                goal = {"team": team, "country": self.opts[TEAM_KEYS[team]], "player": w, "name": name(w)}
                if kind == "goal_disallowed" or scored:
                    st["log"]["goals" if scored else "goals_disallowed"].append(dict(goal, minute=minute,
                                                                                    minute_byte=mb, **self._period()))
                self._emit(kind, minute, score, **goal)
            elif kind == "substitution":
                team = item[4]
                off, on = swaps[team].pop(0) if swaps[team] else (0, 0)
                sub = {"team": team, "off": off, "on": on, "off_name": name(off), "on_name": name(on)}
                st["log"]["substitutions"].append(dict(sub, minute=minute, **self._period()))
                self._emit("substitution", minute, score, **sub)
            else:                                             # booking, sending_off, injury
                team, w = item[4], item[5]
                card = {"team": team, "player": w, "name": name(w)}
                st["log"][dict(CARD_EVENTS)[kind]].append(dict(card, minute=minute, **self._period()))
                self._emit(kind, minute, score, **card)
        for team in (0, 1):            # a scorer row or an eleven change without its counter's write: not guessed
            if rows[team] or swaps[team]:
                self._fail(f"team {team}: scorer rows {rows[team]} or eleven changes {swaps[team]} without the "
                           "score or substitutions-left write that makes them events")
        st["candidates"] = {}

    def _competitive(self, board):
        """The result's fields for any kind (issue 252): the stages played, the shoot-out, the winner as the
        fixture's byte +3 holds it after play_match (0 team 0, 1 team 1, 2 drawn), the budget, and per player of
        both squads what the match and the post-match update did to confidence, energy and status."""
        st = self.st
        fx = st.get("fixture_after") or [0] * FIXTURE_SIZE
        out = {"kind": self.opts.get("kind", 1), "winner": fx[3], "score_90": st.get("score_90"),
               "extra_time": st.get("score_90") is not None, "substitution_budget": st.get("budget"), "shootout": None}
        if st.get("score_120") is not None:
            final = board["final_score"]
            out["score"] = list(st["score_120"])
            out["shootout"] = {"score": [final[t] - st["score_120"][t] for t in (0, 1)], "kicks": st["kicks"]}
        before = st.get("players_before") or {}
        after = self._players_now([self.opts["first"], self.opts["second"]])
        players = []
        for w in sorted(set(before) | set(after), key=int):
            b, a = before.get(w), after.get(w)
            team = (a or b)[0]
            b, a = (b or [team, None, None, None])[1:], (a or [team, None, None, None])[1:]
            players.append({"player": int(w), "team": team, "confidence": [b[0], a[0]], "energy": [b[1], a[1]],
                            "status": [b[2], a[2]],
                            "suspended": bool(a[2] is not None and a[2] & SUSPENDED),
                            "carried_booking": bool(a[2] is not None and a[2] & CARRIED_BOOKING),
                            "injured": a[1] == 0})
        out["players"] = players
        return out

    def _period(self):
        """What a result entry made in extra time carries (nothing in the 90 minutes, so a friendly's is unchanged)."""
        return {"extra_time": True} if self.st.get("stage") == "extra_time" else {}

    # -- the shoot-out ---------------------------------------------------------------------------------------
    def _on_shootout(self, replay):
        """0791:A10A penalty_shootout: play_match calls it when the decider is still level after extra time."""
        if replay:
            return
        self._flush()
        st = self.st
        st["stage"], st["score_120"] = "shootout", [self.m.rd(SCORE, 1), self.m.rd(SCORE + 1, 1)]
        self._emit("shootout", score_120=list(st["score_120"]))

    def _so_byte(self, a10a_bp, offset):
        return self.m.read(self.m.reg("ss") * 16 + ((a10a_bp + offset) & 0xFFFF), 1)[0]

    def _on_kick(self, replay):
        """0791:A006 play_shootout_kick(A10A's BP): the side [bp-0x1F] kicks; its taker is entry [bp-0x1E+side] of
        its takers [bp-0x1A+12 side] (a pitch slot; the player word at the pitch record's +0xD)."""
        if replay:
            return
        self._flush()
        bp = self.m.stack_word(2)
        side = self._so_byte(bp, SO_SIDE)
        slot = self._so_byte(bp, SO_TAKERS + 12 * side + self._so_byte(bp, SO_INDEX + side))
        player = self.m.word_at(self.m.DS * 16 + PITCH + PITCH_SIZE * slot + 0xD)
        st = self.st
        st["kick"] = {"team": side, "player": player, "name": self._text()[0](player), "scored": False,
                      "round": sum(1 for k in st["kicks"] if k["team"] == side) + 1}

    def _on_kicked(self, replay):
        """The return from A006 (A1EF): a kick the score bytes did not count is a miss, stamped now."""
        if replay:
            return
        kick = self.st["kick"]
        if kick is None:
            self._fail("a shoot-out kick ended that the kit did not see start (0791:A006)")
        self._flush()                  # a goal's kick is emitted here, at its write's place in the order
        if not kick["scored"]:
            minute, s0, s1 = self._stamp()
            self._emit_kick(minute, [s0, s1])

    def _emit_kick(self, minute, score):
        st = self.st
        kick, st["kick"] = st["kick"], None
        if kick is None:
            self._fail("a shoot-out goal without its kick (0791:A006)")
        shoot = [score[t] - st["score_120"][t] for t in (0, 1)]
        st["kicks"].append(dict(kick))
        self._emit("shootout_kick", minute, score, shootout_score=shoot, **kick)

    def _order_key(self, order_bp):
        """The managed side's shoot-out order (9B93): Up/Down move the highlight over the eleven (squad slots 1..11),
        Enter adds the highlighted player (9B93 then skips the ones taken and the unavailable, 1771:3216) until as
        many are picked as can play ([bp-4]). goal2's order first, then Enter for the rest: the original's own
        result for a manager who only presses Enter (the highlighted, from the top, in squad order)."""
        m, st = self.m, self.st
        if st["order"] is None:
            if st["answer"] is None:
                squad = self._squad(self.opts["managed"])
                self._decide("shootout_order", takers=m.frame_word(order_bp, ORDER_NEEDED_BP),
                             available=[w for w in squad[:11] if w and self._available(w)])
                return None
            answer, st["answer"] = st["answer"], None
            st["order"] = {"want": list(answer.get("shootout_order") or []), "moves": 0}
        here, want = m.frame_word(order_bp, ORDER_HIGHLIGHT_BP), st["order"]["want"]
        if want:
            target = self._squad(self.opts["managed"]).index(want[0]) + 1
            if here != target:
                st["order"]["moves"] += 1
                if st["order"]["moves"] > S.MAX_MOVES:
                    raise S.ScreenError(f"the shoot-out order's highlight does not reach slot {target} (it reads {here})")
                return S.step_toward(here, target)
            want.pop(0)
            st["order"]["moves"] = 0
        return S.ENTER

    def _available(self, w):
        """1771:3216: a player is unavailable with energy +0xE below 1 or elements 8, 6 or 3 set (F027 section 2)."""
        e = self._player(w, PLAYER_ENERGY)
        return 0 < e < 0x80 and not self._player(w, STATUS) & (SUSPENDED | SENT_OFF | SUBSTITUTED_OFF)

    def _board(self):
        m = self.m
        stats = list(m.read(m.DS * 16 + STATS, 20))
        return {"statistics": {n: [stats[k], stats[10 + k]] for k, n in enumerate(STAT_NAMES)},
                "bars": [[m.rd(b), m.rd(b + 2)] for b in BARS], "man_of_the_match": m.rd(MOTM),
                "final_score": [m.rd(SCORE, 1), m.rd(SCORE + 1, 1)],
                "screen_sha256": hashlib.sha256(self._screen_raw()).hexdigest(), "ticks": self.st["ticks"],
                "seed": m.rd(SEED)}

    def _finish(self):
        st, m = self.st, self.m
        name, _ = self._text()
        board = st["board"] or self._board()
        draws = st["draws"]
        self._menu = None
        self._result = {
            "first": self.opts["first"], "second": self.opts["second"], "managed": self.opts["managed"],
            "index": self.opts["index"], "score": board["final_score"], "half_time_score": st["half_time_score"],
            "goals": st["log"]["goals"], "goals_disallowed": st["log"]["goals_disallowed"],
            "goal_counts": [m.rd(GOAL_COUNTS, 1), m.rd(GOAL_COUNTS + 1, 1)],
            "bookings": st["log"]["bookings"], "sendings_off": st["log"]["sendings_off"],
            "injuries": st["log"]["injuries"], "substitutions": st["log"]["substitutions"],
            "man_of_the_match": board["man_of_the_match"], "man_of_the_match_name": name(board["man_of_the_match"]),
            "board": board, "commentary": st["commentary"], "decisions": st["decisions"], "inputs": self.inputs,
            "ticks": st["ticks"], "kickoff_seed": st["kickoff_seed"], "seed_after": m.rd(SEED),
            "image_sha256": self.image_sha256, "kit": VERSION, "draws": len(draws),
            "draws_digest": hashlib.sha256("\n".join("%d %d %04x %04x" % tuple(d) for d in draws).encode()).hexdigest()
            if self.opts["record_draws"] else None,
            "squads_after": {str(self.opts["first"]): self._squad(self.opts["first"]),
                             str(self.opts["second"]): self._squad(self.opts["second"])},
        }
        self._result.update(self._competitive(board))
        if self.ports:                 # the port mode: which ports ran in place of the original, and how often
            self._result["ports"] = {"names": list(self.ports.names), "calls": dict(self.ports.calls)}
        st["over"] = True
        self._emit("end", score=self._result["score"])

    # -- the screen, for messages and diagnostics ---------------------------------------------------------
    def _screen_raw(self):
        return self.m.read(self.m.far(SCREEN_PTR), 4000)

    def screen_text(self):
        raw = self._screen_raw()
        return "\n".join(bytes(raw[r * 160:(r + 1) * 160:2]).decode("cp437", errors="replace").rstrip()
                         for r in range(25))

    # -- stop and resume ---------------------------------------------------------------------------------
    def _replay_start(self):
        # Capture after construction/fixture edits but before the first public operation. The origin is an
        # ordinary frame-free checkpoint, so loading never needs to locate the original external image.
        if (self.ports and getattr(self, "prover", None) is None
                and getattr(self, "_replay_origin", None) is None and not self.m.frames):
            self._replay_origin = self._encode_save(*self._save_state())
            self._replay_events = 0
            self._replay_actions = []

    def _replay_action(self, kind, args):
        self._replay_start()
        if getattr(self, "_replay_origin", None) is not None and not getattr(self, "_replaying", False):
            # Freeze caller-owned dictionaries and normalize keys as the save format will do.
            self._replay_actions.append(json.loads(json.dumps([self._replay_events, kind, args])))

    def _frame_state(self):
        return [{"entry": f.entry.address, "variant": f.variant, "ss": f.ss, "sp": f.sp, "bp": f.bp,
                 "ret_lin": f.ret_lin, "expect_sp": f.expect_sp, "after_sp": f.after_sp,
                 "call": None if f.waiting is None else
                 {k: getattr(f.waiting, k) for k in ("target", "args", "ret_to", "far", "caller_pops")}}
                for f in self.m.frames]

    def save(self):
        """The whole match now (guest memory, registers, the kit's state) as bytes; Match.load() resumes it.
        Call it between events."""
        if self._menu is not None and not self.st["over"]:
            raise MatchError("save between events, not while the kit drives a screen")
        if self.m.frames and getattr(self, "_replay_origin", None) is None:
            raise MatchError("a port's frame is live (" + "; ".join(self.port_frames()) + "): save at a later event, "
                             "once the call has returned")      # is not in the guest's memory
        if getattr(self, "prover", None) is not None:
            raise MatchError("a proved match (prove=) is not saved: its proof state is not in the guest's memory")
        state, memory = self._save_state()
        if self.m.frames:
            state["replay"] = {"origin": self._replay_origin.hex(), "events": self._replay_events,
                               "actions": self._replay_actions, "frames": self._frame_state()}
        return self._encode_save(state, memory)

    def _save_state(self):
        snap = self.m.snapshot()
        state = {"st": self.st, "opts": self.opts, "inputs": self.inputs, "side": self.side,
                 "image_sha256": self.image_sha256, "end_lin": self.end_lin, "fixture_ptr": list(self.fixture_ptr),
                 "timeout_s": self.timeout_s, "regs": snap["regs"], "load": snap["load"],
                 "queue": [asdict(e) for e in self._queue], "result": self._result, "version": VERSION,
                 "header": self.image_header.hex()}
        if self.ports:                 # opts["ports"] names them; a stop a port made resumes at its return as new
            state["no_replay_at"] = self.m.no_replay_at
        if getattr(self, "tables", None) is not None:      # a sealed match keeps records_after() across load (#632)
            from .port import tables
            state["tables"] = tables.to_record(self.tables)
        return state, snap["memory"] + self.image_tail

    @staticmethod
    def _encode_save(state, memory):
        blob = json.dumps(state).encode()
        memory = zlib.compress(memory, 6)
        return b"OMK1" + len(blob).to_bytes(4, "little") + blob + memory

    @staticmethod
    def _checkpoint_state(data):
        """[designed: T78c] Validate backend identity before allocating either machine.

        Historical unmarked versions retain their original backend. Port checkpoints
        require the current kit schema and the complete explicit port registry.
        """
        if len(data) < 8 or bytes(data[:4]) != b"OMK1":
            raise ValueError("not a saved match of this kit")
        n = int.from_bytes(data[4:8], "little")
        if n > len(data) - 8:
            raise ValueError("truncated checkpoint header")
        try:
            state = json.loads(data[8:8 + n])
            version, opts = state["version"], state["opts"]
            engine = opts.get("engine", "original")
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            raise ValueError("invalid checkpoint header") from exc
        if version not in LOADS:
            raise ValueError(f"saved by kit version {version}, this is {VERSION} (it loads {', '.join(LOADS)})")
        if engine not in ("original", "port"):
            raise ValueError("unknown checkpoint engine")
        if engine == "port":
            from . import port
            specs = opts.get("ports")
            if (version != VERSION or not isinstance(specs, list)
                    or any(not isinstance(spec, str) for spec in specs)
                    or {reg.name for reg, variant in port.load(specs)} != set(port.available())):
                raise ValueError("stale or incomplete port checkpoint")
        return n, state, engine

    @staticmethod
    def _restore_decision_pairs(decisions):
        # [derived: answer()'s schema] JSON erases tuple identity. Restore only
        # declared sorted mapping pairs, retaining substitutions/order as lists
        # and the existing live result API (including nested own-tactic pairs).
        for decision in decisions:
            answer = decision["answer"]
            for key in ("tactics", "positions", "marking"):
                if key in answer:
                    answer[key] = [tuple(pair) for pair in answer[key]]
            if "own_tactics" in answer:
                answer["own_tactics"] = [(player, [tuple(pair) for pair in tactics])
                                         for player, tactics in answer["own_tactics"]]

    @classmethod
    def load(cls, data):
        n, state, engine = cls._checkpoint_state(data)
        # Validate a replay origin before replay can allocate or execute a backend.
        if "replay" in state:
            try:
                origin = bytes.fromhex(state["replay"]["origin"])
                _, origin_state, origin_engine = cls._checkpoint_state(origin)
                if "replay" in origin_state:
                    raise ValueError("replay origin is not a plain checkpoint")
                if origin_engine != engine:
                    raise ValueError("replay origin backend differs from checkpoint")
            except (ValueError, TypeError, KeyError) as exc:
                raise MatchError(f"port replay failed: {exc}") from exc
        memory = zlib.decompress(data[8 + n:])
        if "replay" in state:
            return cls._load_replay(state, memory)
        self = cls.__new__(cls)
        self.engine = engine
        if engine == "port":
            from .port.engine import PortMachine
            self.m = PortMachine(memory, state["load"])
        else:
            self.m = Machine(memory, state["load"])
        self.m.restore({"memory": memory[:MEM_SIZE], "regs": state["regs"]})
        self.image_header = bytes.fromhex(state["header"])
        self.image_tail = memory[MEM_SIZE:]
        self.image_sha256, self.opts, self.inputs = state["image_sha256"], state["opts"], state["inputs"]
        self.side, self.end_lin, self.timeout_s = state["side"], state["end_lin"], state["timeout_s"]
        self.fixture_ptr = tuple(state["fixture_ptr"])
        self.st = state["st"]
        self._queue = [Event(e["kind"], e["minute"], tuple(e["score"]), e["data"]) for e in state["queue"]]
        self._menu = None
        self._result = state["result"]
        self._restore_decision_pairs(self.st["decisions"])
        if self._result is not None:
            self._restore_decision_pairs(self._result["decisions"])
        self._names = None
        self._hooks()
        self._install_ports(self.opts.get("ports"))
        self.prover = None
        self.m.no_replay_at = state.get("no_replay_at")
        self.tables = None
        if "tables" in state:
            from .port import tables
            try:
                self.tables = tables.from_record(state["tables"])
            except tables.TablesError as e:
                raise ValueError(str(e)) from None
        return self

    @classmethod
    def _load_replay(cls, state, memory):
        replay = state.pop("replay")
        try:
            origin = bytes.fromhex(replay["origin"])
            # Origins are ordinary checkpoints; reject recursive replay envelopes.
            n = int.from_bytes(origin[4:8], "little")
            if "replay" in json.loads(origin[8:8 + n]):
                raise ValueError("replay origin is not a plain checkpoint")
            self = cls.load(origin)
            self._replay_origin, self._replay_events = origin, 0
            self._replay_actions, self._replaying = [], True
            events = self.events()
            actions = iter(replay["actions"])
            action = next(actions, None)
            count = replay["events"]
            if type(count) is not int or count < 0:
                raise ValueError("invalid event count")
            for boundary in range(count + 1):
                while action is not None and action[0] == boundary:
                    _, kind, args = action
                    if kind not in ("answer", "pause"):
                        raise ValueError("unknown replay action")
                    getattr(self, kind)(**args)
                    action = next(actions, None)
                if boundary < count:
                    next(events)
            if action is not None:
                raise ValueError("replay actions are out of order or beyond the checkpoint")
            actual, actual_memory = self._save_state()
            canonical = lambda x: json.dumps(x, sort_keys=True)
            # JSON round trip normalizes integer dictionary keys and tuples before sorting.
            actual = json.loads(json.dumps(actual))
            if (actual_memory != memory or canonical(actual) != canonical(state)
                    or canonical(json.loads(json.dumps(self._frame_state()))) != canonical(replay["frames"])):
                raise ValueError("reconstructed state differs from checkpoint")
            self._replaying = False
            self._replay_actions = replay["actions"]
            return self
        except (ValueError, KeyError, TypeError, StopIteration, MatchError) as exc:
            raise MatchError(f"port replay failed: {exc}") from exc
