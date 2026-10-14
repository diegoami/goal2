"""The result screen: run the vendored engine, display score + goals, label as stand-in.

[confirmed: A-WATCH-1] The watched match is the quick engine's result shown
with commentary lines (goals, scorers, minutes), labelled a stand-in. T14 is
the **stand-in** result screen; the real watched engine (M1-M6) is a follow-up.

[confirmed: T01] `quick_engine.simulate(state)` returns a dict with `score`,
`goals`, and the two seed words (`seed_DS7B62`, `seed_DS8336`).

[designed: T14 screen layout] Default half-time replay: title row 0, score
row 2, goals from row 4, seed row, footer row 24. The default does not mutate
`state`. [designed: T26] Full-friendly mode uses the selected state, labels its
assumed setup and pages goals from both halves.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable

# Ensure the vendored engine's `import players` resolves to goal2/engine/players.py.
_ENGINE_DIR = str(Path(__file__).resolve().parents[1] / "engine")
if _ENGINE_DIR not in sys.path:
    sys.path.insert(0, _ENGINE_DIR)

from goal2.game.state import GameState
from goal2.game.quick_match import run_full_match
from goal2.engine.quick_engine import FoulPathNotModelled, ExtraTimeNotModelled
from goal2.engine import quick_engine as _qe
from goal2.engine.savestate import Savestate
from goal2.ui.grid import Grid, HEIGHT, WIDTH
from goal2.ui.input import Key, read_key
from goal2.ui.plain_renderer import render


# Colour constants: VGA palette (matches DS:0x720 in the original).
# 0 = black, 7 = white, 1 = blue.
_FG_NORMAL = 7
_BG_NORMAL = 0
_FG_TITLE  = 7
_BG_TITLE  = 1


def run_result(
    savestate_path_or_bytes: str | bytes,
    keys: Iterable[Key] | None,
    *,
    state: GameState | None = None,
    full_match: bool = False,
) -> bool:
    """Show the quick-engine result and return True on Enter, False on Esc.

    `savestate_path_or_bytes` is either a path to a DOSBox-X half-time
    savestate or the savestate bytes directly
    [confirmed: `goal2/engine/savestate.py::Savestate.__init__` accepts
    `path_or_bytes` — the zip is opened from a path or BytesIO].
    `keys` is an optional iterable of Key values (for scripted tests); when
    None the screen reads from stdin.
    [designed: T26] With `full_match=True`, `state` supplies the selected
    country, eleven and tactics for an assumed complete friendly. The default
    remains the seed-exact second-half replay path.

    Returns True on Enter (continue to next fixture), False on Esc.
    """
    # Load the savestate and run the engine.
    sav = Savestate(savestate_path_or_bytes)
    try:
        if full_match:
            if state is None:
                raise ValueError("full match requires adapted game state")
            result = run_full_match(sav, state)
        else:
            result = _qe.simulate(sav)
    except (FoulPathNotModelled, ExtraTimeNotModelled) as exc:
        result = None
        refusal_msg = str(exc)
    except ValueError as exc:
        if not full_match:
            raise
        result = None
        refusal_msg = str(exc)

    key_iter = iter(keys) if keys is not None else None
    page = 0

    while True:
        grid = _build_grid(result, refusal_msg if result is None else None,
                           full_match=full_match, page=page)

        if key_iter is not None:
            try:
                key = next(key_iter)
            except StopIteration:
                break
        else:
            # [designed: T23] Display and flush the current frame before input.
            print(render(grid), end="", flush=True)
            key = read_key()

        if key == Key.ENTER:
            return True
        elif key == Key.ESC:
            return False
        elif full_match and result is not None and key == Key.PAGE_DOWN:
            page = min(page + 1, max(0, (len(result["goals"]) - 1) // 16))
        elif full_match and key == Key.PAGE_UP:
            page = max(page - 1, 0)


def _build_grid(result: dict | None, refusal_msg: str | None,
                *, full_match: bool = False, page: int = 0) -> Grid:
    """Render the result screen into a Grid and return it.

    Row 0:     "RESULT  STAND-IN" (blue bg)
    Row 2:     "FINAL SCORE  H-A"  or  "REFUSED: <message>"
    Rows 4..:  goal rows  " MM  team T  scorer N"
               or (only in non-refusal path) "  no goals"
    Then:      seed words row
    Row 24:    "ENTER CONTINUE  ESC QUIT"
    """
    grid = Grid()

    # ── Title (row 0) ──────────────────────────────────────────────────────
    # [designed: T26] The interactive path states its assumed setup.
    title = "RESULT  ASSUMED FRIENDLY" if full_match else "RESULT  STAND-IN"
    grid.draw_text(0, 0, title.ljust(WIDTH), fg=_FG_TITLE, bg=_BG_TITLE)

    # ── Score / refusal row (row 2) ─────────────────────────────────────────
    if refusal_msg is not None:
        msg = f"REFUSED: {refusal_msg}"
        grid.draw_text(2, 0, msg.ljust(WIDTH), fg=_FG_NORMAL, bg=_BG_NORMAL)
        # In the refusal path, do not render goal rows or seed rows —
        # a refusal has no result to display. Only the title and footer
        # are shown (the footer is drawn below).
    elif result is not None:
        score = result["score"]
        score_text = f"FINAL SCORE  {score[0]}-{score[1]}"
        grid.draw_text(2, 0, score_text.ljust(WIDTH), fg=_FG_NORMAL, bg=_BG_NORMAL)

        # ── Goals rows (rows 4+) ───────────────────────────────────────────
        row = 4
        if result["goals"]:
            first_count = len(result["halves"][0]["goals"]) if full_match else 0
            # [designed: T26] Sixteen rows leave room for score, seeds,
            # page guidance and footer; PageDown exposes later goals.
            start = 16 * page if full_match else 0
            visible = result["goals"][start:start + 16] if full_match else result["goals"]
            if full_match:
                pages = max(1, (len(result["goals"]) + 15) // 16)
                grid.draw_text(3, 0, f"GOALS {page + 1}/{pages}  PGUP/PGDN".ljust(WIDTH))
            for i, goal in enumerate(visible, start):
                minute = goal["minute"]
                team = goal["team"]
                player_index = goal["player"]
                half = f" H{1 if i < first_count else 2}" if full_match else ""
                line = f" {minute:>2}{half}  team {team}  scorer {player_index}"
                grid.draw_text(row, 0, line.ljust(WIDTH), fg=_FG_NORMAL, bg=_BG_NORMAL)
                row += 1
        else:
            grid.draw_text(row, 0, "  no goals".ljust(WIDTH), fg=_FG_NORMAL, bg=_BG_NORMAL)
            row += 1

        # ── Seed words row ─────────────────────────────────────────────────
        row += 1  # blank row before seeds
        seed_text = (
            f"SEED DS:7B62  0x{result['seed_DS7B62']:04X}  "
            f"DS:8336  0x{result['seed_DS8336']:04X}"
        )
        grid.draw_text(row, 0, seed_text.ljust(WIDTH), fg=_FG_NORMAL, bg=_BG_NORMAL)

    # ── Footer (row 24) ───────────────────────────────────────────────────
    footer = "ENTER CONTINUE  ESC QUIT"
    grid.draw_text(HEIGHT - 1, 0, footer.ljust(WIDTH), fg=_FG_TITLE, bg=_BG_TITLE)

    return grid


# ── Test helper (not part of the public API) ────────────────────────────────

def _render(savestate_path_or_bytes: str | bytes) -> Grid:
    """Load the savestate, run the engine, and render the result grid.

    This is the test surface: the engine runs once inside this helper,
    and the result is rendered without showing the screen. Raises if the
    savestate file is absent.
    """
    sav = Savestate(savestate_path_or_bytes)
    try:
        result = _qe.simulate(sav)
    except (FoulPathNotModelled, ExtraTimeNotModelled) as exc:
        return _build_grid(None, str(exc))
    return _build_grid(result, None)
