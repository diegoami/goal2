import inspect,io,json,sys,unittest
from goal2.desktop import pygame_viewer as v
from goal2.desktop.style import COLORS
from goal2.tests.test_pygame_pitch_view import PitchPixels
names=['test_field_bounds_visibility_and_unknown_state','test_watermark_minute_terminal_tail_and_bounded_queue','test_accumulated_target_cadence_and_country_color_association']
def run():
 stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.TestSuite(PitchPixels(n) for n in names));return r,stream.getvalue()
r,log=run();print('BASELINE\n'+log);assert r.wasSuccessful()
source=inspect.getsource(v.render_pitch).replace('screen.fill((18, 28, 37))','screen.fill(tuple(bytes.fromhex(COLORS["background"][1:])))').replace('(232, 239, 229)','tuple(bytes.fromhex(COLORS["text"][1:])))'[:-1])
namespace=dict(vars(v),COLORS=COLORS);exec(compile(source,'<planning runtime colors>','exec'),namespace);v.render_pitch=namespace['render_pitch']
r,log=run();print('RUNTIME PALETTE MOCK\n'+log);assert len(r.failures)==3 and not r.errors
print('PASS scope diagnosis: three retained presentation-only pixel expectations fail with runtime shared palette; no source edits')
