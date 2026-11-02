#!/usr/bin/env python3
"""[designed: T156] Capture server for the uninterrupted T156 run of the original GOAL2.

    python3 -I server.py RUN          (RUN under /tmp, e.g. /tmp/goal2-t156-run1; then client.py RUN ...)

One original GOAL2 under goal2-archaeology's E031 PlayDriver (DOSBox-X 2024.03.01, a private Xvfb display
the driver picks, never :99, raw XTEST keys, mapper-nohost.map, cycles=fixed 8000), imported read only from
the archaeology engine clone; nothing is written there (sys.dont_write_bytecode). The game folder, savestates,
renders and log live under RUN. Each request is ONE key or ONE timed wait; its step records the digest of the
last screen read before it, the digest of the read after it, the savestate's sha256 (the savestate kept in
RUN/states, never committed), the PNG rendered from that savestate by the clone's tools/screens/render.py
(RUN/png) and its sha256. measurements/T156/build.py turns RUN/steps.jsonl into the committed log."""
import sys
sys.dont_write_bytecode = True
import hashlib, json, os, shutil, socket, time
from pathlib import Path

ENGINE = Path("/home/diego/projects/goal2-archaeology-engine")
E031 = ENGINE / "experiments" / "E031-play-the-game"
sys.path.insert(0, str(E031))
sys.path.insert(0, str(ENGINE / "tools" / "screens"))
import play  # noqa: E402  (PlayDriver, progress, marks; module import writes nothing)
import driver  # noqa: E402
import render  # noqa: E402

RUN = Path(sys.argv[1]).resolve()
SOCK = RUN / "ctl.sock"
MAPPER = E031 / "mapper-nohost.map"


def sha(b):
    return hashlib.sha256(b).hexdigest()


class S:
    def __init__(self):
        for d in ("states", "png", "text"):
            (RUN / d).mkdir(parents=True, exist_ok=True)
        self.logp = RUN / "steps.jsonl"
        self.n = sum(1 for _ in self.logp.open()) if self.logp.exists() else 0
        self.d = None
        self.cur = None

    def record(self, label, action, before, state, blob, changed, extra=None):
        sc = state.screen()
        dg = sc.digest()
        pngb, font = render.render_savestate(state)
        step = self.n
        (RUN / "states" / f"{step:04d}.sav").write_bytes(blob)
        (RUN / "png" / f"{step:04d}.png").write_bytes(pngb)
        (RUN / "text" / f"{step:04d}.txt").write_text(sc.text())
        e = {"step": step, "label": label, "action": action, "before_digest": before,
             "text_digest": dg, "changed": changed, "sav_sha256": sha(blob), "png_sha256": sha(pngb),
             "bottom": sc.lines()[24].rstrip(), "font": font, "utc": driver.host_times()["utc"],
             "progress": play.progress(state), **(extra or {})}
        with self.logp.open("a", encoding="utf-8") as f:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
        self.n += 1
        self.cur = dg
        return {**e, "screen": sc.text(), "marks": play.marks(sc)}

    def read(self):
        _, state, blob = self.d.read()
        return state, blob

    def handle(self, req):
        cmd = req["cmd"]
        if cmd == "launch":
            gl = [Path(p) for p in req.get("gl", [])]
            self.d = play.PlayDriver({"cycles": "fixed 8000"}, workdir=RUN / "work", game_dir=RUN / "work" / "game",
                                     gl=gl, mapper=str(MAPPER), keys="raw")
            self.d.launch(None)
            state, blob = self.read()
            return self.record(req.get("label", "launch"), "launch" + (" with " + ",".join(
                f"{p.name} sha256 {sha(p.read_bytes())}" for p in gl) if gl else ""), None, state, blob, None,
                {"display": self.d.display})
        if cmd == "key":
            before = self.cur
            self.d.keys(req["key"], hold=driver.KEY_HOLD)
            timeout = req.get("timeout", 8)
            end = time.monotonic() + timeout
            last = None
            reads = 0
            while True:
                state, blob = self.read()
                reads += 1
                dg = state.screen().digest()
                if req.get("noset"):
                    break
                if dg != before and dg == last:
                    break
                if time.monotonic() > end:
                    break
                last = dg
            return self.record(req.get("label", "key " + req["key"]), "key " + req["key"], before, state, blob,
                               dg != before, {"reads": reads})
        if cmd == "wait":
            before = self.cur
            time.sleep(req["secs"])
            state, blob = self.read()
            dg = state.screen().digest()
            return self.record(req.get("label", "wait"), f"wait {req['secs']}s", before, state, blob, dg != before)
        if cmd == "copyout":  # copy a file the game wrote (a .GL) out of the game folder
            src = RUN / "work" / "game" / req["name"]
            dst = RUN / "saves" / req["name"]
            dst.parent.mkdir(exist_ok=True)
            shutil.copy(src, dst)
            return {"copied": str(dst), "sha256": sha(dst.read_bytes())}
        if cmd == "ls":
            return {"files": sorted(p.name for p in (RUN / "work" / "game").iterdir())}
        if cmd == "alive":
            return {"alive": self.d is not None and self.d.dbx is not None and self.d.dbx.poll() is None,
                    "rc": None if self.d is None or self.d.dbx is None else self.d.dbx.poll()}
        if cmd == "terminate":
            self.d.terminate()
            self.d = None
            return {"terminated": True}
        if cmd == "exit":
            if self.d:
                self.d.terminate()
            return {"exit": True}
        raise ValueError(cmd)


def main():
    s = S()
    if SOCK.exists():
        SOCK.unlink()
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(str(SOCK))
    srv.listen(1)
    print("serving", SOCK, flush=True)
    while True:
        c, _ = srv.accept()
        data = b""
        while not data.endswith(b"\n"):
            chunk = c.recv(65536)
            if not chunk:
                break
            data += chunk
        try:
            req = json.loads(data)
            out = s.handle(req)
        except Exception as e:  # noqa: BLE001
            import traceback
            out = {"error": repr(e), "tb": traceback.format_exc()}
        c.sendall(json.dumps(out, ensure_ascii=False).encode() + b"\n")
        c.close()
        if req.get("cmd") == "exit":
            break


if __name__ == "__main__":
    main()
