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

[The folder](https://drive.google.com/drive/folders/12fgdrQUQB4pHdq0ibY-NP-aU8jgNaRzc) is private
to the owner. Its location is in `artifacts.json`:

```json
{ "localDir": ".cache",
  "drive": { "folderUrl": "https://drive.google.com/drive/folders/12fgdrQUQB4pHdq0ibY-NP-aU8jgNaRzc",
             "rcloneRemote": "goal2drive:" } }
```

- By hand: open the folder and save the files into `.cache/`.
- With [rclone](https://rclone.org), once per machine (a browser login; the remote sees only this
  folder):
  `rclone config create goal2drive drive scope=drive root_folder_id=12fgdrQUQB4pHdq0ibY-NP-aU8jgNaRzc`.
  Then `python3 tools/artifacts.py pull` copies the folder into `.cache/`, `pull GOAL.DAT` one
  file, `push .cache/<file>` uploads one, and `where` prints the location.
- In a cloud session: run `rclone config create` there with `config_token=<token>` taken from a
  configured machine (`rclone config show goal2drive`), kept in a secret, never committed; or pull
  by hand and upload into the session.
