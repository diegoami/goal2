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

[designed: T23] Interactive screens print and flush plain-text frames before
reading input. Frames append to stdout; colours and cursor highlighting are
omitted. Scripted key iterables remain silent.

[designed: T25] On POSIX terminals, the interactive screen chain reads keys
immediately in cbreak mode and restores the saved terminal settings when it
ends. A bare or incomplete Escape waits up to 0.15 seconds for an ANSI key
sequence continuation. Scripted keys and redirected input remain supported.

[derived: `goal2/ui/input.py`, `goal2/ui/result.py`, `goal2/main_loop.py`]
The result screen runs the vendored half-time simulation on the adapted
snapshot; fixture progression ends at a placeholder. This command is the
current screen-chain prototype.
