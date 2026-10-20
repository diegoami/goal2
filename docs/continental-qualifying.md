# Continental qualifying

[derived: F023 §§3–4 and §8, goal2-archaeology `3656a2d26e0f57a410d648edeaa6cd9eb7d1f607`]
A campaign that starts in a year divisible by four opens at stage 2, the continental
qualifying groups (F025 §2, P8: 1992, 1996, 2000). Stage 2 draws 32 groups of four, eight per
continent, from four rank pots ([campaign state](campaign-state.md), T41a). Each group is a
double round robin of kind-2 fixtures: twelve per group, every pair twice, once in each A/B
order, interleaved with kind-1 inter-group friendlies. Every country plays six of each. The
A table is re-sorted after every stage-2 fixture ([competition tables](campaign-standings.md)),
so once the stage has been played slot 1 of each group is its winner. The eight group winners
of a continent are its qualifiers for the stage-3 finals (F023 §4).

[designed: T50] `goal2.game.continental_qualifying.outcome` reads that result from the
persisted world schedule and results. `standings.opening_groups` recovers all 32 groups from
the saved rows and the pinned pair table, so a resumed game never draws again, and no RNG is
used. Qualifiers exist only once every one of the stage's 768 scheduled fixtures has a result;
before that, positions are provisional. The managed country is `in progress`, `qualified`
(its group's winner) or `eliminated`. It plays all six group fixtures whatever its position:
after its last fixture the remaining world fixtures resolve silently
([silent results](campaign-silent-results.md)), the stage is complete and the outcome is final.

[designed: owner, 2026-10-20, T50] The desktop's New campaign has a **Start year** choice:
1990 (the default; World Cup qualifying, stage 5, first) or 1992 (continental qualifying,
stage 2, first). The choice is a draft until New campaign is pressed. The Fixtures page shows a
**Continental qualifying** card: the managed country's continent and group, its status, and,
once the stage is complete, the 32 finalists by continent. A finished stage disables Play
with "this stage is complete; the next stage is not available yet": the stage-3 finals
(hosts, finals groups and fixtures) are T52's, so the campaign stops at the end of stage 2
until that builder exists. Managing, saving and resuming stay available.

[designed] Check it with `python3 -m unittest goal2.tests.test_campaign_continental_qualifying -v`
(synthetic bounded results, about 5 s) and, with the desktop and watched extras,
`python3 tools/desktop-ui/acceptance.py --scenario continental-qualifying --template .cache/e010-r0008-halftime.sav --data .cache/GOAL.DAT`,
which plays two whole managed stages through the real window (one to qualification, one to
elimination, six original competitive matches each, save/resume mid-group).
