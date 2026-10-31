"""The check a goal2 session runs: is this the original's engine, run right, on this machine?

    python3 -m original_match.check [--image FILE.sav] [--cache .cache] [--family] [--json REPORT.json]
    python3 -m original_match.check --engine port --state STATE.json --tables DIR [--no-unicorn] ...   (sealed, T80)

1. engine: E011-r0001's fixture (Denmark v country 19, calendar number 21, no input but the speed byte 0 at the
   captain prompt, as E011's starting keys left it) from the reference image must be the match E021 recorded
   from E011's DOSBox-X run (experiments/E021-m0-whole-match/out/20261011T201945897620Z-none-E011-r0001.json, its
   reads placed on E011's own): score, ticks, every main-RNG draw by its digest, the seed at the full-time board,
   the man of the match and the board screen's digest.
2. family (--family, about 100 s): E032's ten seeds written at the captain prompt must be E032's records
   (experiments/E032-match-engine-inventory/out/timing-delay20-*.jsonl): score, ticks, draws and their digest.
3. interactive: example.py's match (goal2's own lineup and tactics, a tactic change at a pause, a substitution
   at half time) run straight and saved and resumed at minute 60 must be identical to each other and to the
   digest this kit recorded (EXPECTED_INTERACTIVE): the same inputs and answers give the same match.
4. goals: in a quick result from a pause at minute 30 and in seed 70's match with a goal the original takes back,
   the goal events, every event's score, the result's goals, the board and the original's own goal count agree
   (goal_problems).
5. knockout: example.py's knockout match (a World Cup knockout fixture, kind 200: goal2's budget of 5 a side, three
   substitutions and a tactic before extra time, goal2's shoot-out order; level after 90 and 120 minutes, decided
   on penalties) run straight, saved and resumed at the first extra-time decision, and saved and resumed at the
   shoot-out order, must be identical to each other and to the digest this kit recorded (EXPECTED_KNOCKOUT,
   competitive_digest: the result with its stages, shoot-out, winner and players' consequences); goal_problems
   holds over its events (the shoot-out's kicks count in the score bytes the board shows, not in the result's
   score), its shoot-out's score is its scored kicks, and the winner is the side ahead on penalties.
The expected values are digests and counts, no original bytes. Exit 0 when every check passes.

The port mode (T58; README "Ports"): `--ports M,...|all` runs every step with those port modules in place of the
original's routines, `--variant M.NAME` with one of a module's variants (a falsifier: it must make a step FAIL); the
family step then prints each seed (the same, changed, or stopped) and the ports' calls."""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

from . import Image, Match, Fixture, VERSION
import fileopts
from .assets import reference_image, check_cache, REFERENCE
from . import example

EXPECTED_ENGINE = {"score": [1, 1], "ticks": 4149, "draws": 182188, "seed_at_board": 46625, "man_of_the_match": 127,
                   "draws_digest": "939f25379c56da7a13d32d4a8d3a5830b0f30eb4db9bb71f459e3b47bd494749",
                   "board_screen_sha256": "af83875517ff679aefaff91bb59d5461071c21c1674cd4258f50da7af3a2f295",
                   # the ring's 199 lines at the board (E021 `commentary` texts, oldest first, joined by newlines)
                   "commentary_last199_sha256": "0b749b4494f29e67250e73ef2d9f718e2484a5475d3b86bc3e15f7e89f12d877"}
EXPECTED_FAMILY = {   # seed: [score, ticks, draws, draws digest] (E032)
    0x0101: [[1, 0], 4279, 192967, "a365b543a2fd8cf85bfee434501dbe6efbfa7cd2ccf0921e18cfecf7f8469704"],
    0x1234: [[1, 1], 4146, 184109, "74b8eb805a4e391f2a0e4e213830b5c734d1b5086c75c682c5978b6403f9563e"],
    0x2345: [[0, 1], 4138, 187079, "fdd36353b12d04ce743c945f7f1161690403bbcdc51ed5ef4fb6cb7aedf65224"],
    0x2B7E: [[0, 2], 4029, 175773, "9c52581937efaeadc6b517fcf01f71d9e1d5c1afb647f833f31954aa09ce8c0e"],
    0x4C1D: [[1, 0], 4659, 210776, "062f3ec21511863a0ff66ba7988e44f908274a3500c0c60de6d2f8ba74455e1b"],
    0x6A33: [[0, 2], 4159, 184733, "e609a2ab96983daa3487ca71c254869482fbf576cde998b3cf5a61f58eaadf91"],
    0x8E05: [[1, 0], 4157, 186815, "139451d24fb36777d923c555e2f15ed093dade0fd66e41dd1a285b227a518c57"],
    0xA1F0: [[1, 0], 4281, 191805, "a0b3a43269fb60c1f7c1912dfc1b83afbaa0ed02abe60a3711a40edc83cce63b"],
    0xC3C3: [[2, 1], 4262, 184677, "4273d8ff21afa63b1451dc2ae5f6ffc48837eab6bbcccce387d6d0ad19727d8a"],
    0xE719: [[1, 0], 4240, 191629, "21f4cfca112e037de352c45767b898f67e01b31ff2db352e65c56fa377268b13"],
}
# example.py's match as this kit played it on the reference image (E033 out/check-*.json): a regression value,
# not independent evidence; a machine that gives another digest plays another match from the same inputs.
EXPECTED_INTERACTIVE = "0078fad9859d4b4083a88707785e2cf0a49e1b6cddfa48bfec5aa765590e592f"
EXPECTED_KNOCKOUT = "7de611c6dec2508bf8504a83a2c680fd253c1ff798ad2c9e1e6db79592034049"
# [designed: T78d, the parent T78's "their digests without the screen"] The same two digests with the
# board's screen left out, as the original engine gives them (`--no-screen` on the original: the
# original is the arbiter; experiments/E036-match-port/out/T78/check-original-noscreen-v1.json).
EXPECTED_INTERACTIVE_NO_SCREEN = "8de3af19448095441a67f5776c13ec4fb47330d747fc16d71c9f77c01ed15d1b"
EXPECTED_KNOCKOUT_NO_SCREEN = "f5d846d69d1e507bab11ca6e43b0016934e05cca89d4c6ddbb2134d812f20869"
# Whether the digests take the board's screen: the port compares without it (its board screen is not
# the original's bytes; T78's records and compare.py --no-screen likewise), or --no-screen.
SCREEN = True
REFERENCE_FIXTURE = Fixture(first=7, second=19, index=21)
MATCH = Match                  # the port mode: a Match with the ports given (ported()), here and in example.py


def _first_line(e):
    return f"{type(e).__name__}: {(str(e).splitlines() or [''])[0][:200]}"


def ported(specs, engine="original"):
    """Match with `specs` as its ports by default (Match.load keeps a saved match's own)."""
    class Ported(Match):
        def __init__(self, *args, **kw):
            kw.setdefault("ports", specs)
            kw.setdefault("engine", engine)
            super().__init__(*args, **kw)
    return Ported


def result_digest(r):
    """A digest of what a match produced: score, events, the board, the commentary, the squads and the seed."""
    keep = {k: r[k] for k in ("score", "half_time_score", "goals", "bookings", "sendings_off", "injuries",
                              "substitutions", "man_of_the_match", "ticks", "seed_after", "squads_after")}
    keep["board"] = {k: r["board"][k] for k in ("statistics", "bars") + (("screen_sha256",) if SCREEN else ())}
    keep["commentary"] = [c["text"] for c in r["commentary"]]
    return hashlib.sha256(json.dumps(keep, sort_keys=True).encode()).hexdigest()


def competitive_digest(r):
    """result_digest plus what a competitive fixture adds: the kind, the stages, the shoot-out, the winner, the
    budget and the players' consequences (confidence, energy, status before and after)."""
    keep = {k: r[k] for k in ("kind", "winner", "score_90", "extra_time", "shootout", "substitution_budget", "players")}
    return hashlib.sha256((result_digest(r) + json.dumps(keep, sort_keys=True)).encode()).hexdigest()


def engine(image):
    m = MATCH(image, REFERENCE_FIXTURE, managed=7, record_draws=True, delay_byte=0)
    for _ in m.events():
        pass
    r = m.result()
    lines = "\n".join(c["text"] for c in r["commentary"][-199:])
    got = {"score": r["score"], "ticks": r["ticks"], "draws": r["draws"], "seed_at_board": r["board"]["seed"],
           "man_of_the_match": r["man_of_the_match"], "draws_digest": r["draws_digest"],
           "board_screen_sha256": r["board"]["screen_sha256"],
           "commentary_last199_sha256": hashlib.sha256(lines.encode()).hexdigest()}
    want = dict(EXPECTED_ENGINE)
    if not SCREEN:
        del got["board_screen_sha256"], want["board_screen_sha256"]
    return got == want, {k: (got[k], want[k]) for k in got if got[k] != want[k]}


def family(image):
    bad = {}
    for seed, want in EXPECTED_FAMILY.items():
        m = MATCH(image, REFERENCE_FIXTURE, managed=7, record_draws=True, delay_byte=0, seed=seed)
        if MATCH is not Match:         # the port mode: a port may stop a match; say so per seed, then go on
            try:
                for _ in m.events():
                    pass
            except Exception as e:
                bad[f"0x{seed:04X}"] = {"stopped": _first_line(e),
                                        "port_calls": dict(m.ports.calls) if m.ports else None}
                print(f"  seed 0x{seed:04X} stopped   {bad[f'0x{seed:04X}']['stopped']}", flush=True)
                print(f"  seed 0x{seed:04X} port calls {bad[f'0x{seed:04X}']['port_calls']}", flush=True)   # long (#633)
                continue
        else:
            for _ in m.events():
                pass
        r = m.result()
        got = [r["score"], r["ticks"], r["draws"], r["draws_digest"]]
        if got != want:
            bad[f"0x{seed:04X}"] = {"got": got[:3], "want": want[:3], "digest_equal": got[3] == want[3]}
        if MATCH is not Match:
            calls = r.get("ports", {}).get("calls")
            print(f"  seed 0x{seed:04X} {'same   ' if got == want else 'changed'}   score {got[0]} ticks {got[1]} "
                  f"draws {got[2]}{'' if got == want else f' (want {want[:3]}, digest equal {got[3] == want[3]})'}  "
                  f"port calls {calls}", flush=True)
    return not bad, bad


def interactive(image):
    straight = result_digest(example.play(image, quiet=True, resume_at=None))
    resumed = result_digest(example.play(image, quiet=True, resume_at=60))
    expected = EXPECTED_INTERACTIVE if SCREEN else EXPECTED_INTERACTIVE_NO_SCREEN
    ok = straight == resumed and (expected is None or straight == expected)
    return ok, {"straight": straight, "resumed": resumed, "expected": expected, "screen": SCREEN}


def goal_problems(events, result):
    """What is wrong with a match's goals (an empty list: nothing). Every event's score is the score of the goals
    before it: a `goal` raises its team's by one, a `goal_disallowed` lowers it by one and needs a goal of that team
    not yet taken back, no other event changes it; the last score is the board's; per team, the result's goals
    are the board's score and the original's own count DS:80F0 (record_goal 6443, which counts an own goal for the
    side the score byte credits, up to 11)."""
    problems, score, open_goals, kicks = [], [0, 0], [0, 0], [0, 0]
    for i, ev in enumerate(events):
        s = list(ev.score)
        if ev.kind in ("goal", "goal_disallowed"):
            t, step = ev.data["team"], 1 if ev.kind == "goal" else -1
            if step < 0 and not open_goals[t]:
                problems.append(f"event {i}: goal_disallowed of team {t} without a goal before it")
            open_goals[t] += step
            score[t] += step
        elif ev.kind == "shootout_kick" and ev.data["scored"]:     # a kick in: the score bytes count it
            score[ev.data["team"]] += 1
            kicks[ev.data["team"]] += 1
        if s != score:
            problems.append(f"event {i} ({ev.kind}, minute {ev.minute}): score {s}, the goals before it make {score}")
            score = s
    if score != list(result["board"]["final_score"]):
        problems.append(f"the events end at {score}, the board says {result['board']['final_score']}")
    shootout = result.get("shootout")
    if (shootout["score"] if shootout else [0, 0]) != kicks or [result["score"][t] + kicks[t] for t in (0, 1)] != list(
            result["board"]["final_score"]):
        problems.append(f"the shoot-out's score {shootout and shootout['score']}, its scored kicks {kicks}, the score "
                        f"{result['score']} and the board {result['board']['final_score']} disagree")
    for t in (0, 1):
        n = sum(1 for g in result["goals"] if g["team"] == t)
        if n != result["score"][t] or result["goal_counts"][t] != min(result["score"][t], 11):
            problems.append(f"team {t}: {n} goals in the result, board {result['score'][t]}, the original's count "
                            f"{result['goal_counts'][t]}")
    return problems


def play_events(image, seed=None, pauses=(), answer=None):
    """The reference fixture with pauses at the given minutes; answer(m, decision data) answers each decision (play
    on by default). Returns the events and the result."""
    m = MATCH(image, REFERENCE_FIXTURE, managed=7, seed=seed)
    events, paused = [], set()
    for ev in m.events():
        events.append(ev)
        if ev.kind == "minute" and ev.minute in pauses and ev.minute not in paused:
            paused.add(ev.minute)
            m.pause()
        if ev.kind == "decision":
            (answer or (lambda m, d: m.answer()))(m, ev.data)
    return events, m.result()


def take_back_answers(m, d):
    """The answers under which seed 70's watched match has the original take a goal back at minute 29 (E033
    stamps.py `decisions`): a tactic and a substitution at a pause, a second keeper at half time."""
    if d["context"] == "pause" and d["eleven"]:
        m.answer(tactics={4: not bool(d["tactics"] >> 3 & 1)}, substitutions=[(d["eleven"][10], d["bench"][7])])
    elif d["context"] == "half_time" and not d.get("refused"):
        m.answer(substitutions=[(d["eleven"][9], d["bench"][1])])
    elif d["context"] == "substitution" and d["injured"]:
        m.answer(substitutions=[(d["injured"][0], d["bench"][2])])
    else:
        m.answer()


def goals(image):
    """goal_problems on a quick result from a pause at minute 30 (PR 251 review round 2, R1) and on seed 70's
    watched match with a goal taken back (R2)."""
    def quick(m, d):
        m.answer(quick=True, speed=3) if d["context"] == "pause" else m.answer()
    runs = {"quick from minute 30": play_events(image, pauses=(30,), answer=quick),
            "seed 70, a goal taken back": play_events(image, seed=70, pauses=(20, 60), answer=take_back_answers)}
    detail = {name: {"score": r["score"], "goals": len(r["goals"]),
                     "goal_events": sum(e.kind == "goal" for e in ev),
                     "taken_back": sum(e.kind == "goal_disallowed" for e in ev), "problems": goal_problems(ev, r)}
              for name, (ev, r) in runs.items()}
    return not any(d["problems"] for d in detail.values()), detail


def knockout(image):
    runs = {}
    for name, at in (("straight", None), ("resumed at extra time", "extra_time"), ("resumed at the order", "shootout_order")):
        events = []
        r = example.play_knockout(image, quiet=True, resume_at=at, record=events)
        runs[name] = (competitive_digest(r), r, events)
    digests = {name: d for name, (d, _, _) in runs.items()}
    _, r, events = runs["straight"]
    so = r["shootout"]
    problems = goal_problems(events, r)
    if not (r["extra_time"] and so and so["score"][0] != so["score"][1]):
        problems.append(f"not decided on penalties: extra time {r['extra_time']}, shoot-out {so}")
    elif r["winner"] != (0 if so["score"][0] > so["score"][1] else 1):
        problems.append(f"winner {r['winner']} is not the side ahead on penalties {so['score']}")
    expected = EXPECTED_KNOCKOUT if SCREEN else EXPECTED_KNOCKOUT_NO_SCREEN
    ok = len(set(digests.values())) == 1 and not problems and (expected is None or digests["straight"] == expected)
    return ok, {"digests": digests, "expected": expected, "screen": SCREEN, "problems": problems,
                "score": r["score"], "score_90": r["score_90"], "shootout": so and so["score"], "winner": r["winner"]}


def parser():
    """The command line's one definition: main() parses with it, and so does the heavy-job slot (heavy_slot.parsed)."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--image", help="a savestate or Memory component (default: the reference, fetched by hash)")
    ap.add_argument("--state", help="the sealed engine (T80): goal2's state (Image.state_of, JSON) in place of an image; "
                                    "needs --tables")
    ap.add_argument("--tables", help="with --state: the folder of GOAL.EXE's constant tables (port/tables.py)")
    ap.add_argument("--cache", default=".cache")
    ap.add_argument("--family", action="store_true")
    ap.add_argument("--engine", choices=("original", "port"), default="original")
    ap.add_argument("--no-unicorn", action="store_true", help="run in a fresh interpreter with Unicorn imports positively denied; requires --engine port")
    ap.add_argument("--json")
    ap.add_argument("--no-screen", action="store_true", help="compare without the board's screen (implied by --engine port)")
    ap.add_argument("--ports", help="the port mode: port modules (port/) to run in place of the original's routines, "
                                    "comma-separated, or all")
    ap.add_argument("--variant", help="the port mode: MODULE.NAME, one of a port module's variants (a falsifier)")
    return ap


class Refused(Exception):
    """A command line that parses but that main() will not run."""


def validate(a):
    """The spec names to run (--ports and --variant, as the saved match keeps them) for a parsed command line, or Refused.
    The one definition of every refusal after parsing: main() calls it, and so does the heavy-job slot (_takes_a_slot), so
    a refused line is answered at once and never queues for a slot (#328). A refusal that needs the run (the reference
    image not in the cache and not downloadable) is not here."""
    if getattr(a, 'no_unicorn', False) and getattr(a, 'engine', 'original') != 'port':
        raise Refused('--no-unicorn requires --engine port')
    specs = [s for s in (a.ports or "").split(",") if s]
    if getattr(a, 'engine', 'original') == 'port':
        specs = ['all'] + specs
    if a.variant:
        if "." not in a.variant:
            raise Refused("--variant is MODULE.NAME")
        specs = [s for s in specs if s != a.variant.split(".")[0]] + [a.variant]
    if specs:
        from . import port
        try:
            specs = port.spec_names(port.load(specs))         # refuses an unknown module or variant before any run
        except ValueError as e:
            raise Refused(str(e))
    state = getattr(a, 'state', None)
    if (state is None) != (getattr(a, 'tables', None) is None):
        raise Refused('--state and --tables go together')
    if state is not None and a.image is not None:
        raise Refused('--state replaces --image')
    try:                       # each path option is checked by the operation the run applies to it (runtime/fileopts.py)
        if state is not None:
            fileopts.check_input(state, "--state")
            check_tables(a.tables)
        elif a.image is not None:
            fileopts.check_input(a.image, "--image")
        else:
            check_cache(a.cache)
        if a.json is not None:
            fileopts.check_new_output(a.json, "--json")
    except fileopts.PathError as e:
        raise Refused(str(e))
    return specs


TABLE_FILES = ("manifest.json", "ds.hex", "code_data.hex")


def check_tables(folder):
    """--tables names a folder holding the three files port/tables.py reads, each a readable regular file."""
    for name in TABLE_FILES:
        fileopts.check_input(str(Path(folder) / name), "--tables")


def load_state(a):
    """The sealed engine's input (T80): goal2's state from --state and the tables from --tables, as an Image."""
    from .port import tables
    data = fileopts.read_input(a.state, "--state")
    check_tables(a.tables)
    return data, Image.from_state(json.loads(data), tables.load(a.tables))


def load_image(a):
    """The image's bytes, as the run reads them: --image, else the reference in --cache."""
    return fileopts.read_input(a.image, "--image") if a.image is not None else reference_image(a.cache)


def write_report(path, report):
    """The --json report, created exclusively."""
    with fileopts.create_new_output(path, "--json") as f:
        json.dump(report, f, indent=1)


def _takes_a_slot(argv=None):
    """Whether main() will run this command line (argparse and validate both accept it), so that it waits for a slot."""
    import heavy_slot
    ns = heavy_slot.parsed(parser(), argv)
    if ns is None:
        return False
    try:
        validate(ns)
    except Refused:
        return False
    return True


def main(argv=None):
    ap = parser()
    a = ap.parse_args(argv)
    global MATCH, SCREEN
    try:
        specs = validate(a)
    except Refused as e:
        ap.error(str(e))
    if a.no_unicorn and not getattr(sys, '_goal2_unicorn_denied', False):
        import os
        bootstrap = "import builtins,sys,runpy\noriginal_import=builtins.__import__\ndef guarded(name,*a,**kw):\n if name=='unicorn' or name.startswith('unicorn.'):raise ImportError('positive Unicorn denial')\n return original_import(name,*a,**kw)\nbuiltins.__import__=guarded\nsys._goal2_unicorn_denied=True\ntry:__import__('unicorn')\nexcept ImportError:pass\nelse:raise AssertionError('denial did not take effect')\nsys.argv=['original_match.check']+sys.argv[1:]\nrunpy.run_module('original_match.check',run_name='__main__')\n"
        os.execv(sys.executable, [sys.executable, '-B', '-c', bootstrap, *(argv if argv is not None else sys.argv[1:])])
    MATCH = example.Match = ported(specs, a.engine)
    if specs:
        print(f"ports: {', '.join(specs)}", flush=True)
    if a.state is not None:            # the sealed engine (T80): goal2's state and GOAL.EXE's tables, no image
        data, image = load_state(a)
    else:
        data = load_image(a)
        image = Image.from_bytes(data)
    report = {"kit": VERSION, "image_sha256": hashlib.sha256(data).hexdigest(), "reference": REFERENCE, "checks": {}}
    if a.state is not None:
        report["state"] = True
    SCREEN = not (a.no_screen or a.engine == "port")
    if not SCREEN:
        report["screen"] = False
        print("digests without the board's screen", flush=True)
    if a.engine != "original":
        report["engine"] = a.engine
    if specs:
        report["ports"] = specs
    steps = [("engine", engine), ("interactive", interactive), ("goals", goals), ("knockout", knockout)] + (
        [("family", family)] if a.family else [])
    for name, fn in steps:
        t0, c0 = time.time(), time.process_time()
        if specs:                      # the port mode: a step a port stops FAILs, and the next steps still run
            try:
                ok, detail = fn(image)
            except Exception as e:
                ok, detail = False, {"stopped": _first_line(e)}
        else:
            ok, detail = fn(image)
        report["checks"][name] = {"pass": ok, "detail": detail, "wall_s": round(time.time() - t0, 1),
                                  "cpu_s": round(time.process_time() - c0, 1)}
        print(f"{name:12s} {'PASS' if ok else 'FAIL'}  {report['checks'][name]['wall_s']} s  {detail if not ok or name in ('interactive', 'knockout') else ''}")
    if a.json is not None:
        write_report(a.json, report)
    sys.exit(0 if all(c["pass"] for c in report["checks"].values()) else 1)


if __name__ == "__main__":
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))    # runtime/
    import heavy_slot
    if _takes_a_slot():    # a command line main() refuses (argparse or validate) holds no slot
        heavy_slot.take("check")   # a heavy job (#318): waits for a slot of tools/heavy.sh
    main()
