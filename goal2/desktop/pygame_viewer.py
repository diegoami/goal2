"""[designed: T66] SDL child, display only. Scroll with wheel/arrows; End follows live; Escape closes."""
from functools import cache
from collections import deque
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
    # [designed: #278] The bundled font, as the desktop's: Windows has no DejaVu Sans Mono, and
    # pygame's default font is not monospaced and has no ☺ ☻.
    path = str(Path(__file__).with_name('fonts') / ('DejaVuSansMono-Bold.ttf' if bold else 'DejaVuSansMono.ttf'))
    _FONTS[size, bold] = font = pygame.font.Font(path, size)
    return font


# [confirmed: DS:0883 (T96 research)] The order the original draws the 22 pitch slots each tick.
DRAW_ORDER = (22, 11, 1, 12, 6, 17, 2, 13, 21, 10, 18, 7, 3, 20, 9, 14, 5, 16, 4, 15, 8, 19)
# [confirmed: 0791:9372 Up/Down step DS:066A over 0..4, initial 1; 0791:05C6 the five styles]
MARKS = ('Little men', 'Role codes', 'Arrows', 'Home/away', 'Numbers')
DEFAULT_MARKS = 1


def glyph(marks, slot, code, selector, holder):
    """[confirmed: 0791:05C6, 0791:0691 and the draw at 0791:8537] A player's character: keepers
    (slots 1 and 12) are always ☺; style 0 ☺, 1 the role code, 2 an arrow DS:06D4[(slot < 12) xor
    (remaining > threshold)], 3 DS:06D2[slot < 12] (H for slots 1..11), 4 the slot digit
    (slot - 1) % 11 + 0x2F. A ☺ on the player on the ball (DS:830B) is drawn ☻."""
    if slot in (1, 12) or marks == 0:
        return '☻' if slot == holder else '☺'
    if marks == 1:
        return code
    if marks == 2:
        return '►' if int(slot < 12) ^ selector else '◄'
    if marks == 3:
        return 'H' if slot < 12 else 'A'
    return chr((slot - 1) % 11 + 0x2F)


def marker_size(sx, sy):
    """[designed: T96] The largest DejaVu Sans Mono size whose advance (0.6 em) fits one column
    and whose height fits one row, so neighbouring cells never overlap."""
    return max(10, min(round(sy), int(sx / 0.6)))


def render_pitch(screen, font, display, scroll=0, commentary=False, marks=DEFAULT_MARKS):
    """[designed: T94; accepted vision #266 screen 06] Score header, maximum pitch with each
    player's one-letter role code, the last two commentary lines; Space shows the full commentary."""
    import pygame
    width, height = screen.get_size()
    (left, top, w, h), (sx, sy) = layout(width, height)
    screen.fill(BLACK)
    visible = display.visible()
    names = display.countries or ['Starting…', '']
    colours = TEAM_COLORS if display.managed != 1 else TEAM_COLORS[::-1]
    frame = display.frame
    score = frame['score'] if frame is not None else (visible.events[-1]['score'] if visible.events else [0, 0])
    # Narrow windows get smaller header and footer type, so nothing overlaps.
    wide = width >= 1200
    big, small = mono(30 if wide else 24, True), mono(22 if wide else 17)
    x = 18
    for part, colour in ((names[0].upper(), colours[0]), (f'  {score[0]} - {score[1]}  ', CYAN), (names[1].upper(), colours[1])):
        label = big.render(part, True, colour);screen.blit(label, (x, 10));x += label.get_width()
    minute = frame['minute'] if frame is not None else (visible.events[-1]['minute'] if visible.events else 0)
    screen.blit(big.render(f'   {minute}′ / {display.kind.upper()}', True, CYAN), (x, 10))
    speed = small.render(f'SPEED {display.speed_name().upper()}', True, YELLOW)
    screen.blit(speed, (width - speed.get_width() - 18, 16))
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
        # One character per grid cell, as in the original's text screen: the glyph fits its cell
        # and, of players on one cell, the last drawn in the original's order shows.
        marker = mono(marker_size(sx, sy), True)
        occupied = {}
        players = {p[0]: p for p in frame['players']}
        holder = frame.get('officials', {}).get('holder')
        for slot in DRAW_ORDER:
            _, team, number, word, px, py, state, hidden = players[slot]
            if not hidden:
                occupied[at(px, py)] = (glyph(marks, slot, display.code(word, number), frame['selector'], holder), colours[team])
        for point, (text, colour) in occupied.items():
            label = marker.render(text, True, colour)
            screen.blit(label, label.get_rect(center=point))
        bx, by, hidden = frame['ball']
        # [confirmed: 0791:8F10 draw_ball] The ball shows only on an empty cell.
        if not hidden and at(bx, by) not in occupied:
            pygame.draw.circle(screen, YELLOW, at(bx, by), max(3, round(sy * 0.3)))
        officials = frame.get('officials')
        if officials:
            # [confirmed: 0791:A3B6 glyph 0x0D01; 8E24 and 9119 draw after the players] The two
            # linesmen on the touchlines and the referee: light magenta faces over the players.
            spots = [tuple(l) for l in officials['linesmen']]
            if not officials['referee'][2]:
                spots.append(tuple(officials['referee'][:2]))
            for ox, oy in spots:
                label = marker.render('☺', True, MAGENTA)
                screen.blit(label, label.get_rect(center=at(ox, oy)))
    # [designed: T102; confirmed: E031 C39] Enter in play asks for the bench, as in the original.
    hint = small.render('[←→] Speed  [↑↓] Marks  [Enter] Bench  [Space] Commentary  [Esc] Close', True, MAGENTA)
    screen.blit(hint, (width - hint.get_width() - 18, height - FOOTER + 8))
    lines = visible.commentary()
    footer = mono(22 if wide else 18)
    room = width - 36 - hint.get_width() - 24
    for n, line in enumerate(lines[-2:]):
        # The first footer line shares its row with the key hint; long lines end in an ellipsis.
        limit = room if n == 0 else width - 36
        while footer.size(line)[0] > limit and len(line) > 1:
            line = line[:-2] + '…'
        screen.blit(footer.render(line, True, YELLOW if n == 0 and len(lines) > 1 else CYAN), (18, height - FOOTER + 6 + n * 28))
    board = display.board()
    if board is not None and not commentary:
        # [designed: T102] The view freezes on the decision and shows the original's board text;
        # the bench is in the goal2 window.
        panel = pygame.Rect(left + w * 0.2, top + h * 0.3, w * 0.6, h * 0.4)
        pygame.draw.rect(screen, BLACK, panel);pygame.draw.rect(screen, CYAN, panel, 2)
        title = mono(48 if wide else 32, True).render(board, True, YELLOW)
        screen.blit(title, title.get_rect(center=(panel.centerx, panel.y + panel.height * 0.35)))
        note = small.render('The bench is open in the goal2 window', True, WHITE)
        screen.blit(note, note.get_rect(center=(panel.centerx, panel.y + panel.height * 0.7)))
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
    core_keys = '--core-keys' in sys.argv[3:]  # [designed: T116] Python-route pacing stays local
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
        marks = DEFAULT_MARKS
        # [designed: T102] Enter presses in play, reported in the status for the parent's pause.
        requests = 0
        controls = deque(maxlen=64)
        control_sequence = 0
        buffer = b''
        with (folder / 'display').open('rb') as source:
            running = True
            while running:
                for event in pygame.event.get():
                    # [confirmed: E031 C08/C39c, E015 r0013] Space opens the commentary
                    # ("spacebar-commentary"); in it, Esc returns to play ("Esc-play").
                    if (event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER)
                            and display.pitch_rate and display.result is None and display.decision() is None):
                        if core_keys:
                            control_sequence += 1;controls.append([control_sequence,'bench'])
                        else:requests += 1
                        continue
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                        commentary = not commentary
                        continue
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and commentary:
                        commentary = False
                        continue
                    # [confirmed: E031 C39] Left slows the match by one step; Right speeds it up.
                    if event.type == pygame.KEYDOWN and event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                        if core_keys:
                            if display.pitch_rate and display.result is None and display.decision() is None:
                                control_sequence += 1
                                controls.append([control_sequence,'left' if event.key==pygame.K_LEFT else 'right'])
                        else:display.step_rate(-1 if event.key == pygame.K_LEFT else 1)
                    # [confirmed: 0791:9372] Up/Down step the marks on the pitch; with the
                    # commentary open, or with no pitch (text-only watching), they scroll.
                    if (event.type == pygame.KEYDOWN and event.key in (pygame.K_UP, pygame.K_DOWN)
                            and display.pitch_rate and not commentary and display.result is None):
                        marks = (marks + (1 if event.key == pygame.K_DOWN else -1)) % len(MARKS)
                        continue
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
                    scroll = render_pitch(screen, font, display, scroll, commentary, marks)
                else:
                    scroll = render(screen, font, display, scroll)
                pygame.display.flip()
                # [designed] One due sample per loop and one real flip before consumption.
                display.rendered()
                value = {'token': token, 'kind': 'ready' if running else 'closed',
                         'sequence': display.sequence, 'digest': display.digest()}
                if display.pitch_rate:
                    value.update(frame_sequence=display.consumed, requests=requests,
                                 frame_digest=frame_digest(display.frame) if display.frame else None)
                if core_keys:value['controls'] = list(controls)
                status(target, value)
                clock.tick(240 if display.pitch_rate else 30)
        pygame.quit()
        return 0
    except Exception as exc:
        status(target, {'token': token, 'kind': 'error', 'message': str(exc)[:1000]})
        return 1


if __name__ == '__main__':
    sys.exit(main())
