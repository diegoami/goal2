"""[designed: T158] Shared helpers of the throwaway technology probes (tools/tech_probe/README.md).

Every probe script inserts the repository root on sys.path itself, so it runs by path under any interpreter
(the portable's embeddable CPython ignores PYTHONPATH). Deleted with the rest of tools/tech_probe/ after the
owner's decision on #527.
"""
from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
PROBE = Path(__file__).resolve().parent
DESIGN = ROOT / "docs" / "design" / "ui-2026-11"
FONT = DESIGN / "mockups" / "fonts" / "PxPlus_IBM_VGA_8x16.ttf"
WINDOWS = os.name == "nt"


def windows_cpu_percent():
    """The whole PC's CPU load as Windows reports it (WSL shares the same CPUs), or None."""
    exe = "powershell.exe" if not WINDOWS else "powershell"
    try:
        r = subprocess.run([exe, "-NoProfile", "-Command",
                            "(Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average"],
                           capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
        return float(r.stdout.strip().replace(",", "."))
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def load():
    """The load at the moment of a measurement: Linux load averages (WSL) and the Windows CPU %."""
    out = {"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "windows_cpu_pct": windows_cpu_percent()}
    if hasattr(os, "getloadavg"):
        out["loadavg"] = [round(x, 2) for x in os.getloadavg()]
    else:
        try:
            r = subprocess.run(["wsl.exe", "-e", "cat", "/proc/loadavg"], capture_output=True, text=True, timeout=30)
            out["wsl_loadavg"] = [float(x) for x in r.stdout.split()[:3]]
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    return out


def interpreter():
    return f"{platform.python_implementation()} {platform.python_version()}"


def host():
    return {"os": platform.system(), "machine": platform.machine(), "cpus": os.cpu_count(),
            "release": platform.release()}


class Results:
    """One measurement file of measurements/T158: {"kind", "host", "interpreters", "records": [...]}, rewritten
    after every record so that a run that dies keeps what it measured. An existing file is extended."""
    def __init__(self, path, kind, **header):
        self.path = Path(path)
        if self.path.is_file():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            self.data = {"kind": kind, "host": host(), **header, "records": []}

    def add(self, record):
        self.data["records"].append(record)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, self.path)


def install_rust():
    """[designed: T158] goal2rust's hybrid on goal2's vendored kit. goal2rust imports the kit as the top-level
    package `original_match`; goal2 vendors it as goal2.engine.original_match (byte-identical at
    goal2-archaeology b519d999 apart from the fileopts move, whose port files equal goal2rust's pinned 2cbeb36f).
    The vendored modules are aliased under the kit's name, then goal2rust.install() replaces the port machine and
    runner in those same module objects. Returns the machine class now in use."""
    import importlib
    import pkgutil
    import goal2.engine.original_match as om
    # Every submodule first: one imported later under the kit's name would be a second copy with other classes.
    for info in pkgutil.walk_packages(om.__path__, om.__name__ + "."):
        if not info.name.rsplit(".", 1)[-1] in ("example", "check", "build"):
            importlib.import_module(info.name)
    for name in list(sys.modules):
        if name == "goal2.engine.original_match" or name.startswith("goal2.engine.original_match."):
            sys.modules.setdefault(name[len("goal2.engine."):], sys.modules[name])
    import goal2rust
    goal2rust.install()
    machine = om.port.engine.PortMachine
    if not machine.__module__.startswith("goal2rust"):
        raise RuntimeError(f"goal2rust did not install: the port machine is {machine.__module__}")
    return machine


def reference(cache):
    """The reference match of the packaged smoke (tools/portable/smoke_match.py): state, template, fixture."""
    from goal2.engine.original_match import Fixture
    from goal2.engine.original_match.assets import reference_image
    from goal2.game.state import from_savestate
    raw = reference_image(cache)
    state = from_savestate(raw)
    state.captain = 0
    return state, raw, Fixture(7, 19, 21)
