#!/usr/bin/env python3
"""[designed: T79] MOCK-ONLY preflight; synthetic accepted-test packets, no original-output claim.
No product files, engine, transport, pacing, project() or publication are changed.
Main owns execution and native-display serialization. Output directory must be new.
"""
import argparse
import collections
import copy
import hashlib
import inspect
import json
import os
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def digest(value):
    def encode(obj):
        if isinstance(obj, collections.deque):
            return list(obj)
        raise TypeError(type(obj).__name__)
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=encode).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('baseline', 'mock', 'mutate-render'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--render-scale', type=int, choices=(1, 2), default=1)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    report = {'tag': '[designed: T79] MOCK-ONLY planning probe', 'mode': args.mode,
              'claim_limit': 'Synthetic T83 test packets; no engine run, original output, full game state, handoff or OS-scaling acceptance.',
              'platform': platform.platform(), 'python': sys.version,
              'render_scale': args.render_scale,
              'paint_claim': 'MOCK-ONLY canonical canvas letterbox transform feasibility; not proposed production design or OS-scale acceptance',
              'probe_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'requested_qt_scale': os.environ.get('QT_SCALE_FACTOR'),
              'sources': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in (ROOT/'goal2/desktop/pygame_viewer.py', ROOT/'goal2/desktop/match_view.py', ROOT/'goal2/desktop/style.py')},
              'checks': {}, 'captures': []}
    import pygame
    from goal2.desktop import pygame_viewer as viewer
    from goal2.desktop.style import COLORS
    from goal2.tests.test_pygame_pitch_view import pitch, sample, send
    original_project = viewer.project
    original_render = viewer.render_pitch
    original_source = inspect.getsource(original_render)
    report['runtime_mock'] = 'None' if args.mode == 'baseline' else 'Only runtime render_pitch background/reading-text color substitutions from accepted COLORS'
    if args.mode != 'baseline':
        changed = original_source.replace('screen.fill((18, 28, 37))', 'screen.fill(tuple(bytes.fromhex(COLORS["background"][1:])))')
        changed = changed.replace('(232, 239, 229)', 'tuple(bytes.fromhex(COLORS["text"][1:]))')
        changed = changed.replace('(232,239,229)', 'tuple(bytes.fromhex(COLORS["text"][1:]))')
        assert changed != original_source, 'mock anchors did not match accepted renderer'
        namespace = dict(vars(viewer), COLORS=COLORS)
        exec(compile(changed, '<T79 runtime-only color mock>', 'exec'), namespace)
        viewer.render_pitch = namespace['render_pitch']
    pygame.init()
    try:
        physical = pygame.display.set_mode((900 * args.render_scale, 640 * args.render_scale))
        screen = pygame.Surface((1000, 720))
        factor = min(physical.get_width()/1000, physical.get_height()/720)
        fitted = (round(1000*factor), round(720*factor))
        offset = ((physical.get_width()-fitted[0])//2, (physical.get_height()-fitted[1])//2)
        real_flip = pygame.display.flip
        def paint_flip():
            physical.fill((0, 0, 0))
            physical.blit(pygame.transform.smoothscale(screen, fitted), offset)
            real_flip()
        pygame.display.flip = paint_flip
        pygame.display.set_caption('goal2 — T79 MOCK-ONLY planning probe')
        font = pygame.font.Font(None, 24)
        traces = []
        class FontTrace:
            def render(self, text, antialias, color, *rest):
                surface = font.render(text, antialias, color, *rest)
                traces.append({'text': text, 'color': list(color), 'size': list(surface.get_size())})
                return surface
            def __getattr__(self, name):
                return getattr(font, name)
        d = pitch()
        f = sample()
        f['players'][0] = [1, 1, 1, 101, -3, -21, 0, False]
        f['players'][21] = [22, 0, 11, 122, 5, 25, 13, False]
        # [designed] Literal synthetic commentary, never represented as original output.
        send(d, 'event', {'kind': 'commentary', 'minute': 7, 'score': [1, 0],
                          'data': {'text': 'MOCK-ONLY synthetic commentary'}})
        f['watermark'] = 1
        packet = ['owned', d.sequence, 'frame', f]
        d.accept(packet)
        assert d.advance(0)
        packet_before = digest(packet)
        state_before = digest(d.__dict__)
        expected_lines = d.visible().lines()
        if args.mode == 'mutate-render':
            real_render = viewer.render_pitch
            def mutate(screen, font, display, scroll=0):
                display.frame['score'][0] += 1
                return real_render(screen, font, display, scroll)
            viewer.render_pitch = mutate
        viewer.render_pitch(screen, FontTrace(), d)
        pygame.display.flip()
        state_after = digest(d.__dict__)
        packet_after = digest(packet)
        capture = args.output/'canonical-surface.png'
        pygame.image.save(screen, str(capture))
        actual_capture = args.output/'native-surface.png'
        pygame.image.save(physical, str(actual_capture))
        native_window = pygame.display.get_wm_info()
        report['wm_info'] = {str(k): v if isinstance(v, (int, float, str, bool, type(None))) else repr(v) for k,v in native_window.items()}
        if sys.platform == 'win32':
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.WinDLL('user32', use_last_error=True)
            hwnd = native_window.get('window')
            rect = wintypes.RECT()
            user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
            user32.GetWindowRect.restype = wintypes.BOOL
            assert hwnd and user32.GetWindowRect(hwnd, ctypes.byref(rect)), 'native HWND window rectangle unavailable'
            user32.GetDpiForWindow.argtypes = [wintypes.HWND]
            user32.GetDpiForWindow.restype = wintypes.UINT
            work = wintypes.RECT()
            assert user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(work), 0), 'Windows work area unavailable'
            report['windows_native'] = {'hwnd': hwnd, 'dpi_for_window': user32.GetDpiForWindow(hwnd),
                'window_rect': [rect.left, rect.top, rect.right, rect.bottom],
                'available_desktop': [work.left, work.top, work.right, work.bottom],
                'desktop_pixels': [user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)]}
        report.update(actual_sdl_driver=pygame.display.get_driver(), pygame=pygame.version.ver,
                      sdl=list(pygame.get_sdl_version()), surface_size=list(physical.get_size()), canonical_size=list(screen.get_size()),
                      canonical_flags=screen.get_flags(), physical_flags=physical.get_flags(),
                      paint_factor=factor, fitted_size=list(fitted), paint_offset=list(offset),
                      physical_font_height=font.get_height()*factor,
                      canonical_pixel_sha256=hashlib.sha256(pygame.image.tobytes(screen, 'RGB')).hexdigest(),
                      physical_pixel_sha256=hashlib.sha256(pygame.image.tobytes(physical, 'RGB')).hexdigest(),
                      window_size=list(pygame.display.get_window_size()), font_height=font.get_height(),
                      font_linesize=font.get_linesize(), text_trace=traces,
                      physical_text_geometry=[{'text': row['text'], 'estimated_painted_size': [round(v*factor) for v in row['size']]} for row in traces],
                      display_state_before=state_before, display_state_after=state_after,
                      packet_before=packet_before, packet_after=packet_after,
                      expected_visible_lines=expected_lines)
        for image in (capture, actual_capture):
            report['captures'].append({'path': image.name, 'sha256': hashlib.sha256(image.read_bytes()).hexdigest()})
        checks = report['checks']
        checks['render_is_read_only'] = state_before == state_after and packet_before == packet_after
        checks['actual_physical_surface'] = physical.get_size() == (900*args.render_scale, 640*args.render_scale)
        checks['aspect_preserving_fit'] = fitted[0] <= physical.get_width() and fitted[1] <= physical.get_height() and abs(fitted[0]/1000-fitted[1]/720) <= .002
        checks['project_unchanged'] = viewer.project is original_project and viewer.project(-3, -21) == (269, 231)
        checks['shared_background'] = tuple(screen.get_at((5, 5)))[:3] == tuple(bytes.fromhex(COLORS['background'][1:]))
        read = [row for row in traces if row['text'] in (expected_lines[0], expected_lines[2], expected_lines[3])]
        checks['pinned_score_provenance_and_commentary'] = len(read) == 3
        checks['shared_reading_color'] = all(row['color'] == list(bytes.fromhex(COLORS['text'][1:])) for row in read)
        checks['reading_geometry'] = all(row['size'][0] <= 960 and row['size'][1] <= 26 for row in read)
        checks['preserved_numbered_markers'] = any(row['text'] == '1' for row in traces) and any(row['text'] == '11' for row in traces)
        checks['preserved_pitch_and_ball'] = tuple(screen.get_at((277, 231)))[:3] == viewer.TEAM_COLORS[1] and tuple(screen.get_at((643, 214)))[:3] == (255, 244, 161)
        report['result'] = 'PASS' if all(checks.values()) else 'FAIL'
        failed = [name for name, passed in checks.items() if not passed]
        report['failed_checks'] = failed
        if failed:
            raise AssertionError('T79 planning visual/read-only contract: ' + ', '.join(failed))
        print('PASS T79 MOCK-ONLY real SDL planning surface; read-only synthetic packets; shared palette; pinned source-order text and geometry')
    except Exception as exc:
        report['result'] = 'FAIL'
        report['exception'] = type(exc).__name__
        report['failure'] = str(exc)
        raise
    finally:
        viewer.render_pitch = original_render
        if 'real_flip' in locals():
            pygame.display.flip = real_flip
        pygame.quit()
        (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')

if __name__ == '__main__':
    main()
