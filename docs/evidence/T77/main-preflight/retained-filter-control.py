"""[designed: T77] Planning-only runtime mutant; retained acceptance must detect state corruption."""
from pathlib import Path
import sys
ROOT=Path.cwd();sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tools/desktop-ui'))
from goal2.desktop.window import ManagementWindow
original=ManagementWindow.refresh_pool
def corrupt(self):
 original(self)
 if self.search.text():self.model.state.rng_seed_7b62=(self.model.state.rng_seed_7b62+1)&65535
ManagementWindow.refresh_pool=corrupt
try:
 from acceptance import pool
 pool(ROOT/'.cache/e010-r0008-halftime.sav',ROOT/'.cache/GOAL.DAT')
finally:ManagementWindow.refresh_pool=original
