"""[designed: T62] Pinned, ignored verification inputs; never an application caller."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "3656a2d26e0f57a410d648edeaa6cd9eb7d1f607"
IMAGES = {
    "e0afff6751747233-e006-1000-r0001.sav": "e0afff6751747233f6ab8b9ba73dab0790b7509f15257ed7ae24f528b935657d",
    "3789d8490d2b42d8-e006-2100-r0005.sav": "3789d8490d2b42d8a589fec2afeb51de0ace4b4c5d1e5e24ff232321874dd106",
}


def archaeology():
    from check_provenance import _archaeology
    return _archaeology()


def source_bytes(path):
    return subprocess.check_output(["git", "show", f"{SOURCE}:{path}"], cwd=archaeology())


def verify_vendor():
    manifest = json.loads((ROOT / "tools/watched-kit-hashes.json").read_text())
    if manifest["source"] != SOURCE:
        raise ValueError("kit manifest source pin differs")
    actual = {p.relative_to(ROOT).as_posix() for p in (ROOT / "goal2/engine/original_match").rglob("*")
              if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}
    if actual != set(manifest["files"]):
        raise ValueError("kit file set differs from accepted source")
    for rel, digest in manifest["files"].items():
        raw = source_bytes("runtime/original_match/" + Path(rel).name)
        if hashlib.sha256(raw).hexdigest() != digest or (ROOT / rel).read_bytes() != raw:
            raise ValueError(f"vendored kit differs from accepted source: {rel}")
    return len(actual)


def stage(cache=None):
    """[designed] Export exact upstream verification sources to ignored cache, never alter upstream."""
    verify_vendor()
    subprocess.run(["git", "merge-base", "--is-ancestor", SOURCE, "origin/main"], cwd=archaeology(), check=True)
    cache = Path(cache or ROOT / ".cache")
    folder = cache / ("watched-evidence-" + SOURCE[:12])
    paths = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", SOURCE], cwd=archaeology(), text=True).splitlines()
    exact = {"tests/test_original_match.py", "tests/mutations_original_match.py",
             "experiments/E032-match-engine-inventory/compare.py", "experiments/E032-match-engine-inventory/record_schema.py",
             "experiments/E032-match-engine-inventory/out/timing-delay20-kickoff-20261015.jsonl",
             "experiments/E032-match-engine-inventory/out/timing-delay20-8seeds-20261015.jsonl",
             "experiments/E021-m0-whole-match/out/20261011T201945897620Z-none-E011-r0001.json"}
    for rel in paths:
        wanted = (rel in exact or rel.startswith("runtime/original_match/")
                  or rel.startswith(("runtime/emul/", "runtime/driver/")) and rel.endswith(".py")
                  or rel.startswith("experiments/E033-original-match-kit/") and rel.endswith(".py")
                  or rel.startswith("static/goal-exe/code/seg_000E_") and rel.endswith(".asm"))
        if wanted:
            target = folder / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            raw = source_bytes(rel)
            if not target.exists() or target.read_bytes() != raw:
                target.write_bytes(raw)
    for name, sha in IMAGES.items():
        origin = cache / name
        if not origin.is_file():
            raise FileNotFoundError(f"missing verified image {origin}; supply E006 asset {name} (SHA-256 {sha})")
        if hashlib.sha256(origin.read_bytes()).hexdigest() != sha:
            raise ValueError(f"image hash mismatch: {origin}; expected {sha}")
        target = folder / ".cache/dl" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest() != sha:
            shutil.copyfile(origin, target)
    return folder
