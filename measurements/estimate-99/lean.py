"""Lean variant: no seed-write recording, the keypressed thunk 214B:0723 patched natively (mov al,0; retf)
instead of a Python hook. Compare score, ticks, final seed word and board statistics with the stock run
(the statistics compared by a hash taken within one process). Args: <PR 243 tree> <watchstart .sav> <seeds>."""
import sys, time, json
from pathlib import Path
A = Path(sys.argv[1]); SAV = Path(sys.argv[2])
for p in ("experiments/E021-m0-whole-match", "experiments/E032-match-engine-inventory", "runtime/emul"):
    sys.path.insert(0, str(A / p))
from timing import set_delay_at_kickoff
from watched_match import WatchedMatch
from unicorn import UC_HOOK_MEM_WRITE, UC_HOOK_CODE
data = SAV.read_bytes()
def run(seed, lean, delay=20):
    t0 = time.process_time()
    m = WatchedMatch(data); m.set_seed(seed)
    if delay is not None:
        set_delay_at_kickoff(m, delay)
    if lean:
        kp = m.lin("214B:0723")
        orig = m.mu.hook_add
        def hook_add(kind, cb, *a, **k):
            if kind == UC_HOOK_MEM_WRITE:
                return None
            if kind == UC_HOOK_CODE and k.get("begin") == kp:
                return None
            return orig(kind, cb, *a, **k)
        m.mu.hook_add = hook_add
        m.mu.mem_write(kp, bytes([0xB0, 0x00, 0xCB]))
    m.run(timeout_s=150)
    cpu = time.process_time() - t0
    st = m.statistics()
    return {"seed": hex(seed), "lean": lean, "cpu_s": round(cpu, 1), "board": m.stopped_at_board,
            "score": m.state()["score"], "ticks": len(m.tick_marks), "seed_end": hex(m.rd(0x7B62)),
            "stats": hash(json.dumps(st, sort_keys=True, default=str))}
for s in sys.argv[3].split(","):
    a, b = run(int(s, 0), False), run(int(s, 0), True)
    print(json.dumps(a)); print(json.dumps(b))
    print("same:", all(a[k] == b[k] for k in ("score", "ticks", "seed_end", "stats", "board")), flush=True)
