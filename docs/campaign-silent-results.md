# Other countries’ scheduled results

[derived: proposed F023/F024 at archaeology
`0ef880e1f6ec9bc12b3f12c3aaecb4d747d9d5cb`; designed: T48]
Fresh campaigns retain the full opening schedule (768 stage-2 rows or640 stage-5
rows), alongside the managed fixture projection. Each immutable row retains its
original fixture ID, ordered A/B countries, kind and source draw-round number.
The full result ledger is a source-order prefix, including both unattended and
managed matches. Existing managed-only history remains the public management API.

[designed] One atomic playable turn resolves the CPU rows before the next
supported managed match, plays that match, then resolves CPU rows until the next
managed fixture. A source draw round may contain two managed fixtures: country4
in the stage-5 example has original:1471 friendly and original:1475 qualifier in
round2. Consequently a playable turn is not a claim of a whole source draw round.
The unsupported managed competitive boundary is preserved. No CPU row involving
the managed country goes through the unattended resolver.

[derived: F024 §4] Original unattended scoring uses one B19D(12) count batch,
not92 D733 ticks. Each team has12 attempts to win the midfield, attack/defence and
attack/keeper contests. The vendored count primitive and line sums are reused.
Tied kinds4 and8..203 add B19D(4); if still tied, the original primary-stream coin
sets the winner code without changing the score. [derived: 214B:06FA] The coin
is1 when rand(2)==1 and0 otherwise. Friendly/ordinary draws keep winner code2.

[designed; derived: T46] Team setup is a stand-in: available top-ability eleven,
stored tactics, original manager/position tables and zero unknown host bonus.
The original B11F/34E7/BD83 setup, CPU post-fixture player recovery/confidence and
scorer attribution are not integrated. This is not complete original D47E or
fixture-tail fidelity. No full quick match is run for an unattended fixture.
The adapter is replaceable independently of the round coordinator.

[derived: F004; designed] Every result stores its primary RNG seed before/after
and exact draw count. CPU prefix, managed engine and CPU suffix share that stream
in source fixture order. The second stream remains untouched by silent scoring.
The saved live primary seed is the end of the committed full-world prefix; the
managed last-match summary retains that match’s own ending seed. They can differ
because CPU fixtures run afterward. Affine LCG step validation checks the saved
seed chain without simulating matches again.

[designed] Preparation and completion work on private deep copies. CPU failure,
invalid output, stale worker or view failure cannot publish partial results,
RNG changes or a managed result alone. All results become authoritative together
through the existing desktop/browser candidate boundary. Full-time save/resume
stores the schedule and results explicitly; loading does not redraw/regenerate
the schedule. Duplicate/out-of-order IDs, changed endpoints, scores or RNG links
are rejected. Pending-match saves remain refused by T47.

[designed: compatibility] Older saves without world metadata retain their
managed-only behavior and byte shape. No schedule is guessed for an old save.
The pre-T47 full-state hash oracle explicitly uses this legacy case; new tests
compare complete full-world uninterrupted, halftime-split and resumed games.
Competition-table display is T49; later stage builders remain separate work.

```sh
python3 -m unittest goal2.tests.test_campaign_silent_results -v
python3 tools/prove_campaign_silent_results.py
```
