"""[designed: T66] SDL child, display only. Scroll with wheel/arrows; End follows live; Escape closes."""
import json
import os
from pathlib import Path
import sys
from goal2.desktop.match_view import Display, MAX_PACKET, MAX_JOURNAL


def status(path, value):
    temporary = path.with_suffix('.new')
    temporary.write_text(json.dumps(value))
    os.replace(temporary, path)


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
                scroll, follow, finished = position(display, scroll, follow, finished,
                                                     display.sequence != previous_sequence)
                scroll = render(screen, font, display, scroll)
                pygame.display.flip()
                status(target, {'token': token, 'kind': 'ready' if running else 'closed',
                                'sequence': display.sequence, 'digest': display.digest()})
                clock.tick(30)
        pygame.quit()
        return 0
    except Exception as exc:
        status(target, {'token': token, 'kind': 'error', 'message': str(exc)[:1000]})
        return 1


if __name__ == '__main__':
    sys.exit(main())
