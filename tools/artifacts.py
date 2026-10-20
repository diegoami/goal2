#!/usr/bin/env python3
"""[designed: owner, 2026-10-20] Original-game files live in the owner's private Google Drive folder
(CLAUDE.md rule 14, docs/artifacts.md), never in this public repository or its releases.

    python3 tools/artifacts.py where            the folder's link and the rclone remote
    python3 tools/artifacts.py pull [NAME...]   copy the folder (or NAMEs in it) into .cache/
    python3 tools/artifacts.py push FILE...     upload local files to the folder

The location is artifacts.json; transfers use rclone (https://rclone.org), with a
remote the owner configured once (`rclone config`, type drive).
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def settings() -> dict:
    block = json.loads((ROOT / "artifacts.json").read_text())
    return {"folderUrl": block.get("drive", {}).get("folderUrl", ""),
            "remote": block.get("drive", {}).get("rcloneRemote", ""),
            "localDir": ROOT / block.get("localDir", ".cache")}


def join(remote: str, name: str) -> str:
    return f"{remote}{name}" if remote.endswith(":") else f"{remote}/{name}"


def rclone(cfg: dict) -> str:
    exe = shutil.which("rclone")
    if not exe or not cfg["remote"]:
        sys.exit("rclone and artifacts.json drive.rcloneRemote are needed for transfers; "
                 f"download by hand from {cfg['folderUrl'] or '(no folderUrl set yet)'} into {cfg['localDir']}")
    return exe


def main(argv: list[str]) -> int:
    cfg = settings()
    if not argv or argv[0] not in {"where", "pull", "push"}:
        print(__doc__)
        return 2
    command, names = argv[0], argv[1:]
    if command == "where":
        print(f"folder: {cfg['folderUrl'] or '(not set: artifacts.json drive.folderUrl)'}")
        print(f"rclone remote: {cfg['remote'] or '(not set)'}\nlocal: {cfg['localDir']}")
        return 0
    exe = rclone(cfg)
    cfg["localDir"].mkdir(parents=True, exist_ok=True)
    if command == "pull":
        sources = [join(cfg["remote"], n) for n in names] or [cfg["remote"]]
        for src in sources:
            dest = cfg["localDir"] if not names else cfg["localDir"] / Path(src).name
            subprocess.run([exe, "copy" if not names else "copyto", src, str(dest)], check=True)
        return 0
    if not names:
        sys.exit("push needs at least one file")
    for name in names:
        subprocess.run([exe, "copyto", name, join(cfg["remote"], Path(name).name)], check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
