# How these screens were made

[designed: T176] The original's screens are rendered from DOSBox-X savestates
([the original's method](../original-game/capture-method.md)). The rebuild's are **grabs of its own
windows**: the real `QMainWindow`, built by the real model over the real game, drawn offscreen at
the fixed page's own 1440×900 and saved with `QWidget.grab()`. The pitch is the real pygame viewer,
saving its own post-flip surface. Nothing is mocked and no screen is drawn for the picture.

## The tool

[`tools/desktop-ui/manual-screens.py`](../../tools/desktop-ui/manual-screens.py) walks the build
and writes `images/` and `image-provenance.tsv`. It needs the desktop extra and the original files
in `.cache/` ([docs/artifacts.md](../artifacts.md)):

```sh
python3 -m venv .venv && . .venv/bin/activate
python3 -m pip install '.[desktop,match-view,watched]'
python3 tools/artifacts.py pull GOAL.DAT e039-r0005-date-call.sav e010-r0008-halftime.sav e006-r0001-main.sav
```

Then, one route per run (the provenance table merges the runs):

```sh
# the player's own route: the import dialog, Launch, the original's new game, a whole round
python3 tools/desktop-ui/manual-screens.py --data .cache/GOAL.DAT \
    --core-boot .cache/e039-r0005-date-call.sav --round --import-dialog \
    --out docs/current-game/images

# the same round, watched, so the pitch window saves its own frames into ../pitch-frames
python3 tools/desktop-ui/manual-screens.py --data .cache/GOAL.DAT \
    --core-boot .cache/e039-r0005-date-call.sav --round --pitch \
    --out docs/current-game/images

# the two script routes
python3 tools/desktop-ui/manual-screens.py --data .cache/GOAL.DAT \
    --template .cache/e010-r0008-halftime.sav --core .cache/e006-r0001-main.sav \
    --out docs/current-game/images
```

`QT_QPA_PLATFORM` defaults to `offscreen` and `--pitch` sets `SDL_VIDEODRIVER=dummy`, so a run
needs no display. A run takes minutes, not seconds: `--core-boot` makes the original play its own
new game, and `--round` makes it play a match.

## How a screen is reached

Each capture drives the window the way a player does, and records it:

- A **destination** is `window.navigate(i)`, which is what the side bar's button and `Ctrl+<i>` do.
- A **view** of a destination is its `QStackedWidget` (T101: a page never scrolls, so a part that
  does not fit is a view reached by a route). The capture walks every view by name.
- A **round** is *Play next game*, then the action each screen advertises, as a player pressing
  Enter does: `Q` at the captain (the original's quick result) unless `--pitch` asked for a watched
  match, *Start second half* at half time, *Next* through the pages.
- The **pitch** is the shipped viewer with one line changed from outside: `pygame.display.flip` also
  saves the surface, every 150th frame. The renderer, the font and the pixels are the build's own.

A screen the capture cannot reach is **reported, not invented**: the run prints it and
[the inventory](screen-inventory.md) lists it under "not captured" with the reason.

## Provenance

`image-provenance.tsv` has one row per image:

| column | meaning |
| --- | --- |
| `screen` | the name used in this manual |
| `image` | the path under this folder |
| `route` | `first start`, `boot`, `core` or `template` (see the [README](README.md)) |
| `reached` | the action that opened it |
| `png_sha256` | the SHA-256 of the committed PNG |

[`check_manual.py`](check_manual.py) exits 0 only when every row's image is there with that hash,
every PNG has a row, and every screen is written up in the inventory. Run it after a re-capture:
the hashes change whenever the build's drawing changes, which is the point.

## What the images are not

They are 1440×900, the fixed page's design size. The window scales the whole page to other sizes
(T101), so a screen at another size looks the same, smaller or larger; `window-small` is the one
example of that, at 900×640. Font rendering is Linux's; a Windows grab of the same screen differs
in its glyph shapes and spacing.
