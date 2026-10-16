"""Count the basic blocks and code bytes one watched match executes in the E021 harness (seed 0x1234,
delay count 20 at kick-off), and the hottest blocks. Args: <PR 243 tree> <E011-r0001 watchstart .sav>.
Reads only; prints to stdout. The UC_HOOK_BLOCK observer slows the run about fourfold."""
import sys, time, collections
from pathlib import Path
A = Path(sys.argv[1]); SAV = Path(sys.argv[2])
for p in ("experiments/E021-m0-whole-match", "experiments/E032-match-engine-inventory", "runtime/emul"):
    sys.path.insert(0, str(A / p))
from timing import set_delay_at_kickoff
from watched_match import WatchedMatch
from unicorn import UC_HOOK_BLOCK
m = WatchedMatch(SAV.read_bytes()); m.set_seed(0x1234); set_delay_at_kickoff(m, 20)
cnt = collections.Counter(); ins = collections.Counter()
def blk(uc, addr, size, d):
    cnt[addr] += 1; ins[addr] += size
m.mu.hook_add(UC_HOOK_BLOCK, blk)
t = time.process_time(); m.run(timeout_s=900); print("cpu", round(time.process_time() - t, 1), m.state()["score"])
tot = sum(ins.values()); print("blocks", sum(cnt.values()), "bytes executed", tot)
load = m.load
def name(a):
    for seg in (0x791, 0x1771, 0x214B, 0x23E4, 0x000E):
        base = (load + seg) * 16
        if 0 <= a - base < 0x10000:
            return "%04X:%04X" % (seg, a - base)
    return hex(a)
for a, n in ins.most_common(15):
    print(name(a), "blocks", cnt[a], "bytes", n, "%.1f%%" % (100 * n / tot))
