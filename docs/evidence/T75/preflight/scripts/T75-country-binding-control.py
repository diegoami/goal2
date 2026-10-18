from pathlib import Path
import runpy,sys
from unittest.mock import patch
root=Path.cwd();sys.path[:0]=[str(root),str(root/'tools/desktop-ui')]
from goal2.desktop.window import ManagementWindow
sys.argv=[str(root/'tools/desktop-ui/country-selection.py'),'--template','.cache/e010-r0008-halftime.sav','--data','.cache/GOAL.DAT']
with patch.object(ManagementWindow,'display_model',property(lambda self:self.model)):
 runpy.run_path(sys.argv[0],run_name='__main__')
