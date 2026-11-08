# goal2 as it is today: the build's own manual

[designed: owner, 2026-11-08; T176] The original has a manual with its screens
([docs/original-game](../original-game/README.md)). This is the rebuild's half of that pair: what
goal2 shows **today**, screen by screen, grabbed from the real windows. It exists so that the look
of the rebuild can be compared with the original by reading, instead of by running the game again
each time.

It is a record, not a design. Nothing here argues that a screen is right or wrong; where the build
differs from the original the row says what the difference is and points at the original's own
chapter. The design goal2 is being rebuilt towards is
[docs/design/ui-2026-11](../design/ui-2026-11/README.md), and the build below is what that design
replaces (its §4 lists what it keeps, changes and drops).

| | |
| --- | --- |
| [The flow](flow.md) | the player's journey through the build, screen by screen |
| [The screen inventory](screen-inventory.md) | every screen: what it shows, its keys, the original screen it stands for |
| [The match](match.md) | the pitch window, the stops the match makes and the boards |
| [The capture method](capture-method.md) | how the 60 images were made, and how to make them again |
| [`images/`](images) | the screens, 1440×900 |
| [`image-provenance.tsv`](image-provenance.tsv) | one row per image: the route, how it was reached, the PNG's SHA-256 |

Every image is the rebuild's own pixels. No original byte is in this folder (CLAUDE.md rule 14):
the savestates and `GOAL.DAT` the capture reads stay in the git-ignored `.cache/`.

## What the build is, in one paragraph

goal2 today is a PySide6 window of five destinations — *Country*, *Team*, *Pool*,
*Fixtures & match*, *Save* — reached from a side bar, over one of two games: **the core route**,
where the original's own game runs under Unicorn and every value is read from its memory
(`goal2/desktop/core_model.py`, [docs/core.md](../core.md)), and **the `--template` route**, where
goal2's own Python game plays friendlies from a savestate (`goal2/desktop/model.py`). A player who
installs the portable build gets the core route: the import dialog, then a Launch window, then that
main window. The watched match is **not** in the main window; it is a separate pygame window
(`goal2/desktop/pygame_viewer.py`), opened by *SHOW MATCH (F8)*.

## The three routes, and which one a player sees

| Route | Command | Who sees it | Screens here |
| --- | --- | --- | --- |
| **The player's** | `python3 -m goal2.desktop` (no flags) | anyone who installs the build; it imports the data folder, then boots the original's own new game (`--core-boot`) | `import-*`, `boot-*`, `match-pitch-*` |
| **The core, resumed** | `python3 -m goal2.desktop --core <state> --data GOAL.DAT` | scripts and development, from a mid-career savestate | `core-*` |
| **The Python game** | `python3 -m goal2.desktop --template <state> --data GOAL.DAT` | scripts and development; friendlies only | `template-*`, `window-*` |

The first two open the same window over the same model, so a `core-*` screen and a `boot-*` screen
of the same name differ only in the career they show. The `--template` route has a **different**
window (`goal2/desktop/window.py` against `core_window.py`) with its own Country, Team, Pool and
Fixtures pages; both are in the inventory, because both ship.

## What this manual does not cover

- **Windows.** Every image was grabbed on Linux, offscreen. The build also runs on Windows, where
  Qt and SDL draw with the system's own fonts and scaling; nothing here measures that.
- **The bot and a whole season.** The capture plays one round. Stage changes, the finals draw, the
  year's end and the elimination screens are not in these images.
- **Anything the capture could not reach.** Those are listed at the end of
  [the screen inventory](screen-inventory.md) with the reason, never filled in from memory.
