# The assumption register

Every rule the rebuild plays by, and where it comes from. [`plan.md`](plan.md) says how it is used.

**Source tags**
- `finding`: a goal2-archaeology finding (F-number). All are `proposed` as of `d6ad065`; a vendored
  model is also held to its own seed-exact check.
- `owner`: the owner's answer (goal2-archaeology `experiments/E015-human-playthrough/owner-questions-2026-10-11.md`, or an issue here).
- `help file`: GOAL.HLP, quoted in goal2-archaeology `sources/goal-hlp.md` (passage `P<nn>`). It is
  the game's documentation, not its code: it loses to a finding.
- A run record cited without a finding says so; it counts like `finding` until one is written.
- `assumed`: our guess. Each one says why, and what replaces it (a goal2-archaeology question or
  milestone).

A row changes in the PR that changes its rule. Its **Live** column names the implementation the
code runs now.

## New game and data

| Id | Rule | Source | Live | Replaced by |
| --- | --- | --- | --- | --- |
| NG-1 | `GOAL.DAT`'s blocks: 128 countries, 3,060 surnames and initials, 128 managers, 3 values and 1 tactics byte per country, two country permutations, a 20-entry squad table per country; no skills stored | finding F002 | — (P1) | — |
| NG-2 | The RNG: `seed = seed·0x7ABD + 0x1B0F` (16-bit), `rand(n) = hi16(seed·n) + 1`; a new game seeded from the DOS hour·256 + minute | finding F004 | vendored LCG (P0) | — |
| NG-3 | Players are made per country from a seed of the country's number, not the clock: age, peak, potential = rating(c) + 0x7F, ability, profile, position, tactic bits; rating(c) = ((5 − continent)(33 − continent rank) + (129 − world rank)) idiv 2 | finding F007 | — (P1) | — |
| NG-4 | The 12 skills are derived, not stored: skill = table[profile, position, i] · (ability + 1) div 256; "kicking" and "goal kicking" are one | finding F008 | — (P1) | — |
| NG-5 | Peak age at creation: 25–29 outfield, 28–32 keepers | finding F016 | — (P1) | — |
| NG-6 | The new game's start date (the DOS year) only seeds and labels; the first stage is the first year's friendlies | assumed: F004 names the year an input but not its use beyond the seed | — (P5) | Q030 |

## Squad and team

| Id | Rule | Source | Live | Replaced by |
| --- | --- | --- | --- | --- |
| SQ-1 | A squad of 20; a pool of 80 more per manager, both sorted by position | finding F011 (the help file says "the 100 best": code wins) | — (P3) | — |
| SQ-2 | Team tactics: 8 elements per country (push forward, quick pass, long passes, go in hard, full pitch, stand ground, offside trap, man-to-man); a player's tactic bits override elements 1–4 | finding F010 | — (P3) | — |
| SQ-3 | The squad changes only between fixtures, never in finals or on tour | help file | — (P3) | Q008 |
| SQ-4 | Picks come from the national pool only; there are no transfers between countries | owner B2, C7 | — (P3) | — |
| SQ-5 | The stored eleven, substitutes included, starts the next match | goal2-archaeology run record E015-r0010, no finding yet (owner A3 thought otherwise; the record wins) | — (P3) | — |
| SQ-6 | No training or fitness choice; recovery is automatic | owner B3 | — (P4) | — |
| SQ-7 | The squad screen starts from a valid existing eleven or the first eleven, lets the user draft any 11 squad members, keeps their squad order, and accepts only an included captain; edits commit on valid Enter | [designed: owner authorization T28] | `goal2/ui/squad.py` | — |

## The match

| Id | Rule | Source | Live | Replaced by |
| --- | --- | --- | --- | --- |
| A-MATCH-0 | The quick engine: 46 `D733` minutes per half, 12 attempts per team per minute, each won by three contests (midfield, attack against twice the defence, attack against the keeper); line strength from ability, energy and form, halved on the wrong foot, plus the manager bonus | finding F012 (seed-exact 10/10) | vendored `quick_engine.py` (P0) | — |
| A-MATCH-1 | A complete friendly uses one mutable quick-engine instance for 92 `D733` calls: minutes 0..45 then 46..91, each with countdown `91 − minute`; it starts at 0–0 with the selected country/eleven/tactics and a template opponent. The template's player energy is retained, while the original setup and half-time recovery are omitted. | confirmed timing and opposite kick-off sides: goal2-archaeology E010-q010-quick-engine `notes.md`, "Match clock & loop" at 1b694ed; assumed initial setup and first-half fidelity | `goal2.game.quick_match` (T26); T08 only proves independent second-half replay | a whole recorded quick match with a kick-off state; goal2-archaeology's quick engine from kick-off |
| A-MATCH-2 | Competitive fixtures: no fouls, bookings or sendings off in the quick engine (the model refuses the foul path); every competitive match plays as a friendly | assumed: the foul path `D5C1`/`7EEF` is not modelled | — (P2) | goal2-archaeology's foul path in the quick engine |
| A-MATCH-3 | A drawn knockout goes to a coin toss | assumed: extra time and penalties are not modelled; the help file says extra time, then 5 penalties each, then sudden death | — (P5) | goal2-archaeology's extra time and penalties (F015's shoot-out ranks takers already) |
| A-MATCH-4 | Energy and form set a player's strength; fitness is never read in a match | finding F021 | vendored `condition.py` (P4) | — |
| A-MATCH-5 | Home advantage: none | assumed: the help file says it exists; Q028 is open | — (P5) | Q028 |
| A-WATCH-1 | The watched match is the quick engine's result shown with commentary lines (goals, scorers, minutes), labelled a stand-in | owner decision (goal2 #2) | `goal2.ui.result` (T26 assumed full friendly) | goal2-archaeology M1–M6, the watched engine |
| A-MATCH-6 | Performance ratings start at 55 and move per commentary event (goal +40, own goal −50, booked −20, sent off −100, wins the ball +20, tackle −10); the man of the match is the best of the eleven, first in order on a tie; a quick result shows none | finding F014 | — (P3, stand-in commentary only) | the watched engine |
| A-WATCH-2 | In a watched match a substitution is requested while play runs and carried out only when the game stops (outside half time); an injury (Signori, Italy) also raises a request. The owner substituted in the same sitting at half time, at a stoppage and after an injury | owner, sitting 20261015-070348 (run E015-r0013, notes at 05:25-05:48Z); no finding | — (P4) | goal2-archaeology: Q037 (issue #146) and a watched-match question; not measured by a method yet |
| A-WATCH-3 | Offside is called often in a watched match, also against the team that is not attacking: Italy attacking (Causio's run), offside called against Portugal (Domingos). A goal can be disallowed for a team-mate's offside: "Goal by Lentini, Schillaci is offside" (commentary text, scrolled back) | owner, sitting 20261015-070348 (E015-r0013); the commentary line is the owner's reading, no finding | none: the stand-in has no offside | goal2-archaeology: a static question on which team the offside check applies to (the code of `GOAL.EXE`), then a finding |
| A-WATCH-4 | A sending off happens in a watched match (Portugal's T Oceano, red card, shown on the match statistics screen); Portugal then played with ten. The match type (friendly or competitive) was not recorded | owner, sitting 20261015-070348 (E015-r0013); not a finding | none (see A-MATCH-2) | goal2-archaeology: the foul path `D5C1`/`7EEF` and the match type of that sitting |

## Between matches

| Id | Rule | Source | Live | Replaced by |
| --- | --- | --- | --- | --- |
| BM-1 | Energy: quick matches cost each player 1 every 5 minutes (while above 1), +2 at a half's start for 1–30; after a match fitness is copied to energy if energy > 0; energy 0 means injured | finding F018 | vendored `energy.py` (P4) | — |
| BM-2 | Recovery between fixtures draws from the RNG, capped | finding F018 (draw-dependent `3651`) | vendored `energy.py` (P4) | — |
| BM-3 | Confidence (1–32) after a result: margin against the expected margin from the ratings; the bench moves too | finding F019 | vendored `confidence.py` (P4) | — |
| BM-4 | Which fixture kind counts as a friendly in the confidence rules: every friendly is the kind without doubling | assumed: F019/F020 leave it open | — (P4) | Q016/Q017 follow-up |
| BM-5 | Events: sent off −2 (the other side +2), injury −2 and energy 0, a booking no change; team morale = (Σ min(32, form) over the eleven + 6) / 11, at least 1, display only | finding F020 | vendored `morale.py` (P4) | — |
| BM-6 | An injured or suspended player misses matches: an injury lasts until energy recovers above 0; a sending off suspends for the next fixture | owner C3 (that they miss); assumed (how long) | — (P4) | Q033 |
| BM-7 | Substitutions: 5 per match, a substituted player stays off | owner C2 (the help file says 2 in competition, 5 in friendlies) | — (P4) | Q034 |

## The cycle and the other countries

| Id | Rule | Source | Live | Replaced by |
| --- | --- | --- | --- | --- |
| A-COMP-1 | 4 continents of 32; the 4-year cycle: Y1 friendlies and championship qualifying; Y2 friendlies and championship finals; Y3 friendlies and World Cup qualifying; Y4 tours and World Cup finals | help file | — (P5) | Q030 |
| A-COMP-2 | Championship: qualifying in 8 groups of 4, two legs, group winners through; finals in 2 groups of 4, top two to the semi-finals, then a 3rd-place match and the final | help file | — (P5) | Q030 |
| A-COMP-3 | World Cup: 32 places (Europe 16, America 8, Africa 4, Asia 4); qualifying in 8 groups of 4 per continent (Europe's top two, America's winners; Africa's and Asia's winners in two-leg play-offs, a coin on a tie); finals in 8 groups of 4, top two to the last 16 | help file | — (P5) | Q030 |
| A-COMP-4 | Group ties: points, goal difference, goals scored, then a coin | help file | — (P5) | Q031 |
| A-COMP-5 | The draw: groups seeded by world rank, the rest by the LCG; the host chosen by the LCG among the qualifiers | assumed: the help file says the host is chosen after qualifying, not how | — (P5) | Q031 |
| A-COMP-6 | Matches between two computer countries are decided by the quick engine | assumed: F021 notes `D47E` uses `0BC4` + `B19D(12)` for unplayed fixtures, not yet a model | — (P5) | Q032 |
| A-COMP-7 | Rankings recomputed at stages 2 and 5 from points; placing bonuses 800/600/400/200 and 200 per knockout fixture | finding F017 §7 | vendored `recreate.py` where it covers it (P5) | Q020 |
| A-COMP-8 | Ageing at stage entry 2, 3, 5 and 7 (4 per cycle); ability at its best from peak − 1 to peak + 3, rising before, falling after | finding F016 | vendored `ageing.py` (P5) | — |
| A-COMP-9 | Retirements: a computer country's player retires past 30 (33 for keepers) with no caps, or past peak + 5, and is re-created in place; a managed country loses one at a time between fixtures; results feed new talent through points, ranks and rating | finding F017 | vendored `recreate.py` (P5) | — |
| A-CPU-1 | The computer's eleven: the best-rated player per position of the country's formation, fit players only | assumed: Q035 is open; the owner's `C` key is the game's own choice | — (P3) | Q035 |
| A-CPU-2 | The computer's tactics: its country's stored set; it changes tactics when more than 2 goals behind | the read side [confirmed: F010]; the change side [confirmed: F028 (E028) and the vendored quick_engine at 8760df9: C01A behind by more than 2 — five rand(5) includes + element 6 through BBFF, once per stretch (DS:8332), then the BEC7 re-place and the 230C re-sort; C0DF the mirror when ahead (DS:8334); BF6B at margin exactly 2; BD83's reset to the R008 default below 2; managed sides skipped] — pinned by T22's `test_cpu_tactics_change` (C01A/C0DF/BF6B/BD83 once each; the BEC7 matrix covers the slot-9 gate in C01A, the unavailable-skip in BEC7, the +0x46 and +0x54 height contributions, and the 230C re-sort, each in a parameterised test); the model is not seed-exact on this path (F021: the E020 halves never reached 230C) | — (P3) | Q035; cross-fixture persistence: the original keeps the changed +0x2D byte in memory between fixtures while the rebuild reloads the same savestate per fixture — moot until P5's fixture loop, then needs evidence on whether the original resets tactics at match setup |
| A-CPU-3 | Computer squads change only by retirement and re-creation | finding F017; assumed that nothing else changes them | — (P5) | Q036 |

## The game around it

| Id | Rule | Source | Live | Replaced by |
| --- | --- | --- | --- | --- |
| GA-1 | No sacking, no end of game: the cycle repeats until the managers stop | assumed: the owner was never sacked (B4); the backlog lists sacking as a placeholder | — (P5) | a backlog question on sacking |
| GA-2 | Up to 6 human managers in one game | finding F011 (6 pools); owner B7 | — (P7) | — |
| GA-3 | Replays of goals are off by default (the owner finds them an annoyance) | owner B5 | — (P6) | — |
| GA-4 | Keys: the arrows set match speed, Y shows a replay and N skips it (corrected by the owner, 2026-10-15; the row said Y skips), C is the computer's choice, Esc goes back | owner B6; goal2-archaeology `static/screens/catalogue.tsv` | — (P3, P6) | — see GA-5, GA-6 |
| GA-5 | Prompts around a match, each of which times out when no key is pressed (the owner's estimate for the replay prompt: about 2 s; not measured): before the match, "really watch it?" (Y/N), the captain, and who takes the goal kick (C = the computer chooses; the goal-kick prompt timeout confirmed); after a goal, "replay?" (offered for either team's goals; Y shows it, no key shows none); after a replay, "save the goal?" (Y/N; saved as a `.HIL` file in the game folder); at the end of the game, "save the match summary to disk?" (also times out). A saved game is a `.GL` file | owner, sitting 20261015-070348 (E015-r0013); the `.HIL`/`.GL` files seen in the session's game folder; no finding | — (P6) | goal2-archaeology: the screens' code for the time-out length (static), then a finding |
| GA-6 | Match-screen keys: Left/Right set the match speed (moderate speeds keep the commentary readable), R gives the quick result, Space opens a scrollable commentary (PgUp, PgDn, Home, End, Up/Down, the mouse wheel; the list has no line numbers), Up/Down change how players are drawn (four modes: the original, little faces, numbers, the letters A/H; the owner finds A/H pointless), F9 turns the music on and off, Esc or Enter go back to the bench | owner, sitting 20261015-070348 (E015-r0013); extends GA-4 | — (P3, P6) | the catalogue of screens (`static/screens/catalogue.tsv`) |
| GA-7 | Before a match the owner edits the eleven and the tactics: a position change for a player (a sweeper played as centre back; Berti to central midfield, Baggio striker, Bergomi sweeper), per-player tactics for the full backs (push forward), man-to-man marking assignments per player (fewer players marked after a change; default marking otherwise), the team tactics (full or half pitch, stand ground, offside trap, push forward, quick or short passes, go in hard), and the formation (4-4-2) | owner, sitting 20261015-070348 (E015-r0013, r0017); extends A-CPU-1 and A-CPU-2 | — (P3) | goal2-archaeology: the tactic and marking bytes in the sitting's snapshots (R008 and the squad slots) |
