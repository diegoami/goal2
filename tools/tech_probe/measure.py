"""[designed: T158] The toolkit candidates' start time, memory and portable size (T158 point 1 and 4).

    python measure.py ui --candidate NAME --runs 5 --out F [--settle 1.5] -- <the prototype's command>
    python measure.py capture --title TEXT --out PNG -- <the prototype's command>      (Windows)
    python measure.py sizes --portable DIR [--extra NAME=DIR ...] [--wheel NAME=FILE ...] --out F

ui: starts the prototype's command (with --quit-after appended) --runs times, one after the other. Each run
records the time from the start of the process to its `READY` line (the first frame on screen, as each
prototype reports it), the prototype's own READY figure (from its interpreter's start), and the memory of the
whole process tree (the prototype and every process it started: a browser or a web view's) --settle seconds
after READY: the sum of the resident sets and of the private (unique) sets. Needs psutil.

sizes: the bytes, on disk and deflated (zlib level 6, file by file, as a ZIP stores them), of every part of an
unpacked portable folder (docs/packaging.md): the CPython without its site-packages, each installed
distribution (from its RECORD), PyPy, and of any extra folder (pywebview installed with pip --target) or file
(goal2rust's wheel). summarize.py adds them up into what the ZIP becomes for each choice.
"""
from __future__ import annotations

import argparse
import csv
import subprocess
import sys
import time
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402


def tree_memory(pid):
    import psutil
    try:
        root = psutil.Process(pid)
        procs = [root] + root.children(recursive=True)
    except psutil.Error:
        return None
    rss = uss = 0
    names = []
    for p in procs:
        try:
            info = p.memory_full_info()
            rss += info.rss
            uss += getattr(info, "uss", 0)
            names.append(p.name())
        except psutil.Error:
            pass
    return {"rss_mb": round(rss / 2**20, 1), "uss_mb": round(uss / 2**20, 1), "processes": len(names),
            "names": sorted(set(names))}


def end_tree(process):
    import psutil
    try:
        root = psutil.Process(process.pid)
        procs = root.children(recursive=True) + [root]
    except psutil.Error:
        return
    for p in procs:
        try:
            p.kill()
        except psutil.Error:
            pass


def ui(args):
    out = common.Results(args.out, "ui-start-memory")
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    for run in range(1, args.runs + 1):
        load = common.load()
        started = time.perf_counter()
        process = subprocess.Popen(command + ["--quit-after", str(args.settle + 1.5)], stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, cwd=common.ROOT)
        record = {"candidate": args.candidate, "run": run, "load": load, "command": command}
        try:
            while True:
                line = process.stdout.readline()
                if not line:
                    raise RuntimeError("the prototype ended before READY: " + process.stderr.read()[-1500:])
                if line.startswith("READY"):
                    record["ready_s"] = round(time.perf_counter() - started, 4)
                    record["ready_own_s"] = float(line.split()[1])
                    break
            time.sleep(args.settle)
            record["memory"] = tree_memory(process.pid)
            process.wait(60)
        except Exception as exc:
            record["error"] = f"{type(exc).__name__}: {exc}"
        finally:
            if process.poll() is None:
                end_tree(process)
        out.add(record)
        print(args.candidate, run, record.get("ready_s"), record.get("memory", {}) and record["memory"].get("rss_mb"),
              record.get("error", ""), flush=True)
        time.sleep(1)


CAPTURE = r"""
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System; using System.Runtime.InteropServices;
public class W { [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out R r);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("dwmapi.dll")] public static extern int DwmGetWindowAttribute(IntPtr h, int a, out R r, int s);
  public struct R { public int L, T, Ri, B; } }
'@
$p = Get-Process | Where-Object { $_.MainWindowTitle -like '*TITLE*' } | Select-Object -First 1
if (-not $p) { Write-Error 'no window'; exit 2 }
$h = $p.MainWindowHandle
[W]::SetForegroundWindow($h) | Out-Null
Start-Sleep -Milliseconds 700
$r = New-Object W+R
[W]::DwmGetWindowAttribute($h, 9, [ref]$r, 16) | Out-Null
$b = New-Object System.Drawing.Bitmap ($r.Ri - $r.L), ($r.B - $r.T)
$g = [System.Drawing.Graphics]::FromImage($b)
$g.CopyFromScreen($r.L, $r.T, 0, 0, $b.Size)
$b.Save('OUT', [System.Drawing.Imaging.ImageFormat]::Png)
"""


def capture(args):
    """Windows: start the prototype, wait for its first frame, then take a picture of its window (found by its
    title) and keep only that window's rectangle, nothing else of the screen."""
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    process = subprocess.Popen(command + ["--quit-after", "8"], stdout=subprocess.PIPE, text=True, cwd=common.ROOT)
    try:
        while not process.stdout.readline().startswith("READY"):
            pass
        time.sleep(args.wait)
        script = CAPTURE.replace("TITLE", args.title).replace("OUT", str(Path(args.out).resolve()))
        r = subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True, text=True)
        print(r.stdout, r.stderr)
    finally:
        process.wait(30)


def deflated(path):
    data = Path(path).read_bytes()
    return len(data), len(zlib.compress(data, 6))


def group(name, files, root):
    size = packed = 0
    for f in files:
        a, b = deflated(f)
        size += a
        packed += b
    return {"group": name, "files": len(files), "bytes": size, "zip_bytes": packed, "root": str(root)}


def sizes(args):
    out = common.Results(args.out, "portable-sizes")
    portable = Path(args.portable)
    site = portable / "python" / "Lib" / "site-packages"
    claimed = set()
    for info in sorted(site.glob("*.dist-info")):
        name = info.name.split("-")[0].lower()
        files = []
        with (info / "RECORD").open(newline="", encoding="utf-8") as f:
            for row in csv.reader(f):
                p = (site / row[0]).resolve()
                if p.is_file() and p not in claimed:
                    files.append(p)
                    claimed.add(p)
        out.add(group(name, files, info))
    rest = [p for p in site.rglob("*") if p.is_file() and p.resolve() not in claimed]
    out.add(group("site-packages-other", rest, site))
    cpython = [p for p in (portable / "python").rglob("*") if p.is_file() and site not in p.parents]
    out.add(group("cpython", cpython, portable / "python"))
    out.add(group("pypy", [p for p in (portable / "pypy").rglob("*") if p.is_file()], portable / "pypy"))
    out.add(group("launcher", [p for p in portable.iterdir() if p.is_file()], portable))
    for spec in args.extra or []:
        name, folder = spec.split("=", 1)
        out.add(group(name, [p for p in Path(folder).rglob("*") if p.is_file() and "__pycache__" not in p.parts
                             and p.parent.name != "bin"], folder))
    for spec in args.wheel or []:
        name, file = spec.split("=", 1)
        import zipfile
        with zipfile.ZipFile(file) as z:
            size = sum(i.file_size for i in z.infolist())
            packed = sum(i.compress_size for i in z.infolist())
        out.add({"group": name, "files": len(z.infolist()), "bytes": size, "zip_bytes": packed, "root": file})


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="what", required=True)
    u = sub.add_parser("ui")
    u.add_argument("--candidate", required=True)
    u.add_argument("--runs", type=int, default=5)
    u.add_argument("--settle", type=float, default=1.5)
    u.add_argument("--out", required=True)
    u.add_argument("command", nargs=argparse.REMAINDER)
    c = sub.add_parser("capture")
    c.add_argument("--title", required=True)
    c.add_argument("--wait", type=float, default=1.0)
    c.add_argument("--out", required=True)
    c.add_argument("command", nargs=argparse.REMAINDER)
    s = sub.add_parser("sizes")
    s.add_argument("--portable", required=True)
    s.add_argument("--extra", action="append")
    s.add_argument("--wheel", action="append")
    s.add_argument("--out", required=True)
    args = parser.parse_args()
    {"ui": ui, "sizes": sizes, "capture": capture}[args.what](args)


if __name__ == "__main__":
    main()
