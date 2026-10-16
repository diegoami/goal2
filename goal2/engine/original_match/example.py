"""A worked interactive match: goal2's own state, one tactic change at a pause, one substitution at half time,
stopped at minute 60 and resumed from the saved bytes.

    python3 -m original_match.example [--image FILE.sav] [--cache .cache] [--quiet]

Without --image the reference image is fetched by hash (assets.py). Prints the match as it happens."""
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image")
    ap.add_argument("--cache", default=".cache")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    data = open(a.image, "rb").read() if a.image else reference_image(a.cache)
    play(Image.from_bytes(data), quiet=a.quiet)


if __name__ == "__main__":
    main()
