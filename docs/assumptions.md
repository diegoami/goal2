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

## The match

| Id | Rule | Source | Live | Replaced by |
| --- | --- | --- | --- | --- |
| A-MATCH-0 | The quick engine: 46 `D733` minutes per half, 12 attempts per team per minute, each won by three contests (midfield, attack against twice the defence, attack against the keeper); line strength from ability, energy and form, halved on the wrong foot, plus the manager bonus | finding F012 (seed-exact 10/10) | vendored `quick_engine.py` (P0) | — |
| A-MATCH-1 | The first half runs as the second (the model covers the second half only), from a kick-off state the adapter builds | assumed: F012 says 46 per half; the kick-off itself is unread | — (P2) | a whole recorded quick match; goal2-archaeology's quick engine from kick-off |
| A-MATCH-2 | Competitive fixtures: no fouls, bookings or sendings off in the quick engine (the model refuses the foul path); every competitive match plays as a friendly | assumed: the foul path `D5C1`/`7EEF` is not modelled | — (P2) | goal2-archaeology's foul path in the quick engine |
| A-MATCH-3 | A drawn knockout goes to a coin toss | assumed: extra time and penalties are not modelled; the help file says extra time, then 5 penalties each, then sudden death | — (P5) | goal2-archaeology's extra time and penalties (F015's shoot-out ranks takers already) |
| A-MATCH-4 | Energy and form set a player's strength; fitness is never read in a match | finding F021 | vendored `condition.py` (P4) | — |
| A-MATCH-5 | Home advantage: none | assumed: the help file says it exists; Q028 is open | — (P5) | Q028 |
| A-WATCH-1 | The watched match is the quick engine's result shown with commentary lines (goals, scorers, minutes), labelled a stand-in | owner decision (goal2 #2) | — (P3) | goal2-archaeology M1–M6, the watched engine |
| A-MATCH-6 | Performance ratings start at 55 and move per commentary event (goal +40, own goal −50, booked −20, sent off −100, wins the ball +20, tackle −10); the man of the match is the best of the eleven, first in order on a tie; a quick result shows none | finding F014 | — (P3, stand-in commentary only) | the watched engine |

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
| A-CPU-2 | The computer's tactics: its country's stored set; it changes tactics when more than 2 goals behind | finding F021's note (`230C`/`20E3`) for the change; assumed for what it changes to | — (P3) | Q035 |
| A-CPU-3 | Computer squads change only by retirement and re-creation | finding F017; assumed that nothing else changes them | — (P5) | Q036 |

## The game around it

| Id | Rule | Source | Live | Replaced by |
| --- | --- | --- | --- | --- |
| GA-1 | No sacking, no end of game: the cycle repeats until the managers stop | assumed: the owner was never sacked (B4); the backlog lists sacking as a placeholder | — (P5) | a backlog question on sacking |
| GA-2 | Up to 6 human managers in one game | finding F011 (6 pools); owner B7 | — (P7) | — |
| GA-3 | Replays of goals are off by default (the owner finds them an annoyance) | owner B5 | — (P6) | — |
| GA-4 | Keys: the arrows set match speed, Y skips a replay, C is the computer's choice, Esc goes back | owner B6; goal2-archaeology `static/screens/catalogue.tsv` | — (P3, P6) | — |
