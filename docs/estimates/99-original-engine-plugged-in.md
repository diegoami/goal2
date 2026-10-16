# Estimate: the original engine plugged in (issue 99)

The question (issue 99, the owner, 2026-10-15): what does it cost to **plug in the original game's
engine, run it emulated, and build the remaster around it**, so that the remaster needs the original
(or parts of it) to be played? The owner: the game is fully abandonware, the registered version
included, so the original's bytes as a run-time dependency are acceptable. The repositories' rule still
holds: nothing of the original is committed (CLAUDE.md rule 19), so the player obtains the files.

This is an estimate for the owner to compare with the sibling estimate (issue 98, a close-enough
engine) and goal2-archaeology PR 243 (`docs/match-engine-plan.md`, an exact port). It recommends; goal2
decides. It holds no status: the labels do.

Sources: goal2 at `66ed7a2` (this branch's base); goal2-archaeology
`main` at `0084491` (findings, `runtime/emul/`, the named view) and PR 243's branch at `5db9d15`
(E032, unmerged); the timing runs in [`measurements/estimate-99/`](../../measurements/estimate-99/)
(read-only runs of PR 243's harness on E011-r0001's watchstart state; no DOSBox-X, no original bytes
committed).

## In short

| | |
| --- | --- |
| **Recommended first stage** | The original's **watched match** run in-process under Unicorn, called on goal2's own state through the original's `run_match`, in goal2's existing friendly loop. **About 13.5 agent-hours (8.5–22), 4 PRs, about 5–6 review rounds.** |
| **First playable version** | The browser friendly loop as it is today (country → squad → tactics → preview), then **"watch"** plays the original's own match from goal2's state: the real score, scorers and minutes, bookings and injuries, man of the match and ratings, the original's commentary lines and board statistics, and the player bytes the match and its post-match tail write (energy, form [confirmed: F018, F020]) back into goal2's state. A progress bar by match minute, no pitch picture yet. Exact by construction. |
| **The whole match as the player knows it** (half-time and in-play changes, pitch playback, extra time and shoot-outs) | +14 h (9–24), 4 PRs. **Scope A in all: 27.5 h (17.5–46).** |
| **The whole game as a headless core** (competitions, other results, ageing, retirements, rankings, 1–6 managers: the original's own rules under a new browser interface) | +37 h (25–60), 9 PRs. **A + whole game: 64.5 h (42.5–106).** About 20 h of it is browser UI any route needs. |
| **Public distribution** (a player's own copy of GOAL2 booted without DOSBox-X) | +9.5 h (6–16), 2 PRs. Only if people other than the owner will play. |
| **Run-time cost** | A watched match is **9.7–14.6 CPU s** here (plain runs across 5 distinct seeds, combining `out-speed.txt` and `out-lean.txt`; PR 243: 8.3–16.8), loading the image 0.05 s. Not reducible by trimming the harness (measured below); about 250–370 watched matches per CPU hour. |
| **The player supplies** | Owner: what goal2 already needs today (a savestate and `GOAL.DAT` from goal2-archaeology's private releases, by hash) plus `pip install unicorn`. Others (after the public stage): their own copy of GOAL2's `GOAL.EXE` and `GOAL.DAT`, checked by hash. |
| **Three biggest uncertainties** | (1) whether `run_match` can be called on any fixture from a menu-state image without hidden preconditions; (2) how many undeclared key waits and timed prompts the whole game has (scope C); (3) whether copies of GOAL2 found online match the owner's hashes and how much DOS the boot needs (public stage). |

## What is already there

| Piece | Where | What it gives this route |
| --- | --- | --- |
| The exact harness | goal2-archaeology `runtime/emul/watched_match.py` (T38/E021) | Resumes a DOSBox-X savestate's memory and CPU in Unicorn and runs the original's code from the captain screen to the full-time board; key reads answered only at declared screens; routine substitution hooks. [confirmed: goal2-archaeology `0084491`, `runtime/README.md`, E021] |
| Its speed | E032 (PR 243) and this estimate | 8.3–16.8 CPU s a match with the delay count written at kick-off; identical draw for draw to the unmodified run (10 of 10). [derived: E032 notes at goal2-archaeology `5db9d15`; `measurements/estimate-99/out-speed.txt`] |
| A clean entry for a match | the named view, `0791:F1F6 run_match(fixture far pointer)` | Runs the set-up `A4A1` (including the computer side's eleven), the team screen, the match `F098`, man of the match, the summary board, group tables, the save-summary prompt and the post-match updates. One call plays one fixture, watched or quick (`DS:9A3E`). [confirmed: goal2-archaeology `0084491`, `static/goal-exe/named/seg_0791_12.c:347`; F005, F009, F010, F024] |
| goal2's state is the original's memory image | goal2 `goal2/game/state.py` (T06/T17) | `GameState` carries the raw guest memory and writes squads, eleven, captain and tactics back into it; the players and countries are at the original's addresses. Writing goal2's state into the emulator and reading it back is a copy, not a translation. [confirmed: T06, T17; F002, F007, F010] |
| goal2 already needs the original at run time | goal2 `README.md`, `goal2/web/server.py` `WebSession.load` | A new game takes a savestate and `GOAL.DAT`, fetched from goal2-archaeology's private releases by hash (`tools/measure_p1.py`). Route 99 widens that dependency from data to code; it does not create it. [derived: goal2 `origin/main`] |
| Template states | goal2-archaeology releases | E006-r0001 (main screen of a new game, used by goal2's P1 test), E011-r0001 (watchstart), E031's shoot-out start (`play-the-game kept savestates`). [confirmed: release listings] |
| Screen and key map of the whole game | goal2-archaeology `docs/play-guide.md` (E031), `docs/screens.md`, F030 (prompts and their time-outs) | What scope C's screen catalogue starts from. |

## Which parts of the original, run how

### Three scopes

| Scope | What the original runs | What goal2 keeps in Python | Verdict |
| --- | --- | --- | --- |
| **A. The match** | `run_match` per managed fixture: set-up, the match (watched or quick), post-match updates | everything between matches (calendar, competitions, other results, ageing), as planned in T40–T59 | **recommended first**: cheap, exact, reusable by every other route |
| **B. Chosen rules as routine calls** | `run_match` plus single routines called like functions: the silent result `D47E`, ageing `1771:7FB1`, re-creation `96D3`, the stage builders | the calendar and the glue between those calls | **not recommended**: each routine's preconditions (stage bytes, fixture tables, screens it shows) must be learned one by one; it is scope C's work done piecemeal, with Python glue that can drift from the original's order |
| **C. The whole game as a headless core** | the original's own main loop from its main screen: every menu, fixture, bulletin and year change | the interface (browser), the save files, the bot | **the decision after A**: the cheapest exact full game; it makes goal2 a new interface over the original |

### How it runs

| Method | Speed | Fit | Verdict |
| --- | --- | --- | --- |
| **Unicorn in-process** (the existing harness, `pip install unicorn`) | 9.7–14.6 CPU s a watched match; image load 0.05 s | Python, no display, deterministic, hooks and memory reads at will; a state is copied by copying 1.1 MB | **use** |
| DOSBox-X headless (goal2-archaeology's driver, E031) | a watched match took 4–8 minutes of wall time at the owner's fixed 8000 cycles; a 4-year cycle took 93 minutes with an agent playing [derived: `docs/play-guide.md` C63, C64, C65] | needs Xvfb, a pinned DOSBox-X build (#117), screens read through savestates; the emulator is in use by another agent | reject for the remaster; it stays the archaeology's ground truth |
| A browser emulator (js-dos and the like) | not measured | the game would run in the page as itself; goal2's Python state, tests and bot could not reach it | out of scope |

## The work, stage by stage

Hours are implementer agent-hours (a Claude subagent, goal2's process: one task, one PR, one OpenCode
review). The range is low–high. "U" tasks are goal2-archaeology's (engine code lives upstream and is
vendored, CLAUDE.md rule 18); "G" tasks are goal2's.

### Stage 1: the original's watched match in the friendly loop (the first playable)

| Task | What | Check (one command) | Hours |
| --- | --- | --- | --- |
| U1 | **Guest call of `run_match`.** `Guest.call(routine, args)`: a far call frame on a menu-state image (a pre-match state of E011's own game if its records have one, else E006-r0001's main screen with E011's player and country records and seeds written), a fixture record written to a scratch slot, the declared key reads of the path (team screen "play", the two boards, the save-summary prompt answered "no"), stop at the return. A return-form table for the hooked routines so goal2 can vendor without the listings. The delay count at kick-off as an option. **Includes a 1-hour try of the next level up** (the original's own fixture dispatch, `000E:6E15`), which decides risk R1 and stage 3's cost | at the captain-screen wait `CC7B`, the guest memory equals E011-r0001's watchstart on the bytes the match reads (pitch records, both squads, tactics, seeds), and the 10-seed E032 family then plays identically | 5 (3–8) |
| G1 | **Vendor the harness** into `goal2/engine/emul/` with PROVENANCE rows; `unicorn` as an optional dependency (a new external dependency: the owner's approval, process.md §7); template fetched by hash into `.cache/` | the vendored harness reproduces E032's 10 recorded matches from the release state | 2.5 (1.5–4) |
| G2 | **GameState to fixture and back**: write the managed side's eleven, captain, tactics and the seeds into the image, call U1, read back score, scorers, minutes, cards, injuries, ratings, the player bytes the post-match tail writes, squad words and seeds | a fidelity test: the adapter's match equals the vendored harness on the same image for 10 seeds; a changed squad word changes the match (shown failing) | 3 (2–5) |
| G3 | **Into the loop**: "watch" runs G2 in a worker with a progress bar by match minute; the result screen shows the original's commentary lines (template strings read from the image at run time, never committed) and board statistics; quick results stay on the vendored quick engine; assumptions register A-WATCH-1 replaced | browser test: a watched friendly ends on a result screen whose score and lines equal G2's output | 3 (2–5) |
| | **Stage 1** | | **13.5 (8.5–22)** |

PR 243 prices its option D at about 7 hours (its P0 tooling 3 h and P6 image adapter 4 h). Stage 1
differs: it needs no porting tooling, and it adds goal2's side (vendoring, the state mapping, the
loop), which PR 243 does not count.

### Stage 2: the whole match as the player knows it

| Task | What | Hours |
| --- | --- | --- |
| G4 | **Half-time**: the half-time team-screen wait becomes a pause where the player substitutes and changes tactics; applied through the original's own screen (`ED8A`) keys, so the original's re-sort (`230C`) and substitution budget run as they do there [confirmed: F029, F027] | 3 (2–5) |
| G5 | **During play**: the player pauses at a tick; the key poll `9372` returns the key that opens the in-match menu; the browser's actions become that menu's keys; the penalty-taker prompt (F030) answered from the browser. A change lands at the tick the player paused on, which the original also allows | 4 (3–7) |
| G6 | **Pitch playback**: per tick, the changed cells of the pitch picture `[DS:7C16]` (the original's 80×25 text pitch, which is also the players' occupancy grid [derived: E032 notes]) and the commentary; the browser replays them at a chosen speed, either as the original's text pitch or as a drawn pitch from the same positions | 5 (3–8) |
| G7 | **Competitive matches**: extra time, penalties, the shoot-out `A10A`, two-substitution budget, from E031's shoot-out start state | 2 (1–4) |
| | **Stage 2** | **14 (9–24)** |

### Stage 3: the whole game as a headless core (scope C)

| Task | What | Hours |
| --- | --- | --- |
| U2/G8 | **The core runner**: the original's main loop from the main-screen state; every key read is a yield point reported as (its call site, the text page, the state view); keys in; the remaster's save is the image itself (compressed), with its seeds, so a game replays | 5 (3–8) |
| G9 | **Screen catalogue**: each key-read site mapped to a screen kind and the state it shows, read through the state adapter rather than parsed from text (starting from `docs/screens.md`, the E031 play guide and F030); an unknown site stops with its site and text page | 6 (4–10) |
| G10–G14 | **The browser over the core**, one task each: new game and managers (1–6) and country choice; main menu, fixtures, tables, rankings, history; squad, pool, select team, tactics; bulletins, news, retirements and the year change; the match flow of stages 1–2 under the core. goal2's existing screens are reused where they fit | 20 (14–32) |
| G15 | **The owner's deviations as guest patches**: a declared, tested patch mechanism, and the first patch (#73: unlimited substitutions in friendlies, five otherwise, where the original allows 5/2) | 3 (2–5) |
| G16 | **A 4-year cycle unattended**: a scripted player through the core, its facts checked against E031 g1's logged session | 3 (2–5) |
| | **Stage 3** | **37 (25–60)** |

What stage 3 replaces: T40–T58 in [`full-cycle-backlog.md`](../full-cycle-backlog.md) (19 tasks, 8 of
them Hard), which re-implement in Python the rules the core would run as the original: the calendar,
energy and recovery, confidence, injuries and bans, the computer's teams, other results, tables,
qualifying and finals, rankings, ageing, retirement, the next cycle. That backlog has no hour estimates;
at goal2's observed 1–4 hours a task it is roughly 30–70 hours of rules work, before the watched engine
(PR 243's port, about 50 h, or issue 98's engine). Stage 3's rules-specific part is G8, G9, G15 and G16,
17 hours; its 20 hours of browser screens are work every route needs (P6 in `docs/plan.md`).

### Stage 4: public distribution

| Task | What | Hours |
| --- | --- | --- |
| G17 | **Boot shim**: `GOAL.EXE` (LZEXE 0.91-packed: its header reads `LZ91`) booted in Unicorn from the player's files with a minimal DOS and BIOS: the start-up's memory and vector calls, opening and reading `GOAL.DAT`, the BIOS tick the delay calibration `214B:1DA7` waits on, the text screen; run to the title or main screen; checked against E006-r0001's main-screen state on every field the state adapter reads. Removes the DOSBox-X savestate format (#117) from the player's path | 8 (5–14) |
| G18 | **Install path**: a file picker or a folder argument; hash check against the registered sets with a clear refusal naming the file that differs; where the files are cached (`.cache/`) | 1.5 (1–2) |
| | **Stage 4** | **9.5 (6–16)** |

### Totals and reviews

| Scope | Hours (range) | PRs | Review rounds (expected) | CPU for checks |
| --- | --- | --- | --- | --- |
| Stage 1 (first playable) | 13.5 (8.5–22) | 4 (1 upstream) | 5–6 | a 10-seed family is about 2 CPU minutes |
| Stage 1 + 2 (scope A, the match) | 27.5 (17.5–46) | 8 | 10–11 | under 30 CPU minutes in all |
| + stage 3 (scope C, the whole game) | 64.5 (42.5–106) | 17 | 21–23 | the cycle run G16: tens of CPU minutes (assumed) |
| + stage 4 (public) | 74 (48.5–122) | 19 | 24–26 | — |

Review rounds: one review per PR, about 1.3 rounds on average (goal2's PRs so far: most merged after
one round, a few after two); the guest-call tasks (U1, G2, G8) are the ones likely to need two. No
DOSBox-X session and no sitting of the owner is needed at any stage.

## The cost at run time

| What | Cost | Basis |
| --- | --- | --- |
| A watched match | **9.7–14.6 CPU s** (plain runs across 5 distinct seeds, combining both scripts; recorded CPU/wall differences in `out-speed.txt` are at most 0.9 s) | `out-speed.txt`, `out-lean.txt`; PR 243 measured 8.3–16.8 |
| Loading the image (1.1 MB of guest memory) | 0.05 s | `out-speed.txt` (`load_cpu_s`) |
| Why it cannot be trimmed much | One match executes 47.2 million basic blocks (659 MB of code bytes, about 200 million instructions at an assumed 3 bytes each): Unicorn runs about 20 million instructions a second here. The harness's Python bookkeeping is not the cost: dropping the seed recording and replacing the key-poll hook by a native patch left the time unchanged (9.7–14.6 s, identical results). Skipping the removable display routines made it **slower** (12.7–16.1 s), because a Python hook costs more than the native code it replaces | `out-blocks.txt`, `out-lean.txt`, `out-speed.txt` |
| A quick result through the original | not measured; assumed under 1 s (the quick engine `D733` runs instead of the per-tick watched engine). goal2's vendored quick engine stays available and is exact [confirmed: F012] | assumption |
| A 4-year cycle in the core, all managed matches quick | not measured; assumed a few CPU minutes; each watched match adds 10–15 s | assumption |
| The bot | 250–370 watched matches per CPU hour per process, in parallel processes; quick results, or the vendored quick engine, for search. A state is forked by copying the image, so the bot can look ahead exactly | derived |
| Memory | the guest's 1.1 MB per running match plus Unicorn's own (not measured) | |

To repeat the runs: extract PR 243's tree (`git archive origin/docs/match-engine-plan runtime
experiments static/goal-exe/code` in goal2-archaeology), then `python3 -B
measurements/estimate-99/speed.py <tree> <E011-r0001 watchstart .sav> 0x1234,0x2345,0x4c1d,0xc3c3,0xe719`
(and `lean.py <tree> <sav> <seeds>`, `blocks.py <tree> <sav>`); they write only to stdout.

Faster would need a different emulator core (a dynamic-recompiling DOS core is not available from
Python) or the port (PR 243), which replaces guest routines through the same hooks.

## What the player supplies, and what that means for distribution

| Who | Supplies | How it is obtained |
| --- | --- | --- |
| The owner, stages 1–3 | `GOAL.DAT` and one template savestate (E006-r0001 or E011-r0001), as goal2 needs today; `pip install unicorn` | fetched from goal2-archaeology's private releases by SHA-256 into `.cache/` (git-ignored), as `tools/measure_p1.py` does; needs the owner's GitHub access |
| Anyone, after stage 4 | their own copy of *goal (version 2)*: `GOAL.EXE` and `GOAL.DAT` at least (`GOAL.HLP` for the help text) | the player downloads the game (the owner: abandonware, the registered version included) and points the remaster at the folder; the remaster checks the hashes against the registered sets (`GOAL.EXE` 92,391 bytes, SHA-256 `a6928b0b…`; `GOAL.DAT` 44,040 bytes, `bc5e5c04…`; set `goal2-a949da2f`/`goal2-67cf27d6`) and never copies them anywhere but its local cache |

goal2 itself then contains no byte of the original (rule 19 holds), so it can be published as code. The
game it plays is the original, which the player brings. Until stage 4 the remaster can only be played by
someone with access to the private releases.

## Risks

| # | Risk | Likelihood | What it costs | What we do |
| --- | --- | --- | --- | --- |
| R1 | `run_match` called on a fixture from a menu-state image needs state the menu path sets (the fixture record's layout and kind, the managed side, `DS:9A3E`, flags of `000E`'s dispatch) | medium | +3–6 h in U1 | U1's check compares the guest memory at the captain screen with E011's real watchstart; if it differs, enter one level higher (the original's fixture dispatch), which stage 3 needs anyway |
| R2 | Undeclared key reads: bulletins, injuries, timed prompts (F030: 6 s and 10 s waits), the "watch this match?" prompt; each voids a run | high in scope C, low in A | inside G9's estimate; +5 h if the catalogue is twice as long as `screens.md` | every unknown site stops with its site and text page; no guessing keys |
| R3 | 10–15 s for a watched match is slow for the bot's search and a visible wait in the browser | certain | — | progress bar; quick results and the vendored quick engine for search; parallel processes; the port later |
| R4 | The owner's designed deviations (#73, future tuning) become patches to the original's code, and the plan's "engine parts behind interfaces" and assumptions register lose their role for whatever the original runs | certain in scope C | 1–3 h a deviation; a deep change may be impractical | G15's mechanism; keep deviations few; this is the main reason not to choose scope C if the remaster is meant to diverge from the original |
| R5 | Copies of GOAL2 found online differ from the owner's (another release, the shareware version, a repack); the boot needs more DOS than assumed | medium | +4–8 h in G17 | check one public archive's hashes first (0.5 h); accept only the registered sets |
| R6 | goal2 writes bytes into the image the original would not (order of squads, a stale copy) | medium | a wrong but plausible match | write through the original's own routines or screens where they exist (G4, G5); F029: the squad words are the master |
| R7 | An emulator difference on a path E021 never checked (shoot-out, other countries) | low | a run that differs from DOSBox-X | E021's check placed the harness on E011's DOSBox-X reads tick-exactly [confirmed: goal2-archaeology `0084491`, `runtime/README.md`, E021]; G7 and G16 run the uncovered paths against E031's logged sessions |
| R8 | A new external dependency (`unicorn`, C wheels per platform) | certain | — | the owner's approval (process.md §7); optional, so goal2 still runs its Python-only paths without it |

## What is assumed

| Unknown | Assumed | Cost to find out |
| --- | --- | --- |
| How fast agents do this kind of task | 1–4 h per goal2 task, from goal2's PR history (T01–T38) and PR 243's rates; the guest-call tasks at the high end | — |
| `run_match`'s preconditions | a fixture record and a few flags; one level up if not (R1) | about 1 h, inside U1 |
| The fixture record's layout | readable from F023 (stage builders) and F024 | inside U1 |
| A quick result's and a whole cycle's run time in Unicorn | under 1 s and a few minutes | 1 h of runs; not worth it before stage 3 |
| The number of distinct key-read screens in the whole game | about `docs/screens.md`'s catalogue plus F030's prompts, 25–35 | measured by G9 itself |
| Public copies of GOAL2 match the owner's hashes | at least one does | 0.5 h, before stage 4 |
| The boot needs only a small DOS: memory, vectors, file open/read/close, the BIOS tick, the text screen | yes | discovered in G17 |
| Unicorn 2.1.4's 16-bit emulation is right on paths not yet compared | yes (R7) | G7, G16 |

## How this compares (for the owner's three-way choice)

| | This route (original plugged in) | Exact port (PR 243) | Close-enough engine (issue 98) |
| --- | --- | --- | --- |
| First playable watched match | stage 1: **13.5 h (8.5–22)** | option D first, about 7 h (archaeology side only) | see issue 98's estimate |
| The whole watched match engine | exact by construction at stage 1; the in-match interface at stage 2 (+14 h) | about 50 h (29.8–89.1), 8 tasks | see issue 98 |
| The rest of the game's rules | stage 3: 17 h of rules-specific work (the original runs them) plus screens | not covered (goal2's T40–T59) | not covered (goal2's T40–T59) |
| Exactness | the original, everywhere it runs | exact where the seed families reach | close in distribution |
| Run time, a watched match | 9.7–14.6 CPU s | measured at its P6; the hooked pilot 18 s | presumably fast (pure Python) |
| Needs the original at run time | yes: data and code | no, after P6 | no |
| Can be tuned or changed | by guest patches only | in Python, after the port | freely |

The routes combine: stage 1 is the oracle a close-enough engine is checked against and the frame into
which the port's pieces drop (PR 243's hooks are U1's hooks), so stage 1 is not lost whichever route
follows.

## Recommendation

1. **Do stage 1 now** (13.5 h, 4 PRs): it gives the remaster the real watched match, exact, in the loop
   it already has, and it replaces the stand-in A-WATCH-1. It is the cheapest real engine of the three
   routes for the remaster and the base the other two can use.
2. **Let U1's one-hour try of the fixture dispatch decide R1**, and with it how much of stage 3 is
   known.
3. **Then choose between stage 3 and the Python campaign (T40–T59).** Stage 3 if the goal is the
   owner's stated one, a faithful game that a bot plays for idle play, reached soon and exact (about 37 h
   instead of 30–70 h of rules work plus a watched engine). The Python campaign if the remaster is meant
   to diverge from the original, be tuned, or one day run without it. I lean to stage 3 for the stated
   goal, with goal2's existing Python models kept as checks against the core.
4. **Do stage 4 only if others will play.** Until then the owner's private releases are enough.
