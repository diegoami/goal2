"""[designed: owner, 2026-11-02, T147] The packaged smoke, on Windows, of a build unpacked from its ZIP (docs/packaging.md).

    python smoke.py --zip ZIP --at DIR --cache DIR --source DIR --reference-python PY --reference-engine PYPY --out FILE

The ZIP is unpacked into --at (the workflow names a folder with spaces and a non-ASCII letter) and its one top folder
is the build's root. Every child of the packaged runtime runs with a bare environment: PATH holds only Windows' own
folders (no Python, no Git; checked), no PYTHONPATH, and its working directory is outside the source tree. The checks:
1. `goal2.cmd --help` (through cmd.exe) exits 0.
2. The bundled `pypy\\pypy.exe` answers as PyPy 3.11; with the launcher's environment, started (as a worker is) in the
   CPython's site-packages, it imports goal2 from its own site-packages and cannot import PySide6.
3. One watched match (smoke_match.py) played by the bundled CPython with the launcher's environment, its worker under
   the bundled PyPy, equals the same match played from the source tree (--source on PYTHONPATH, --reference-python with
   --reference-engine as its worker); it uses the original files in --cache, outside the build.
Also recorded, not checked: whether a worker started from pythonw.exe (as the desktop starts it) gets a console window,
under pypy.exe and under pypyw.exe. The result (every check and timing) goes to --out; the exit status is 1 when a
check fails.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import goal2_launch  # noqa: E402

PROBE = "import platform,sys;print(platform.python_implementation(),*sys.version_info[:2])"
KEPT = ("SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "TEMP", "TMP", "USERPROFILE", "APPDATA", "LOCALAPPDATA",
        "HOMEDRIVE", "HOMEPATH", "NUMBER_OF_PROCESSORS", "PROCESSOR_ARCHITECTURE", "OS", "SYSTEMDRIVE",
        "PROGRAMDATA", "PUBLIC", "USERNAME", "COMPUTERNAME")
CONSOLE_PROBE = r"""
import subprocess, sys, pathlib
out = pathlib.Path(sys.argv[1])
child = "import ctypes,sys;open(sys.argv[1],'w').write(str(ctypes.windll.kernel32.GetConsoleWindow()))"
for exe in sys.argv[2:]:
    name = pathlib.Path(exe).name
    with open(out / (name + '.err'), 'wb') as err:
        subprocess.run([exe, '-c', child, str(out / (name + '.hwnd'))], stdin=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL, stderr=err, timeout=120)
"""


def bare_environment() -> dict:
    system = os.environ.get("SYSTEMROOT", r"C:\Windows")
    env = {k: os.environ[k] for k in os.environ if k.upper() in KEPT}
    env["PATH"] = os.pathsep.join([str(Path(system) / "System32"), system, str(Path(system) / "System32" / "Wbem")])
    env["PYTHONUTF8"] = "1"
    return env


def run(argv, **kw):
    started = time.monotonic()
    r = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace", **kw)
    return r, round(time.monotonic() - started, 1)


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    for name in ("--zip", "--at", "--cache", "--source", "--reference-python", "--reference-engine", "--out"):
        p.add_argument(name, type=Path, required=True)
    args = p.parse_args(argv)
    at = args.at.resolve()
    with zipfile.ZipFile(args.zip) as zf:
        tops = {n.split("/", 1)[0] for n in zf.namelist()}
        if len(tops) != 1:
            raise SystemExit(f"{args.zip}: expected one top folder, found {sorted(tops)}")
        zf.extractall(at)
    root = at / tops.pop()
    env = bare_environment()
    launched = goal2_launch.environment(root, env)
    work = Path(tempfile.mkdtemp(prefix="work ", dir=at))
    result = {"root": str(root), "work": str(work), "checks": {}}
    checks = result["checks"]
    found = {tool: shutil.which(tool, path=env["PATH"]) for tool in ("python", "python3", "py", "pypy", "git")}
    result["path"] = env["PATH"]
    checks["no_python_or_git_on_path"] = {"pass": not any(found.values()), "found": found}

    # 1. the launcher's --help, through cmd.exe as a player's double-click or console would start it
    comspec = env.get("COMSPEC", r"C:\Windows\System32\cmd.exe")
    r, s = run(f'"{comspec}" /d /s /c ""{root / "goal2.cmd"}" --help"', cwd=work, env=env)
    checks["launcher_help"] = {"pass": r.returncode == 0, "exit": r.returncode, "s": s,
                               "help_text_seen": "goal2 desktop" in r.stdout, "stderr": r.stderr[-2000:]}

    # 2. the bundled PyPy
    pypy = root / "pypy" / "pypy.exe"
    r, _ = run([str(pypy), "-c", PROBE], cwd=work, env=env)
    site = root / "python" / "Lib" / "site-packages"
    g, _ = run([str(pypy), "-c", "import goal2;print(goal2.__file__)"], cwd=site, env=launched)
    q, _ = run([str(pypy), "-c", "import PySide6"], cwd=site, env=launched)
    goal2_at = Path(g.stdout.strip()).resolve() if g.returncode == 0 else None
    checks["pypy"] = {"pass": r.stdout.strip() == "PyPy 3 11" and goal2_at is not None
                      and root / "pypy" / "Lib" / "site-packages" in goal2_at.parents and q.returncode != 0,
                      "answers": r.stdout.strip(), "goal2": str(goal2_at), "pyside6_import_exit": q.returncode,
                      "stderr": (r.stderr + g.stderr)[-2000:]}

    # 3. one watched match, packaged and from the source tree
    match = work / "smoke_match.py"          # a copy: nothing of the source tree beside the packaged run's script
    shutil.copy2(HERE / "smoke_match.py", match)
    packaged, reference = work / "packaged.json", work / "reference.json"
    r, s = run([str(root / "python" / "python.exe"), str(match), "--cache", str(args.cache.resolve()),
                "--out", str(packaged), "--expect-root", str(root)], cwd=work, env=launched)
    ref_env = dict(os.environ, PYTHONPATH=str(args.source.resolve()), GOAL2_ENGINE_PYTHON=str(args.reference_engine))
    f, fs = run([str(args.reference_python), str(match), "--cache", str(args.cache.resolve()), "--out", str(reference)],
                cwd=args.source, env=ref_env)
    a = json.loads(packaged.read_text()) if r.returncode == 0 and packaged.is_file() else None
    b = json.loads(reference.read_text()) if f.returncode == 0 and reference.is_file() else None
    keys = ("outcome_sha256", "events_sha256", "result_sha256", "score", "seeds", "engine_year", "events")
    checks["match"] = {"pass": bool(a and b) and all(a[k] == b[k] for k in keys), "packaged": a, "reference": b,
                       "packaged_s": s, "reference_s": fs,
                       "stderr": (r.stderr[-2000:] if a is None else "") + (f.stderr[-2000:] if b is None else "")}

    # recorded only: does a worker started from pythonw.exe get a console window?
    probe = work / "console"
    probe.mkdir()
    script = work / "console_probe.py"
    script.write_text(CONSOLE_PROBE)
    run([str(root / "python" / "pythonw.exe"), str(script), str(probe), str(pypy), str(root / "pypy" / "pypyw.exe")],
        cwd=work, env=launched, timeout=300)
    console = {}
    for exe in ("pypy.exe", "pypyw.exe"):
        hwnd = probe / (exe + ".hwnd")
        console[exe] = (int(hwnd.read_text()) != 0) if hwnd.is_file() else f"no answer: {(probe / (exe + '.err')).read_text(errors='replace')[-500:] if (probe / (exe + '.err')).is_file() else ''}"
    result["worker_console_window"] = console

    result["pass"] = all(c["pass"] for c in checks.values())
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    for name, c in checks.items():
        print(f"{'PASS' if c['pass'] else 'FAIL'} {name}: {json.dumps({k: v for k, v in c.items() if k != 'pass'})[:1500]}")
    print(f"worker console window from pythonw.exe: {console}")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
