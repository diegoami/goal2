# Closing the gap: why the rebuilt window does not yet read as GOAL2

[designed: owner, 2026-11-08; T205, #666] The screens, flow and keys of [this design](README.md)
were approved (#526) and are built (`goal2/ui/`, T162–T191). Its palette and font are read from the
original's own captures. The owner's report is that the result is close and something is always
off. This document says what, with measurements taken from the **window as built**, records the
decisions that follow, and points at the backlog that carries the work.

It changes **how the approved screens are drawn**, never what they show or which key does what.

Contents:
1. [What it is measured against](#1-what-it-is-measured-against)
2. [The diagnosis](#2-the-diagnosis)
3. [The decisions](#3-the-decisions-owner-2026-11-08)
4. [The proposal, and what it does not reach](#4-the-proposal-and-what-it-does-not-reach)
5. [The backlog](#5-the-backlog)
6. [What is not reopened](#6-what-is-not-reopened)
7. [Method, so the numbers can be checked](#7-method-so-the-numbers-can-be-checked)

## 1. What it is measured against

Three sets of pixels, and this document is careful about which is which.

| | |
| --- | --- |
| **The original** | `docs/original-game/images/`, with [provenance](../../original-game/image-provenance.tsv). Shown at 4:3 wherever it is compared, because that is how it was seen. |
| **The window as built** | the renders each UI task leaves in `T1*-screens/` — `T178-screens/s06-desk.png`, `T165-screens/s08-squad.png`, `T167-screens/s15-match-menu.png`, `fix-583-screens/s17-pitch.png`. Its code is `goal2/ui/`, its look `goal2/ui/theme.py` and `start_look.py`. |
| **The proposal** | [`proposal/`](proposal/README.md), six screens redrawn with the grammar below. |

The mockups in `images/` are the design's own pictures and are **not** the subject: the window
exists, so the subject is the window. Where this document quotes a number it names which set it
came from.

## 2. The diagnosis

[designed: T209] Every number of this section is measured on the window as built on 2026-11-08, before the decisions of §3 were
built (`CELL = 16`, `TEXT = 24`, `HEADING_SIZE = 32`, `BIG`, `HUGE`, a uniform 1440×900 page). The rules it leads to are
stated in [README.md §3](README.md#3-rules-for-the-whole-ui).

§3's rule is "the original's palette and a blocky font, on a modern layout", from the owner's words
in #526. The palette and the font are right. What is missing is the part that rule sets aside:
**GOAL2's character is in its layout grammar, not in its colours or its typeface.** Four causes.

### 2.1 Text is large, but the page is larger

The original is a strict **80 × 25** character grid: an 8×16 cell on 640×400. The window's
`goal2/ui/theme.py` has `CELL = 16`, `TEXT = 24` and `HEADING_SIZE = 32` — the owner's playtest
#598 already raised the normal text from 16 px to 24 px, superseding §3's earlier
whole-cell-multiple rule. At 1440×900 that is **90 columns** at the 16 px cell, and about **37
lines** at a 24 px line box — against the original's 80 columns and 25 rows. The two numbers come
from different bases, which is the point: the line box is not a whole cell, so nothing sits on a
grid boundary.

The remaining step is small and it is the one that matters: **32 px on a 16 × 32 cell**, which is
90 × 28 — the original's grid, doubled.

### 2.2 Half the ink, and dead regions

Mean luminance over a 4×4 tiling of each screen (the share of non-black ink per region), measured
with the command in [§7](#7-method-so-the-numbers-can-be-checked):

| Screen | mean | min tile | tiles under 1.5 % |
| --- | --- | --- | --- |
| original hub, `manager-menu.png` | **6.02** | 1.83 | **0** |
| the window today, `T178-screens/s06-desk.png` | 3.84 | 0.00 | **5** |
| the proposal, `proposal/images/s06-hub.png` | 4.07 | 1.94 | **0** |
| original squad, `m244-squad.png` | **10.21** | 1.97 | **0** |
| the window today, `T165-screens/s08-squad.png` | 5.38 | 0.87 | **4** |
| the proposal, `proposal/images/s08-squad.png` | 6.52 | 2.81 | **0** |

The original is about 93 % black too: density is not about filling space, it is that the ink is
spread evenly over the whole frame. That holds of the management screens these two rows were measured
from, not of every original screen. [designed: main, 2026-11-09; correction of this section's first draft,
which said "every region of every original screen carries ink" after measuring two screens] Over all 135
screens of `docs/original-game/images`, 57 have a tile under 1.5 % and 13 have one at 0.00 % (dos-shell,
file-not-found-prompt, title-player-count, title-load-prompt, the two load-name prompts, round-playing and
the bracket, table and results screens). Among the management screens `fixtures-watch.png` bottoms out at
1.50 % and `match-menu.png` at 0.28 %. The 1.5 % floor is therefore the hub's and the squad's; a rebuilt
screen whose original is sparse the same way is judged against its own counterpart (§5's mapping), not
against the floor. **One** of the built desk's sixteen regions carries no ink at
all and **five** are under 1.5 %; the original's emptiest region is 1.83 %.
[original-presentation-cues.md](../original-presentation-cues.md) already names "large unused
areas" as a sign to inspect; this is the number behind it.

### 2.3 Hierarchy by size instead of by colour

The original has **exactly one text size everywhere**: every glyph on every screen is the same 8×16
cell. Its hierarchy comes from colour (brown labels, white values, cyan headings, magenta hints,
yellow names — §3's palette table already has the meanings), from the frame a thing sits in, and
from position.

Where the original wants something visually large, it draws **line-art, not larger type**: the GOAL
wordmark, the stencil "Fixtures" title, the vertical "Tactics", the giant match clock.

The window scales the bitmap font instead. `start_look.py` defines three sizes above the text:
`theme.HEADING_SIZE` (32 px, used by `#bigValue`, `#story` and the rest), `BIG` (48 px, the
bulletin's `#masthead` and `#bulletinTitle`) and `HUGE` (64 px, the title's `#titleBrand`). Large
type in a bitmap face is the strongest signal that a screen is a web page.

### 2.4 Frames versus cards

The original's frame is a 1 px rule with the label **sitting on the rule**, lowercase, brown or
red, the rule continuing as dashes to the panel's edge:

```
-name---------  -rating-------
 E Go           unknown
-team---------  -managers-----
 Italy           1 E Go
-rankings-----   2
 World  :  3     3
```

Frames nest and touch; there is no padding and no fill. The window draws bordered cards with an
uppercase cyan heading inside at the top left. That one substitution changes the personality of
every management screen.

### 2.5 Where the window already does it right

[docs/current-game](../../current-game/README.md) (T204, #664) pictures the **shipped** window,
the one `goal2/ui/` replaces. On several screens it is closer to the original than either the mockups
or the new window: skill bars drawn as discrete cells, the role code in a right-hand column with
the name coloured by line, lowercase route labels, the pitch key line in the original's own joined
form. Those belong in the new window; this backlog keeps them rather than letting them be lost.

## 3. The decisions (owner, 2026-11-08)

1. **Fidelity target: the original's grammar at 2×.** Keep the approved screen list, flow and keys;
   draw them on a **16 × 32 cell**, a **90 × 28 grid**, with one text size, rule-and-label frames,
   dash leaders, line-art titles and no dead region. This supersedes the owner's #598 (24 px / 32 px)
   in the same direction it already went.
2. **Presentation: 4:3, as DOSBox shows it.** The logical page is stretched 1.2 vertically, so
   boxes, letters and the pitch have the proportions the game had on a CRT. A 90 × 28 page of
   16 × 32 cells is 1440 × 896, which the stretch takes to 1440 × 1075 — half a per cent short of
   an exact 4:3 1440 × 1080, so a window letterboxes the remainder rather than stretching the cell
   unevenly.

### A caveat for anyone measuring the captures

[docs/original-game/README.md](../../original-game/README.md) records that the renderer uses an
**8-pixel** text cell while DOSBox-X displays the same text at **9 pixels**. So a proportion taken
from a capture is both 20 % too short (square pixels, decision 2) and, in character widths,
narrower than it was on screen. Both corrections apply before a capture's geometry is copied.

## 4. The proposal, and what it does not reach

[`proposal/`](proposal/README.md) draws six screens with the whole grammar, each beside its
original capture and the window as built. It is a picture of a design, not app code; nothing in
`goal2/` changes.

It is honest about its limit. On the measure that matters most it succeeds — **no region under
1.5 % on either screen**, against five and four today, and its emptiest region (1.94 % on the desk,
2.81 % on the squad) is above the original's own (1.83 %, 1.97 %).

On raw density it closes much less: **24 % of the squad's gap** (5.38 → 6.52 against the original's
10.21) and **11 % of the desk's** (3.84 → 4.07 against 6.02). Six screens drawn by hand carry less
of the original's incidental content than the original does. The grammar is what is being proposed;
the rest of the density follows from applying it to every panel of every screen, which is
implementation work, not drawing work.

## 5. The backlog

The work is [#666](https://github.com/diegoami/goal2/issues/666) and its children: six foundation
issues (#667–#672), eight signature elements (#673–#680) and four defects found by the manual
(#681–#684). Nothing here is scheduled by this document; the issues carry the status (CLAUDE.md
rule 9).

**Two corrections the issues need**, because they were written before this document was grounded in
the built window:

1. #667 quotes the mockups' `font: 16px/1.35`. The live numbers are `goal2/ui/theme.py`'s
   `CELL = 16`, `TEXT = 24`, `HEADING_SIZE = 32`. The change is **24 → 32 on a 16 × 32 cell with
   one size only**, superseding #598.
2. Every issue's "Now" paragraph points at `mockups/style.css`. Each must point at `goal2/ui/`:
   `theme.py` and `start_look.py` for the look, the `sNN_*.py` modules for the screens.

**And a re-scope.** The six foundation issues were written as if nothing had been built. The window
exists, so #667–#671 are one change to `goal2/ui/theme.py` and the screen modules, not six
independent ones; they are better run as a single task with five acceptance lines than as five
tasks. The eight signature elements stay independent, and each is still a day's work or less.

## 6. What is not reopened

- The **screens, flow and keys** of [§1](README.md#1-the-players-journey),
  [§2](README.md#2-every-screen) and [§5](README.md#5-the-mapping-of-every-original-screen): the
  owner approved them (#526) and the mapping covers every original screen.
- The **Enter hint** at the right of the bottom bar (§3). #679 changes its form, not the fact that
  it says what Enter does now.
- Watching in the main window, no watch control, **R** for the quick result, hot-seat multi-manager,
  the first-start import, the save list, mouse parity and the keyboard rule: all as decided.
- The palette: §3's table is read from the captures by [palette.py](palette.py).
- The behaviour coverage of [manual-fidelity.md](manual-fidelity.md) (T191, #611): that audit asks
  whether each original action works, this document asks how the screens look. They do not overlap.

## 7. Method, so the numbers can be checked

**The ink table** (§2.2) — mean luminance of each tile of a 4×4 tiling:

```sh
magick docs/original-game/images/manager-menu.png -colorspace Gray \
    -crop 25x25% -format '%[fx:mean*100]\n' info:-
```

**The density check** (§2.2, T208, #672) — the same measure as a command, with no ImageMagick needed (the
PNG is decoded in Python). It takes screens or folders of them, prints the 4×4 table of each screen that has
a tile under the floor (default 1.5 %, `--floor` to override for a deliberate exception) and exits non-zero:

```sh
python3 docs/design/ui-2026-11/check_density.py docs/design/ui-2026-11/T178-screens/s06-desk.png
```

It agrees with the `magick` command above to 0.05 percentage points on a committed screen
(`goal2/tests/test_density_check_672.py`). [designed: owner, 2026-11-08] No gate runs it yet; #667 wires the
floor into the UI tasks' Done-when lines, per screen: the default floor for a screen whose original clears it
(the hub, the squad), `--floor` lowered to the counterpart's own minimum for one that does not.

**The grid** (§2.1) — `goal2/ui/theme.py`'s `CELL`, `TEXT` and `HEADING_SIZE`, and the row pitch of
a list measured from the horizontal projection of its column.

**The palette** (§3's table in README.md) — `python3 docs/design/ui-2026-11/palette.py`, unchanged.

**The screens** — the original's are `docs/original-game/images/` with their provenance; the
window's are the `T1*-screens/` folders; the proposal's are rebuilt by
`python3 docs/design/ui-2026-11/proposal/build.py`; the shipped window's are
`docs/current-game/images/` with `check_manual.py` over their hashes.
