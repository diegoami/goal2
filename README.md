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

The plan is [`docs/plan.md`](docs/plan.md); every rule the rebuild plays by, and where it comes
from, is in [`docs/assumptions.md`](docs/assumptions.md). Tasks live in `docs/tasks/` (`T<nn>.md`, indexed in `docs/tasks/README.md`).

Run the screen chain with local game data and a savestate:

```bash
python3 -m goal2.loop .cache/<savestate>.sav .cache/GOAL.DAT
```

[designed: T23, T27] Interactive screens print and flush plain-text frames
before reading input. Frames append to stdout; VGA colours are omitted, and
selection rows show an ASCII `>` marker. Scripted key iterables remain silent.

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
names both teams in engine score order, identifies the managed team, shows
halftime and fulltime scores, and lists each goal with its team, scorer, half
and minute. PageUp/PageDown pages overflow; Enter finishes and Esc quits.
Technical seed values stay available in the recorded-half replay screen,
which `python -m goal2.play` continues to show from a half-time savestate.
Issue #73's observed replay and commentary controls inform the UI work; this
result summary does not add replay prompts or fixture progression.
