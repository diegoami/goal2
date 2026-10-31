"""A worked interactive match: goal2's own state, one tactic change at a pause, one substitution at half time,
stopped at minute 60 and resumed from the saved bytes. With --competitive, a knockout match (kind 200) that goes
to extra time and penalties: goal2's budget of 5 substitutions (the original's is 2), three of them made before
extra time with a tactic, goal2's own shoot-out order, the match stopped at the order and resumed.

    python3 -m original_match.example [--image FILE.sav] [--cache .cache] [--quiet] [--competitive]
    python3 -m original_match.example --state STATE.json --tables DIR [--quiet] [--competitive]   (sealed, T80)

Without --image the reference image is fetched by hash (assets.py). With --state, the sealed engine plays it on
the port from goal2's state and GOAL.EXE's tables (README, "The sealed engine"). Prints the match as it happens."""
import argparse
import time

from . import Image, Match, Fixture
from .assets import reference_image

DENMARK, OPPONENT, INDEX = 7, 19, 40      # the fixture goal2 chooses: Denmark v country 19, calendar number 40
GO_IN_HARD, STAND_GROUND = 4, 6           # tactic elements (F026): 4 tackling, 6 defence


def goal2_state(image):
    """What goal2 holds (GameState.countries): here, the image's records with goal2's own choices: the 14th
    player starts instead of the 11th, and 'go in hard' (element 4) is set."""
    countries = image.countries()
    rec = bytearray(countries[DENMARK])
    rec[20:22], rec[26:28] = rec[26:28], rec[20:22]          # squad slots 11 and 14 (words 10 and 13)
    rec[0x2D] |= 1 << (GO_IN_HARD - 1)
    countries[DENMARK] = bytes(rec)
    return countries


def play(image, quiet=False, resume_at=60):
    """The scenario; with resume_at, the match is saved at that minute and continued from the saved bytes."""
    countries = goal2_state(image)
    m = Match(image, Fixture(first=DENMARK, second=OPPONENT, index=INDEX), managed=DENMARK, countries=countries)
    say = (lambda *a: None) if quiet else print
    t0, paused, saved = time.time(), False, None if resume_at else b""
    while not m.over:
        for ev in m.events():
            if ev.kind == "commentary":
                if ev.data["template"] in (0x26, 0x34) or ev.minute in (1, 46):   # goal and injury lines, kick-offs
                    say(f"        {ev.data['text']}")
                continue
            if ev.kind == "minute":
                if ev.minute == 20 and not paused:
                    paused = True
                    m.pause()                      # as a manager pressing Enter in play
                if ev.minute == resume_at and saved is None:
                    saved = m.save()               # stop here: everything is in these bytes
                    say(f"  -- saved at minute {resume_at}: {len(saved)} bytes; resuming from them")
                    m = Match.load(saved)
                    break                          # continue with the loaded match
                continue
            say(" ", ev)
            if ev.kind == "decision":
                d = ev.data
                if d["context"] == "pause":
                    m.answer(tactics={STAND_GROUND: True})
                    say(f"  -> answer: tactics, stand ground (element {STAND_GROUND})")
                elif d["context"] == "half_time" and not d.get("refused"):
                    pos = dict(d["positions"])             # player word -> position code (0 the keeper)
                    off = d["eleven"][9]
                    on = next((w for w in d["bench"] if pos.get(w) == pos[off]),
                              next(w for w in d["bench"] if w and pos.get(w) != 0))
                    m.answer(substitutions=[(off, on)])
                    say(f"  -> answer: substitute {off} (position {pos[off]}) by {on} (position {pos[on]})")
                elif d["context"] == "substitution" and d["injured"] and d["bench"]:
                    m.answer(substitutions=[(d["injured"][0], d["bench"][1])])
                    say(f"  -> answer: replace the injured {d['injured'][0]}")
                else:
                    m.answer()
                    say("  -> answer: play on")
    r = m.result()
    say(f"\nfull time {r['first']} {r['score'][0]}-{r['score'][1]} {r['second']} (half time {r['half_time_score']})")
    say("goals:", [(g["name"], g["minute"]) for g in r["goals"]])
    say("substitutions:", [(s["off_name"], s["on_name"], s["minute"]) for s in r["substitutions"]])
    say("bookings:", [(b["name"], b["minute"]) for b in r["bookings"]], "injuries:", [(i["name"], i["minute"]) for i in r["injuries"]])
    say("man of the match:", r["man_of_the_match_name"], "| statistics:", r["board"]["statistics"])
    say("decisions:", [(d["context"], d["minute"], {k: v for k, v in d["answer"].items() if v}) for d in r["decisions"]])
    say(f"{time.time() - t0:.1f} s wall")
    return r


KNOCKOUT, KNOCKOUT_INDEX, BUDGET = 200, 39, 5     # a World Cup knockout match (F023), calendar number 39 (with
#   these answers it goes to penalties: E034 find-knockout-20261016b.jsonl); goal2's budget, 5 a side (its rule)


def knockout_answer(m, d, say):
    """goal2's answers in the knockout example: play on at half time; before extra time three substitutions (the
    last three of the eleven, each by a bench player of his position, else any outfield one) and 'stand ground';
    play on at extra time's half time; at the shoot-out the available players in reverse squad order (forwards
    first, the keeper last); an injured player replaced while the budget lasts."""
    if d["context"] == "extra_time" and d["half"] == 1 and not d.get("refused"):
        pos, subs, used = dict(d["positions"]), [], set()
        for off in d["eleven"][8:11]:
            on = next((w for w in d["bench"] if w and w not in used and pos.get(w) == pos[off]),
                      next(w for w in d["bench"] if w and w not in used and pos.get(w) != 0))
            used.add(on)
            subs.append((off, on))
        m.answer(substitutions=subs, tactics={STAND_GROUND: True})
        say(f"  -> answer: substitutions {subs} (budget left {d['substitutions_left']}), stand ground")
    elif d["context"] == "shootout_order":
        order = list(reversed(d["available"]))
        m.answer(shootout_order=order)
        say(f"  -> answer: shoot-out order {order}")
    elif d["context"] == "substitution" and d["injured"] and d["bench"] and d["substitutions_left"]:
        m.answer(substitutions=[(d["injured"][0], next(w for w in d["bench"] if w))])
        say(f"  -> answer: replace the injured {d['injured'][0]}")
    else:
        m.answer()
        say("  -> answer: play on")


def play_knockout(image, quiet=False, resume_at="shootout_order", index=None, record=None):
    """The knockout scenario; with resume_at (a decision's context), the match is saved at the first such decision
    (before its answer) and continued from the saved bytes. record: a list that gets every event."""
    m = Match(image, Fixture(first=DENMARK, second=OPPONENT, index=index or KNOCKOUT_INDEX, kind=KNOCKOUT),
              managed=DENMARK, substitutions=BUDGET)
    say = (lambda *a: None) if quiet else print
    t0, saved = time.time(), None
    while not m.over:
        for ev in m.events():
            if record is not None:
                record.append(ev)
            if ev.kind in ("commentary", "minute"):
                if ev.kind == "commentary" and (ev.data["template"] in (0x26, 60) or ev.data["text"].startswith("----")):
                    say(f"        {ev.data['text']}")          # goals, the takers, the stage lines
                continue
            say(" ", ev)
            if ev.kind == "decision":
                if ev.data["context"] == resume_at and saved is None:
                    saved = m.save()
                    say(f"  -- saved at the {resume_at} decision: {len(saved)} bytes; resuming from them")
                    m = Match.load(saved)                  # still waiting on the same decision
                    knockout_answer(m, ev.data, say)
                    break                                  # continue with the loaded match
                knockout_answer(m, ev.data, say)
    r = m.result()
    so = r["shootout"]
    say(f"\n{r['first']} {r['score'][0]}-{r['score'][1]} {r['second']} after {'extra time' if r['extra_time'] else '90'}"
        f" (90 minutes {r['score_90']})" + (f", penalties {so['score'][0]}-{so['score'][1]}" if so else "")
        + f"; winner team {r['winner']}")
    say("goals:", [(g["name"], g["minute"], "et" if g.get("extra_time") else "") for g in r["goals"]])
    say("substitutions:", [(s["off_name"], s["on_name"], s["minute"]) for s in r["substitutions"] if s["team"] == 0])
    if so:
        say("kicks:", [(k["name"], "in" if k["scored"] else "out") for k in so["kicks"]])
    say("after (player, confidence, energy):", [(p["player"], p["confidence"], p["energy"]) for p in r["players"]
                                                 if p["team"] == 0][:5], "...")
    say("decisions:", [(d["context"], d["minute"]) for d in r["decisions"]])
    say(f"{time.time() - t0:.1f} s wall")
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image")
    ap.add_argument("--cache", default=".cache")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--competitive", action="store_true")
    ap.add_argument("--state", help="goal2's state (Image.state_of, JSON): the sealed engine, with --tables")
    ap.add_argument("--tables", help="with --state: the folder of GOAL.EXE's constant tables")
    a = ap.parse_args()
    if (a.state is None) != (a.tables is None) or (a.state is not None and a.image is not None):
        ap.error("--state and --tables go together, in place of --image")
    if a.state is not None:
        import json
        from .port import tables
        global Match

        class Match(globals()["Match"]):           # the sealed engine runs on the port
            def __init__(self, *args, **kw):
                kw.setdefault("engine", "port")
                super().__init__(*args, **kw)
        with open(a.state) as f:
            image = Image.from_state(json.load(f), tables.load(a.tables))
    else:
        data = open(a.image, "rb").read() if a.image else reference_image(a.cache)
        image = Image.from_bytes(data)
    (play_knockout if a.competitive else play)(image, quiet=a.quiet)


if __name__ == "__main__":
    main()
