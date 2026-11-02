#!/usr/bin/env python3
"""[designed: T156] Client of server.py: one request per call.
    python3 client.py RUN key KEYSYM [LABEL] [TIMEOUT]   one key; read until the screen changes and two reads agree, or TIMEOUT s
    python3 client.py RUN wait SECS [LABEL]              one timed wait, then one read
    python3 client.py RUN launch [LABEL] [FILE ...]      start the original (files the game wrote, copied into its folder)
    python3 client.py RUN copyout NAME | ls | alive | terminate | exit
Prints the logged step and the 80x25 screen (M=1 also prints the highlight marks)."""
import json, socket, sys
run, cmd, *a = sys.argv[1:]
req = {"cmd": cmd}
if cmd == "key":
    req["key"] = a[0]
    if len(a) > 1 and a[1]: req["label"] = a[1]
    if len(a) > 2: req["timeout"] = float(a[2])
elif cmd == "wait":
    req["secs"] = float(a[0])
    if len(a) > 1: req["label"] = a[1]
elif cmd == "launch":
    if a: req["label"] = a[0]
    req["gl"] = a[1:]
elif cmd == "copyout":
    req["name"] = a[0]
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.connect(run + "/ctl.sock")
s.sendall(json.dumps(req).encode() + b"\n")
data = b""
while not data.endswith(b"\n"):
    ch = s.recv(1 << 20)
    if not ch: break
    data += ch
r = json.loads(data)
scr = r.pop("screen", None)
marks = r.pop("marks", None)
r.pop("tb", None) if "error" not in r else None
r.pop("font",None); r.pop("utc",None); r.pop("sav_sha256",None); r.pop("png_sha256",None)
print(json.dumps({k: (v[:8] if isinstance(v, str) and len(v) == 64 else v) for k, v in r.items()}, ensure_ascii=False))
if scr:
    lines = scr.splitlines()
    for i, l in enumerate(lines):
        import os; m = ((marks or {}).get(str(i)) or (marks or {}).get(i)) if os.environ.get("M") else None
        print(f"{i:2d}|{l}" + (f"\n  |{m}" if m else ""))
