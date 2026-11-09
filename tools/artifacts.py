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


def pull_commands(cfg: dict, names: list[str]) -> list[list[str]]:
    """The rclone arguments a pull runs.

    A named pull copies each file to `localDir/<its own name>`. The source is the remote-joined
    path, and a drive remote ends with ':' ("goal2drive:NAME"), which holds no path separator, so
    the destination must come from the name the caller gave, never from the joined source: that is
    what left files called `.cache/goal2drive:NAME` behind (#683).
    """
    if not names:
        return [["copy", cfg["remote"], str(cfg["localDir"])]]
    return [["copyto", join(cfg["remote"], name), str(cfg["localDir"] / Path(name).name)]
            for name in names]


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
        for arguments in pull_commands(cfg, names):
            subprocess.run([exe, *arguments], check=True)
        return 0
    if not names:
        sys.exit("push needs at least one file")
    for name in names:
        subprocess.run([exe, "copyto", name, join(cfg["remote"], Path(name).name)], check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
