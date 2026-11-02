"""[designed: T156] Print which cells of a kept savestate's screen are highlighted (background differs
from the row's most common one): the text alone does not say which menu option is selected.
    python3 -I highlight.py RUN [STEP]      (the latest savestate in RUN/states when STEP is omitted)
Reads the archaeology engine clone's savestate parser, read only."""
import sys, glob
sys.dont_write_bytecode=True
sys.path.insert(0,'/home/diego/projects/goal2-archaeology-engine/runtime/driver')
import savestate
run = sys.argv[1]
n = sys.argv[2] if len(sys.argv) > 2 else sorted(glob.glob(f'{run}/states/*.sav'))[-1]
if n.isdigit(): n = f'{run}/states/{int(n):04d}.sav'
sc=savestate.Savestate(open(n,'rb').read()).screen()
for r in range(25):
    bg=[a>>4 for a in sc.attrs[r*80:(r+1)*80]]
    common=max(set(bg), key=bg.count)
    m=''.join('^' if b!=common else ' ' for b in bg)
    if m.strip(): print(r, sc.lines()[r]); print('  ', m)
