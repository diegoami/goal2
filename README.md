# goal2

Agent instructions: [AGENTS.md](AGENTS.md) for Codex, [CLAUDE.md](CLAUDE.md) for
Claude Code; both follow [docs/process.md](docs/process.md).

A faithful rebuild of *goal (version 2)* (New Era Software, 1993), and the bot that maximises its
World Cup win rate. Everything here is built from the evidence of the private
[goal2-archaeology](https://github.com/diegoami/goal2-archaeology) repository: its findings (`F0nn`,
each with listing lines and run records), its task records and its releases.

- **Language**: Python. The archaeology runtime's models drop in as the engine truth.
- **Engine truth is vendored** under `goal2/engine/`, pinned in `PROVENANCE.md` (file, source
  commit, findings). Vendored files are never edited here.
- **Evidence tags** (`CLAUDE.md` rule 17): every behaviour claim in code or docs is `[confirmed]`,
  `[derived]` or `[designed]`.
- **Private forever**: nothing of the original GOAL2 — no asset, savestate or executable byte — is
  committed; states load from local caches and the archaeology releases by path, git-ignored
  (game-archaeologist U17/U21).

[designed: owner #148, 2026-10-16; session binding choice] New primary UI work
uses PySide6 desktop: [roadmap](docs/desktop-ui-roadmap.md). Existing browser and
terminal launch instructions below describe the retained interfaces; the desktop
launch command will arrive with its implementation tasks.

The plan is [`docs/plan.md`](docs/plan.md); every rule the rebuild plays by, and where it comes
from, is in [`docs/assumptions.md`](docs/assumptions.md). Tasks live in `docs/tasks/` (`T<nn>.md`, indexed in `docs/tasks/README.md`).

Run the screen chain with local game data and a halftime savestate. The loop
keeps its rebuild-owned continuation save at `.cache/session.g2save` by
default. After a friendly, choose **Save and quit**; resume with the save and
the local GOAL.DAT:

```bash
python3 -m goal2.loop .cache/<savestate>.sav .cache/GOAL.DAT
python3 -m goal2.loop --resume .cache/session.g2save .cache/GOAL.DAT
```

Pass `--save PATH` to choose another session-save path. Session saves use a
versioned explicit-data format for this rebuild and do not claim compatibility
with the original game's save formats. [designed: T33]

[designed: T31] Interactive screens flush each 80×25 frame before reading
input. ANSI-capable terminals clear and redraw in place without a trailing
newline that scrolls the last row; redirected output and dumb terminals append
plain frames. VGA colours are omitted, and selection rows show an ASCII `>`
marker. Scripted key iterables remain silent.

[designed: T28] On the squad screen, ↑/↓ moves through the squad and Space
toggles inclusion in a local starting-eleven draft. Enter confirms exactly 11
players and makes the highlighted included player captain; invalid confirmation
shows a reason and leaves the draft open. Esc or exhausted scripted input
discards the draft.

[designed: T29] After tactics, the match preview names the managed team, its
opponent, the selected eleven and captain. Enter starts the assumed friendly;
Esc or exhausted scripted input quits before simulation. Unsupported match
templates show a refusal and cannot be confirmed. Scripted input stays silent.

[designed: T25] On POSIX terminals, the interactive screen chain reads keys
immediately in cbreak mode and restores the saved terminal settings when it
ends. A bare or incomplete Escape waits up to 0.15 seconds for an ANSI key
sequence continuation. Scripted keys and redirected input remain supported.

[derived: `goal2/ui/input.py`, `goal2/ui/preview.py`, `goal2/ui/result.py`, `goal2/main_loop.py`]
[designed: T26, A-MATCH-1, T30] The interactive result screen runs a complete
friendly through both halves on one vendored quick-engine instance. It starts
at 0–0 with the selected country, eleven and tactics; the opponent comes from
the template and uses the current computer-selection stand-in. The result
title labels the setup as assumed; it names both teams in engine score order,
identifies the managed team, shows halftime and fulltime scores, and lists
each goal with its team, scorer, half and minute. PageUp/PageDown pages
overflow; Enter finishes and Esc quits. After a successful friendly, the next
screen offers another friendly, Save and quit, or Quit. Another friendly keeps
the chosen country, squad, eleven, captain and tactics, and starts with retained player
records and both final RNG words. The squad screen shows each player's current
energy. The template supplies initial players, tables and seeds; original
match setup and half-time energy recovery are not reproduced. These retained
changes define this rebuild's consecutive-friendly loop and make no claim about
original between-fixture fidelity. Technical seed values stay available in the
recorded-half replay screen, which `python -m goal2.play` continues to show
from a half-time savestate. Issue #73's observed replay and commentary controls
inform the UI.


[designed: T34] A standalone browser interface preview is available in [`docs/prototypes/browser-ui/`](docs/prototypes/browser-ui/README.md). Start it from the repository root with:

```bash
python3 -m http.server 8000 --directory docs/prototypes/browser-ui
```

Then open `http://localhost:8000`.

[designed: T35–T38] Start a new live browser session with a local halftime savestate and
the matching local GOAL.DAT:

```bash
python3 -m goal2.web .cache/<savestate>.sav .cache/GOAL.DAT
```

Open `http://127.0.0.1:8000`. Pass `--host` or `--port` to choose a different
bind address or port. The server loads both files once and keeps one in-memory
session. **Save session** writes the existing versioned `.g2save` format to
`.cache/session.g2save`; **Load saved session** validates that file and its next
friendly before replacing the live session. A failed save leaves the previous
file intact and can be retried. Choose a country, edit the starting eleven, captain and eight tactics
bits, then use **Confirm team** to update that session. **Cancel draft** restores
the confirmed choices. The overview shows the confirmed team and named matchup
from the shared resolver. Press **Play friendly** to run one complete assumed
friendly using the confirmed team. The result shows the ordered team names,
managed side, half-time and full-time scores, named goal events, match count and
both retained seeds. Reload and navigation do not run a match. Use **Another
friendly · Manage team** to return to the same country's team management with
updated player energy and choices, then play again. To resume after closing the
server, run:

```bash
python3 -m goal2.web --resume .cache/session.g2save .cache/GOAL.DAT
```

For a different save location, pass `--save /path/to/session.g2save` both when
starting a new game and when resuming. To move a session to another computer,
copy the `.g2save` file there and use its path with `--resume`; that computer
also needs its local `GOAL.DAT`. A `.g2save` is the rebuild's JSON session
format, distinct from original binary `.sav` inputs.

Run the real-browser country, management and friendly checks with Playwright installed:

```bash
PLAYWRIGHT_MODULE=/path/to/playwright node tools/browser-ui/acceptance.mjs --scenario management
PLAYWRIGHT_MODULE=/path/to/playwright node tools/browser-ui/acceptance.mjs --scenario friendlies
PLAYWRIGHT_MODULE=/path/to/playwright node tools/browser-ui/acceptance.mjs --scenario persistence
```

[designed: T41] The live browser also offers **New campaign** with country, even
start year and explicit seeds. **Play scheduled friendly** uses the next source
fixture, retains score history, and stops at the unsupported qualifier boundary.
Save/load and process resume preserve that position. See the
[browser instructions](tools/browser-ui/README.md) and
[campaign contract](docs/campaign-state.md) for the exact scope and acceptance.

[designed: T42] Scheduled campaign quick friendlies now apply half-time energy,
post-match fitness restoration and ordered fixture recovery. Squad energy updates
with the completed result, and save/resume preserves the transition once. See the
[campaign energy scope and evidence](docs/campaign-energy.md); standalone friendly
behavior and original watched-engine integration remain separate paths.

[derived: F019/F020; designed: T43] Scheduled quick campaign friendlies now apply
result-relative confidence with ordered bench draws and scorer-shadow restoration.
Browser management shows player confidence and confirmed team morale; results show
the recomputed morale. See [campaign confidence](docs/campaign-confidence.md) for
evidence, saved continuation and the current national-pool/status limits.

[derived: F027; designed: T44] Campaign selection now explains and refuses
unavailable starters, allows lineup repair and filters computer starters.
Played fixtures apply the status-byte ban/booking transition once; Save/Load
preserve it without expiry. See [campaign eligibility](docs/campaign-eligibility.md).
