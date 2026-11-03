"""[designed: T158] The content of the prototypes' two screens, shared by every toolkit candidate.

The screens are the approved design's S06 (the manager's desk) and S16 (choose your captain), followed by the
kick-off of S17 (the pitch, commentary beside it): docs/design/ui-2026-11/README.md. Names, fixtures and the
captain card's values are the mockups' own (run T156-R1, illustrative skill values); the other players' card
values are made up here, deterministically, as the mockups' are. The colours are the design's palette table,
read from the original's captures by docs/design/ui-2026-11/palette.py [confirmed: that table]. Throwaway: it
goes with tools/tech_probe/ after the owner's decision.
"""
import json

W, H = 1440, 900

PALETTE = {
    "ground": "#000000", "bright": "#ffffff", "normal": "#aaaaaa", "frame": "#aaaaaa", "frame_dark": "#555555",
    "cyan": "#00aaaa", "red": "#aa0000", "brown": "#aa5500", "magenta": "#aa00aa", "highlight": "#aaaaaa",
    "yellow": "#ffff55", "light_red": "#ff5555", "green": "#00aa00",
    "gk": "#00aa00", "def": "#ff5555", "mid": "#00aaaa", "att": "#ffff55", "home": "#ff5555", "away": "#ffffff",
    "bar": "#aaaaaa", "bar_empty": "#aa00aa",
}
LINE_COLOUR = {"g": "gk", "d": "def", "m": "mid", "a": "att"}

MENU = [("team info", "", ""), ("fixture list", "", ""), ("tournament", "", ""), ("history", "", ""),
        ("select squad", "", "Space"), ("play next game", "Norway away · friendly", "")]
MENU_HINT = ["Team info", "Fixture list", "Tournament", "History", "Select squad", "Play next game"]
PLAY = 5

SQUAD = [("g", "G", "F V Breukelen"), ("d", "S", "R Koeman"), ("d", "C", "B Van Aerle"), ("d", "C", "A V Tiggelen"),
         ("m", "D", "J Wouters"), ("m", "m", "R Witschge"), ("m", "M", "F Rijkaard"), ("m", "F", "D Bergkamp"),
         ("a", "w", "B Roy"), ("a", "W", "R Gullit"), ("a", "$", "M Van Basten"),
         ("g", "G", "S Menzo"), ("d", "S", "F De Boer"), ("d", "C", "D Blind"), ("m", "Ç", "W Jonk"),
         ("m", "Ç", "P Bosz"), ("m", "M", "J Van't Ship"), ("m", "m", "A Winter"), ("a", "$", "P Van Vossen"),
         ("a", "$", "W Kieft")]
ELEVEN = SQUAD[:11]
COMPUTER_PICK = 3   # the highlight starts on the computer's pick (T156-R1 step 43)

SKILLS = ["keeping", "kicking", "tackling", "heading", "marking", "passing", "crossing", "feinting", "control",
          "dribbling", "shooting", "penalties"]
CHARACTERISTICS = [("hardness", "tough"), ("fitness", "match fit"), ("energy", "fine"), ("morale", "good"),
                   ("leadership", "inspiring")]
TACTICS = [("position", "stay back"), ("possession", "keep ball"), ("passing", "short passes"),
           ("tackling", "go in hard"), ("mark", "—")]
POSITION = {"G": "goalkeeper", "S": "sweeper", "C": "centre back", "D": "defensive midfield", "m": "midfield",
            "M": "midfield", "F": "forward midfield", "w": "winger", "W": "winger", "$": "striker", "Ç": "midfield"}


def card(index):
    """The card of the eleven's player `index`: the mockup's for A V Tiggelen, made-up values for the others."""
    line, code, name = ELEVEN[index]
    if index == COMPUTER_PICK:
        skills = [1, 6, 8, 7, 8, 6, 4, 4, 6, 4, 3, 4]
        chars = [6, 7, 7, 6, 7]
        facts = "age 29 · caps 41 · goals 1 · 5′11″ · right foot"
    else:
        seed = sum(map(ord, name))
        skills = [(seed * (i + 3) * 7 + i) % 9 + 1 for i in range(12)]
        if line == "g":
            skills[0] = 9
        chars = [(seed * (i + 5)) % 6 + 4 for i in range(5)]
        facts = f"age {22 + seed % 11} · caps {seed % 60} · goals {seed % 9} · 5′{8 + seed % 4}″ · right foot"
    return {"line": line, "code": code, "name": name, "facts": facts, "position": POSITION.get(code, "midfield"),
            "skills": list(zip(SKILLS, skills)), "characteristics": [(c[0], v, c[1]) for c, v in zip(CHARACTERISTICS, chars)],
            "tactics": TACTICS}


# Kick-off: (x, y) in percent of the pitch, as the S17 mockup (Holland, the away side, white; Norway light red).
AWAY = [(6, 50, "G"), (18, 30, "C"), (18, 70, "C"), (14, 50, "S"), (35, 50, "D"), (30, 20, "M"), (30, 80, "M"),
        (46, 50, "F"), (46, 15, "W"), (46, 85, "W"), (50, 56, "$")]
HOME = [(94, 50, "G"), (88, 50, "S"), (84, 30, "C"), (84, 70, "C"), (78, 15, "B"), (78, 85, "B"), (66, 30, "M"),
        (66, 70, "M"), (60, 50, "Ç"), (52, 42, "W"), (57, 64, "F")]
COMMENTARY = ["1′ Bratseth wins the toss", "1′ Nilsen to take kick off"]


def data():
    return {"palette": PALETTE, "menu": MENU, "menu_hint": MENU_HINT, "play": PLAY, "squad": SQUAD,
            "eleven": [card(i) for i in range(11)], "pick": COMPUTER_PICK, "away": AWAY, "home": HOME,
            "commentary": COMMENTARY, "line_colour": LINE_COLOUR}


def ball(t):
    """The ball's place (percent of the pitch) at t seconds: a loop round the centre circle, so a prototype's
    animation and its frame rate can be judged."""
    import math
    return 50 + 9 * math.cos(t * 1.3), 50 + 16 * math.sin(t * 1.3)


if __name__ == "__main__":
    print(json.dumps(data(), ensure_ascii=False, indent=1))
