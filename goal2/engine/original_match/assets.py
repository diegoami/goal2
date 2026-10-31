"""The reference image, fetched by hash (no original bytes here).

The kit runs on any image of the original outside a match; its check (check.py) runs on one image named by its
SHA-256: E006-r0001, the main screen of a new game managing Denmark, a DOSBox-X savestate on release E006 of the
private repository goal2-archaeology. It is the file goal2 already fetches for its P1 measurement
(goal2 tools/measure_p1.py, E006_R0001_SHA), so goal2 needs no new asset. Its players and countries equal
E011-r0001's start state (E033 notes, section 2), so E011-r0001's recorded match is the check's reference."""
import hashlib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

REPO = "diegoami/goal2-archaeology"
REFERENCE = {"release": "E006", "asset": "e0afff6751747233-e006-1000-r0001.sav",
             "sha256": "e0afff6751747233f6ab8b9ba73dab0790b7509f15257ed7ae24f528b935657d"}


class AssetError(RuntimeError):
    pass


def check_cache(cache_dir):
    """The cache the way reference_image uses it, without the download (fileopts.PathError otherwise): the reference there
    is a readable regular file, or it is missing and the cache folder can be created and written (the download writes
    there). What this does not check, because it needs the run: the file's SHA-256, `gh` and the network."""
    import fileopts
    path = str(Path(cache_dir) / REFERENCE["asset"])
    if os.path.lexists(path):
        fileopts.check_input(path, "--cache")
    else:
        fileopts.check_log_output(path, "--cache")


def reference_image(cache_dir=".cache"):
    """The reference savestate's bytes: from cache_dir if there, else downloaded with the GitHub CLI (`gh`,
    authenticated for the private repository); always checked against its SHA-256."""
    check_cache(cache_dir)
    cache = Path(cache_dir)
    path = cache / REFERENCE["asset"]
    if not path.is_file():
        cache.mkdir(parents=True, exist_ok=True)
        cmd = ["gh", "release", "download", REFERENCE["release"], "--repo", REPO, "--pattern", REFERENCE["asset"]]
        with tempfile.TemporaryDirectory(dir=cache) as tmp:
            try:
                subprocess.run(cmd + ["--dir", tmp], check=True, capture_output=True)
            except (OSError, subprocess.CalledProcessError) as e:
                raise AssetError(f"cannot download {REFERENCE['asset']} ({e}); run: {' '.join(cmd)} --dir {cache}") from e
            shutil.move(str(Path(tmp) / REFERENCE["asset"]), str(path))
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != REFERENCE["sha256"]:
        raise AssetError(f"{path}: its SHA-256 is not {REFERENCE['sha256']}; remove it and fetch it again")
    return data
