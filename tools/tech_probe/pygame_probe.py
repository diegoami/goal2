"""[designed: T158] The pygame-ce candidate (today's pitch viewer's library): S06 and S16 to kick-off, painted.

    python tools/tech_probe/pygame_probe.py [--quit-after S] [--screenshot DIR]

Everything is drawn on one 1440x900 surface with the design's font (no anti-aliasing: the VGA blocks stay
sharp) and palette; pygame's SCALED window scales the whole page to any window size. Every clickable thing keeps
its rectangle for the mouse. No widgets, so no accessibility tree. pygame-ce also runs under PyPy, which would
let the window and the engine share one interpreter. Prints `READY <s>` after the first frame. Throwaway.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

START = time.perf_counter()
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import screens  # noqa: E402
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame  # noqa: E402

P = {k: pygame.Color(v) for k, v in screens.PALETTE.items()}
BLACK = pygame.Color("#000000")


class Painter:
    def __init__(self, surface):
        self.s = surface
        self.f16 = pygame.font.Font(str(common.FONT), 16)
        self.f32 = pygame.font.Font(str(common.FONT), 32)
        self.hits = []

    def text(self, x, y, value, colour="bright", big=False, right=False):
        img = (self.f32 if big else self.f16).render(str(value), False, P[colour] if isinstance(colour, str) else colour)
        r = img.get_rect(topright=(x, y)) if right else img.get_rect(topleft=(x, y))
        self.s.blit(img, r)
        return r

    def wrap(self, x, y, width, value, colour="normal"):
        words, line = value.split(), ""
        for w in words:
            if self.f16.size(line + " " + w)[0] > width and line:
                self.text(x, y, line, colour)
                y, line = y + 20, w
            else:
                line = (line + " " + w).strip()
        self.text(x, y, line, colour)
        return y + 20

    def box(self, r, title=None, colour="frame_dark"):
        pygame.draw.rect(self.s, P[colour], r, 2)
        if title:
            self.text(r[0] + 16, r[1] + 16, title.upper(), "cyan")

    def kv(self, x, y, pairs, gap=64):
        for k, v in pairs:
            self.text(x, y, k, "brown")
            self.text(x + gap, y, v)
            y += 25
        return y

    def bar(self, x, y, w, value):
        pygame.draw.rect(self.s, P["bar_empty"], (x, y, w, 13))
        pygame.draw.rect(self.s, P["bar"], (x, y, int(w * min(1, value / 9)), 13))

    def kbd(self, x, y, key, on=False):
        w = max(26, self.f16.size(key)[0] + 14)
        pygame.draw.rect(self.s, BLACK if on else P["frame_dark"], (x, y - 3, w, 24), 1)
        self.text(x + (w - self.f16.size(key)[0]) // 2, y, key, BLACK if on else "bright")
        return x + w

    def frame(self, who, banner=""):
        self.s.fill(BLACK)
        self.text(24, 16, "GOAL2", "cyan", big=True)
        self.text(132, 24, who)
        if banner:
            self.text(1416, 24, banner, "light_red", right=True)
        pygame.draw.line(self.s, P["frame_dark"], (0, 63), (1440, 63), 2)
        pygame.draw.line(self.s, P["frame_dark"], (0, 830), (1440, 830), 2)

    def keys(self, items, primary, notice, action):
        x = 24
        for ks, label in items:
            for k in ks:
                x = self.kbd(x, 857, k) + 8
            x = self.text(x, 857, label, "magenta").right + 22
        if notice:
            self.text(x, 857, notice, "yellow")
        w = self.f16.size(primary)[0] + 100
        r = pygame.Rect(1416 - w, 844, w, 44)
        pygame.draw.rect(self.s, P["highlight"], r)
        self.text(r.x + 22, 857, primary, BLACK)
        self.kbd(r.right - 70, 857, "Enter", on=True)
        self.hits.append((r, action))


class App:
    def __init__(self, surface):
        self.p = Painter(surface)
        self.screen, self.cursor, self.pick, self.notice = "desk", 0, screens.COMPUTER_PICK, ""

    def draw(self):
        self.p.hits = []
        getattr(self, self.screen)()

    def desk(self):
        p = self.p
        p.frame("manager's desk", "2028 European Championship · QUALIFYING")
        boxes = [("Manager", 130, None, [("name", "K Ees"), ("rating", "unknown")]),
                 ("Team", 184, ("Holland", "bright"), [("world", 14), ("Europe", 3)]),
                 ("Next opponents", 208, ("Norway", "yellow"), [("world", 32), ("Europe", 18), ("match", "friendly · away")]),
                 ("Managers", 84, None, [])]
        y = 82
        for title, h, big, pairs in boxes:
            p.box((24, y, 420, h), title)
            yy = y + 46
            if big:
                p.text(40, yy, big[0], big[1], big=True)
                yy += 50
            p.kv(40, yy, pairs)
            if title == "Managers":
                p.text(40, yy, "1 · K Ees (Holland)")
            y += h + 14
        y = 82
        for i, (label, sub, key) in enumerate(screens.MENU):
            r = pygame.Rect(462, y, 656, 48)
            on = i == self.cursor
            if on:
                pygame.draw.rect(p.s, P["highlight"], r)
            else:
                pygame.draw.rect(p.s, P["frame_dark"], r, 2)
            end = p.text(480, y + 15, label, BLACK if on else "bright")
            if sub:
                p.text(end.right + 14, y + 15, sub, BLACK if on else "normal")
            if key:
                p.kbd(1050, y + 15, key, on)
            p.hits.append((r, lambda i=i: self.click_menu(i)))
            y += 58
        p.wrap(462, y + 4, 656, "Use ↑↓ to find an option, Enter to select it. Your own matches are watched: play "
               "next game leads to the match menu, the captain and the pitch.")
        p.box((1136, 82, 280, 730), "Holland")
        y = 130
        for i, (line, code, name) in enumerate(screens.SQUAD):
            if i == 11:
                y += 10
            p.text(1164, y, code, screens.LINE_COLOUR[line])
            p.text(1192, y, name)
            y += 25
        p.keys([(["F1"], "help"), (["F3"], "load goal"), (["F4"], "load summary"), (["F7"], "save"), (["F10"], "quit"),
                (["T"], "team tactics"), (["↑", "↓"], "choose")], screens.MENU_HINT[self.cursor], self.notice,
               self.activate)

    def captain(self):
        p = self.p
        c = screens.card(self.pick)
        p.frame("Norway v Holland · captain")
        p.box((24, 82, 1392, 64), None, "highlight")
        p.text(42, 96, "Choose your captain to kick off", "yellow", big=True)
        p.wrap(560, 96, 840, "The match starts as soon as a captain is chosen. The highlight starts on the computer's "
               "pick. Enter: the highlighted player · C: computer select · no key: the computer's pick stands after "
               "the original's wait.")
        p.box((24, 160, 1074, 650))
        p.text(42, 178, c["code"], screens.LINE_COLOUR[c["line"]], big=True)
        n = p.text(72, 178, c["name"], big=True)
        p.text(n.right + 16, 190, c["facts"], "normal")
        p.text(1080, 190, "ready to play", right=True)
        p.text(42, 226, f"position {c['position']} · club position {c['position']} · cards none", "normal")
        p.text(42, 262, "SKILLS", "cyan")
        y = 290
        for name, v in c["skills"]:
            p.text(42, y, name)
            p.bar(152, y + 2, 440, v)
            p.text(604, y, v, "normal")
            y += 21
        p.text(668, 262, "TACTICS", "cyan")
        y = p.kv(668, 290, c["tactics"], gap=96) + 8
        p.text(668, y, "CHARACTERISTICS", "cyan")
        y += 28
        for name, v, word in c["characteristics"]:
            p.text(668, y, name)
            p.bar(780, y + 2, 200, v + 1)
            p.text(992, y, word)
            y += 21
        p.box((1116, 160, 300, 650), "Holland's eleven")
        y = 200
        for i, (line, code, name) in enumerate(screens.ELEVEN):
            r = pygame.Rect(1126, y, 280, 26)
            on = i == self.pick
            if on:
                pygame.draw.rect(p.s, P["highlight"], r)
            p.text(1140, y + 5, code, BLACK if on else screens.LINE_COLOUR[line])
            p.text(1166, y + 5, name, BLACK if on else "bright")
            p.hits.append((r, lambda i=i: self.click_player(i)))
            y += 26
        p.keys([(["↑", "↓"], "player"), (["C"], "computer select"), (["Esc"], "desk (prototype only)")],
               "Captain: kick off", self.notice, lambda: self.go("kickoff"))

    def kickoff(self):
        p = self.p
        p.frame("watching · Norway v Holland")
        p.box((24, 82, 1392, 80))
        x = p.text(42, 106, "Norway", "home", big=True).right + 18
        x = p.text(x, 106, "0", big=True).right + 18
        x = p.text(x, 106, "0", big=True).right + 18
        x = p.text(x, 106, "Holland", big=True).right + 48
        x = p.text(x, 106, "1′", big=True).right + 18
        p.text(x, 114, "FRIENDLY", "normal")
        for i, line in enumerate(screens.COMMENTARY):
            p.text(1396, 96 + 24 * i, line[3:], right=True)
        ox, oy, w, h = 24, 180, 1000, 560
        pygame.draw.rect(p.s, P["frame"], (ox, oy, w, h), 2)
        pygame.draw.line(p.s, P["frame"], (ox + w // 2, oy), (ox + w // 2, oy + h), 2)
        pygame.draw.rect(p.s, P["frame"], (ox, oy + h // 4, int(w * .15), h // 2), 2)
        pygame.draw.rect(p.s, P["frame"], (ox + w - int(w * .15), oy + h // 4, int(w * .15), h // 2), 2)
        pygame.draw.circle(p.s, P["frame"], (ox + w // 2, oy + h // 2), 60, 2)
        for side, colour in ((screens.AWAY, "away"), (screens.HOME, "home")):
            for x, y, code in side:
                img = p.f32.render(code, False, P[colour])
                p.s.blit(img, img.get_rect(center=(ox + x * w / 100, oy + y * h / 100)))
        bx, by = screens.ball(time.perf_counter() - START)
        pygame.draw.rect(p.s, P["bright"], (ox + bx * w / 100 - 4, oy + by * h / 100 - 4, 8, 8))
        p.box((1042, 180, 374, 630), "Commentary")
        y = 220
        for line in screens.COMMENTARY + [f"1′ {screens.ELEVEN[self.pick][2]} captains Holland"]:
            p.text(1058, y, line)
            y += 24
        p.wrap(1058, y + 6, 340, "Speed »»»»» · marks: positions · your side: white")
        p.keys([(["↑", "↓"], "display"), (["←", "→"], "speed"), (["R"], "result"), (["Space"], "commentary"),
                (["F9"], "sound")], "Bench (Esc: desk in the prototype)", self.notice, lambda: self.go("desk"))

    def go(self, screen):
        self.screen, self.notice = screen, ""
        if screen == "captain":
            self.pick = screens.COMPUTER_PICK

    def activate(self):
        if self.cursor == screens.PLAY:
            return self.go("captain")
        self.notice = f"{screens.MENU_HINT[self.cursor]}: not in the prototype"

    def click_menu(self, i):
        self.cursor = i
        self.activate()

    def click_player(self, i):
        self.pick = i

    def key(self, k, text):
        enter = k in (pygame.K_RETURN, pygame.K_KP_ENTER)
        if self.screen == "desk":
            if k == pygame.K_DOWN:
                self.cursor = (self.cursor + 1) % len(screens.MENU)
            elif k == pygame.K_UP:
                self.cursor = (self.cursor - 1) % len(screens.MENU)
            elif enter:
                self.activate()
            elif k in (pygame.K_F1, pygame.K_F3, pygame.K_F4, pygame.K_F7, pygame.K_F10, pygame.K_t, pygame.K_SPACE):
                self.notice = f"{pygame.key.name(k)}: not in the prototype"
        elif self.screen == "captain":
            if k == pygame.K_DOWN:
                self.pick = (self.pick + 1) % 11
            elif k == pygame.K_UP:
                self.pick = (self.pick - 1) % 11
            elif enter:
                self.go("kickoff")
            elif k == pygame.K_c:
                self.pick = screens.COMPUTER_PICK
                self.go("kickoff")
            elif k == pygame.K_ESCAPE:
                self.go("desk")
        elif k == pygame.K_ESCAPE or enter:
            self.go("desk")

    def click(self, pos):
        for rect, action in self.p.hits:
            if rect.collidepoint(pos):
                return action()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quit-after", type=float)
    parser.add_argument("--screenshot", type=Path)
    args = parser.parse_args()
    pygame.init()
    if args.screenshot:
        args.screenshot.mkdir(parents=True, exist_ok=True)
        surface = pygame.Surface((screens.W, screens.H))
        app = App(surface)
        for name in ("desk", "captain", "kickoff"):
            app.go(name)
            app.draw()
            pygame.image.save(surface, str(args.screenshot / f"pygame-{name}.png"))
        return 0
    surface = pygame.display.set_mode((screens.W, screens.H), pygame.SCALED | pygame.RESIZABLE)
    pygame.display.set_caption("GOAL2 prototype (pygame-ce)")
    app = App(surface)
    clock = pygame.time.Clock()
    first, quit_at = True, None
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return 0
            if event.type == pygame.KEYDOWN:
                app.key(event.key, event.unicode)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                app.click(event.pos)
        app.draw()
        pygame.display.flip()
        if first:
            first = False
            print(f"READY {time.perf_counter() - START:.4f}", flush=True)
            if args.quit_after is not None:
                quit_at = time.perf_counter() + args.quit_after
        if quit_at and time.perf_counter() > quit_at:
            return 0
        clock.tick(60)


if __name__ == "__main__":
    sys.exit(main())
