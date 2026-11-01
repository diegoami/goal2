"""[designed: owner, 2026-11-02, T147] The portable Windows build: a folder `goal2-<version>-win64/` and its ZIP.

    python tools/build_portable.py build --wheel dist/goal2-<version>-py3-none-any.whl [--downloads DIR] [--out DIR] [--stats FILE]
    python tools/build_portable.py check-zip ZIP [--originals DIR]

The folder (docs/packaging.md):
- `python/`: the official embeddable CPython 3.13, its `._pth` file listing `Lib\\site-packages` and running
  `import site`, with the desktop, watched and match-view extras (tools/portable/requirements-win64.txt) and goal2
  from its wheel installed there.
- `pypy/`: the PyPy 3.11 Windows release, with goal2 from the same wheel in its own `Lib\\site-packages` (the match
  workers import only goal2's pure-Python modules) and the CPython's `vcruntime140*.dll` beside `pypy.exe`, which
  imports `VCRUNTIME140.dll` but does not ship it (a DLL missing only on a clean machine, T147's hazard).
- `goal2.cmd` and `goal2_launch.py` (tools/portable/): the launcher.
- `portable-files.json`: every file of the folder and where it came from (cpython, pypy, wheels, goal2, launcher).

Every download is pinned by version and SHA-256 (tools/portable/manifest.json; the wheels by pip --require-hashes),
and a file whose SHA-256 differs is refused. Nothing of the original game may ship (CLAUDE.md rule 14): a file with an
original-game file type (check_premerge.FORBIDDEN, the extensions the workflows refuse to upload) is accepted only
from the pinned third-party downloads (the interpreters' .exe files, Qt's .dat files), never from goal2's wheel or
the launcher, and no file may be absent from the record. check-zip applies the same rules to the ZIP and, with
--originals, refuses an entry whose bytes equal any original-game file found there (the workflow's `.cache/`).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import tomllib
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
PORTABLE = ROOT / "tools" / "portable"
MANIFEST = PORTABLE / "manifest.json"
LAUNCHER = ("goal2.cmd", "goal2_launch.py")
RECORD = "portable-files.json"
THIRD_PARTY = {"cpython", "pypy", "wheels"}
VCRUNTIME = ("vcruntime140.dll", "vcruntime140_1.dll")
sys.path.insert(0, str(ROOT / "tools"))
from check_premerge import FORBIDDEN  # noqa: E402


class BuildError(RuntimeError):
    """The build refuses its inputs or its result."""


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def version() -> str:
    return tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]


def fetch(entry: dict, downloads: Path) -> Path:
    """The manifest entry's file in `downloads`, downloaded when absent; refused (and removed) when its SHA-256 is not
    the manifest's."""
    downloads.mkdir(parents=True, exist_ok=True)
    path = downloads / entry["url"].rsplit("/", 1)[1]
    if not path.is_file():
        part = path.with_name(path.name + ".part")
        with urllib.request.urlopen(entry["url"]) as response, open(part, "wb") as out:
            shutil.copyfileobj(response, out)
        part.replace(path)
    digest = sha256(path)
    if digest != entry["sha256"]:
        path.unlink()
        raise BuildError(f"{path.name}: SHA-256 {digest} is not the manifest's {entry['sha256']}; refused")
    return path


def extract(archive: Path, dest: Path, strip: str = "") -> None:
    """Every file of `archive` under `strip`, into `dest` without that prefix."""
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            if not info.filename.startswith(strip):
                raise BuildError(f"{archive.name}: {info.filename} is outside {strip!r}")
            rel = PurePosixPath(info.filename[len(strip):])
            if rel.is_absolute() or ".." in rel.parts or not rel.parts:
                raise BuildError(f"{archive.name}: unsafe member {info.filename}")
            target = dest.joinpath(*rel.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)


def enable_site_packages(python: Path) -> Path:
    """The embeddable CPython's `._pth`: its entries kept, `Lib\\site-packages` added, `import site` on."""
    pth = sorted(python.glob("python3*._pth"))
    if len(pth) != 1:
        raise BuildError(f"expected one python3*._pth in {python}, found {[p.name for p in pth]}")
    lines = [l.strip() for l in pth[0].read_text().splitlines()]
    entries = [l for l in lines if l and not l.startswith("#") and l != "import site"]
    if "Lib\\site-packages" not in entries:
        entries.append("Lib\\site-packages")
    pth[0].write_bytes(("\r\n".join(entries + ["import site"]) + "\r\n").encode())
    return pth[0]


def requirements_hashed(path: Path) -> list[str]:
    """The requirement lines of `path`; refused unless each pins one version with a SHA-256."""
    lines = [l.strip() for l in path.read_text().splitlines() if l.strip() and not l.lstrip().startswith("#")]
    for line in lines:
        name, _, rest = line.partition(" ")
        if "==" not in name or "--hash=sha256:" not in rest:
            raise BuildError(f"{path.name}: {line!r} is not pinned by version and SHA-256")
    if not lines:
        raise BuildError(f"{path.name}: no requirements")
    return lines


def pip_wheels(python: str, target: Path, requirements: Path, wheels: dict, compile_: bool) -> list[str]:
    """pip installing the pinned wheels for the bundled CPython into `target` (hash-checked, no resolution)."""
    return [python, "-m", "pip", "install", "--disable-pip-version-check", "--no-input", "--target", str(target),
            "--no-deps", "--only-binary", ":all:", "--platform", wheels["platform"],
            "--python-version", wheels["python_version"], "--implementation", wheels["implementation"],
            "--abi", wheels["abi"], "--require-hashes", "-r", str(requirements)] + ([] if compile_ else ["--no-compile"])


def pip_goal2(python: str, target: Path, wheel: Path, compile_: bool) -> list[str]:
    """pip installing goal2's own wheel (built from this checkout) into `target`, offline."""
    return [python, "-m", "pip", "install", "--disable-pip-version-check", "--no-input", "--target", str(target),
            "--no-deps", "--no-index", str(wheel)] + ([] if compile_ else ["--no-compile"])


def files_of(folder: Path) -> set[str]:
    return {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()}


def check_files(files: dict[str, str], where: str) -> None:
    """Refuse an original-game file type that does not come from a pinned third-party download."""
    bad = sorted(f"{rel} (from {src})" for rel, src in files.items()
                 if PurePosixPath(rel).suffix.lower() in FORBIDDEN and src not in THIRD_PARTY)
    if bad:
        raise BuildError(f"{where}: original-game file type outside the pinned downloads: {', '.join(bad)}")


def check_folder(folder: Path) -> dict:
    """The folder's record, after checking that it lists exactly the folder's files and passes check_files."""
    record = json.loads((folder / RECORD).read_text())
    actual = files_of(folder) - {RECORD}
    listed = set(record["files"])
    if actual != listed:
        raise BuildError(f"{folder.name}: files outside the record: {sorted(actual - listed)[:10]}; "
                         f"recorded but missing: {sorted(listed - actual)[:10]}")
    check_files(record["files"], folder.name)
    return record


def build(out: Path, wheel: Path, downloads: Path, manifest_path: Path = MANIFEST, run=subprocess.run,
          python: str = sys.executable, name: str | None = None) -> tuple[Path, Path, dict]:
    """Lay out the folder from the manifest's downloads and `wheel`, check it, zip it: (folder, zip, stats)."""
    started = time.monotonic()
    manifest = json.loads(manifest_path.read_text())
    name = name or f"goal2-{version()}-win64"
    folder = out / name
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    sources: dict[str, str] = {}

    def step(source: str, action) -> None:
        before = files_of(folder)
        action()
        for rel in files_of(folder) - before:
            sources[rel] = source

    cpython, pypy = (fetch(manifest[k], downloads) for k in ("cpython", "pypy"))
    step("cpython", lambda: extract(cpython, folder / "python", manifest["cpython"]["strip"]))
    enable_site_packages(folder / "python")
    step("pypy", lambda: extract(pypy, folder / "pypy", manifest["pypy"]["strip"]))
    for dll in VCRUNTIME:
        if (folder / "python" / dll).is_file() and not (folder / "pypy" / dll).exists():
            step("cpython", lambda dll=dll: shutil.copy2(folder / "python" / dll, folder / "pypy" / dll))
    site = folder / "python" / "Lib" / "site-packages"
    pypy_site = folder / "pypy" / "Lib" / "site-packages"
    requirements = manifest_path.parent / manifest["wheels"]["requirements"]
    requirements_hashed(requirements)
    same = sys.version_info[:2] == tuple(int(x) for x in manifest["wheels"]["python_version"].split("."))

    def pip(argv):
        r = run(argv, check=False)
        if r.returncode != 0:
            raise BuildError(f"pip failed ({r.returncode}): {' '.join(argv)}")
    step("wheels", lambda: pip(pip_wheels(python, site, requirements, manifest["wheels"], same)))
    step("goal2", lambda: pip(pip_goal2(python, site, wheel, same)))
    step("goal2", lambda: pip(pip_goal2(python, pypy_site, wheel, False)))
    for target in (site, pypy_site):
        # pip --target puts console-script launchers (goal2's own `goal2`, PySide6's tools) in the target's
        # Scripts/ or bin/, bound to the building interpreter's path: useless in the folder, and goal2's would be an
        # .exe not from a pinned download. The launcher is goal2.cmd.
        for scripts in ("Scripts", "bin"):
            if (target / scripts).is_dir():
                for rel in [r for r in sources if r.startswith(f"{(target / scripts).relative_to(folder).as_posix()}/")]:
                    del sources[rel]
                shutil.rmtree(target / scripts)
    for launcher in LAUNCHER:
        text = (PORTABLE / launcher).read_text()
        if launcher.endswith(".cmd"):           # cmd.exe reads its batch files with CRLF line ends
            text = text.replace("\r\n", "\n").replace("\n", "\r\n")
        step("launcher", lambda t=text, n=launcher: (folder / n).write_bytes(t.encode()))
    record = {"name": name, "cpython": manifest["cpython"], "pypy": manifest["pypy"],
              "requirements": requirements_hashed(requirements), "goal2_wheel": wheel.name,
              "files": dict(sorted(sources.items()))}
    (folder / RECORD).write_text(json.dumps(record, indent=1) + "\n")
    check_folder(folder)
    archive = out / f"{name}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for rel in sorted(files_of(folder)):
            zf.write(folder / rel, f"{name}/{rel}")
    stats = {"name": name, "files": len(sources) + 1, "folder_bytes": sum((folder / r).stat().st_size for r in sources),
             "zip_bytes": archive.stat().st_size, "build_s": round(time.monotonic() - started, 1)}
    return folder, archive, stats


def originals_in(folder: Path) -> dict[tuple[int, str], str]:
    """(size, SHA-256) -> path of every original-game file type under `folder`."""
    found = {}
    for p in sorted(folder.rglob("*")):
        if p.is_file() and p.suffix.lower() in FORBIDDEN:
            found[(p.stat().st_size, sha256(p))] = str(p)
    return found


def check_zip(archive: Path, originals: Path | None = None) -> dict:
    """The ZIP's own checks: one top folder; exactly the recorded files; check_files; with `originals`, no entry whose
    bytes equal an original-game file there. Returns a summary."""
    with zipfile.ZipFile(archive) as zf:
        names = [i.filename for i in zf.infolist() if not i.is_dir()]
        tops = {n.split("/", 1)[0] for n in names}
        if len(tops) != 1:
            raise BuildError(f"{archive.name}: expected one top folder, found {sorted(tops)}")
        top = tops.pop()
        record = json.loads(zf.read(f"{top}/{RECORD}"))
        inside = {n[len(top) + 1:] for n in names} - {RECORD}
        if inside != set(record["files"]):
            raise BuildError(f"{archive.name}: entries outside the record: {sorted(inside - set(record['files']))[:10]}; "
                             f"recorded but missing: {sorted(set(record['files']) - inside)[:10]}")
        check_files(record["files"], archive.name)
        compared = 0
        if originals is not None:
            known = originals_in(originals)
            if not known:
                raise BuildError(f"no original-game file under {originals} to compare with")
            sizes = {size for size, _ in known}
            for info in zf.infolist():
                if info.is_dir() or info.file_size not in sizes:
                    continue
                h = hashlib.sha256(zf.read(info)).hexdigest()
                if (info.file_size, h) in known:
                    raise BuildError(f"{archive.name}: {info.filename} is the original-game file {known[(info.file_size, h)]}")
            compared = len(known)
    return {"entries": len(names), "originals_compared": compared,
            "forbidden_type_entries": sum(PurePosixPath(r).suffix.lower() in FORBIDDEN for r in record["files"])}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build")
    b.add_argument("--wheel", type=Path, required=True)
    b.add_argument("--downloads", type=Path, default=ROOT / ".cache" / "portable-downloads")
    b.add_argument("--out", type=Path, default=ROOT / "dist")
    b.add_argument("--stats", type=Path)
    c = sub.add_parser("check-zip")
    c.add_argument("zip", type=Path)
    c.add_argument("--originals", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            folder, archive, stats = build(args.out, args.wheel, args.downloads)
            print(f"built {folder} and {archive} ({stats['zip_bytes']} bytes, {stats['build_s']} s)", flush=True)
            if args.stats:
                args.stats.write_text(json.dumps(stats, indent=1) + "\n")
        else:
            print(f"PASS {args.zip.name}: {json.dumps(check_zip(args.zip, args.originals))}", flush=True)
    except BuildError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
