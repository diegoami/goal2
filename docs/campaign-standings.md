# Competition tables

[derived: archaeology F023 §8 at `3656a2d26e0f57a410d648edeaa6cd9eb7d1f607`]
`goal2.game.standings.group_table` reads explicit source slots, fixture order and
completed results. Only played fixtures of the requested group-stage kind count.
Points are two for a win, one for a draw, zero for a loss. Goals and points retain
the original byte arithmetic. Sort keys are points, goal difference and goals
scored; there is no coin or country-ID key.

[derived: same F023 §8, 1771:8476–85F1] The original swaps a slot with any later
strictly better slot, repeating this exchange sort after each played fixture.
It is not a stable sort: a stronger team can indirectly reverse two equal teams.
The adapter processes source fixture order and preserves those earlier exchanges
when later keys tie. Reversing the result-list container changes neither scores
nor ordering. Duplicate fixture IDs/results, wrong endpoints and malformed played
scores are rejected. The caller supplies four stable country identities and the
number of provisional progressing positions; table reads do not draw RNG or
advance the campaign.

[derived: F023 §§3–4/7; designed: T49] In the desktop, **Competition table** opens
the managed country's opening qualifying group with P/W/D/L, goals for/against,
goal difference, points and progression markers. Source stage-2/5 group slots are
recovered from the saved full twelve-round fixture schedule and the pinned pair
table, without recreating a draw or changing the save format. Stage 2 supplies
one progressing group winner. Stage 5 supplies two European places, one American
place, and an African/Asian winner leading to a playoff. Positions are labelled
provisional; a table position alone does not claim qualification is clinched.

[designed] The dialog is a read-only snapshot and closes when the main game
refreshes. Standalone and legacy sessions without a complete opening schedule
report the table unavailable. Later final-stage builders may pass their explicit
slots to the backend; T49 does not create those stages or run competitive matches.
Its code mapping remains a reconstruction from the static listing, not a measured
original campaign-table replay.

[designed] Verify backend behavior with
`python3 -m unittest goal2.tests.test_campaign_standings -v`.
With the desktop extra installed, run
`QT_QPA_PLATFORM=offscreen python3 tools/desktop-ui/standings.py --template .cache/e010-r0008-halftime.sav --data .cache/GOAL.DAT`.
The smoke uses an explicit result fixture with equal points/GD and decisive goals
scored, checks the real button/dialog and named country IDs, matches backend
qualifiers, and proves reads leave the full state/RNG unchanged.
