"""[designed: T170d/#566] The Core oracle for the sealed season route, as test support (not product code).

The claim [designed: T170 Done-when 2]: for the same career, the same keys and the same match answers, a sealed
round (goal2/game/season.py, the accepted route) and its terminal step leave the game in the state the original
leaves it in, field by field. The original is goal2's Core (Unicorn, goal2/core/): the oracle. T170d proves it on
one round and one terminal step; T170e (1992/stage 2) and T170f (1994/stage 5) import this module unchanged.

The two sides run in two interpreters, so the helper has two halves and a comparison:

    core_rounds(blob, rounds)         CPython + Unicorn: the original's play_round through the Driver
    sealed_rounds(component, rounds)  PyPy 3.11, in a child (pypy_engine.call): SeasonSession.advance()/resume()
    check(label, core, sealed)        raises OracleMismatch naming the field and the round

Both halves return `Round` records of the same shape: the seven compared fields, read from the guest memory
at the site where the two sides correspond (below), and a few facts (kind, stage, cursor, count) that explain a
failure. The fields are read by `observe`, one function over a `read(linear, size)`, so neither half can read
them differently.

The correspondence of sites [confirmed: goal2-archaeology static/goal-exe/annotations/routines.tsv 000E:70B9 at
the vendored commit; route.py docstring]: the sealed route calls play_round 000E:70B9 with main_menu_loop's return
000E:77C2, so a completed round is compared where the original's play_round returns to 77C2; the terminal step
[designed: owner #509, T170] is compared at 000E:70E6, the call of stage_end, which the original reaches with
cursor=count, rounds=1 and stage 4 or 8 and which the route returns before as `deferred-rollover`. The original
is stopped there for real (Machine.stop), so no stage_end, no rollover and no later effect runs on it.

Same keys. The sealed side uses route.Keys(route.DEFAULT_KEYS) and keeps one Keys object across its calls, as
SeasonSession does. The Core's timed polls normally get no key unless one is queued (T170's hazard), so the Core
side is given the same key at the same places: CORE_KEYS says, for every site of DEFAULT_KEYS, which Core screen
kind it is and how the Core is handed that key; test_season_oracle_t170d fails if DEFAULT_KEYS and CORE_KEYS
drift apart.

Same match answers. The sealed side answers every decision of the held Match with the default answer
(watched_match.consume_match with no policy); the Core plays the match watched, with no key at any live poll,
the original's own taker timer and no action replay. A managed side whose eleven the original refuses is not
repaired on either side: the Core raises (no fix_eleven) and the case is not a case.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib

# --- the compared fields ----------------------------------------------------------------------------------------

# [confirmed: goal2-archaeology experiments/E040-route-fixture-writes/runner.py BLOCKS, from globals.tsv, F007, F011,
# F023] the far pointer at DS:ptr, the allocated size, the record size (None: one block).
FIELD_SPECS = (
    ("countries", 0xA917, 0x603F, 0xBF, "country"),         # 129 records
    ("players", 0xA91B, 0xEF24, 0x14, "player"),            # 3061 records
    ("fixtures", 0xA92B, 0x4B48, 8, "fixture"),              # 2409 records, numbered from 1
    ("game", 0xA923, 0x10E, None, "game-block byte"),
    ("A91F", 0xA91F, 0x195, 3, "manager slot"),             # manager m at slot 0x80 + m: country, rating, confidence
)
WORDS = (("7B62", 0x7B62), ("8336", 0x8336))                 # the main and the speaker RNG words (route.SEEDS)
FIELDS = tuple(spec[0] for spec in FIELD_SPECS) + tuple(name for name, _ in WORDS)
GAME_CURSOR, GAME_COUNT, GAME_STAGE, GAME_ROUNDS = 0x26, 0x28, 0x3C, 0x3D     # [confirmed: views.py, route.py]
SITE_RETURN, SITE_TERMINAL = "000E:77C2", "000E:70E6"
TERMINAL_STAGES = (4, 8)


class OracleMismatch(AssertionError):
    """The two sides differ. `round` is the label, `fields` the names of the differing fields, `details` one line
    each."""

    def __init__(self, round, fields, details):
        self.round, self.fields, self.details = round, tuple(fields), tuple(details)
        super().__init__(f"round {round}: " + "; ".join(details))


def observe(read, ds):
    """The seven fields from guest memory: `read(linear, size)` -> bytes, `ds` the data segment's linear address.
    Fields are bytes, the RNG words ints. Pure: nothing is written."""
    def word(offset):
        return int.from_bytes(read(ds + offset, 2), "little")

    def far(ptr):
        return word(ptr + 2) * 16 + word(ptr)
    out = {name: bytes(read(far(ptr), size)) for name, ptr, size, _, _ in FIELD_SPECS}
    out.update({name: word(offset) for name, offset in WORDS})
    return out


def game_facts(read, ds):
    """(stage, cursor, count, rounds) of the game record: what explains a failure and decides the terminal site."""
    def word(offset):
        return int.from_bytes(read(ds + offset, 2), "little")
    game = word(0xA923 + 2) * 16 + word(0xA923)
    raw = bytes(read(game, 0x40))
    return dict(stage=raw[GAME_STAGE], cursor=int.from_bytes(raw[GAME_CURSOR:GAME_CURSOR + 2], "little"),
                count=int.from_bytes(raw[GAME_COUNT:GAME_COUNT + 2], "little"), rounds=raw[GAME_ROUNDS])


def at_terminal(facts):
    """[derived: route._deferred_image; T170 scope] The explicit rollover boundary before stage_end."""
    return facts["cursor"] == facts["count"] and facts["rounds"] == 1 and facts["stage"] in TERMINAL_STAGES


@dataclass
class Round:
    """One compared round: where it was observed and the seven fields there."""
    kind: str                       # "complete" or "deferred-rollover" (the route's own two words)
    fields: dict                    # the seven fields at the observed site
    before: dict                    # game_facts before the round
    after: dict                     # game_facts at the observed site
    start: dict = field(default_factory=dict)   # the seven fields before the round: the round must have changed them
    facts: dict = field(default_factory=dict)   # side-specific notes (keys used, status, deltas); never compared


def _describe(spec, expected, actual, limit=3):
    """One line for a differing field: which records and which bytes."""
    name, _, _, stride, unit = spec
    bad = [i for i in range(min(len(expected), len(actual))) if expected[i] != actual[i]]
    if len(expected) != len(actual):
        return f"field {name}: length core={len(expected)} sealed={len(actual)}"
    first = 1 if name == "fixtures" else 0
    records = sorted({i // stride for i in bad}) if stride else []
    shown = []
    for i in bad[:limit]:
        where = f"{unit} {i // stride + first} +0x{i % stride:02X}" if stride else f"{unit} +0x{i:02X}"
        shown.append(f"{where} core=0x{expected[i]:02X} sealed=0x{actual[i]:02X}")
    count = f"{len(bad)} bytes" + (f" in {len(records)} {unit}s" if stride else "")
    return f"field {name}: {count} differ ({'; '.join(shown)}{'; ...' if len(bad) > limit else ''})"


def differences(core, sealed):
    """[(field name, line)] for every field that differs, in FIELDS order. Both sides must hold exactly FIELDS: a
    side that lacks one cannot pass by saying nothing."""
    for who, fields in (("core", core), ("sealed", sealed)):
        if tuple(sorted(fields)) != tuple(sorted(FIELDS)):
            raise OracleMismatch("?", ["fields"], [f"the {who} side holds {sorted(fields)}, not {sorted(FIELDS)}"])
    out = []
    specs = {spec[0]: spec for spec in FIELD_SPECS}
    for name in FIELDS:
        if core[name] == sealed[name]:
            continue
        if name in specs:
            out.append((name, _describe(specs[name], core[name], sealed[name])))
        else:
            out.append((name, f"field {name}: core=0x{core[name]:04X} sealed=0x{sealed[name]:04X}"))
    return out


def check(label, core, sealed):
    """Raise OracleMismatch naming the round and every differing field; return None when all seven are equal.
    `core` and `sealed` are `Round.fields` (or any dict holding exactly FIELDS)."""
    found = differences(core, sealed)
    if found:
        raise OracleMismatch(label, [name for name, _ in found], [line for _, line in found])


def corrupt(fields, name):
    """A copy of `fields` with one deliberate change in field `name`: the oracle's own check that a difference in
    that field is reported (test_season_oracle_t170d)."""
    out = dict(fields)
    if name in dict(WORDS):
        out[name] = (out[name] + 1) & 0xFFFF
    else:
        raw = bytearray(out[name])
        raw[len(raw) // 2] ^= 0x01
        out[name] = bytes(raw)
    return out


# --- the key policy ------------------------------------------------------------------------------------------------

# [designed: T170d; confirmed: route.py READS/POLLS/DEFAULT_KEYS, goal2/core/screens.py SITES, driver.py] Every site
# of route.DEFAULT_KEYS: the Core's kind there and how the Core is handed the same key. "queued" keys are put in the
# Core's queue (Core.queue) before the round; "driver" keys are the Driver's own, the same keys. The match
# screens' 214B:157C<... entries are 0791:E929's table screen (TABLE_READS) and the watch prompt.
CORE_KEYS = {
    "000E:0629": ("bulletin", "driver", "Return"),                       # the news pages' key wait (05F6)
    "000E:6C4F": ("round-results", "driver", "Return"),                  # the round's results
    "000E:6A89": ("fixture-result", "driver", "Return"),                 # a declined fixture's result
    "000E:6B92": ("round-playing", "queued", "Return"),                  # 6970's read of the key its poll found
    "214B:157C<0791:E86E": ("match-watch-prompt", "driver", "n"),         # "Do you want to watch this match ?": N
    "214B:157C<1771:9022": ("tournament-table", "driver", "Return"),     # 0791:E929's group table screen, one pass
    "214B:157C<1771:91BE": ("tournament-table", "driver", "Return"),     # the same frame for the second finals table
    "1771:9567": ("championship-bracket", "driver", "Return"),           # the finals' table 1771:9509, "hit any key"
    "000E:0515": ("bulletin-congratulations", "driver", "Return"),       # the tune: a key at the first poll
    "000E:05EC": ("bulletin-congratulations", "driver", "Return"),       # the crowd animation (or best place): a key at the first poll
    "000E:6B89": ("round-playing", "queued", "Return"),                  # 6970's poll while the round is shown
    "000E:6BF7": ("round-playing", "queued", "Return"),                  # 6970's delay loop
}
QUEUED_KINDS = tuple(sorted({kind for kind, how, _ in CORE_KEYS.values() if how == "queued"}))
QUEUE_DEPTH = 4096        # [designed] one queued Return per simulated fixture is plenty; leaving none is an error


def route_keys():
    """The sealed side's policy: route.DEFAULT_KEYS, copied (a mapping route.Keys then owns)."""
    from goal2.engine.original_match import route
    return dict(route.DEFAULT_KEYS)


def policy_problems(policy=None):
    """What differs between the route's key policy and CORE_KEYS: [] when every site of the policy is accounted for
    (and nothing else is), and every key is the one the Core is handed."""
    from goal2.engine.original_match import route
    policy = route_keys() if policy is None else dict(policy)
    keys = {"Return": route.ENTER, "n": route.KEY_N}
    problems = []
    for site in sorted(set(policy) - set(CORE_KEYS)):
        problems.append(f"route key site {site} has no Core counterpart in CORE_KEYS")
    for site in sorted(set(CORE_KEYS) - set(policy)):
        problems.append(f"CORE_KEYS names {site}, which the route policy does not")
    for site in sorted(set(policy) & set(CORE_KEYS)):
        kind, how, name = CORE_KEYS[site]
        if policy[site] != keys[name]:
            problems.append(f"{site}: route key {policy[site]!r}, Core is handed {name!r} ({keys[name]!r})")
    return problems


# --- the Core half ---------------------------------------------------------------------------------------------------

def _core_driver(blob, goal_dat):
    from goal2.core import Core
    from goal2.core.driver import Driver
    core = Core.load(blob, goal_dat=goal_dat)
    return core, Driver(core)


def component_of(blob, goal_dat):
    """The guest memory of the saved Core `blob`, as the Memory component the sealed side starts from."""
    return _core_driver(blob, goal_dat)[0].memory_component()


def core_rounds(blob, goal_dat, rounds):
    """[Round, ...]: `rounds` calls of the original's play_round from the saved Core `blob` (a manager-menu wait),
    each observed at its site (SITE_RETURN, or SITE_TERMINAL where the terminal predicate holds: the Core is stopped
    there). The Core is driven by the Driver with the route's keys (CORE_KEYS) and the default match answers; an
    eleven the original refuses raises (no repair). Stops, with the rounds so far, after the terminal step."""
    from goal2.core import CoreError
    core, driver = _core_driver(blob, goal_dat)
    m = core.m
    ds = m.DS * 16
    seen = {}

    def snapshot(kind):
        seen["kind"] = kind
        seen["fields"] = observe(m.read, ds)
        seen["after"] = game_facts(m.read, ds)

    def returned(replay):
        if not replay and "kind" not in seen:
            snapshot("complete")
            # [designed: T170d] A key a poll found and no read took waits in the route (Keys.waiting) and in the
            # Core (pending). The route's next call reads it at once; the Core's next read would be the manager
            # menu's, which would start another round by itself. The Core's is set aside here and reported.
            seen["waiting"] = core.pending
            core.pending = None

    def stage_end(replay):
        if replay or "kind" in seen:
            return
        if at_terminal(game_facts(m.read, ds)):
            snapshot("deferred-rollover")
            m.stop("oracle-site")           # the original stays paused here: no stage_end, no rollover

    m.at(SITE_RETURN, returned)
    m.at(SITE_TERMINAL, stage_end)
    out = []
    for number in range(1, rounds + 1):
        seen.clear()
        before = game_facts(m.read, ds)
        start = observe(m.read, ds)
        # [designed: T170d] The route gives Return at every one of these polls (DEFAULT_KEYS); Core.queue refuses a
        # Return for round-playing (its catalogue lists Space and Left/Right), so the pairs go into the queue itself,
        # which _on_keypressed consumes as it does any queued key.
        for kind in QUEUED_KINDS:
            core.queued.extend([(kind, 13)] * QUEUE_DEPTH)
        keys_before = len(core.keys)
        try:
            driver.play_round(watch=True, on_taker=lambda d, w: None, on_replay=lambda d, w: False)
        except CoreError:
            if m.stop_reason != "oracle-site":
                raise
        left = {kind: len(core.unqueue(kind)) for kind in QUEUED_KINDS}
        if any(count == 0 for count in left.values()):
            raise OracleMismatch(number, ["keys"], [f"the Core's queued {sorted(left)} keys ran out: a poll got no key"])
        if "kind" not in seen:
            raise AssertionError(f"round {number}: the original returned from play_round at no observed site")
        out.append(Round(seen["kind"], seen["fields"], before, seen["after"], start,
                         dict(side="core", keys=len(core.keys) - keys_before, queue_left=left, waiting=seen.get("waiting"),
                              pages=[kind for kind, _ in driver.pages])))
        if seen["kind"] == "deferred-rollover":
            break
    return out


# --- the sealed half (runs in the PyPy child) -----------------------------------------------------------------------------

def sealed_rounds(component, rounds):
    """[Round, ...] from the guest memory `component` (a Memory component of the original at a manager menu, as
    Core.memory_component() gives it): `rounds` calls of SeasonSession.advance(), each held Match driven to its end
    with the default answer (consume_match, no policy) and resumed. Runs under engine_python() (pypy_engine.call);
    returns picklable Round records. Stops at a deferred-rollover, which repeats unchanged."""
    from goal2.engine.original_match import route
    from goal2.engine.original_match.image import Image
    from goal2.game import engine_tables, watched_match
    from goal2.game.season import SeasonSession
    tables = engine_tables.load()
    image = Image.from_bytes(component)
    keys = route.Keys(route_keys())
    session = SeasonSession(image.state(tables), tables, keys)
    out = []

    def read_state():
        done = Image.from_state(session.state, tables)
        memory, ds = done.memory, done.DS * 16
        read = lambda linear, size: bytes(memory[linear:linear + size])
        return observe(read, ds), game_facts(read, ds)
    start, before = read_state()
    for number in range(1, rounds + 1):
        step = session.advance()
        matches = 0
        while step.status == "match":
            watched_match.consume_match(session.pending_match)
            matches += 1
            step = session.resume(session.pending_match)
        fields, after = read_state()
        if (fields["7B62"], fields["8336"]) != step.rng_words:
            raise AssertionError(f"round {number}: the observation's RNG words {step.rng_words} are not the state's")
        out.append(Round(step.status, fields, before, after, start,
                         dict(side="sealed", matches=matches, waiting=keys.waiting, call=step.call_number,
                              fixtures=len(step.played_fixtures), news=len(step.news_pages),
                              input_hash=step.input_hash, output_hash=step.output_hash)))
        if step.status == "deferred-rollover":
            break
        before, start = after, fields
    return out
