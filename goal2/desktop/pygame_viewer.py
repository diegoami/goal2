"""[designed: T66] SDL child, display only. Scroll with wheel/arrows; End follows live; Escape closes."""
import json
import os
from pathlib import Path
import sys
import time
from goal2.desktop.match_view import Display, MAX_PACKET, MAX_JOURNAL

# [designed: T83] Modern schematic scale; T81 proves signed axes, not physical metres/art.
CENTER = (500, 282)
SCALE = (11, 17)
FIELD = (93, 146, 815, 273)
TEAM_COLORS = ((45, 135, 245), (245, 105, 45))
GRASS = (26, 100, 57)
MARKING = (213, 231, 204)


def project(x, y):
    """[derived: T81/F013 at424d599] Fixed screen=[signed y,signed x], positive right/down."""
    return CENTER[0] + y * SCALE[0], CENTER[1] + x * SCALE[1]


def frame_digest(frame):
    """[designed: T83] Bind the rendered acknowledgement to the exact delivered sample."""
    import hashlib
    return hashlib.sha256(json.dumps(frame, sort_keys=True).encode()).hexdigest()


def status(path, value):
    temporary = path.with_suffix('.new')
    temporary.write_text(json.dumps(value))
    # [designed: #236] Retry only native Windows replacement denial, for <=250ms.
    deadline = time.monotonic() + .25
    while True:
        try:
            os.replace(temporary, path)
            return
        except PermissionError as exc:
            remaining = deadline - time.monotonic()
            if sys.platform != 'win32' or getattr(exc, 'winerror', None) != 5 or remaining <= 0:
                raise
            time.sleep(min(.01, remaining))
            if time.monotonic() >= deadline:
                raise


def navigation(event, scroll, follow):
    """[designed] SDL input changes presentation position only."""
    import pygame
    if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
        return scroll, follow, False
    if event.type == pygame.MOUSEWHEEL:
        return scroll - event.y * 3, False, True
    if event.type == pygame.KEYDOWN and event.key in (pygame.K_UP, pygame.K_DOWN):
        return scroll + (-3 if event.key == pygame.K_UP else 3), False, True
    if event.type == pygame.KEYDOWN and event.key == pygame.K_END:
        return 10**9, True, True
    return scroll, follow, True


def position(display, scroll, follow, finished, changed):
    """[designed] Follow live commentary; land at the original board once complete."""
    if display.result is not None and not finished:
        return sum(event['kind'] == 'commentary' for event in display.events), False, True
    if follow and changed:
        return 10**9, follow, finished
    return scroll, follow, finished


def render(screen, font, display, scroll=0):
    """[designed] Render the ordered text projection on the real SDL surface."""
    lines = display.lines()
    scroll = max(0, min(scroll, max(0, len(lines) - 26)))
    screen.fill((18, 28, 37))
    for number, line in enumerate(lines[:3] + lines[3+scroll:3+scroll+23]):
        screen.blit(font.render(line, True, (232, 239, 229)), (20, 20 + number * 25))
    return scroll



def render_pitch(screen, font, display, scroll=0):
    """[designed: T83] Schematic evidenced playing grid; exact samples, local slot labels."""
    import pygame
    screen.fill((18, 28, 37))
    visible = display.visible()
    lines = visible.lines()
    for n, line in enumerate(lines[:3]):
        if n != 1:
            screen.blit(font.render(line, True, (232, 239, 229)), (20, 12+n*25))
    for team, name in enumerate(display.countries or ['Starting…']):
        x = 20 + team * 480
        pygame.draw.circle(screen, TEAM_COLORS[team], (x+8,46), 8)
        screen.blit(font.render(name, True, TEAM_COLORS[team]), (x+20,37))
    pygame.draw.rect(screen, GRASS, (60, 112, 880, 340))
    pygame.draw.rect(screen, MARKING, FIELD, 2)
    pygame.draw.line(screen, MARKING, (500,146), (500,418), 2)
    pygame.draw.ellipse(screen, MARKING, (448,248,104,68), 2)
    # [designed] Mouth abs(x)<2 is evidenced; box/net decoration is schematic.
    for x in (77, 907):
        pygame.draw.rect(screen, MARKING, (x,256,16,52), 2)
    for x in (93, 797):
        pygame.draw.rect(screen, MARKING, (x,197,110,170), 2)
    frame = display.frame
    if frame is not None:
        for slot, team, number, word, x, y, state, hidden in frame['players']:
            if hidden:
                continue
            point = project(x,y)
            pygame.draw.circle(screen, (10,20,27), point, 13)
            pygame.draw.circle(screen, TEAM_COLORS[team], point, 11)
            label = font.render(str(number), True, (255,255,255))
            screen.blit(label, label.get_rect(center=point))
        x,y,hidden = frame['ball']
        if not hidden:
            point = project(x,y)
            pygame.draw.circle(screen, (10,20,27), point, 6)
            pygame.draw.circle(screen, (255,244,161), point, 4)
    screen.blit(font.render('Slot labels 1-11 | wheel/arrows: commentary / board | End: follow | Esc: close',
                            True, (232,239,229)), (20,88))
    rows = lines[3:]
    scroll = max(0, min(scroll, max(0,len(rows)-8)))
    for n,line in enumerate(rows[scroll:scroll+8]):
        screen.blit(font.render(line, True, (232,239,229)), (20,490+n*26))
    return scroll

def main():
    folder, token = Path(sys.argv[1]), sys.argv[2]
    target = folder / 'status'
    try:
        import pygame
        pygame.init()
        screen = pygame.display.set_mode((1000, 720))
        pygame.display.set_caption('goal2 — Original friendly')
        font = pygame.font.Font(None, 24)
        clock = pygame.time.Clock()
        display = Display(token)
        scroll = 0
        follow = True
        finished = False
        buffer = b''
        with (folder / 'display').open('rb') as source:
            running = True
            while running:
                for event in pygame.event.get():
                    scroll, follow, keep_open = navigation(event, scroll, follow)
                    running = running and keep_open
                if source.tell() > MAX_JOURNAL:
                    raise ValueError('viewer journal exceeds limit')
                previous_sequence = display.sequence
                buffer += source.read(65536)
                for _ in range(32):
                    if b'\n' not in buffer:
                        break
                    row, buffer = buffer.split(b'\n', 1)
                    if len(row) > MAX_PACKET:
                        raise ValueError('viewer packet exceeds limit')
                    display.accept(json.loads(row))
                if len(buffer) > MAX_PACKET:
                    raise ValueError('viewer packet exceeds limit')
                changed = display.advance(time.monotonic()) if display.pitch_rate else False
                visible = display.visible()
                scroll, follow, finished = position(visible, scroll, follow, finished,
                                                     changed or display.sequence != previous_sequence)
                scroll = (render_pitch if display.pitch_rate else render)(screen, font, display, scroll)
                pygame.display.flip()
                # [designed] One due sample per loop and one real flip before consumption.
                display.rendered()
                value = {'token': token, 'kind': 'ready' if running else 'closed',
                         'sequence': display.sequence, 'digest': display.digest()}
                if display.pitch_rate:
                    value.update(frame_sequence=display.consumed,
                                 frame_digest=frame_digest(display.frame) if display.frame else None)
                status(target, value)
                clock.tick(240 if display.pitch_rate else 30)
        pygame.quit()
        return 0
    except Exception as exc:
        status(target, {'token': token, 'kind': 'error', 'message': str(exc)[:1000]})
        return 1


if __name__ == '__main__':
    sys.exit(main())
