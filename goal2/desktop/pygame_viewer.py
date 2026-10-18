"""[designed: T66] SDL child, display only. Scroll with wheel/arrows; Escape closes."""
import json
import os
from pathlib import Path
import sys
from goal2.desktop.match_view import Display, MAX_PACKET, MAX_JOURNAL


def status(path, value):
    temporary = path.with_suffix('.new')
    temporary.write_text(json.dumps(value))
    os.replace(temporary, path)


def render(screen, font, display, scroll=0):
    """[designed] Render the ordered text projection on the real SDL surface."""
    lines = display.lines()
    scroll = max(0, min(scroll, max(0, len(lines) - 25)))
    screen.fill((18, 28, 37))
    for number, line in enumerate(lines[scroll:scroll+26]):
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
        buffer = b''
        with (folder / 'display').open('rb') as source:
            running = True
            while running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                        running = False
                    elif event.type == pygame.MOUSEWHEEL:
                        scroll -= event.y * 3
                    elif event.type == pygame.KEYDOWN and event.key in (pygame.K_UP, pygame.K_DOWN):
                        scroll += -3 if event.key == pygame.K_UP else 3
                if source.tell() > MAX_JOURNAL:
                    raise ValueError('viewer journal exceeds limit')
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
