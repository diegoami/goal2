"""[designed: T66] SDL child, display only. Scroll with wheel/arrows; End follows live; Escape closes."""
from functools import cache
import json
import os
from pathlib import Path
import sys
import time
from goal2.desktop.match_view import Display, MAX_PACKET, MAX_JOURNAL

# [designed: T94; accepted vision #266 screen 06] The accepted original style: black, large
# type, the managed side gold and the other white (strips are not decoded, G05).
BLACK, WHITE, GREY = (0, 0, 0), (238, 238, 238), (170, 170, 170)
CYAN, YELLOW, GOLD, MAGENTA = (85, 255, 255), (255, 255, 85), (255, 187, 51), (255, 85, 255)
BORDER = (0, 80, 0)
TEAM_COLORS = (GOLD, WHITE)
# [confirmed: F013, kit424d599 seg_0791_05.asm:535-598] The in-play grid: |x| <= 8, |y| <= 37.
GRID = (8, 37)
# [designed: T94] Grid units of room around the field for out-of-field positions.
MARGIN = (1.5, 2.5)
HEADER, FOOTER = 52, 64


def layout(width, height):
    """[designed: T94] The pitch takes the whole window between a one-line score header and the
    two-line commentary footer; returns the pitch rectangle and the grid's pixel scale."""
    left, top = 8, HEADER
    w, h = max(1, width - 16), max(1, height - HEADER - FOOTER)
    scale = (w / (2 * (GRID[1] + MARGIN[1])), h / (2 * (GRID[0] + MARGIN[0])))
    return (left, top, w, h), scale


def project(x, y, size=(1440, 900)):
    """[derived: T81/F013 at424d599] Fixed screen=[signed y,signed x], positive right/down."""
    (left, top, w, h), (sx, sy) = layout(*size)
    return round(left + w / 2 + y * sx), round(top + h / 2 + x * sy)


def frame_digest(frame):
    """[designed: T83] Bind the rendered acknowledgement to the exact delivered sample."""
    import hashlib
    return hashlib.sha256(json.dumps(frame, sort_keys=True).encode()).hexdigest()



@cache
def _status_replace_api():
    """[designed: #254] Bind a single Windows rename that retains open snapshots."""
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                      ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
    create.restype = wintypes.HANDLE
    rename = kernel.SetFileInformationByHandle
    rename.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD)
    rename.restype = wintypes.BOOL
    close = kernel.CloseHandle
    close.argtypes = (wintypes.HANDLE,)
    close.restype = wintypes.BOOL

    class RenameInfo(ctypes.Structure):
        _fields_ = [('Flags', wintypes.DWORD), ('RootDirectory', wintypes.HANDLE),
                    ('FileNameLength', wintypes.DWORD), ('FileName', wintypes.WCHAR * 1)]

    return create, rename, close, RenameInfo


def _replace_status(temporary, path):
    """[designed: #254] Publish one complete snapshot without removing its name first."""
    if os.name != 'nt':
        return os.replace(temporary, path)
    import ctypes
    create, rename, close, info_type = _status_replace_api()
    name = os.fspath(path.absolute()).encode('utf-16-le')
    offset = info_type.FileName.offset
    buffer = ctypes.create_string_buffer(max(ctypes.sizeof(info_type), offset + len(name) + 2))
    info = info_type.from_buffer(buffer)
    # [confirmed: Microsoft FILE_RENAME_INFORMATION; native-rename-diagnosis-01]
    # REPLACE_IF_EXISTS | POSIX_SEMANTICS retains old handles; new opens get the new file.
    info.Flags = 0x1 | 0x2
    info.RootDirectory = None
    info.FileNameLength = len(name)
    ctypes.memmove(ctypes.addressof(buffer) + offset, name, len(name))
    handle = create(os.fspath(temporary), 0x10000, 0x1 | 0x2 | 0x4, None, 3, 0x80, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        if not rename(handle, 22, buffer, len(buffer)):  # FileRenameInfoEx
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        close(handle)


def status(path, value):
    temporary = path.with_suffix('.new')
    temporary.write_text(json.dumps(value))
    # [designed: #236] Retry only native Windows replacement denial, for <=250ms.
    deadline = time.monotonic() + .25
    while True:
        try:
            _replace_status(temporary, path)
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



_FONTS = {}


def mono(size, bold=False):
    """DejaVu Sans Mono at a pixel size; a font from an earlier pygame session is reloaded."""
    import pygame
    font = _FONTS.get((size, bold))
    if font is not None:
        try:
            font.size('x');return font
        except pygame.error:
            _FONTS.clear()
    path = pygame.font.match_font('dejavusansmono', bold=bold)
    _FONTS[size, bold] = font = pygame.font.Font(path, size)
    return font


def render_pitch(screen, font, display, scroll=0, commentary=False):
    """[designed: T94; accepted vision #266 screen 06] Score header, maximum pitch with each
    player's one-letter role code, the last two commentary lines; C shows the full commentary."""
    import pygame
    width, height = screen.get_size()
    (left, top, w, h), (sx, sy) = layout(width, height)
    screen.fill(BLACK)
    visible = display.visible()
    names = display.countries or ['Starting…', '']
    colours = TEAM_COLORS if display.managed != 1 else TEAM_COLORS[::-1]
    frame = display.frame
    score = frame['score'] if frame is not None else (visible.events[-1]['score'] if visible.events else [0, 0])
    big, small = mono(30, True), mono(22)
    x = 18
    for part, colour in ((names[0].upper(), colours[0]), (f'  {score[0]} - {score[1]}  ', CYAN), (names[1].upper(), colours[1])):
        label = big.render(part, True, colour);screen.blit(label, (x, 10));x += label.get_width()
    minute = frame['minute'] if frame is not None else (visible.events[-1]['minute'] if visible.events else 0)
    screen.blit(big.render(f'   {minute}′ / {display.kind.upper()}', True, CYAN), (x, 10))
    # The field: border, playing grid, halfway line, centre circle, goal mouths and boxes.
    pygame.draw.rect(screen, BORDER, (left, top, w, h), 6)
    cx, cy = left + w / 2, top + h / 2
    def at(gx, gy):
        # [designed: T94] A position beyond the drawn margin is shown at the pitch's edge.
        gx = max(-GRID[0] - MARGIN[0], min(GRID[0] + MARGIN[0], gx))
        gy = max(-GRID[1] - MARGIN[1], min(GRID[1] + MARGIN[1], gy))
        return round(cx + gy * sx), round(cy + gx * sy)
    grid_left, grid_top = at(-GRID[0], -GRID[1]);grid_right, grid_bottom = at(GRID[0], GRID[1])
    pygame.draw.rect(screen, GREY, (grid_left, grid_top, grid_right - grid_left + 1, grid_bottom - grid_top + 1), 1)
    pygame.draw.line(screen, GREY, (round(cx), grid_top), (round(cx), grid_bottom), 1)
    pygame.draw.ellipse(screen, GREY, (round(cx - 4.7 * sx), round(cy - 2 * sy), round(9.4 * sx), round(4 * sy)), 1)
    for side in (-1, 1):
        # [designed] Box depth 10 and half-width 5 are schematic; the mouth |x| < 2 is evidenced.
        line = at(0, side * GRID[1])[0]
        box = sorted((line, at(0, side * (GRID[1] - 10))[0]))
        pygame.draw.rect(screen, GREY, (box[0], at(-5, 0)[1], box[1] - box[0], at(5, 0)[1] - at(-5, 0)[1]), 1)
        mouth = sorted((line, line + side * round(1.2 * sx)))
        pygame.draw.rect(screen, GREY, (mouth[0], at(-2, 0)[1], mouth[1] - mouth[0], at(2, 0)[1] - at(-2, 0)[1]), 1)
    if frame is not None:
        marker = mono(max(14, min(40, round(sy * 1.4))), True)
        for slot, team, number, word, px, py, state, hidden in frame['players']:
            if hidden:
                continue
            label = marker.render(display.code(word, number), True, colours[team])
            screen.blit(label, label.get_rect(center=at(px, py)))
        bx, by, hidden = frame['ball']
        if not hidden:
            pygame.draw.circle(screen, YELLOW, at(bx, by), max(3, round(sy * 0.3)))
    lines = visible.commentary()
    footer = mono(22)
    for n, line in enumerate(lines[-2:]):
        screen.blit(footer.render(line, True, YELLOW if n == 0 and len(lines) > 1 else CYAN), (18, height - FOOTER + 6 + n * 28))
    hint = small.render('[C] Commentary  [Esc] Close', True, MAGENTA)
    screen.blit(hint, (width - hint.get_width() - 18, height - FOOTER + 34))
    if commentary or display.result is not None:
        # The full commentary, or the board at full time, over the right part of the pitch.
        rows = visible.lines()[3:] if display.result is not None else lines
        panel = pygame.Rect(left + w * 0.45, top + 6, w * 0.55 - 6, h - 12)
        pygame.draw.rect(screen, BLACK, panel);pygame.draw.rect(screen, CYAN, panel, 2)
        fit = max(1, int((panel.height - 16) // 26))
        scroll = max(0, min(scroll, max(0, len(rows) - fit)))
        for n, line in enumerate(rows[scroll:scroll + fit]):
            screen.blit(footer.render(line, True, WHITE), (panel.x + 12, panel.y + 8 + n * 26))
    return scroll


def main():
    folder, token = Path(sys.argv[1]), sys.argv[2]
    target = folder / 'status'
    try:
        import pygame
        pygame.init()
        # [designed: T94] A large resizable window; the pitch follows its size.
        screen = pygame.display.set_mode((1440, 900), pygame.RESIZABLE)
        pygame.display.set_caption('goal2 — Original friendly')
        font = pygame.font.Font(None, 24)
        clock = pygame.time.Clock()
        display = Display(token)
        scroll = 0
        follow = True
        finished = False
        commentary = False
        buffer = b''
        with (folder / 'display').open('rb') as source:
            running = True
            while running:
                for event in pygame.event.get():
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_c:
                        commentary = not commentary
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
                screen = pygame.display.get_surface()
                if display.pitch_rate:
                    scroll = render_pitch(screen, font, display, scroll, commentary)
                else:
                    scroll = render(screen, font, display, scroll)
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
