"""Time one watched match in the E021 harness: delay 20 only vs delay 20 + E032's removable display set.
Reads PR 243's tree (extracted, read-only) and the E011 watchstart savestate by path; writes nothing but stdout."""
import hashlib, json, sys, time
from pathlib import Path
A = Path(sys.argv[1])
SAV = Path(sys.argv[2])
sys.path.insert(0, str(A / "experiments/E021-m0-whole-match"))
sys.path.insert(0, str(A / "experiments/E032-match-engine-inventory"))
sys.path.insert(0, str(A / "runtime/emul"))
from check import draws_digest
from timing import set_delay_at_kickoff
from watched_match import WatchedMatch
data = SAV.read_bytes()
assert hashlib.sha256(data).hexdigest().startswith("d68e48c734a742a6")
SET = "0791:8F10,0791:9079,0791:0481,0791:1829,0791:0425,0791:0441,0791:94E8,0791:9372".split(",")
for seed in [int(s, 0) for s in sys.argv[3].split(",")]:
    for mode in ("delay20", "delay20+skip"):
        t0 = time.process_time(); w0 = time.time()
        m = WatchedMatch(data)
        t_load = time.process_time() - t0
        m.set_seed(seed)
        set_delay_at_kickoff(m, 20)
        if mode.endswith("skip"):
            for a in SET:
                m.hook(a, lambda g: None)
        m.run(timeout_s=150)
        cpu = time.process_time() - t0
        print(json.dumps({"seed": hex(seed), "mode": mode, "load_cpu_s": round(t_load, 2),
                          "cpu_s": round(cpu, 1), "wall_s": round(time.time() - w0, 1),
                          "board": m.stopped_at_board, "score": m.state()["score"],
                          "ticks": len(m.tick_marks), "digest": draws_digest(m.draws)[:12]}), flush=True)
