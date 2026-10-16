# Campaign confidence and displayed morale

[derived: F019/F020, goal2-archaeology
`0ef880e1f6ec9bc12b3f12c3aaecb4d747d9d5cb`] Player confidence is byte +0x0C.
The byte-copy `engine/confidence.py` supplies country-rank expectation, result
terms and independently clipped participant/bench updates. `engine/morale.py`
supplies the original panel arithmetic. These findings are proposed static
readings, with isolated B7FA probes and a signed-edge panel corroboration;
they do not establish complete played-fixture or full campaign parity.

[derived: F019, 1771:10E7/B71C] Country rating is signed truncation toward zero
of `((5-continent)*(33-continent_rank)+129-world_rank)/2`. The result term
starts with signed `(opponent_rating-own_rating)/32`, then uses signed score
margin, winner and the source fixture-kind predicate for doubling. A draw can
have a nonzero term; a win can reduce confidence against a sufficiently weak
opponent. Player ability and quick line-strength sums are not the expectation.
[derived: F019 and T39/F023 calendar mapping] The active scheduled friendly is
kind1, outside DS:0F3E. Read its membership from the local source image rather
than guessing a generic friendly/competitive boolean. No original table is
committed. Future competition fixtures remain refused by the campaign boundary.

[derived: F019/F020, F1F6/7CC5/CB7D] Before the quick match, snapshot both squads'
confidence. Wrap the vendored scorer method: its actual flag-one write updates
the snapshot using the signed new live value, capped above at32. Ordinary team
reactions stay live during play but do not update the snapshot. Restore the
snapshot before post-fixture updates. A scorer affected by earlier temporary
reactions therefore preserves its actual event-ordered value; replaying only
final score or goal totals would lose this information. No synthetic injury,
card or extra scorer bonus is applied. Standalone friendlies keep their prior
carryover path. The original watched-result publisher must never call this
Python quick-only adapter over original returned state.

[derived: F019/F018, B7FA] Traverse sideA then sideB, nonzero squad words in
slot order. Slots1..11 and status-set element3 (one-based mask0x04) participate.
Participants recover energy first, then receive the result term clipped1..32.
A participating bench player also receives a second independently clipped
`rand(2)-rand(2)` confidence delta (subtracted draw first) and consumes element3.
Unused bench receives `rand(2)-rand(4)` instead of the result term, before its
energy recovery. This interleaving advances the same main RNG used by play;
the second RNG retains its engine meaning. The focused real fixture consumes
60 recovery draws plus36 bench-confidence draws after play. Literal tests
check both roles, independent clipping and adjacent set elements.

[derived: F020, 1771:13D0/3216/214B:0C57] Displayed team morale is recomputed
from available confirmed starters: `max(1, ((6+sum(min(32,s8(C)))) &65535)//11)`.
Availability requires signed-positive energy and clear status-set elements8/6/3
(masks0x80/0x20/0x04). The divisor stays11 when fewer starters are available.
There is no lower clamp on each contribution: signed byte128 contributes-128,
so the recorded edge `[128,0,...,0]` returns5946. A booking alone (element5)
is not the availability gate. This transient aggregate is neither a stored
country morale byte nor the separate sacking confidence sum.

[designed: T43] Browser management shows each player's confidence and the
confirmed XI's morale; the result card shows the same derived morale. Editing
a browser draft changes no persistent confidence or confirmed team aggregate.
The existing detached candidate publishes records, final RNG, result/history
and transition marker together. Exceptions discard the candidate; duplicate
Play is refused. Reads, Save and Load do not update confidence. Saved and
uninterrupted two-fixture continuations compare complete state.

[designed: T43 scope] Current campaigns use base20 squads. The separate managed
national-pool route and its overlapping confidence/recovery draws remain T45;
T44 now applies current-squad B27F and availability gates; competitive event
production remains T51. The energy-only public adapter
can still run without confidence; the campaign quick runner requests the joint
ordered path. No whole original fixture-tail RNG parity is claimed. The saved
`campaign_energy` marker retains its earlier fields and adds `confidence_draws`.

```sh
python3 -m unittest goal2.tests.test_campaign_confidence -v
python3 tools/browser-ui/prove-campaign-confidence.py
```

[designed: T45] The disjoint eighty-reserve BA4E prefix now runs before the current
squad operations described above. See [campaign-pool.md](campaign-pool.md) for
ordered recovery/confidence/status calls, save membership and remaining boundaries.
Standalone friendlies and original watched-result publication do not run this prefix.
