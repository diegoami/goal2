# Estimate (#98): a watched-match engine that is close enough, not exact, and tunable

The owner's question (goal2 #98): what would it cost to build a match engine for the remaster that is
not identical to the original's but close enough to make a playable game, and that can be tuned
later? This page is an estimate and a recommendation; goal2 decides. It holds no status (CLAUDE.md
rule 3). Sources: goal2 at `66ed7a2`, goal2-archaeology `main` at `0084491` and its PR 243 at
`5db9d15` (`docs/match-engine-plan.md`, the exact port, "route C"). The sibling estimate (#99) covers
running the original's code; #97 frames the options.

Tags follow CLAUDE.md rule 17. Claims about the original cite the spec row or finding; F022-F030 are
still `proposed` upstream, so claims resting on them are `[derived]`. Every number of this estimate
is `[designed]`: a judgement, not a measurement, except where a measurement is named.

## In short

- **What I would build** `[designed]`: an **event engine**. It plays a watched match minute by
  minute on the arithmetic goal2 already has exactly, the vendored quick engine's strengths, line
  sums and contests, and adds the events a watched match shows: chances, shots, saves, corners, free
  kicks, offsides, fouls, cards, injuries, added time and substitutions at stoppages. Its free
  parameters sit in one knobs file and are tuned against the original's **already measured**
  watched-match rates. There is no pitch geometry and no player positions.
- **Effort** `[designed]`: about **34 implementer-hours (range 24-59) in eight tasks, with about 10
  review rounds (8-14)**. About 8 of those hours (the seam and the browser screen) are integration
  work that any route needs. The engine alone is **about 26 hours (18-47)**, against route C's 49.5
  (29.8-89.1), which does not include integration into goal2.
- **First playable** `[designed]`: after the first three tasks, **about 15 hours (11-24)**. A watched
  friendly plays in the browser from the new engine. It shows the timeline of commentary, the
  original's full-time statistics board, ratings and the man of the match, with goals at the
  original's watched rate. Cards, injuries and substitutions during play arrive about 9 hours later.
  No run of the original and no DOSBox-X session is needed for any of it.
- **Tuning** `[designed]`: about 20 named knobs. One command plays 500 seeded matches in an
  estimated 10-40 s and prints each statistic against its target interval. A tuning change is an
  ordinary PR whose body shows the sheet before and after.
- **Recommendation** `[designed]`: if the owner wants a playable, tunable watched match soon, and
  an engine fast enough for the bot to search, build this event engine behind a seam that the exact
  port (C) or the original's code (D, #99) can also plug into later. **Do not** build a
  close-enough engine with positions on a pitch. It would cost about 55-75 hours, more than the
  exact port, and would still have to be calibrated (section 4). If moving players matter, buy them
  from route C or D.

## 1. What "close enough" means here, as checks

The original is the measure. "Close enough" becomes rows a command can check, not a proof. The
targets already exist, so a first version needs no new runs of the original:

| statistic, per match | original's value | source | check for the event engine |
| --- | --- | --- | --- |
| goals (both sides) | 1.98, sd 1.37; 0/1/2/3/4+ goals = 14/27/20/30/9 % | `[confirmed: C-MATCH-27, F005]` 100 watched friendlies over random new games (E004) | mean inside the original's 95% interval (about ±0.27) on 500 matches; shares of 0-4+ goals within 8 points |
| bookings | 1.49, sd 1.44 | same | mean within ±0.28 |
| sendings off | 0.31, sd 0.56 | same | within ±0.11 |
| injuries | 0.41, sd 0.62 | same | within ±0.12 |
| shots, on target, corners, free kicks, fouls, possession bar (per side) | e.g. shots 3.6 / 3.5, on target 2.1, corners 0.33, free kicks 2.9, possession 53.8 % | `[derived: E026 baseline arm, F026]` 30 matches of one team pair (Denmark v. country 19) | within the arm's interval; a loose check, because it is one pair |
| fouls to cards and injuries | about 0.04 sendings off and 0.0625 injuries per foul, 3-3.5 fouls a half | `[derived: F027 §1]` | as rates per foul, within ±50 % |
| added time | 90 + min(5, bookings + sendings off + injuries), paid at the end of the second half | `[derived: F027 §3]` | exact rule, unit-tested |
| effects of tactics | signs and rough sizes per element: e.g. "stay back" −1.07 shots, "avoid injury" −2.2 own fouls, "offside trap" +3.4 free kicks for; no effect on goals is detectable at 30 matches per arm | `[derived: F026, E026]` | the engine's effect has the original's sign wherever the original's interval excludes zero, and is no larger than the original's upper bound where it does not |
| better side wins more | in the quick engine: a fit side (energy 32, form 31) against a tired one (1, 1) wins 32.9 %, draws 55.8 % (second half only) | `[confirmed: C-MATCH-16]`, quick engine only | monotone in strength; size unmeasured for the watched engine (assumption A3) |

**Not required** `[designed]`: the same result for the same seed as the original, the original's
memory layout, the original's order of draws, or identical commentary text. The quick result (`R`)
keeps the vendored, seed-exact quick engine: none of this touches it.

## 2. What is reused exactly, and what is designed

| part | where it comes from | tag in the code |
| --- | --- | --- |
| player strength `377E` (energy and form, foot halving); line sums `0BC4` with tactic elements 1, 5, 6 and the home-side flag | vendored `goal2/engine/quick_engine.py` (seed-exact on 10 of 10 records) | `[confirmed: C-MATCH-10, C-MATCH-11]` |
| the three contests per attempt (midfield, attack against 2×defence, attack against the keeper) | the same, `B19D` | `[confirmed: C-MATCH-09]` |
| skill reader `278A`, the pass/fail gate `287C`, the keeper duel `5B36` | goal2-archaeology `runtime/model/keeping.py`, `contests.py` (to be vendored, rule 18) | `[confirmed: C-MATCH-23, C-MATCH-25]`, duel `[confirmed: C-MATCH-24]` |
| tackle roll `5474` (holder's skill 10 against challenger's 3 ×4) | read, F022 | `[confirmed: C-MATCH-26]` as a formula; its use in the event engine is designed |
| form swing after a goal (+1 to the scorer's side, −1 to the other), the scorer's +1 form | the quick engine | `[confirmed: C-MATCH-13]` |
| energy per minute (watched) | `runtime/model/energy.py` `watched_step` (to be vendored) | `[derived: F018, F021]` |
| performance ratings (start 55; goal +40, booked −20, sent off −100, ...) and man of the match | `runtime/model/ratings.py` (to be vendored) | `[confirmed: C-MATCH-29]` |
| the cap of 3 players lost per side, bans `B27F`, added time | F027, rules in code | `[derived: F027]` |
| the computer's substitutions (`8062`) and its tactic reapplication after a goal (`C173`) | the quick engine (`8062` is shared); goal2 `ai/cpu.py` | `[confirmed: C-MATCH-17]`; `[derived: F024]` |
| **how often a team builds a chance, which player shoots, whether the shot is saved, blocked or wide, corners, free kicks, offsides, which contests become fouls, how tactics 2, 3, 4, 7, 8 change these, the possession bar** | nothing exact exists for the event engine; guided by F026's mechanisms and E026's sizes | `[designed]`, one assumption-register row each, replaced if the port lands |

In the original the watched engine is a different engine from the quick one: one sweep over 22 pitch
records per tick, about 44 draws per tick and 91,985 draws in a half, against 3,617 in a quick half
`[confirmed: C-MATCH-20, F013]`. The event engine uses the quick engine's arithmetic as its spine and
designs the rest. That is what makes it cheap, and it is also its main limitation (section 7, R1).

## 3. The two shapes considered

| | **E. event engine** (recommended) | **P. pitch engine** (not recommended) |
| --- | --- | --- |
| what it simulates | per minute (or a few phases per minute): possession, the attack, the chance, the shot, the event | 22 players and the ball on a grid: posts by position code (F028), depth tables per tactic (F026), moves toward targets, ball phases, contests where they happen |
| what the screen can show | commentary, scoreboard, statistics board, a momentum/possession strip | moving dots |
| speed (Python) | about 0.02-0.08 s a match, **assumed** from the measured 0.025 CPU s for a vendored quick second half (section 9) | about 0.3-2 s a match, assumed; tens of thousands of player updates a match |
| calibration | each statistic has one or two knobs that move it nearly alone, so tuning converges | the statistics come out of the movement, many knobs move each of them, and every gap means changing the model and measuring again |
| cost | 34 h (24-59), engine alone 26 h | the same seam, browser and discipline, plus about 20-30 h for the movement and the ball, and 10-20 h more calibration: **55-75 h**, more than route C's 49.5 h for an exact engine |
| risk | it looks like a results engine with a story, not a football simulation (R4) | invents positions (the browser roadmap says not to); the bot learns movement quirks the original does not have |

PR 243's own figure for this kind of route ("B": 10-15 h to write, open-ended calibration) is the
writing part of P. It does not count the seam, discipline, browser or tuning tooling `[derived:
PR 243 "Four routes"]`. The event engine closes the open end by having fewer, decoupled knobs and
an acceptance sheet with a stop rule (section 6).

## 4. Build order, effort and review rounds

Each line is one task (`docs/process.md` §2): one branch, one PR, Done-when lines a command can run,
a Claude implementer and one OpenCode review. The hours are implementer time, comparable with
PR 243's. A review round adds about 0.3-0.6 h of the reviewer's elapsed time and a little of the
main session's. The rounds follow goal2's record so far: most tasks took one rework round, and a
judgement-heavy one took two (`docs/model-trials.md`).

| # | task | what it delivers | Done-when (sketch) | hours (range) | review rounds |
| --- | --- | --- | --- | --- | --- |
| W1 | **The seam** | `WatchedEngine` interface: input = the two elevens and benches from `GameState` (goal2's own types, not the memory image), tactics, fixture kind, seed; output = an event stream (minute, kind, side, players), the result, the board statistics, ratings, energy, form, cards, injuries, substitutions. Today's stand-in (A-WATCH-1) wrapped as implementation 0 | the existing friendly tests pass through the seam; a second dummy engine plugs in without touching callers | 3 (2-4) | 1 |
| W2 | **The event core** | per minute: the quick engine's line sums and contests decide who attacks and whether a chance comes; the chance becomes a shot, a save (the `5B36` duel), a block, a corner or a goal; offsides; the scorer by position weights; ratings, energy, form swing; seeded from F004's LCG; first-half kick-off assumed like the second (A-MATCH-1) | 500 seeded matches: goals' mean and 0-4+ shares inside the targets of section 1; same seed, same match; a test per exact reuse that fails if the reuse is cut | 7 (5-12) | 2 |
| W3 | **The browser match** | a watched friendly plays from W2: the timeline at a chosen speed with pause, the scoreboard, the statistics board, ratings and the man of the match; changes at half time as now; results written back to `GameState` | a browser test plays a whole watched friendly and reads its board; the session-save tests still pass | 5 (4-8) | 1.5 |
| | **first playable** | after W1-W3 | | **15 (11-24)** | **4.5** |
| W4 | **The sheet and the knobs** | `goal2/match/knobs` (each knob: value, tag, the row it moves); `python -m goal2.tune sheet --n 500 [--set k=v]` prints every section 1 row with its target, its interval, the value and pass/fail; `--arms` plays the one-flip tactic arms; a few seeded event streams pinned as goldens | the sheet runs in under a minute; a deliberately wrong knob turns its row red (falsifier) | 4 (3-6) | 1 |
| W5 | **Discipline and stoppages** | fouls from contests (element 4 sets their share), bookings, sendings off, injuries per foul, the cap of 3, bans, added time; managed substitutions and tactic changes at stoppages (owner's budget, #73); the computer's substitutions and post-goal tactics | bookings, sendings off, injuries inside their targets; added-time rule and cap unit-tested at their edges | 5 (4-8) | 1.5 |
| W6 | **Tactics** | elements 2, 3, 4, 7, 8 as modifiers on the event probabilities (1, 5, 6 already act through the line sums), guided by F026's mechanisms | the `--arms` sheet: each element's effect has E026's sign where E026's interval excludes zero, and stays within its bound where it does not | 3 (2-6) | 1 |
| W7 | **Calibration pass** | every row of section 1 inside its target; the knobs file records the final values and the sheet; optionally one measurement of the original asked of goal2-archaeology (A3) | the sheet all green on 1,000 matches at two start states | 4 (2-10) | 1 |
| W8 | **Competitive matches** | extra time (its own clock, 120 minutes, 16 attempts `[confirmed: C-MATCH-06]`), the shoot-out (takers by penalty skill, `[confirmed: C-MATCH-24]`, the kick odds designed), budgets per kind (#73) | a knockout draw goes to extra time and then to a shoot-out with a winner; friendlies are unchanged | 3 (2-5) | 1 |
| | **total** | | | **34 (24-59)** | **10 (8-14)** |

The ranges come from goal2's pace so far `[designed]`: the low end is a Claude implementer finishing
each task in one sitting. The high end doubles the judgement-heavy tasks (W2, W6, W7), where the
first knob values will be wrong. Each task stays within the hour-scale runs `docs/process.md` §2 asks
for; W2 may split into "core" and "events" if its first run passes an hour.

CPU time `[designed]`: at the assumed speed, a 500-match sheet takes 10-40 s and the whole
calibration a few CPU minutes. Nothing here competes with a shared machine.

## 5. The first playable version

After W1-W3, about 15 hours `[designed]`. The player picks a country, an eleven and tactics as
today, presses "watch", and sees the match unfold: minute, commentary lines (shots, saves, corners,
offsides, goals with scorers), a running score and a momentum/possession strip. At full time comes
the original's statistics board (shots, on target, corners, free kicks, possession), ratings and the
man of the match. Goals per match come out at the original's watched rate (about 2.0), not the quick
engine's 1.32. Tactic elements 1, 5 and 6 already matter, through the exact line sums. Missing until
W5 and W6: fouls, cards, injuries, substitutions during play, and the effect of the other tactics.
The quick result `R` stays the vendored seed-exact engine.

A complete watched friendly (with cards, injuries, substitutions at stoppages and all eight
tactics) exists after W6, about 27 hours. Competitive fixtures can use it after W8.

## 6. How it is tuned later

**The knobs** `[designed]`: about twenty, each with one main row it moves:

| knob | moves mainly | starting value from |
| --- | --- | --- |
| chances per minute per side (scales the quick engine's 12 attempts) | goals, shots | goals 1.98 (C-MATCH-27) |
| contest weights c1/c2/c3 | goal spread; how much the stronger side wins | quick-engine structure; A3 |
| shot on target share; save duel scale (the `5B36` formula kept) | on target, saves | E026 baseline |
| block → corner share; wide → goal kick | corners | E026 |
| offside per attack, and with the offside trap | free kicks, offsides | E026 element 7 |
| foul share of lost contests, by tackling element | fouls, free kicks | F027, E026 element 4 |
| booking, sending off and injury per foul | cards, injuries | C-MATCH-27, F027 |
| possession bar from the midfield contest; keep ball / quick pass shift | possession | E026 element 2 |
| eight tactic modifiers, each with a bound | the arms sheet | E026 |
| home-side flag | home results | exact (`[confirmed: C-MATCH-32]`) as the quick engine has it |
| commentary density | nothing measured (cosmetic) | taste |

**Seeing the effect of a change** `[designed]`:
- `python -m goal2.tune sheet --set chances=1.3`: every row with target, interval, before and
  after, red or green, in under a minute.
- `python -m goal2.tune match --seed 42 [--set ...]`: one match's event stream, before and after,
  for a reader; the same seed replays in the browser.
- `--arms`: the tactic and condition effects table, for the bot.
- A tuning PR carries the sheet diff in its body. The pinned goldens change only in such a PR, which
  says so. A knob outside its target is allowed only with the owner's word, recorded beside the knob.

**Stop rule** `[designed]`: tuning ends when every row is green. More tuning needs a new target,
for example the owner's taste or a new measurement of the original, not more matches.

## 7. Risks

| # | risk | how likely, how bad | what we do |
| --- | --- | --- | --- |
| R1 | **The engine plays like the quick engine with a story**: its sensitivity to skill, form and tactics is the quick engine's rescaled, not the watched engine's. The bot learns that model. | likely; matters for the bot, less for a player | A3 below; one optional measurement of the original (two strength arms, about 200 matches, about 37 CPU minutes on the harness, asked of goal2-archaeology); the seam lets route C replace the engine later without touching the game or the bot's interface |
| R2 | **The targets are thin**: the board statistics come from one team pair (30 matches), and nothing measured is competitive (C-MATCH-27 is friendlies only) | certain; moderate | check totals against the 100 random new games; treat one-pair rows as loose; competitive rows assumed equal to friendlies (A4) until a measurement exists. The board's fouls (about 3.3 a match in E026's baseline) and F027's 3-3.5 a half do not obviously count the same thing; W5 states which one it targets |
| R3 | **Designed tactic effects mislead**: in the original no element moves goals detectably at 30 matches per arm `[derived: F026]`. A designed modifier can create an effect that does not exist, or miss one that does | moderate | bound each modifier by E026's interval; no element may move goals more than E026's upper bound; the owner can widen it as a game choice, recorded as such |
| R4 | **The owner finds a match without moving players unsatisfying** | unknown; this is a question of taste | ask before W3 (decision D2); if moving players are wanted, take route C or D for them, not P |
| R5 | **Calibration does not converge** because knobs interact (goals and shots share the chance rate) | low with the decoupled design; it would cost W7's high end | the stop rule; at most two rounds of tuning per task, then the gap is recorded and goes to the owner |
| R6 | **Conflicts with the campaign backlog** (T42-T44 energy, recovery and confidence; T51 competitive results) | moderate | the event stream feeds those seams; W1's Done-when keeps the existing callers; W8 waits for T51's competitive path or ships behind it |

## 8. What I assume

| # | assumption | why not measured | what replaces it |
| --- | --- | --- | --- |
| A1 | a Claude implementer works at goal2's recorded pace; one OpenCode review per task, about 1.25 rounds on average | it is the project's own history | the first two tasks' actual hours |
| A2 | the event engine runs at 0.02-0.08 s per match in Python | the engine does not exist; the measured anchor is the vendored quick engine (section 9) | W2's own timing |
| A3 | the watched engine rewards a stronger, fitter side about as the quick engine does (C-MATCH-16), scaled to the watched goal rate | measuring it on the original costs about 37 CPU minutes and a harness session upstream; worth it before the bot relies on it, not before playable | the optional W7 measurement |
| A4 | competitive matches have the friendlies' rates, except for the substitution budget and the deciders | no competitive watched sample exists (C-MATCH-27's "Next") | a measurement, if goal2-archaeology takes Q029/Q033 |
| A5 | the first half plays like the second (A-MATCH-1) and kick-off alternates as in the quick engine | already assumed in goal2 | unchanged |
| A6 | the owner accepts designed rules for how a watched match plays, tagged and registered | the plan currently says the opposite (D1 below) | the owner's answer |
| A7 | showing no player positions is acceptable for the first playable version | the browser roadmap already says not to invent ball positions | the owner's answer (D2) |

## 9. Measured for this estimate

One measurement, from a goal2 checkout whose `.cache/` holds the E010 state (no run of the original):

```text
$ python3 -B -c "import sys,time; sys.path.insert(0,'goal2/engine')
  from goal2.engine.savestate import Savestate; from goal2.engine.quick_engine import simulate
  b=open('.cache/e010-r0001-halftime.sav','rb').read(); t=time.process_time()
  [simulate(Savestate(b)) for _ in range(40)]; print((time.process_time()-t)/40)"
0.0253      # CPU s per second half: vendored quick engine, the real E010-r0001 half-time state
$ # the same timing over goal2.game.quick_match.run_full_match on the synthetic state of
$ # goal2/tests/test_full_match.py (seeds 0x1000 + 97k, k < 50)
0.0046      # CPU s per whole friendly; the synthetic squads score no goals, so this is a floor
```

So a whole quick match on real squads costs about 0.05 CPU s, including a savestate parse for each
half. The event engine adds an event layer on top, hence the assumed 0.02-0.08 s (A2), against
8.3-16.8 CPU s for the original's code in the harness `[derived: PR 243, E032]`.

## 10. Against the other routes, in one table

| | **E. close-enough event engine (this)** | **C. exact port** (PR 243) | **D. the original's code as the engine** (PR 243; #99 estimates it in full) |
| --- | --- | --- | --- |
| engine effort | 26 h (18-47) | 49.5 h (29.8-89.1); the issue's 40 h is an earlier figure | about 7 h in PR 243; see #99 |
| goal2 integration (seam, browser, write-back) | 8 h (6-12), included in the 34 | not included; about the same 8 h assumed | not included; about the same assumed, plus fetching the original at run time |
| review rounds | about 10 | eight tasks, one review each in the plan | see #99 |
| first playable watched match | about 15 h | after P6 (P0-P6: 43.1 h) plus integration, or through D | about 7 h plus integration |
| fidelity | distributions inside the original's intervals; not seed-exact; designed rules tagged | exact where seed families reach, a measured distance elsewhere | exact |
| speed per match | about 0.05 s (assumed) | unknown until P6 | 8.3-16.8 CPU s |
| needs the original at run time | no | no (after P6) | yes (`GOAL.EXE` from a private release) |
| tunable | by design: knobs and a sheet | only by changing ported code, which ends exactness | no |
| player positions on screen | none | exact | exact |
| what the bot learns | this model's rules | the original's rules | the original's rules, slowly |

The routes do not exclude each other `[designed]`. W1's seam takes any of them, and W4's sheet can
measure any of them against the original's targets. A path that keeps all options open: E for
playing and for the bot's fast search now, then C later as a "faithful" engine behind the same
seam, if the owner wants positions or exactness.

## 11. Decisions for the owner (rule 13)

- **D1.** goal2's plan says "Nothing about how a watched match plays is invented" (`docs/plan.md`,
  decision 2). The close-enough route invents by definition. Taking it amends that decision: designed
  rules tagged `[designed]`, one register row each, replaced if exact evidence arrives.
- **D2.** Is a watched match without moving players (commentary, board, momentum strip) acceptable
  as the first playable version? The browser roadmap already forbids invented ball positions, and
  this route keeps to that.
- **D3.** What "close enough" means: I propose section 1's rows, inside the original's 95%
  intervals. A looser or tighter target changes W7's hours, not the build.
- **D4.** Whether to pay for the one optional measurement of the original (A3, about 37 CPU
  minutes upstream) before the bot relies on the engine's strength curve.
