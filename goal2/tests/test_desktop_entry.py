"""[designed: T69] Optional dependency boundary and actionable startup refusal."""
import subprocess
import sys
import unittest

BLOCK="""
import importlib.abc,sys
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in ('PySide6','unicorn'):raise ImportError('blocked optional dependency')
sys.meta_path.insert(0,Block())
"""
class DesktopEntryCases(unittest.TestCase):
 def test_headless_model_imports_without_qt_or_unicorn(self):
  p=subprocess.run([sys.executable,'-c',BLOCK+'\nimport goal2.desktop.model\nassert not any(k.startswith(("PySide6","unicorn","goal2.web")) for k in sys.modules)'],capture_output=True,text=True)
  self.assertEqual(p.returncode,0,p.stderr)
 def test_missing_qt_reports_install_instruction_before_reading_assets(self):
  p=subprocess.run([sys.executable,'-c',BLOCK+'\nfrom goal2.desktop.__main__ import main\nraise SystemExit(main(["--template","missing.sav","--data","missing.dat"]))'],capture_output=True,text=True)
  self.assertEqual(p.returncode,2,p.stderr)
  self.assertIn('Install the desktop extra',p.stderr)
  self.assertNotIn('Traceback',p.stderr)

if __name__=='__main__':unittest.main()
