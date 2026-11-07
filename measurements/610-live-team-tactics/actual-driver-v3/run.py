"""Versioned actual-UI driver calibration; does not alter application or engine code.

The first driver reopened the injury bench even after the injury was handled.
Use the actual still-injured XI to decide whether to open that bench again.
Every tactic, frame, command, original reply and headless equality assertion stays.
"""
import hashlib
import inspect
from pathlib import Path
import sys
import textwrap
import unittest
from unittest.mock import patch
from goal2.tests import test_live_team_tactics_610 as tests
source = textwrap.dedent(inspect.getsource(tests.ActualLiveTeamTactics.run_journey))
old = "if screen.phase == 'stop':"
new = "if screen.phase == 'stop' and any(w in self.window.match_day.bench.injured for w in self.window.match_day.bench.eleven):"
assert source.count(old) == 1
source = source.replace(old, new)
namespace = dict(tests.__dict__)
exec(compile(source, __file__, 'exec'), namespace)
print('UI app/test source', hashlib.sha256(Path(tests.__file__).read_bytes()).hexdigest(), flush=True)
print('Versioned driver source', hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), flush=True)
case = tests.ActualLiveTeamTactics('test_half_time_all_flags_confirm_before_play_and_match_headless_publication')
with patch.object(tests.ActualLiveTeamTactics, 'run_journey', namespace['run_journey']):
    result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([case]))
sys.exit(0 if result.wasSuccessful() else 1)
