"""[designed: owner, 2026-10-29, T149] A registry of long background jobs, so work can stop and resume.

    python3 tools/jobs.py start <name> [--cwd DIR] -- <command> [args...]
    python3 tools/jobs.py list
    python3 tools/jobs.py wait <name> [--timeout S]
    python3 tools/jobs.py tail <name> [-n LINES]

`start` runs the command detached from the session (it outlives it), its output in
`.cache/jobs/<name>.log`. The record `.cache/jobs/<name>.json` holds the name, command, working
directory, git head, start time and the wrapper's PID; the wrapper writes the command's PID to
`<name>.pids.json` and `<name>.exit.json` (exit code, end time) when the command ends. Each file
has one writer. `list` shows each job as running,
finished (with its exit code) or vanished (its wrapper is gone with no exit record: killed, or the
machine restarted). `wait` waits by PID, never by `pgrep -f` (CLAUDE.md rule 11a). A running name
cannot be started again; a finished or vanished one is kept as `<name>.<start>.json` and replaced.
The environment is never recorded; a secret passed on the command line is refused. POSIX only
(Linux, WSL, macOS): it detaches with setsid and reads process state from /proc.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")
SECRET = re.compile(r"(TOKEN|SECRET|PASSWORD|PASSWD|API_?KEY)[A-Z_]*=|--(token|password|secret)\b", re.I)


class JobError(ValueError):
    """A request the registry refuses."""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def folder(root: Path) -> Path:
    return root / ".cache" / "jobs"


def alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    # A finished child that nobody reaped yet is not running.
    try:
        with open(f"/proc/{pid}/stat") as f:
            return f.read().rsplit(")", 1)[1].split()[0] != "Z"
    except OSError:
        return True


def read(root: Path, name: str) -> dict | None:
    path = folder(root) / f"{name}.json"
    if not path.exists():
        return None
    job = json.loads(path.read_text())
    pids = folder(root) / f"{name}.pids.json"
    if pids.exists():
        job.update(json.loads(pids.read_text()))
    done = folder(root) / f"{name}.exit.json"
    if done.exists():
        job.update(json.loads(done.read_text()), state="finished")
    elif alive(job.get("wrapper_pid")):
        job["state"] = "running"
    else:
        job["state"] = "vanished"
    return job


def jobs(root: Path) -> list[dict]:
    # Only <name>.json: exit, PID and kept older records all have a '.' in their stem.
    names = sorted(p.stem for p in folder(root).glob("*.json") if NAME.match(p.stem))
    return [job for job in (read(root, n) for n in names) if job is not None]


def head(cwd: Path) -> str | None:
    r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=cwd, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def start(root: Path, name: str, command: list[str], cwd: Path | None = None) -> dict:
    if not NAME.match(name):
        raise JobError(f"job name {name!r}: letters, digits, '_', '-' only")
    if not command:
        raise JobError("no command given (put it after --)")
    if any(SECRET.search(arg) for arg in command):
        raise JobError("the command line holds a secret; pass it in the environment, which is never recorded")
    cwd = (cwd or root).resolve()
    jobs_dir = folder(root);jobs_dir.mkdir(parents=True, exist_ok=True)
    old = read(root, name)
    if old is not None:
        if old["state"] == "running":
            raise JobError(f"job {name} is running (PID {old.get('command_pid') or old['wrapper_pid']})")
        stamp = re.sub(r"[^0-9]", "", old["started_utc"])
        for suffix in (".json", ".pids.json", ".exit.json", ".log"):
            path = jobs_dir / f"{name}{suffix}"
            if path.exists():
                path.rename(jobs_dir / f"{name}.{stamp}{suffix}")
    job = dict(name=name, command=command, cwd=str(cwd), head=head(cwd), started_utc=now(),
               log=str(jobs_dir / f"{name}.log"), wrapper_pid=None)
    write(jobs_dir / f"{name}.json", job)
    argv = [sys.executable, str(Path(__file__).resolve()), "_run", str(root), name]
    try:
        # posix_spawn, not Popen: nothing in this process waits for the detached wrapper.
        quiet = [(os.POSIX_SPAWN_OPEN, fd, os.devnull, os.O_RDWR, 0) for fd in (0, 1, 2)]
        job["wrapper_pid"] = os.posix_spawn(sys.executable, argv, os.environ, file_actions=quiet, setsid=True)
    except NotImplementedError:
        # [designed: #495] uv's Pythons (python-build-standalone) are built without spawn's setsid; Popen's
        # fork/exec detaches the same way, and its object is dropped unwaited like the spawned PID.
        job["wrapper_pid"] = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                              stderr=subprocess.DEVNULL, start_new_session=True).pid
    write(jobs_dir / f"{name}.json", job)
    return job


def write(path: Path, value: dict) -> None:
    tmp = path.with_name(path.name + ".tmp");tmp.write_text(json.dumps(value, indent=2));tmp.replace(path)


def run(root: Path, name: str) -> int:
    """The detached wrapper: run the command, then record how it ended."""
    job = json.loads((folder(root) / f"{name}.json").read_text())
    with open(job["log"], "ab") as log:
        try:
            child = subprocess.Popen(job["command"], cwd=job["cwd"], stdin=subprocess.DEVNULL,
                                     stdout=log, stderr=subprocess.STDOUT)
        except OSError as error:
            log.write(f"jobs.py: could not start: {error}\n".encode());code = 127
        else:
            write(folder(root) / f"{name}.pids.json", dict(command_pid=child.pid))
            code = child.wait()
    write(folder(root) / f"{name}.exit.json", dict(exit_code=code, ended_utc=now()))
    return code


def wait(root: Path, name: str, timeout: float | None = None, poll: float = 5.0) -> dict:
    job = read(root, name)
    if job is None:
        raise JobError(f"no job {name}")
    deadline = None if timeout is None else time.monotonic() + timeout
    while job["state"] == "running":
        if deadline is not None and time.monotonic() > deadline:
            raise TimeoutError(f"job {name} still running after {timeout} s")
        time.sleep(poll)
        job = read(root, name)
    return job


def describe(job: dict) -> str:
    state = job["state"]
    if state == "finished":
        state += f" exit {job['exit_code']} at {job['ended_utc']}"
    elif state == "running":
        state += f" PID {job.get('command_pid') or job.get('wrapper_pid')}"
    return (f"{job['name']}: {state}; started {job['started_utc']} at {(job.get('head') or '?')[:12]} "
            f"in {job['cwd']}; log {job['log']}; command {' '.join(job['command'])}")


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["_run"]:
        return run(Path(argv[1]), argv[2])
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("start");p.add_argument("name");p.add_argument("--cwd", type=Path)
    sub.add_parser("list")
    p = sub.add_parser("wait");p.add_argument("name");p.add_argument("--timeout", type=float)
    p = sub.add_parser("tail");p.add_argument("name");p.add_argument("-n", type=int, default=20)
    # The command is everything after the first "--", split off before argparse sees it: a
    # REMAINDER positional would also swallow the options given before it (--cwd).
    command = argv[argv.index("--") + 1:] if "--" in argv else []
    args = parser.parse_args(argv[:argv.index("--")] if "--" in argv else argv)
    try:
        if args.action == "start":
            print(describe({**start(args.root, args.name, command, args.cwd), "state": "running"}))
        elif args.action == "list":
            found = jobs(args.root)
            print("\n".join(describe(j) for j in found) if found else "no jobs")
        elif args.action == "wait":
            job = wait(args.root, args.name, args.timeout)
            print(describe(job))
            return 0 if job["state"] == "finished" and job["exit_code"] == 0 else 1
        else:
            job = read(args.root, args.name)
            if job is None:
                raise JobError(f"no job {args.name}")
            lines = Path(job["log"]).read_text(errors="replace").splitlines() if Path(job["log"]).exists() else []
            print("\n".join(lines[-args.n:]))
    except (JobError, TimeoutError) as error:
        print(f"jobs.py: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
