"""[designed: CLAUDE.md rule 14] No savestate of the running original enters the repository or an upload.

`Core.save()` writes the emulated GOAL.EXE's whole memory (`goal2/core/runner.py`, `save`), a `.ucstate` is a ZIP
of the same memory and registers (`goal2/core/cycle_evidence.py`), and a `.g2game` wraps a `session.g2save`
(`goal2/ui/saves.py`), which the gate already refuses. The gate's list, `.gitignore` and every workflow's upload
refusal name the same extensions, so none of the three can drift from the others.
"""
import importlib
import re
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
gate = importlib.import_module('check_premerge')
sys.path.remove(str(ROOT / 'tools'))

SAVESTATES = ('.g2core', '.ucstate', '.g2game')
REFUSAL = re.compile(r"grep -iE '\\\.\(([a-z0-9|]+)\)\$'")


class SavestateExclusion(unittest.TestCase):
    def test_the_gate_refuses_tracked_savestates(self):
        for suffix in SAVESTATES:
            with self.subTest(suffix=suffix), \
                    patch.object(gate, 'git', return_value=f'goal2/x{suffix}\0README.md\0'):
                with self.assertRaises(gate.ValidationError):
                    gate.check_originals()

    def test_every_upload_refusal_names_the_gate_s_extensions(self):
        expected = {suffix.lstrip('.') for suffix in gate.FORBIDDEN}
        found = 0
        for workflow in sorted((ROOT / '.github' / 'workflows').glob('*.yml')):
            for match in REFUSAL.finditer(workflow.read_text()):
                found += 1
                with self.subTest(workflow=workflow.name, at=match.start()):
                    self.assertEqual(set(match.group(1).split('|')), expected)
        self.assertGreater(found, 0, 'no upload refusal found in the workflows')

    def test_git_ignores_savestates(self):
        for suffix in SAVESTATES:
            with self.subTest(suffix=suffix):
                ignored = subprocess.run(['git', 'check-ignore', '-q', '--no-index', f'saves/x{suffix}'], cwd=ROOT)
                self.assertEqual(ignored.returncode, 0, f'{suffix} is not ignored by .gitignore')


if __name__ == '__main__':
    unittest.main()
