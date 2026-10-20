# Where artifacts live

[designed: owner, 2026-10-20] Keep everything the project needs in the repository, so a fresh
clone (a cloud session included) has it. CLAUDE.md rule 19 draws the one line this public
repository cannot cross.

| What | Where |
| --- | --- |
| The rebuild's own outputs: measurements, proofs, screenshots of the rebuild, reports, generated fixtures that hold no original byte | **Committed** in the repository (`measurements/`, `docs/`, test fixtures) |
| The same, when a file is over ~50 MB | A **GitHub release** of `diegoami/goal2` (`gh release upload <tag> <file>`), linked from the doc that uses it |
| The original game's bytes: `GOAL.DAT` and other GOAL2 assets, executables, DOSBox-X savestates (`*.sav`), rebuild saves that embed them (`*.g2save`) | The owner's **private Google Drive folder**, pulled into `.cache/` |

The original game's bytes stay out of git and out of public releases because this repository and
its releases are public and the game is copyrighted (U17/U21); `tools/check_premerge.py` refuses
tracked files with those extensions.

## The Google Drive folder

Configured in `harness.json`:

```json
"artifacts": {
  "localDir": ".cache",
  "drive": { "folderUrl": "<the folder's share link>", "rcloneRemote": "<remote>:<path>" }
}
```

- To download by hand: open `folderUrl` and save the files into `.cache/`.
- With [rclone](https://rclone.org) (`rclone config`, a remote of type `drive`, once per machine):
  `python3 tools/artifacts.py pull` copies the folder into `.cache/`; `pull GOAL.DAT` one file;
  `push .cache/<file>` uploads one; `where` prints the configured location.
- In a cloud session, configure rclone from a token kept in the environment (never committed), or
  pull by hand and upload into the session.
